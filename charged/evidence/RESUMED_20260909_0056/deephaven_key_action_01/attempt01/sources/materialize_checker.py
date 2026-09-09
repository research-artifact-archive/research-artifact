"""Prepare the changed-action checker before native outcomes."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
text = (HERE.parent / 'deephaven_event_graph_01/check_trace.py').read_text()


def replace(old, new):
    global text
    assert text.count(old) == 1, (old[:100], text.count(old))
    text = text.replace(old, new)


replace('"""Author post-outcome checker; reconstructs controller and native work separately."""',
        '"""Author checker fixed before changing-action outcomes; reconstructs native captures and work."""')
replace("SCHEDULES = {k: v for k, v in SCHEDULES.items() if k in ('none', 'v_end_split', 'cross_stage', 'k_full_v_split')}\nQUOTAS = {k: QUOTAS[k] for k in SCHEDULES}\n", '')
replace('    # Independent static-tree DFS.\n',
        "    require(row['initial_actions'] == [3, 3, 3], 'wrong initial Action vector')\n"
        "    require(type(row['captured_key_epoch']) is int and row['captured_key_epoch'] >= 0, 'bad K epoch')\n"
        "    require(type(row['captured_value_epoch']) is int and row['captured_value_epoch'] >= 0, 'bad V epoch')\n"
        "    contracted = row['captured_key_epoch'] % 2 == 1\n"
        "    # Independent DFS of the captured directive view, not the final live key table.\n")
replace('            stack.extend((2 * node + 2, 2 * node + 1))',
        '            if not (contracted and node == 1):\n'
        '                stack.extend((2 * node + 2, 2 * node + 1))')
replace("    require(len(row['rows']) == 16, 'wrong viewport size')", 
        "    require(row['expanded_size'] == len(order) == (17 if contracted else 31), 'wrong expanded size')\n"
        "    require(len(row['rows']) == 16, 'wrong viewport size')")
replace('    successful_v_epoch = None',
        '    successful_k_epoch = successful_v_epoch = None\n    key_updates = []')
replace('                if j == 1:\n                    successful_v_epoch = active[\'begin_epoch\']',
        '                if j == 1:\n                    successful_v_epoch = active[\'begin_epoch\']\n'
        '                else:\n                    successful_k_epoch = active[\'begin_epoch\']')
replace('                if j == 1:\n                    successful_v_epoch = pending[\'begin_epoch\']',
        '                if j == 1:\n                    successful_v_epoch = pending[\'begin_epoch\']\n'
        '                else:\n                    successful_k_epoch = pending[\'begin_epoch\']')
replace("        elif kind in ('START', 'COMPLETE', 'FULL'):",
        "        elif kind == 'KEY_UPDATE':\n"
        "            require(stage == 'W' and pending_writer in ('FULL', 'COMPLETE'), 'unrequested Action mutation')\n"
        "            require(a == len(key_updates) + 1 == completed_cycles + 1, 'Action epoch sequence mismatch')\n"
        "            require((b, c, d) == (3, 4 if a % 2 else 3, 3), 'wrong or unchanged Action mutation')\n"
        "            require((pending_writer == 'COMPLETE') == cycle_open, 'Action mutation at wrong cycle phase')\n"
        "            key_updates.append({'index': idx, 'epoch': a, 'actions': [b, c, d]})\n"
        "        elif kind in ('START', 'COMPLETE', 'FULL'):")
replace("            clock = b\n            writers.append({'index': idx, 'kind': kind, 'before': a, 'after': b})",
        "            if kind != 'START':\n"
        "                require(len(key_updates) == completed_cycles and key_updates[-1]['index'] < idx,\n"
        "                        'cycle completed without exactly one Action mutation')\n"
        "            clock = b\n            writers.append({'index': idx, 'kind': kind, 'before': a, 'after': b})")
replace("    require(epochs[0] == successful_v_epoch and 0 <= epochs[0] <= cycles, 'wrong source epoch for successful V body')",
        "    require(row['captured_key_epoch'] == successful_k_epoch and 0 <= successful_k_epoch <= cycles,\n"
        "            'recorded K capture does not match successful native body')\n"
        "    require(row['captured_value_epoch'] == successful_v_epoch and epochs[0] == successful_v_epoch\n"
        "            and 0 <= successful_v_epoch <= cycles, 'wrong source epoch for successful V body')\n"
        "    require(successful_k_epoch <= successful_v_epoch, 'V predates captured K')\n"
        "    require(len(key_updates) == completed_cycles, 'Action mutation ledger does not cover cycles')")
replace("            'model_value': value(0, 2 * q), 'aborted_bodies':", 
        "            'model_value': value(0, 2 * q), 'captured_key_epoch': successful_k_epoch,\n"
        "            'captured_value_epoch': successful_v_epoch, 'expanded_size': row['expanded_size'],\n"
        "            'key_updates': key_updates, 'aborted_bodies':")
replace("    assert len(rows) == len(expected) == 12 and {r['id'] for r in rows} == expected\n    results, errors = [], []",
        "    assert len(expected) == 36\n"
        "    results, errors = [], []\n"
        "    observed = [row.get('id') for row in rows]\n"
        "    missing = sorted(expected - set(observed))\n"
        "    duplicates = sorted({value for value in observed if observed.count(value) > 1})\n"
        "    if missing or duplicates or set(observed) - expected:\n"
        "        errors.append({'kind': 'denominator', 'missing': missing, 'duplicates': duplicates,\n"
        "                       'unexpected': sorted(set(observed) - expected)})")
replace("base = next(row for row in rows if row['id'] == '3_v_end_split_curve_fast_tie')", 
        "base = next(row for row in rows if row['id'] == '3_k_dir_full_curve_fast_tie')")
replace("for mutation in ('mixed_epoch', 'deleted_update', 'excess_work', 'wrong_policy', 'changed_budget'):",
        "for mutation in ('mixed_epoch', 'deleted_update', 'excess_work', 'wrong_policy', 'changed_budget',\n"
        "                         'wrong_k_epoch', 'wrong_v_epoch', 'wrong_expanded_size', 'unchanged_action'):")
replace("row['events'] = [e for e in row['events'] if e[1] != 'START']", 
        "row['events'] = [e for e in row['events'] if e[1] != 'FULL']")
replace("            else:\n                next(e for e in row['events'] if e[1] == 'POLICY')[2] += 1",
        "            elif mutation == 'changed_budget':\n"
        "                next(e for e in row['events'] if e[1] == 'POLICY')[2] += 1\n"
        "            elif mutation == 'wrong_k_epoch':\n                row['captured_key_epoch'] += 1\n"
        "            elif mutation == 'wrong_v_epoch':\n                row['captured_value_epoch'] += 1\n"
        "            elif mutation == 'wrong_expanded_size':\n                row['expanded_size'] = 31\n"
        "            else:\n                next(e for e in row['events'] if e[1] == 'KEY_UPDATE')[4] = 3")
replace("'classification': 'author post-outcome checker, not independent evaluation or source proof'", 
        "'classification': 'author checker fixed before outcomes, not independent evaluation or source proof'")
replace("'denominator': 12, 'checked': len(results), 'errors': errors,", 
        "'denominator': 36, 'observed_rows': len(rows), 'missing_ids': missing,\n"
        "              'checked': len(results), 'errors': errors,")
with (HERE / 'check_trace.py').open('x') as stream:
    stream.write(text)
print('Prepared changing-action checker; no raw input read.')
