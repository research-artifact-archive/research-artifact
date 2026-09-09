package io.deephaven.engine.table.impl;

import io.deephaven.api.ColumnName;
import io.deephaven.engine.context.ExecutionContext;
import io.deephaven.engine.liveness.LivenessScope;
import io.deephaven.engine.liveness.LivenessScopeStack;
import io.deephaven.engine.rowset.RowSetFactory;
import io.deephaven.engine.table.Table;
import io.deephaven.engine.table.hierarchical.HierarchicalTable;
import io.deephaven.engine.table.hierarchical.TreeTable;
import io.deephaven.engine.table.impl.remote.RetryStudyHooks;
import io.deephaven.engine.testutil.ControlledUpdateGraph;
import io.deephaven.engine.testutil.OutOfBandTest;
import io.deephaven.engine.testutil.testcase.RefreshingTableTestCase;
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
import static io.deephaven.engine.testutil.TstUtils.addToTable;
import static io.deephaven.engine.testutil.TstUtils.i;
import static io.deephaven.engine.testutil.TstUtils.testRefreshingTable;
import static io.deephaven.engine.util.TableTools.byteCol;
import static io.deephaven.engine.util.TableTools.intCol;
import static io.deephaven.util.QueryConstants.NULL_INT;

/** Six fixed exploratory schedules; real update-graph changes cause any inconsistency. */
@Category(OutOfBandTest.class)
public class TestRetryResourceStudy extends RefreshingTableTestCase {
    private static final int N = 31;
    private static final int M = 3;
    private static final int R = 16;

    @Test
    public void testNoUpdate() throws Exception { runCase("none", new String[0]); }

    @Test
    public void testKBefore() throws Exception { runCase("k_before", new String[] {"K:BEGIN"}); }

    @Test
    public void testKAfter() throws Exception { runCase("k_after", new String[] {"K:END"}); }

    @Test
    public void testVBefore() throws Exception { runCase("v_before", new String[] {"V:BEGIN"}); }

    @Test
    public void testVAfter() throws Exception { runCase("v_after", new String[] {"V:END"}); }

    @Test
    public void testBoth() throws Exception { runCase("both", new String[] {"K:END", "V:BEGIN"}); }

    private static final class Request {
        final CountDownLatch completed = new CountDownLatch(1);
        volatile Throwable error;
    }

    private static final class Trace implements RetryStudyHooks.Observer {
        final List<String> events = Collections.synchronizedList(new ArrayList<>());
        final BlockingQueue<Request> requests = new LinkedBlockingQueue<>();
        final String[] targets;
        int issued;

        Trace(String[] targets) { this.targets = targets; }

        void record(String stage, String kind, long a, long b, long c, long d) {
            events.add("[\"" + stage + "\",\"" + kind + "\"," + a + "," + b + "," + c + "," + d + "]");
        }

        @Override
        public void event(String stage, String kind, long a, long b, long c, long d) {
            record(stage, kind, a, b, c, d);
            if (issued < targets.length && c == 0 &&
                    (kind.equals("BEGIN") || kind.equals("END")) &&
                    targets[issued].equals(stage + ":" + kind)) {
                ++issued;
                final Request request = new Request();
                requests.add(request);
                try {
                    if (!request.completed.await(30, TimeUnit.SECONDS)) {
                        throw new IllegalStateException("Writer did not complete within30seconds");
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    throw new IllegalStateException("Interrupted schedule wait", e);
                }
                if (request.error != null) {
                    throw new IllegalStateException("Writer failed", request.error);
                }
            }
        }
    }

    private void runCase(String id, String[] targets) throws Exception {
        final int[] ids = new int[N];
        final int[] parents = new int[N];
        for (int j = 0; j < N; ++j) {
            ids[j] = j;
            parents[j] = j == 0 ? NULL_INT : (j - 1) / 2;
        }
        final int[] keyIds = {0, 1, 2};
        final int[] depths = new int[M];
        final byte expand = HierarchicalTable.KEY_TABLE_ACTION_EXPAND_ALL;
        final byte[] actions = {expand, expand, expand};
        final QueryTable source = testRefreshingTable(
                intCol("ID", ids), intCol("Parent", parents), intCol("Sentinel", ids));
        final TreeTable tree = source.tree("ID", "Parent");
        final String depthName = tree.getRowDepthColumn().name();
        final QueryTable keys = testRefreshingTable(
                intCol(depthName, depths), intCol("ID", keyIds), byteCol("Action", actions));
        final HierarchicalTable.SnapshotState snapshotState = tree.makeSnapshotState();
        final ControlledUpdateGraph updateGraph = ExecutionContext.getContext().getUpdateGraph().cast();
        final ExecutionContext executionContext = ExecutionContext.getContext();
        final Trace trace = new Trace(targets);
        final ExecutorService executor = Executors.newSingleThreadExecutor();
        int cycles = 0;
        String resultRows = "[]";
        String status = "FAILURE";
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
                                assertTrue(observedEpoch >= 0 && observedEpoch <= targets.length);
                                if (epoch == null) { epoch = observedEpoch; }
                                assertEquals(epoch.intValue(), observedEpoch);
                                rows.add("[" + node + "," + parent + "," + sentinel + "]");
                            }
                            return "[" + String.join(",", rows) + "]";
                        } finally {
                            freeSnapshotTableChunks(result);
                        }
                    } finally {
                        RetryStudyHooks.clear();
                    }
                }
            });
            final long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(45);
            while (!future.isDone()) {
                if (System.nanoTime() > deadline) {
                    throw new IllegalStateException("Execution exceeded45seconds");
                }
                final Request request = trace.requests.poll(100, TimeUnit.MILLISECONDS);
                if (request == null) { continue; }
                final int epoch = ++cycles;
                final int[] sentinels = new int[N];
                for (int j = 0; j < N; ++j) { sentinels[j] = epoch * 1000 + j; }
                final long before = updateGraph.clock().currentValue();
                try {
                    updateGraph.runWithinUnitTestCycle(() -> {
                        addToTable(source, RowSetFactory.flat(N),
                                intCol("ID", ids), intCol("Parent", parents), intCol("Sentinel", sentinels));
                        source.notifyListeners(i(), i(), RowSetFactory.flat(N));
                        addToTable(keys, RowSetFactory.flat(M),
                                intCol(depthName, depths), intCol("ID", keyIds), byteCol("Action", actions));
                        keys.notifyListeners(i(), i(), RowSetFactory.flat(M));
                    });
                    trace.record("W", "CYCLE", before, updateGraph.clock().currentValue(),
                            source.getLastNotificationStep(), keys.getLastNotificationStep());
                } catch (Throwable e) {
                    request.error = e;
                    throw e;
                } finally {
                    request.completed.countDown();
                }
            }
            resultRows = future.get(5, TimeUnit.SECONDS);
            assertEquals(targets.length, cycles);
            assertEquals(targets.length, trace.issued);
            status = "SUCCESS";
        } finally {
            executor.shutdownNow();
            if (!executor.awaitTermination(5, TimeUnit.SECONDS)) {
                status = "TIMEOUT";
            }
            System.out.println("RETRY_STUDY {\"id\":\"" + id + "\",\"status\":\"" + status
                    + "\",\"n\":" + N + ",\"m\":" + M + ",\"r\":" + R
                    + ",\"q_planned\":" + targets.length + ",\"q_executed\":" + cycles
                    + ",\"rows\":" + resultRows + ",\"events\":["
                    + String.join(",", trace.events) + "]}");
        }
    }
}
