package io.deephaven.engine.table.impl;

import io.deephaven.api.ColumnName;
import io.deephaven.chunk.WritableChunk;
import io.deephaven.chunk.attributes.Values;
import io.deephaven.engine.table.ColumnDefinition;
import io.deephaven.engine.table.impl.remote.RetryStudyHooks.StudyAbortError;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import io.deephaven.engine.context.ExecutionContext;
import io.deephaven.engine.liveness.LivenessScope;
import io.deephaven.engine.liveness.LivenessScopeStack;
import io.deephaven.engine.rowset.RowSetFactory;
import io.deephaven.engine.rowset.RowSetShiftData;
import io.deephaven.engine.table.Table;
import io.deephaven.engine.table.hierarchical.HierarchicalTable;
import io.deephaven.engine.table.hierarchical.TreeTable;
import io.deephaven.engine.table.impl.remote.RetryStudyHooks;
import io.deephaven.engine.updategraph.impl.EventDrivenUpdateGraph;
import io.deephaven.engine.testutil.sources.TestColumnSource;
import io.deephaven.engine.testutil.testcase.RefreshingTableTestCase;
import io.deephaven.test.types.OutOfBandTest;
import io.deephaven.util.SafeCloseable;
import org.junit.Test;
import org.junit.experimental.categories.Category;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

import static io.deephaven.engine.table.impl.sources.ReinterpretUtils.maybeConvertToPrimitiveChunkType;
import static io.deephaven.engine.testutil.TstUtils.i;
import static io.deephaven.engine.testutil.TstUtils.testRefreshingTable;
import static io.deephaven.engine.util.TableTools.byteCol;
import static io.deephaven.engine.util.TableTools.intCol;
import static io.deephaven.util.QueryConstants.NULL_INT;

/** Author-controlled, fixed-structure comparison. All output is exploratory. */
@Category(OutOfBandTest.class)
public class TestRetryEventGraph extends RefreshingTableTestCase {
    private static final int N = 31, M = 3, R = 16, H = 5;
    private static final long[] W = {4, 104};
    private static final String[] POLICIES = {"curve_fast_tie", "local_budget", "upstream2"};
    private static final class Cut {
        final String stage, kind, action;
        final int attempt, threshold;
        Cut(String stage, int attempt, String kind, int threshold, String action) {
            this.stage = stage; this.attempt = attempt; this.kind = kind;
            this.threshold = threshold; this.action = action;
        }
    }
    private static Cut k(int attempt, String kind, int threshold, String action) {
        return new Cut("K", attempt, kind, threshold, action);
    }
    private static Cut v(int attempt, String kind, int threshold, String action) {
        return new Cut("V", attempt, kind, threshold, action);
    }
    private static final Cut[][] SCHEDULES = {
            {},
            {k(1, "K_DIR", 2, "FULL")},
            {v(1, "V_PARENT", 2, "FULL")},
            {v(1, "V_NODE", 4, "FULL")},
            {v(1, "V_CELL", 2, "FULL")},
            {v(1, "END", 1, "FULL")},
            {k(1, "END", 1, "START"), k(2, "END", 1, "COMPLETE")},
            {v(1, "END", 1, "START"), v(2, "END", 1, "COMPLETE")},
            {v(1, "V_NODE", 4, "START"), v(2, "V_NODE", 4, "COMPLETE")},
            {v(1, "END", 1, "START"), v(2, "END", 1, "COMPLETE"),
             v(3, "END", 1, "START"), v(4, "END", 1, "COMPLETE")},
            {k(1, "END", 1, "START"), v(1, "END", 1, "COMPLETE"),
             v(2, "END", 1, "START"), v(3, "END", 1, "COMPLETE")},
            {k(1, "END", 1, "FULL"), v(1, "END", 1, "START"), v(2, "END", 1, "COMPLETE")}
    };
    private static final String[] NAMES = {"none", "k_dir_full", "v_parent_full", "v_node_full", "v_cell_full",
            "v_end_full", "k_end_split", "v_end_split", "v_node_split", "v_two_end_split",
            "cross_stage", "k_full_v_split"};
    private static final int[] Q = {0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2};

    @Test public void testLambdaThree() throws Exception { runMatrix(3); }

