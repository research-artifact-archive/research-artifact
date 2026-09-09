package io.deephaven.engine.table.impl;

import io.deephaven.api.ColumnName;
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

import static io.deephaven.engine.testutil.HierarchicalTableTestTools.freeSnapshotTableChunks;
import static io.deephaven.engine.testutil.HierarchicalTableTestTools.snapshotToTable;
import static io.deephaven.engine.testutil.TstUtils.i;
import static io.deephaven.engine.testutil.TstUtils.testRefreshingTable;
import static io.deephaven.engine.util.TableTools.byteCol;
import static io.deephaven.engine.util.TableTools.intCol;
import static io.deephaven.util.QueryConstants.NULL_INT;

/** Author-controlled, fixed-structure comparison. All output is exploratory. */
@Category(OutOfBandTest.class)
public class TestRetryCompiledImport extends RefreshingTableTestCase {
    private static final int N = 31, M = 3, R = 16, H = 5;
    private static final long[] W = {M + 1, (M + 1) * (3 * H + 5) + N + 1 + 4 * R};
    private static final String[][][] SCHEDULES = {
            {{}, {}},
            {{"FULL"}, {}},
            {{}, {"FULL"}},
            {{}, {"START", "COMPLETE"}},
            {{"START", "COMPLETE"}, {}},
            {{}, {"START", "COMPLETE", "START", "COMPLETE"}},
            {{"FULL"}, {"START", "COMPLETE"}}
    };
    private static final String[] NAMES = {"none", "k_full", "v_full", "v_split", "k_split",
            "v_two_split", "k_full_v_split"};
    private static final int[] Q = {0, 1, 1, 1, 1, 2, 2};

    @Test public void testLambdaOne() throws Exception { runMatrix(1); }
    @Test public void testLambdaThree() throws Exception { runMatrix(3); }
    @Test public void testLambdaTen() throws Exception { runMatrix(10); }

