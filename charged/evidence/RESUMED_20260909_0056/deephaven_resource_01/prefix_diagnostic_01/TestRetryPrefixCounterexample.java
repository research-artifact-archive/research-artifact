package io.deephaven.engine.table.impl;

import io.deephaven.api.ColumnName;
import io.deephaven.engine.rowset.RowSetFactory;
import io.deephaven.engine.table.Table;
import io.deephaven.engine.table.hierarchical.HierarchicalTable;
import io.deephaven.engine.table.hierarchical.TreeTable;
import io.deephaven.engine.table.impl.remote.RetryStudyHooks;
import io.deephaven.engine.testutil.testcase.RefreshingTableTestCase;
import io.deephaven.test.types.OutOfBandTest;
import org.junit.Test;
import org.junit.experimental.categories.Category;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

import static io.deephaven.engine.testutil.HierarchicalTableTestTools.freeSnapshotTableChunks;
import static io.deephaven.engine.testutil.HierarchicalTableTestTools.snapshotToTable;
import static io.deephaven.engine.testutil.TstUtils.testRefreshingTable;
import static io.deephaven.engine.util.TableTools.byteCol;
import static io.deephaven.engine.util.TableTools.intCol;
import static io.deephaven.engine.util.TableTools.newTable;
import static io.deephaven.engine.util.TableTools.stringCol;

@Category(OutOfBandTest.class)
public class TestRetryPrefixCounterexample extends RefreshingTableTestCase {
    @Test
    public void testNearMaximumControl() {
        diagnose(false);
    }

    @Test
    public void testMaximumPrefix() {
        diagnose(true);
    }

    private void diagnose(boolean boundary) {
        final long last = boundary ? Long.MAX_VALUE : Long.MAX_VALUE - 1;
        final QueryTable source = testRefreshingTable(RowSetFactory.fromRange(last - 1, last).toTracking(),
                stringCol("ID", "A", "B"), stringCol("Parent", new String[] {null, null}),
                intCol("Sentinel", 10, 20));
        final TreeTable tree = source.tree("ID", "Parent");
        final Table keys = newTable(intCol(tree.getRowDepthColumn().name(), 0),
                stringCol("ID", new String[] {null}),
                byteCol("Action", HierarchicalTable.KEY_TABLE_ACTION_EXPAND_ALL));
        final AtomicInteger visits = new AtomicInteger();
        final List<String> events = new ArrayList<>();
        String outcome = "UNEXPECTED";
        Throwable caught = null;
        RetryStudyHooks.install((stage, kind, a, b, c, d) -> {
            events.add("[\"" + stage + "\",\"" + kind + "\"," + a + "," + b + "," + c + "," + d + "]");
            if (kind.equals("V_NODE") && visits.incrementAndGet() > 8) {
                throw new IllegalStateException("AUTHOR_DIAGNOSTIC_PREFIX_LIMIT_9");
            }
        });
        try {
            final Table result = snapshotToTable(tree, tree.makeSnapshotState(), keys,
                    ColumnName.of("Action"), null, RowSetFactory.flat(1));
            try {
                assertEquals(1, result.size());
                assertEquals("A", result.getColumnSource("ID").get(0));
                assertEquals(10, result.getColumnSource("Sentinel").getInt(0));
                outcome = "RETURNED_CORRECT_SNAPSHOT";
            } finally {
                freeSnapshotTableChunks(result);
            }
        } catch (Throwable error) {
            caught = error;
            Throwable root = error;
            while (root.getCause() != null) { root = root.getCause(); }
            if ("AUTHOR_DIAGNOSTIC_PREFIX_LIMIT_9".equals(root.getMessage())) {
                outcome = "DIAGNOSTIC_PREFIX_LIMIT";
            } else {
                outcome = "OTHER_EXCEPTION";
            }
        } finally {
            RetryStudyHooks.clear();
            System.out.println("RETRY_PREFIX {\"case\":\"" + (boundary ? "maximum" : "near_maximum")
                    + "\",\"n\":2,\"q\":0,\"last_row_key\":\"" + last
                    + "\",\"visit_entries\":" + visits.get() + ",\"outcome\":\"" + outcome
                    + "\",\"events\":[" + String.join(",", events) + "]}");
        }
        if (boundary) {
            assertEquals("DIAGNOSTIC_PREFIX_LIMIT", outcome);
            assertEquals(9, visits.get());
        } else {
            if (caught != null) { throw new AssertionError("Nearby control failed", caught); }
            assertEquals("RETURNED_CORRECT_SNAPSHOT", outcome);
            assertTrue(visits.get() <= 3);
        }
    }
}