    private void runMatrix(int lambda) throws Exception {
        final List<String> failures = new ArrayList<>();
        for (int schedule : new int[] {0, 7, 10, 11}) {
            for (String policy : POLICIES) {
                try {
                    runCase(lambda, schedule, policy);
                } catch (Throwable failure) {
                    failures.add(lambda + ":" + NAMES[schedule] + ":" + policy + ":" + failure);
                }
            }
        }
        assertTrue(failures.toString(), failures.isEmpty());
    }

    private static final class ImportedProfile {
        final java.util.Map<Integer, List<long[]>> pieces = new java.util.HashMap<>();
        final String sha256;
        final long loadNanoseconds;

        ImportedProfile(int expectedLambda) {
            final long started = System.nanoTime();
            try (final java.io.InputStream input = TestRetryEventGraph.class.getResourceAsStream(
                    "/retry-event-import/profile_" + expectedLambda + ".txt")) {
                if (input == null) { throw new IllegalStateException("Missing imported profile"); }
                final byte[] bytes = input.readAllBytes();
                sha256 = java.util.HexFormat.of().formatHex(
                        java.security.MessageDigest.getInstance("SHA-256").digest(bytes));
                final String[] lines = new String(bytes, java.nio.charset.StandardCharsets.UTF_8).split("\n");
                if (!lines[0].equals("RETRY_PROFILE_V1")
                        || !lines[1].equals("lambda " + expectedLambda)
                        || !lines[2].equals("caps 4 104")
                        || !lines[3].matches("certificate [0-9a-f]{64}")) {
                    throw new IllegalStateException("Profile metadata mismatch");
                }
                for (int k = 4; k < lines.length; ++k) {
                    final String[] fields = lines[k].split(" ");
                    if (fields.length != 5 || !fields[0].equals("piece")) {
                        throw new IllegalStateException("Malformed profile piece");
                    }
                    final int mask = Integer.parseInt(fields[1]);
                    final long[] piece = {Long.parseLong(fields[2]), Long.parseLong(fields[3]),
                            Long.parseLong(fields[4])};
                    if (piece[0] < 0 || piece[1] < 0 || piece[2] < 0) {
                        throw new IllegalStateException("Negative profile entry");
                    }
                    pieces.computeIfAbsent(mask, ignored -> new ArrayList<>()).add(piece);
                }
                if (!pieces.keySet().equals(java.util.Set.of(0, 2, 3))) {
                    throw new IllegalStateException("Wrong unfinished masks");
                }
                for (List<long[]> profile : pieces.values()) {
                    if (profile.get(0)[0] != 0 || profile.get(0)[1] != 0
                            || profile.get(profile.size() - 1)[2] != 0) {
                        throw new IllegalStateException("Wrong profile boundary");
                    }
                    for (int k = 1; k < profile.size(); ++k) {
                        final long[] previous = profile.get(k - 1), next = profile.get(k);
                        if (next[0] <= previous[0] || next[2] >= previous[2]
                                || next[1] != previous[1] + (next[0] - previous[0]) * previous[2]) {
                            throw new IllegalStateException("Noncanonical/discontinuous profile");
                        }
                    }
                }
                for (long huge : new long[] {1000000L, 1000000000000L, 1000000000000000000L}) {
                    if (excess(3, huge) != expectedLambda * (W[0] + W[1])) {
                        throw new IllegalStateException("Wrong huge-budget tail");
                    }
                }
            } catch (Exception failure) {
                throw new IllegalStateException("Cannot load imported certificate profile", failure);
            }
            loadNanoseconds = System.nanoTime() - started;
        }

        long excess(int mask, long budget) {
            if (budget < 0) { throw new IllegalArgumentException("Negative budget"); }
            long[] selected = pieces.get(mask).get(0);
            for (long[] piece : pieces.get(mask)) {
                if (piece[0] > budget) { break; }
                selected = piece;
            }
            return selected[1] + (budget - selected[0]) * selected[2];
        }

        long total(int stage, long budget) {
            return stage == 0 ? W[0] + W[1] + excess(3, budget) : W[1] + excess(2, budget);
        }
    }

    private static final class Request {
        final CountDownLatch completed = new CountDownLatch(1);
        final String action;
        volatile Throwable error;
        boolean cancelled, claimed;
        Request(String action) { this.action = action; }
    }

