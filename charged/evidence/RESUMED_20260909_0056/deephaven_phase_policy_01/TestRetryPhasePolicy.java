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
import io.deephaven.engine.testutil.ControlledUpdateGraph;
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
public class TestRetryPhasePolicy extends RefreshingTableTestCase {
    private static final int N = 31, M = 3, R = 16, H = 5;
    private static final long[] W = {4, 104};
    private static final String[] POLICIES = {"phase_protected_tie", "phase_fast_tie", "phase_local_budget"};
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

    @Test public void testLambdaOne() throws Exception { runMatrix(1); }
    @Test public void testLambdaThree() throws Exception { runMatrix(3); }
    @Test public void testLambdaTen() throws Exception { runMatrix(10); }

    private void runMatrix(int lambda) throws Exception {
        final List<String> failures = new ArrayList<>();
        for (int schedule = 0; schedule < SCHEDULES.length; ++schedule) {
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

    /** Finite-budget full cycle-phase DP, not an imported all-budget profile. */
    private static final class PhaseValues {
        final long[][][] values;
        final int lambda;
        final long buildNanoseconds;
        PhaseValues(int lambda, int q) {
            final long start = System.nanoTime();
            this.lambda = lambda;
            values = new long[3][q + 1][2];
            for (long[][] stage : values) {
                for (long[] budget : stage) { Arrays.fill(budget, -1); }
            }
            for (int j = 2; j >= 0; --j) {
                for (int r = 0; r <= q; ++r) {
                    value(j, r, 0); value(j, r, 1);
                }
            }
            buildNanoseconds = System.nanoTime() - start;
        }
        long value(int stage, int r, int phase) {
            if (stage == 2) { return 0; }
            if (values[stage][r][phase] >= 0) { return values[stage][r][phase]; }
            final long protect = protectedValue(stage, r);
            final long attempt = fastValue(stage, r, phase);
            return values[stage][r][phase] = Math.min(protect, attempt);
        }
        long protectedValue(int stage, int r) {
            return (1 + lambda) * W[stage] + value(stage + 1, r, 0);
        }
        long fastValue(int stage, int r, int phase) {
            long worst = value(stage + 1, r, phase);
            int left = r, endPhase = phase;
            // Every nonempty alternating boundary sequence, including FULL and COMPLETE+START.
            while (endPhase == 1 || left > 0) {
                if (endPhase == 1) { endPhase = 0; }
                else { --left; endPhase = 1; }
                worst = Math.max(worst, value(stage, left, endPhase));
            }
            return W[stage] + worst;
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
        final PhaseValues profile;
        final long initialClock;
        final int qBound;
        int budget;
        volatile boolean cycleOpen, poisoned;
        boolean protectedBody;

        Trace(int lambda, int schedule, boolean solveRequired, long initialClock) {
            this.lambda = lambda;
            targets = SCHEDULES[schedule];
            issued = new boolean[targets.length];
            budget = 2 * Q[schedule];
            this.initialClock = initialClock;
            qBound = Q[schedule];
            profile = solveRequired ? new PhaseValues(lambda, qBound) : null;
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
        StrategyTrace(int lambda, int schedule, String policy, long initialClock) {
            super(lambda, schedule, !policy.equals("phase_local_budget"), initialClock);
            this.policy = policy;
        }
        @Override public boolean tryFast(String stage, int nativeAttempts) {
            final int j = stage.equals("K") ? 0 : 1;
            if (poisoned || nativeAttempts != attempts[j]) {
                throw new StudyAbortError("Unexpected native attempt state");
            }
            final long clock = ExecutionContext.getContext().getUpdateGraph().clock().currentValue();
            final int r = qBound - Math.toIntExact(clock / 2 - initialClock / 2);
            final int phase = clock % 2 == 0 ? 1 : 0;
            if (r < 0 || (phase == 1) != cycleOpen) { throw new StudyAbortError("Clock/phase quota mismatch"); }
            final long model = profile == null ? -1 : profile.value(j, r, phase);
            record(stage, "PHASE", r, phase, clock, model);
            final boolean fast;
            if (policy.equals("phase_local_budget")) { fast = 2 * r + phase <= lambda; }
            else {
                final long protect = profile.protectedValue(j, r);
                final long attempt = profile.fastValue(j, r, phase);
                fast = policy.equals("phase_fast_tie") ? attempt <= protect : attempt < protect;
                if (model != Math.min(protect, attempt)) { throw new StudyAbortError("Bad phase action"); }
            }
            record(stage, "POLICY", budget, fast ? 1 : 0, failures[j], model);
            return fast;
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

    private void runCase(int lambda, int schedule, String policy) throws Exception {
        final int[] ids = new int[N], parents = new int[N];
        for (int j = 0; j < N; ++j) {
            ids[j] = j;
            parents[j] = j == 0 ? NULL_INT : (j - 1) / 2;
        }
        final byte expand = HierarchicalTable.KEY_TABLE_ACTION_EXPAND_ALL;
        final byte[] actions = {expand, expand, expand};
        final QueryTable source = testRefreshingTable(
                intCol("ID", ids), intCol("Parent", parents), intCol("Sentinel", ids));
        final TreeTable tree = source.tree("ID", "Parent");
        final QueryTable keys = testRefreshingTable(intCol(tree.getRowDepthColumn().name(), new int[M]),
                intCol("ID", 0, 1, 2), byteCol("Action", actions));
        final HierarchicalTable.SnapshotState snapshotState = tree.makeSnapshotState();
        final ControlledUpdateGraph updateGraph = ExecutionContext.getContext().getUpdateGraph().cast();
        final ExecutionContext executionContext = ExecutionContext.getContext();
        final Trace trace = new StrategyTrace(lambda, schedule, policy, updateGraph.clock().currentValue());
        final ExecutorService executor = Executors.newSingleThreadExecutor();
        int cycles = 0;
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
                final long before = updateGraph.clock().currentValue();
                try {
                    if (request.action.equals("START")) {
                        assertFalse(trace.cycleOpen);
                        ++cycles;
                        updateGraph.startCycleForUnitTests(false);
                        trace.cycleOpen = true;
                    } else if (request.action.equals("COMPLETE")) {
                        assertTrue(trace.cycleOpen);
                        updateValues(source, keys, actions, cycles);
                        updateGraph.markSourcesRefreshedForUnitTests();
                        updateGraph.completeCycleForUnitTests();
                        trace.cycleOpen = false;
                    } else if (request.action.equals("FULL")) {
                        assertFalse(trace.cycleOpen);
                        final int epoch = ++cycles;
                        updateGraph.runWithinUnitTestCycle(() -> updateValues(source, keys, actions, epoch));
                    } else { throw new IllegalStateException("Unknown writer action"); }
                    trace.record("W", request.action, before, updateGraph.clock().currentValue(),
                            source.getLastNotificationStep(), keys.getLastNotificationStep());
                } catch (Throwable failure) {
                    request.error = failure;
                    throw failure;
                } finally { request.completed.countDown(); }
            }
            resultRows = future.get(5, TimeUnit.SECONDS);
            assertFalse(trace.cycleOpen);
            assertTrue(cycles <= Q[schedule]);
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
            if (trace.cycleOpen) {
                updateGraph.markSourcesRefreshedForUnitTests();
                updateGraph.completeCycleForUnitTests();
                trace.cycleOpen = false;
            }
            Request pendingRequest;
            while ((pendingRequest = trace.requests.poll()) != null) {
                synchronized (pendingRequest) { pendingRequest.cancelled = true; }
                pendingRequest.error = new StudyAbortError("Case closing");
                pendingRequest.completed.countDown();
            }
            executor.shutdownNow();
            if (!executor.awaitTermination(5, TimeUnit.SECONDS)) { status = "TIMEOUT"; }
            System.out.println("RETRY_PHASE {\"id\":\"" + lambda + "_" + NAMES[schedule] + "_" + policy
                    + "\",\"status\":\"" + status + "\",\"error_class\":\"" + error
                    + "\",\"policy\":\"" + policy + "\",\"schedule\":\"" + NAMES[schedule]
                    + "\",\"n\":" + N + ",\"m\":" + M + ",\"r\":" + R + ",\"h\":" + H
                    + ",\"lambda\":" + lambda + ",\"q_bound\":" + Q[schedule] + ",\"q_executed\":" + cycles
                    + ",\"w_caps\":[" + W[0] + "," + W[1] + "],\"model_value\":" + (trace.profile == null ? -1 : trace.profile.value(0, Q[schedule], 0))
                    + ",\"initial_clock\":" + trace.initialClock
                    + ",\"policy_build_nanoseconds\":" + (trace.profile == null ? 0 : trace.profile.buildNanoseconds)
                    + ",\"issued_cuts\":" + Arrays.toString(trace.issued)
                    + ",\"rows\":" + resultRows + ",\"events\":[" + String.join(",", trace.events) + "]}");
        }
    }
}
