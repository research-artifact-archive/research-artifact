#!/usr/bin/env python3
"""Check the PC2 phase table, activation memory and saved path without a solver.

This establishes saved-data consistency for one model path. It does not validate
all real histories, the frontend implementation, or physical execution.
"""
import argparse
import json
from pathlib import Path
import re

EXPECTED_TABLE = '\\begin{table}[!htbp]\n\\caption{One saved \\PCTwoTraceEvents{}-event PC2-Rolling path. O/N: old/new; ARM: unprocessed workpiece; CAL: its calibration counterpart. Ordinary observers stay zero.}\n\\label{tab:pc2-saved-path}\n\\centering\\small\n\\begin{tabular}{@{}p{.41\\linewidth}llrr@{}}\\toprule\nReached after & Arm 1 & Arm 2 & Available & Rank\\\\\\midrule\nUpdate entry & O/initial & O/initial & 2 & 31\\\\\nTwo arrivals, twelve old stops & O/ARM & O/ARM & 2 & 17\\\\\nTransfer arm 1 & N/CAL & O/ARM & 1 & 16\\\\\nCalibration completion 1 & N/ARM & O/ARM & 2 & 15\\\\\nTransfer arm 2 & N/ARM & N/CAL & 1 & 14\\\\\nCalibration completion 2 & N/ARM & N/ARM & 2 & 13\\\\\nThirteen new starts: handover & N/ARM & N/ARM & 2 & 0\\\\\\bottomrule\n\\end{tabular}\n\\par\\smallskip{\\footnotesize At handover, all 13 new monitors are 0 and no command remains; the matched endpoint has both arms operational. Certificate identifiers are in Technical Appendix~\\ref{ta:pc2_history_boundary}. This path supplies no timing and does not replace all-entry/all-outcome checking.}\n\\end{table}\n'