    private static class Trace implements RetryStudyHooks.Observer {
        final List<String> events = Collections.synchronizedList(new ArrayList<>());
        final BlockingQueue<Request> requests = new LinkedBlockingQueue<>();
        final Cut[] targets;
        final boolean[] issued;
        final int[] failures = new int[2], attempts = new int[2];
        final Map<String, Long> prefix = new HashMap<>();
        final int lambda;
        final ImportedProfile profile;
        int budget;
        volatile boolean cycleOpen, poisoned;
        boolean protectedBody;

        Trace(int lambda, int schedule, boolean importRequired) {
            this.lambda = lambda;
            targets = SCHEDULES[schedule];
            issued = new boolean[targets.length];
            budget = 2 * Q[schedule];
            profile = importRequired ? new ImportedProfile(lambda) : null;
        }

        void record(String stage, String kind, long a, long b, long c, long d) {
            events.add("[\"" + stage + "\",\"" + kind + "\"," + a + "," + b + "," + c + "," + d + "]");
        }

        void request(String action) {
            if (poisoned) { throw new StudyAbortError("Request after poisoned run"); }
            final Request request = new Request(action);
            requests.add(request);
            try {
                if (!request.completed.await(15, TimeUnit.SECONDS)) {
                    poisoned = true;
                    synchronized (request) { request.cancelled = true; }
                    requests.remove(request);
                    throw new StudyAbortError("Writer request timed out; no further body permitted");
                }
            } catch (InterruptedException e) {
                poisoned = true;
                synchronized (request) { request.cancelled = true; }
                requests.remove(request);
                Thread.currentThread().interrupt();
                throw new StudyAbortError("Interrupted schedule wait", e);
            }
            if (request.error != null) {
                poisoned = true;
                throw new StudyAbortError("Writer failed", request.error);
            }
        }

        @Override public void event(String stage, String kind, long a, long b, long c, long d) {
            record(stage, kind, a, b, c, d);
            if (poisoned) { throw new StudyAbortError("Event after poisoned run"); }
            final int j = stage.equals("K") ? 0 : 1;
            if (kind.equals("BEGIN")) {
                prefix.clear();
                protectedBody = c == 1;
                if (!protectedBody) { ++attempts[j]; }
            }
            if (kind.equals("INCONSISTENT_EXCEPTION") && protectedBody) {
                throw new StudyAbortError("Inconsistency inside protected body");
            }
            if (kind.equals("CHECK")) {
                if ((d & 2) == 0) {
                    ++failures[j];
                    --budget;
                    if (budget < 0) { throw new StudyAbortError("Failure quota exceeded"); }
                } else if ((d & 1) == 0) {
                    throw new StudyAbortError("Failed body despite consistent state");
                }
            }
            if (kind.equals("BEFORE_LOCK") && cycleOpen) {
                record(stage, "DRAIN_FOR_LOCK", 0, 0, 0, 0);
                request("COMPLETE");
            }
            final boolean work = kind.startsWith("K_") || kind.startsWith("V_");
            if (work) { prefix.merge(kind, a, Long::sum); }
            if (!protectedBody && (work || kind.equals("END"))) {
                final long count = kind.equals("END") ? 1 : prefix.get(kind);
                for (int index = 0; index < targets.length; ++index) {
                    final Cut cut = targets[index];
                    if (!issued[index] && cut.stage.equals(stage) && cut.attempt == attempts[j]
                            && cut.kind.equals(kind) && count >= cut.threshold) {
                        issued[index] = true;
                        record(stage, "CUT", index, attempts[j], count, 0);
                        if (cut.action.equals("COMPLETE") && !cycleOpen) {
                            record(stage, "SKIP_CLOSED_CYCLE", index, 0, 0, 0);
                        } else { request(cut.action); }
                    }
                }
            }
        }
    }

