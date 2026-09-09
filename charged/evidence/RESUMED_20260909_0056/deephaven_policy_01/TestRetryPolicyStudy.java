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
public class TestRetryPolicyStudy extends RefreshingTableTestCase {
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
            for (String policy : new String[] {"compiled", "upstream", "threshold", "protected"}) {
                try {
                    runCase(lambda, schedule, policy);
                } catch (Throwable failure) {
                    failures.add(lambda + ":" + NAMES[schedule] + ":" + policy + ":" + failure);
                }
            }
        }
        assertTrue(failures.toString(), failures.isEmpty());
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
        final long[][] value;
        final boolean[][] fast;
        int budget;
        volatile boolean cycleOpen;

        Trace(int lambda, int schedule) {
            this.lambda = lambda;
            targets = SCHEDULES[schedule];
            budget = 2 * Q[schedule];
            value = new long[3][budget + 1];
            fast = new boolean[2][budget + 1];
            for (int b = 0; b <= budget; ++b) {
                for (int stage = 1; stage >= 0; --stage) {
                    final long protect = (1 + lambda) * W[stage] + value[stage + 1][b];
                    final long attempt = W[stage] + (b == 0 ? value[stage + 1][b]
                            : Math.max(value[stage + 1][b], value[stage][b - 1]));
                    fast[stage][b] = attempt <= protect;
                    value[stage][b] = Math.min(attempt, protect);
                }
            }
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
            super(lambda, schedule);
            this.policy = policy;
        }
        @Override public boolean tryFast(String stage, int attempts) {
            final int j = stage.equals("K") ? 0 : 1;
            final boolean decision;
            if (policy.equals("compiled")) {
                decision = fast[j][budget];
            } else if (policy.equals("threshold")) {
                decision = failures[j] * W[j] < lambda * W[j];
            } else if (policy.equals("protected")) {
                decision = false;
            } else {
                throw new IllegalStateException("Unknown policy");
            }
            record(stage, "POLICY", budget, decision ? 1 : 0, failures[j], value[j][budget]);
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
        final Trace trace = policy.equals("upstream") ? new Trace(lambda, schedule)
                : new StrategyTrace(lambda, schedule, policy);
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
            System.out.println("RETRY_POLICY {\"id\":\"" + lambda + "_" + NAMES[schedule] + "_" + policy
                    + "\",\"status\":\"" + status + "\",\"error_class\":\"" + error
                    + "\",\"policy\":\"" + policy + "\",\"schedule\":\"" + NAMES[schedule]
                    + "\",\"n\":" + N + ",\"m\":" + M + ",\"r\":" + R + ",\"h\":" + H
                    + ",\"lambda\":" + lambda + ",\"q_bound\":" + Q[schedule] + ",\"q_executed\":" + cycles
                    + ",\"w_caps\":[" + W[0] + "," + W[1] + "],\"model_value\":" + trace.value[0][2 * Q[schedule]]
                    + ",\"rows\":" + resultRows + ",\"events\":[" + String.join(",", trace.events) + "]}");
        }
    }
}