    private void runMatrix(int lambda) throws Exception {
        final List<String> failures = new ArrayList<>();
        for (int schedule = 0; schedule < SCHEDULES.length; ++schedule) {
            for (String policy : new String[] {"curve_protected_tie", "curve_fast_tie", "local_budget"}) {
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
            try (final java.io.InputStream input = TestRetryCompiledImport.class.getResourceAsStream(
                    "/retry-study-import/profile_" + expectedLambda + ".txt")) {
                if (input == null) { throw new IllegalStateException("Missing imported profile"); }
                final byte[] bytes = input.readAllBytes();
                sha256 = java.util.HexFormat.of().formatHex(
                        java.security.MessageDigest.getInstance("SHA-256").digest(bytes));
                final String[] lines = new String(bytes, java.nio.charset.StandardCharsets.UTF_8).split("\n");
                if (!lines[0].equals("RETRY_PROFILE_V1")
                        || !lines[1].equals("lambda " + expectedLambda)
                        || !lines[2].equals("caps 4 176")
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
        Request(String action) { this.action = action; }
    }

    private static class Trace implements RetryStudyHooks.Observer {
        final List<String> events = Collections.synchronizedList(new ArrayList<>());
        final BlockingQueue<Request> requests = new LinkedBlockingQueue<>();
        final String[][] targets;
        final int[] issued = new int[2];
        final int[] failures = new int[2];
        final int lambda;
        final ImportedProfile profile;
        int budget;
        volatile boolean cycleOpen;

        Trace(int lambda, int schedule, boolean importRequired) {
            this.lambda = lambda;
            targets = SCHEDULES[schedule];
            budget = 2 * Q[schedule];
            profile = importRequired ? new ImportedProfile(lambda) : null;
        }

        void record(String stage, String kind, long a, long b, long c, long d) {
            events.add("[\"" + stage + "\",\"" + kind + "\"," + a + "," + b + "," + c + "," + d + "]");
        }

        void request(String action) {
            final Request request = new Request(action);
            requests.add(request);
            try {
                if (!request.completed.await(15, TimeUnit.SECONDS)) {
                    throw new IllegalStateException("Writer request timed out");
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException("Interrupted schedule wait", e);
            }
            if (request.error != null) { throw new IllegalStateException("Writer failed", request.error); }
        }

        @Override public void event(String stage, String kind, long a, long b, long c, long d) {
            record(stage, kind, a, b, c, d);
            final int j = stage.equals("K") ? 0 : 1;
            if (kind.equals("CHECK") && (d & 2) == 0) {
                ++failures[j];
                --budget;
                if (budget < 0) { throw new IllegalStateException("Failure quota exceeded"); }
            }
            if (kind.equals("BEGIN") && c == 0 && issued[j] < targets[j].length) {
                request(targets[j][issued[j]++]);
            }
            if (kind.equals("BEFORE_LOCK") && cycleOpen) {
                record(stage, "DRAIN_FOR_LOCK", issued[j], 0, 0, 0);
                request("COMPLETE");
            }
        }
    }

    private static final class StrategyTrace extends Trace implements RetryStudyHooks.Policy {
        final String policy;
        StrategyTrace(int lambda, int schedule, String policy) {
            super(lambda, schedule, !policy.equals("local_budget"));
            this.policy = policy;
        }
        @Override public boolean tryFast(String stage, int attempts) {
            final int j = stage.equals("K") ? 0 : 1;
            if (policy.equals("local_budget")) {
                final boolean local = budget <= lambda;
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
                if (decision && attempt != own) { throw new IllegalStateException("Bad certified action"); }
            } else if (policy.equals("curve_fast_tie")) {
                decision = attempt == own;
                if (!decision && protect != own) { throw new IllegalStateException("Bad certified action"); }
            } else { throw new IllegalStateException("Unknown policy"); }
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
        final Trace trace = new StrategyTrace(lambda, schedule, policy);
        final ExecutorService executor = Executors.newSingleThreadExecutor();
        int cycles = 0;
        String resultRows = "[]", status = "FAILURE", error = "";
        try {
            final Future<String> future = executor.submit(() -> {
                try (final SafeCloseable context = executionContext.open();
                        final SafeCloseable scope = LivenessScopeStack.open(new LivenessScope(true), true)) {
                    RetryStudyHooks.install(trace);
                    try {
                        final Table result = snapshotToTable(tree, snapshotState, keys,
                                ColumnName.of("Action"), null, RowSetFactory.flat(R));
                        try {
                            assertEquals(R, result.size());
                            final List<String> rows = new ArrayList<>();
                            Integer epoch = null;
                            for (int row = 0; row < R; ++row) {
                                final int node = result.getColumnSource("ID").getInt(row);
                                final int parent = result.getColumnSource("Parent").getInt(row);
                                final int sentinel = result.getColumnSource("Sentinel").getInt(row);
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
                        } finally { freeSnapshotTableChunks(result); }
                    } finally { RetryStudyHooks.clear(); }
                }
            });
            final long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(30);
            while (!future.isDone()) {
                if (System.nanoTime() > deadline) { throw new IllegalStateException("Case timed out"); }
                final Request request = trace.requests.poll(20, TimeUnit.MILLISECONDS);
                if (request == null) { continue; }
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
            error = failure.getClass().getName();
            throw failure;
        } finally {
            if (trace.cycleOpen) {
                updateGraph.markSourcesRefreshedForUnitTests();
                updateGraph.completeCycleForUnitTests();
                trace.cycleOpen = false;
            }
            executor.shutdownNow();
            if (!executor.awaitTermination(5, TimeUnit.SECONDS)) { status = "TIMEOUT"; }
            System.out.println("RETRY_IMPORTED {\"id\":\"" + lambda + "_" + NAMES[schedule] + "_" + policy
                    + "\",\"status\":\"" + status + "\",\"error_class\":\"" + error
                    + "\",\"policy\":\"" + policy + "\",\"schedule\":\"" + NAMES[schedule]
                    + "\",\"n\":" + N + ",\"m\":" + M + ",\"r\":" + R + ",\"h\":" + H
                    + ",\"lambda\":" + lambda + ",\"q_bound\":" + Q[schedule] + ",\"q_executed\":" + cycles
                    + ",\"w_caps\":[" + W[0] + "," + W[1] + "],\"model_value\":" + (trace.profile == null ? -1 : trace.profile.total(0, 2 * Q[schedule]))
                    + ",\"profile_sha256\":\"" + (trace.profile == null ? "" : trace.profile.sha256) + "\",\"profile_load_nanoseconds\":" + (trace.profile == null ? 0 : trace.profile.loadNanoseconds)
                    + ",\"rows\":" + resultRows + ",\"events\":[" + String.join(",", trace.events) + "]}");
        }
    }
}