    private static final class StrategyTrace extends Trace implements RetryStudyHooks.StrictPolicy {
        final String policy;
        StrategyTrace(int lambda, int schedule, String policy) {
            super(lambda, schedule, policy.startsWith("curve_"));
            this.policy = policy;
        }
        @Override public boolean tryFast(String stage, int nativeAttempts) {
            final int j = stage.equals("K") ? 0 : 1;
            if (poisoned || nativeAttempts != attempts[j]) {
                throw new StudyAbortError("Unexpected native attempt state");
            }
            if (!policy.startsWith("curve_")) {
                final boolean local;
                if (policy.equals("local_budget")) { local = budget <= lambda; }
                else if (policy.equals("upstream2")) { local = nativeAttempts < 2; }
                else if (policy.equals("unknown_budget_threshold")) { local = failures[j] < lambda; }
                else if (policy.equals("always_protected")) { local = false; }
                else { throw new StudyAbortError("Unknown baseline"); }
                record(stage, "POLICY", budget, local ? 1 : 0, failures[j], -1);
                return local;
            }
            final boolean decision;
            final long own = profile.excess(j == 0 ? 3 : 2, budget);
            final long child = profile.excess(j == 0 ? 2 : 0, budget);
            final long protect = lambda * W[j] + child;
            final long attempt = budget == 0 ? child
                    : Math.max(child, W[j] + profile.excess(j == 0 ? 3 : 2, budget - 1));
            if (policy.equals("curve_protected_tie")) {
                decision = protect != own;
                if (decision && attempt != own) { throw new StudyAbortError("Bad certified action"); }
            } else if (policy.equals("curve_fast_tie")) {
                decision = attempt == own;
                if (!decision && protect != own) { throw new StudyAbortError("Bad certified action"); }
            } else { throw new StudyAbortError("Unknown policy"); }
            record(stage, "POLICY", budget, decision ? 1 : 0, failures[j], profile.total(j, budget));
            return decision;
        }
    }

    private void updateValues(QueryTable source, QueryTable keys, byte[] actions, int epoch) {
        final int[] sentinels = new int[N];
        for (int j = 0; j < N; ++j) { sentinels[j] = epoch * 1000 + j; }
        ((TestColumnSource<?>) source.getColumnSource("Sentinel")).add(
                RowSetFactory.flat(N), intCol("Sentinel", sentinels).getChunk());
        source.notifyListeners(new TableUpdateImpl(i(), i(), RowSetFactory.flat(N),
                RowSetShiftData.EMPTY, source.newModifiedColumnSet("Sentinel")));
        ((TestColumnSource<?>) keys.getColumnSource("Action")).add(
                RowSetFactory.flat(M), byteCol("Action", actions).getChunk());
        keys.notifyListeners(new TableUpdateImpl(i(), i(), RowSetFactory.flat(M),
                RowSetShiftData.EMPTY, keys.newModifiedColumnSet("Action")));
    }

    /** Uses only the existing public requestRefresh API; source latches control scheduling. */
    private final class CycleDriver implements AutoCloseable {
        final EventDrivenUpdateGraph graph;
        final QueryTable source, keys;
        final byte[] actions;
        final Trace trace;
        final int quota;
        final ExecutorService writer = Executors.newSingleThreadExecutor();
        final Runnable sourceRunnable;
        volatile Cycle active;
        int cycles;
        final class Cycle {
            final CountDownLatch entered = new CountDownLatch(1), release = new CountDownLatch(1);
            final boolean split;
            final int epoch;
            Future<?> future;
            Cycle(boolean split, int epoch) { this.split = split; this.epoch = epoch; }
        }
        CycleDriver(EventDrivenUpdateGraph graph, QueryTable source, QueryTable keys,
                byte[] actions, Trace trace, int quota) {
            this.graph = graph; this.source = source; this.keys = keys;
            this.actions = actions; this.trace = trace; this.quota = quota;
            sourceRunnable = () -> {
                final Cycle cycle = active;
                if (cycle == null) { throw new StudyAbortError("Unowned event-graph refresh"); }
                cycle.entered.countDown();
                try {
                    if (cycle.split && !cycle.release.await(15, TimeUnit.SECONDS)) {
                        throw new StudyAbortError("Paused source timed out");
                    }
                } catch (InterruptedException failure) {
                    Thread.currentThread().interrupt();
                    throw new StudyAbortError("Paused source interrupted", failure);
                }
                if (!trace.poisoned) { updateValues(source, keys, actions, cycle.epoch); }
            };
            graph.addSource(sourceRunnable);
        }
        void handle(String action) throws Exception {
            final long before = graph.clock().currentValue();
            if (action.equals("START") || action.equals("FULL")) {
                if (active != null || cycles >= quota) { throw new StudyAbortError("Bad refresh start/quota"); }
                final Cycle cycle = new Cycle(action.equals("START"), ++cycles);
                active = cycle;
                cycle.future = writer.submit(graph::requestRefresh);
                if (cycle.split) {
                    if (!cycle.entered.await(15, TimeUnit.SECONDS)) { throw new StudyAbortError("Source entry timed out"); }
                    trace.cycleOpen = true;
                } else {
                    cycle.future.get(15, TimeUnit.SECONDS);
                    active = null;
                }
            } else if (action.equals("COMPLETE")) {
                final Cycle cycle = active;
                if (cycle == null || !cycle.split || !trace.cycleOpen) { throw new StudyAbortError("No paused cycle"); }
                cycle.release.countDown();
                cycle.future.get(15, TimeUnit.SECONDS);
                active = null;
                trace.cycleOpen = false;
            } else { throw new StudyAbortError("Unknown event-graph action"); }
            trace.record("W", action, before, graph.clock().currentValue(),
                    source.getLastNotificationStep(), keys.getLastNotificationStep());
        }
        @Override public void close() throws Exception {
            final Cycle cycle = active;
            if (cycle != null) {
                cycle.release.countDown();
                try { cycle.future.get(5, TimeUnit.SECONDS); }
                finally { active = null; trace.cycleOpen = false; }
            }
            graph.removeSource(sourceRunnable);
            writer.shutdownNow();
            if (!writer.awaitTermination(5, TimeUnit.SECONDS)) { throw new StudyAbortError("Writer did not terminate"); }
        }
    }

