"""Prepare new changing-action inputs; this script does not execute native cases."""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / 'deephaven_event_graph_01'
text = (PARENT / 'TestRetryEventGraph.java').read_text()


def replace(old, new):
    global text
    assert text.count(old) == 1, (old[:120], text.count(old))
    text = text.replace(old, new)


text = text.replace('TestRetryEventGraph', 'TestRetryKeyAction')
text = text.replace('RETRY_EVENT_GRAPH', 'RETRY_KEY_ACTION')
text = text.replace('RetryEvent_', 'RetryKeyAction_')
replace('/** Author-controlled, fixed-structure comparison. All output is exploratory. */',
        '/** Author-controlled fixed structure with genuinely changing expansion actions. Exploratory. */')
replace('for (int schedule : new int[] {0, 7, 10, 11}) {',
        'for (int schedule = 0; schedule < SCHEDULES.length; ++schedule) {')
replace('int budget;\n        volatile boolean cycleOpen, poisoned;',
        'int budget;\n        volatile int completedEpoch;\n'
        '        int bodyEpoch, capturedKeyEpoch = -1, capturedValueEpoch = -1;\n'
        '        long expandedSize = -1;\n        volatile boolean cycleOpen, poisoned;')
replace('protectedBody = c == 1;\n                if (!protectedBody)',
        'protectedBody = c == 1;\n                bodyEpoch = completedEpoch;\n'
        '                if (!protectedBody)')
replace('if (kind.equals("CHECK")) {',
        'if (kind.equals("END") && c == 1 && d == 1) {\n'
        '                if (j == 0) { capturedKeyEpoch = bodyEpoch; }\n'
        '                else { capturedValueEpoch = bodyEpoch; }\n'
        '            }\n            if (kind.equals("CHECK")) {')
replace('throw new StudyAbortError("Failed body despite consistent state");\n                }',
        'throw new StudyAbortError("Failed body despite consistent state");\n'
        '                } else {\n'
        '                    if (j == 0) { capturedKeyEpoch = bodyEpoch; }\n'
        '                    else { capturedValueEpoch = bodyEpoch; }\n'
        '                }')
replace('private void updateValues(QueryTable source, QueryTable keys, byte[] actions, int epoch) {',
        'private void updateValues(QueryTable source, QueryTable keys, byte[] actions, int epoch, Trace trace) {\n'
        '        final byte[] epochActions = actions.clone();\n'
        '        epochActions[1] = epoch % 2 == 1 ? HierarchicalTable.KEY_TABLE_ACTION_CONTRACT\n'
        '                : HierarchicalTable.KEY_TABLE_ACTION_EXPAND_ALL;')
replace('RowSetFactory.flat(M), byteCol("Action", actions).getChunk());',
        'RowSetFactory.flat(M), byteCol("Action", epochActions).getChunk());')
replace('RowSetShiftData.EMPTY, keys.newModifiedColumnSet("Action")));\n    }',
        'RowSetShiftData.EMPTY, keys.newModifiedColumnSet("Action")));\n'
        '        trace.record("W", "KEY_UPDATE", epoch, epochActions[0], epochActions[1], epochActions[2]);\n'
        '    }')
replace('updateValues(source, keys, actions, cycle.epoch);',
        'updateValues(source, keys, actions, cycle.epoch, trace);')
replace('trace.record("W", action, before, graph.clock().currentValue(),',
        'if (!action.equals("START")) { trace.completedEpoch = cycles; }\n'
        '            trace.record("W", action, before, graph.clock().currentValue(),')
replace('assertEquals(N, expandedSize);',
        'trace.expandedSize = expandedSize;\n'
        '                            assertTrue(trace.capturedKeyEpoch >= 0);\n'
        '                            final boolean contracted = trace.capturedKeyEpoch % 2 == 1;\n'
        '                            assertEquals(contracted ? 17L : 31L, expandedSize);\n'
        '                            final List<Integer> expectedNodes = new ArrayList<>();\n'
        '                            final java.util.ArrayDeque<Integer> pendingNodes = new java.util.ArrayDeque<>();\n'
        '                            pendingNodes.push(0);\n'
        '                            while (!pendingNodes.isEmpty()) {\n'
        '                                final int node = pendingNodes.pop();\n'
        '                                if (node >= N) { continue; }\n'
        '                                expectedNodes.add(node);\n'
        '                                if (!(contracted && node == 1)) {\n'
        '                                    pendingNodes.push(2 * node + 2);\n'
        '                                    pendingNodes.push(2 * node + 1);\n'
        '                                }\n'
        '                            }\n'
        '                            assertEquals(expandedSize, expectedNodes.size());')
replace('assertTrue(node >= 0 && node < N);',
        'assertTrue(node >= 0 && node < N);\n'
        '                                assertEquals(expectedNodes.get(row).intValue(), node);')
replace('assertTrue(observedEpoch >= 0 && observedEpoch <= Q[schedule]);',
        'assertTrue(observedEpoch >= 0 && observedEpoch <= Q[schedule]);\n'
        '                                assertEquals(trace.capturedValueEpoch, observedEpoch);')
replace('+ ",\\\"refresh_requests\\\":" + cycleDriver.cycles',
        '+ ",\\\"refresh_requests\\\":" + cycleDriver.cycles\n'
        '                    + ",\\\"captured_key_epoch\\\":" + trace.capturedKeyEpoch\n'
        '                    + ",\\\"captured_value_epoch\\\":" + trace.capturedValueEpoch\n'
        '                    + ",\\\"expanded_size\\\":" + trace.expandedSize\n'
        '                    + ",\\\"initial_actions\\\":[" + expand + "," + expand + "," + expand + "]"')
with (HERE / 'TestRetryKeyAction.java').open('x') as stream:
    stream.write(text)
for name in ('ConstructSnapshot.java', 'HierarchicalTableImpl.java', 'RetryStudyHooks.java',
             'profile_3.txt', 'certificate_3.json'):
    assert not (HERE / name).exists()
    shutil.copy2(PARENT / name, HERE / name)
print('Prepared Java and inherited core/profile bytes; no native cases run.')