def verify_text(certificate, input_source, table_source):
    """Inspect immutable saved data only; no search, Java or benchmark is run."""
    data = certificate
    states = {s['id']: s for s in data['states']}
    if len(states) != len(data['states']) or data['decision'] != 'WIN' or not states[126]['initial']:
        raise ValueError('PC2 validation path requires unique states, a WIN record and its saved entry flag')
    # Check the all-entry rank claim against the saved graph, separately from the
    # illustrative rank-31 path below. This performs no synthesis or measurement.
    edges = data['strategy_edges']
    entries = [q for q, state in states.items() if state['initial']]
    if (len(states), len(edges), len(entries)) != (381, 522, 126):
        raise ValueError('PC2 all-entry certificate census changed')
    if max(s['rank'] for s in states.values()) != 37 or max(states[q]['rank'] for q in entries) != 37:
        raise ValueError('PC2 maximum state/entry rank differs from 37')
    successors = {q: [] for q in states}
    for a, _, b in edges:
        if a not in states or b not in states or states[a]['rank'] <= states[b]['rank']:
            raise ValueError('PC2 certificate is not closed with strictly decreasing ranks')
        successors[a].append(b)
    reached = set(entries)
    pending = list(entries)
    while pending:
        for q in successors[pending.pop()]:
            if q not in reached:
                reached.add(q); pending.append(q)
    if reached != set(states):
        raise ValueError('PC2 certificate contains a state outside all-entry reachability')
    longest = {}
    for q in sorted(states, key=lambda q: states[q]['rank']):
        if states[q]['goal']:
            longest[q] = 0
        else:
            if not successors[q]:
                raise ValueError('PC2 certificate contains a non-goal deadlock')
            longest[q] = 1 + max(longest[b] for b in successors[q])
    if max(longest[q] for q in entries) != 37:
        raise ValueError('PC2 longest entry-to-goal path differs from 37')
    path = [126,139,141,142,143,144,145,146,147,148,149,150,151,152,153,114,
            22,21,20,19,18,17,16,15,14,13,12,11,10,9,8,7]
    events = []
    for a, b in zip(path, path[1:]):
        matching = [e for e in data['strategy_edges'] if e[0] == a and e[2] == b]
        if len(matching) != 1 or states[a]['rank'] != states[b]['rank'] + 1:
            raise ValueError('PC2 saved path must follow unique certified edges with strict rank decrease')
        events.append(matching[0][1])
    if (events[:2] != ['in.1','in.2'] or
            not all(e.startswith('stopOldSpec_') for e in events[2:14]) or
            events[14:18] != ['reconfigure_PRODUCTION_CELL_1','calibrated.1','reconfigure_PRODUCTION_CELL_2','calibrated.2'] or
            not all(e.startswith('startNewSpec_') for e in events[18:])):
        raise ValueError('PC2 phase event labels differ from the saved two-arrival, twelve-stop, sequential-transfer, thirteen-start path')
    rows = [(126,('OLD',0),('OLD',0),2,31),
            (153,('OLD',1),('OLD',1),2,17),
            (114,('NEW',6),('OLD',1),1,16),
            (22,('NEW',1),('OLD',1),2,15),
            (21,('NEW',1),('NEW',6),1,14),
            (20,('NEW',1),('NEW',1),2,13),
            (7,('NEW',1),('NEW',1),2,0)]
    for q, arm1, arm2, available, rank in rows:
        s = states[q]
        actual = (tuple(s['physical'][0][:2]),tuple(s['physical'][1][:2]),s['physical_operational_arms'],s['rank'])
        if actual != (arm1,arm2,available,rank):
            raise ValueError('PC2 table tuple or rank differs from saved certificate at ' + str(q))
    for q in path:
        if states[q]['physical'][0][2] != [0]*24 or states[q]['physical'][1][2] != [] or not states[q]['safe']:
            raise ValueError('PC2 saved ordinary observers or safe-state flag differ')
    goal = states[7]
    new_testers = {k:v for k,v in goal['testers'].items() if k.startswith('new:')}
    if len(new_testers) != 13 or set(new_testers.values()) != {0} or goal['pending'] != [] or not goal['goal']:
        raise ValueError('PC2 saved goal must have thirteen zero-valued new testers and no pending commands')
    if data['goal_matches'].get('7') != 'new-00000009':
        raise ValueError('PC2 saved endpoint identity differs')
    start = 'startNewSpec_P_NEW_OUT_IF_FINISHED_1'
    marker = 'new:P_NEW_OUT_IF_FINISHED_1:7'
    activation_prefix = events[:path.index(12)]
    if len(activation_prefix) != 26 or activation_prefix[-1] != start or states[12]['testers'].get(marker) != 0 or marker in states[13]['testers']:
        raise ValueError('PC2 activation edge and installed memory differ from saved data')
    if any(x in activation_prefix for x in ('out.1','drillOk.1','cleanOk.1','paintOk.1')):
        raise ValueError('PC2 exhibited prefix must retain all three initially false completion fluents')
    source = input_source
    for phrase in ('fluent Drilled[i:Arms] = <drillOk[i],reset[i]>',
                   'fluent Cleaned[i:Arms] = <cleanOk[i],reset[i]>',
                   'fluent Painted[i:Arms] = <paintOk[i],reset[i]>',
                   'assert NEW_OUT_IF_FINISHED_1 = (out[1] -> (Drilled[1] && Cleaned[1] && Painted[1]))',
                   'ltl_property P_NEW_OUT_IF_FINISHED_1 = []NEW_OUT_IF_FINISHED_1'):
        if source.count(phrase) != 1:
            raise ValueError('PC2 source requirement/fluent definition changed')
    table = table_source
    expected_table = EXPECTED_TABLE
    rendered = []
    for line in table.splitlines():
        fields = [x.strip() for x in line.split('&')]
        if len(fields) != 5 or fields[0] == 'Reached after':
            continue
        rank = re.fullmatch(r'([0-9]+)\\\\(?:\\bottomrule)?', fields[4])
        if rank is None or not fields[3].isdigit():
            raise ValueError('PC2 table contains an unparsed numeric row')
        rendered.append((fields[0], fields[1], fields[2], int(fields[3]), int(rank[1])))
    labels = ['Update entry', 'Two arrivals, twelve old stops', 'Transfer arm 1',
              'Calibration completion 1', 'Transfer arm 2', 'Calibration completion 2',
              'Thirteen new starts: handover']
    physical_names = {('OLD',0):'O/initial', ('OLD',1):'O/ARM', ('NEW',1):'N/ARM', ('NEW',6):'N/CAL'}
    derived = [(label, physical_names[a], physical_names[b], available, rank)
               for label, (_, a, b, available, rank) in zip(labels, rows)]
    if rendered != derived:
        raise ValueError('PC2 rendered table rows differ from the independently checked certificate tuples')
    if table != expected_table:
        raise ValueError('PC2 path rendering must retain its explicitly reviewed table binding')
    return {'evidence': 'Distributed saved validation certificate and calibration input',
            'path_state_ids': path, 'event_count': len(events), 'phase_rows': len(rows),
            'rendered_rows_independently_checked': True,
            'activation_prefix_length': len(activation_prefix), 'installed_new_memory': 0,
            'handover_target': 'new-00000009', 'ordinary_observers': '0^24 on first component; empty on second',
            'scope': 'One nonempty saved model path and source formula; not actual-history nonemptiness for all occurrences, timing evidence, or independent frontend/runtime certification',
            'new_solver_or_experiment_executed': False}


EXPECTED_PATH_IDS = "The path in Table~\\ref{tab:pc2-saved-path} starts at $q_{126}$ and ends at $q_7$, whose handover target is \\texttt{new-00000009}. All 13 new monitors are 0 there and no command remains. Its prefix to $q_{12}$ has two arrivals, twelve stops, four transfer/completion events and eight starts, with no $out_1$ or successful tool result."

def verify_history_pointer(appendix):
    if appendix.count(EXPECTED_PATH_IDS) != 1:
        raise ValueError("PC2 relocated certificate identifiers or observer-prefix explanation changed")

def verify(root):
    from read_saved_source import read_source
    logical='FSE2027_SUBMISSION_20260914/experiments/witness_20260929/e6/pc2_rolling/v2/'
    certificate=json.loads(read_source(root,logical+'validation/export/lazy_none/certificate.json'))
    source=read_source(root,logical+'inputs/ProductionCell_Arms2_Calibration.lts').decode()
    table=(root/'paper/source/figures/pc2_saved_path.tex').read_text()
    verify_history_pointer((root/'paper/source/technical_fragments/pc2_history_boundary.tex').read_text())
    return {'status':'PASS','details':verify_text(certificate,source,table)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    print(json.dumps(verify(args.artifact_root.resolve()),indent=2))


if __name__=='__main__':main()