    private void runCase(int lambda, int schedule, String policy) throws Exception {
        final EventDrivenUpdateGraph graph = EventDrivenUpdateGraph.newBuilder(
                "RetryEvent_" + lambda + "_" + schedule + "_" + policy).build();
        try (final SafeCloseable graphContext = ExecutionContext.getContext().withUpdateGraph(graph).open()) {
            runEventCase(lambda, schedule, policy, graph);
        } finally { graph.stop(); }
    }

    private void runEventCase(int lambda, int schedule, String policy, EventDrivenUpdateGraph updateGraph) throws Exception {

        final int[] ids = new int[N], parents = new int[N];
        for (int j = 0; j < N; ++j) {
            ids[j] = j;
            parents[j] = j == 0 ? NULL_INT : (j - 1) / 2;
        }
        final byte expand = HierarchicalTable.KEY_TABLE_ACTION_EXPAND_ALL;
        final byte[] actions = {expand, expand, expand};
        final QueryTable source, keys;
        final TreeTable tree;
        final HierarchicalTable.SnapshotState snapshotState;
        updateGraph.sharedLock().lock();
        try {
            source = testRefreshingTable(intCol("ID", ids), intCol("Parent", parents), intCol("Sentinel", ids));
            tree = source.tree("ID", "Parent");
            keys = testRefreshingTable(intCol(tree.getRowDepthColumn().name(), new int[M]),
                    intCol("ID", 0, 1, 2), byteCol("Action", actions));
            snapshotState = tree.makeSnapshotState();
        } finally { updateGraph.sharedLock().unlock(); }
        final ExecutionContext executionContext = ExecutionContext.getContext();
        final Trace trace = new StrategyTrace(lambda, schedule, policy);
        final ExecutorService executor = Executors.newSingleThreadExecutor();
        final CycleDriver cycleDriver = new CycleDriver(updateGraph, source, keys, actions, trace, Q[schedule]);
        String resultRows = "[]", status = "FAILURE", error = "";
        try {
            final Future<String> future = executor.submit(() -> {
                try (final SafeCloseable context = executionContext.open();
                        final SafeCloseable scope = LivenessScopeStack.open(new LivenessScope(true), true)) {
                    RetryStudyHooks.install(trace);
                    try {
                        final ColumnDefinition<?>[] columns = tree.getAvailableColumnDefinitions()
                                .toArray(ColumnDefinition[]::new);
                        @SuppressWarnings("unchecked")
                        final WritableChunk<? super Values>[] destinations = Arrays.stream(columns)
                                .map(column -> maybeConvertToPrimitiveChunkType(column.getDataType()))
                                .map(type -> type.makeWritableChunk(R)).toArray(WritableChunk[]::new);
                        try {
                            final long expandedSize = tree.snapshot(snapshotState, keys,
                                    ColumnName.of("Action"), null, RowSetFactory.flat(R), destinations);
                            assertEquals(N, expandedSize);
                            final Map<String, Integer> indices = new HashMap<>();
                            for (int index = 0; index < columns.length; ++index) {
                                indices.put(columns[index].getName(), index);
                                assertEquals(R, destinations[index].size());
                            }
                            final List<String> rows = new ArrayList<>();
                            Integer epoch = null;
                            for (int row = 0; row < R; ++row) {
                                final int node = destinations[indices.get("ID")].asIntChunk().get(row);
                                final int parent = destinations[indices.get("Parent")].asIntChunk().get(row);
                                final int sentinel = destinations[indices.get("Sentinel")].asIntChunk().get(row);
                                assertTrue(node >= 0 && node < N);
                                assertEquals(node == 0 ? NULL_INT : (node - 1) / 2, parent);
                                assertEquals(0, (sentinel - node) % 1000);
                                final int observedEpoch = (sentinel - node) / 1000;
                                assertTrue(observedEpoch >= 0 && observedEpoch <= Q[schedule]);
                                if (epoch == null) { epoch = observedEpoch; }
                                assertEquals(epoch.intValue(), observedEpoch);
                                rows.add("[" + node + "," + parent + "," + sentinel + "]");
                            }
                            return "[" + String.join(",", rows) + "]";
                        } finally {
                            for (WritableChunk<? super Values> destination : destinations) { destination.close(); }
                        }
                    } finally { RetryStudyHooks.clear(); }
                }
            });
            final long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(30);
            while (!future.isDone()) {
                if (System.nanoTime() > deadline) { throw new IllegalStateException("Case timed out"); }
                final Request request = trace.requests.poll(20, TimeUnit.MILLISECONDS);
                if (request == null) { continue; }
                synchronized (request) {
                    if (request.cancelled || trace.poisoned) { request.completed.countDown(); continue; }
                    request.claimed = true;
                }
                try { cycleDriver.handle(request.action); }
                catch (Throwable failure) { request.error = failure; throw failure; }
                finally { request.completed.countDown(); }
            }
            resultRows = future.get(5, TimeUnit.SECONDS);
            assertFalse(trace.cycleOpen);
            assertTrue(cycleDriver.cycles <= Q[schedule]);
            status = "SUCCESS";
        } catch (Throwable failure) {
            Throwable root = failure;
            while (root.getCause() != null) { root = root.getCause(); }
            error = root.getClass().getName();
            if (String.valueOf(root.getMessage()).contains("timed out")) { status = "TIMEOUT"; }
            else if (root instanceof StudyAbortError) { status = "INVALID"; }
            throw failure;
        } finally {
            trace.poisoned = true;
            try { cycleDriver.close(); }
            catch (Throwable failure) { status = "FAILURE"; error = failure.getClass().getName(); }
            Request pendingRequest;
            while ((pendingRequest = trace.requests.poll()) != null) {
                synchronized (pendingRequest) { pendingRequest.cancelled = true; }
                pendingRequest.error = new StudyAbortError("Case closing");
                pendingRequest.completed.countDown();
            }
            executor.shutdownNow();
            if (!executor.awaitTermination(5, TimeUnit.SECONDS)) { status = "TIMEOUT"; }
            System.out.println("RETRY_EVENT_GRAPH {\"id\":\"" + lambda + "_" + NAMES[schedule] + "_" + policy
                    + "\",\"status\":\"" + status + "\",\"error_class\":\"" + error
                    + "\",\"policy\":\"" + policy + "\",\"schedule\":\"" + NAMES[schedule]
                    + "\",\"n\":" + N + ",\"m\":" + M + ",\"r\":" + R + ",\"h\":" + H
                    + ",\"lambda\":" + lambda + ",\"q_bound\":" + Q[schedule] + ",\"q_executed\":" + cycleDriver.cycles
                    + ",\"refresh_requests\":" + cycleDriver.cycles
                    + ",\"w_caps\":[" + W[0] + "," + W[1] + "],\"model_value\":" + (trace.profile == null ? -1 : trace.profile.total(0, 2 * Q[schedule]))
                    + ",\"profile_sha256\":\"" + (trace.profile == null ? "" : trace.profile.sha256) + "\",\"profile_load_nanoseconds\":" + (trace.profile == null ? 0 : trace.profile.loadNanoseconds)
                    + ",\"issued_cuts\":" + Arrays.toString(trace.issued)
                    + ",\"rows\":" + resultRows + ",\"events\":[" + String.join(",", trace.events) + "]}");
        }
    }
}
