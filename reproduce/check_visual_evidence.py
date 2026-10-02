"""Read-only visual evidence checks; no generators, TeX, solvers, or file writes.

Drawing values are decoded independently. Cell uses the retained formal
policy; RQ3 uses the original saved summary, including all timing ranges.
Reviewed rendering templates bind values to the displayed labels and symbols.
"""
from collections import Counter
import csv
from decimal import Decimal
from pathlib import Path
import re

MODELS = {'GSM': 'gsm', 'Industry': 'industry', 'MetaSocket': 'metasocket',
          'PowerPlant': 'powerplant', 'PC1': 'productioncell_arms1',
          'PC2': 'productioncell_arms2', 'Railcab': 'railcab',
          'Surveillance': 'surveillance', 'Workflow': 'workflow'}
VARIANTS = {'Base': 'base', 'R1': 'r1', 'R2': 'r2'}
METHODS = ('fg_ducs_otf', 'direct_full')
FIELDS = ('states_discovered', 'successor_queries', 'solver_time_ms_median',
          'solver_time_ms_min', 'solver_time_ms_max', 'measurement_scope',
          'structure_repetition', 'completed_valid_repetitions',
          'peak_rss_bytes_median', 'peak_rss_bytes_min', 'peak_rss_bytes_max')
ACTION_WORDS = {r'\rho_A': r'replace\\empty $A$', r'\rho_B': r'replace\\empty $B$',
                r'm_A': r'move\\to $A$', r'm_B': r'move\\to $B$',
                r'\mathsf{start}': r'start\\new rule',
                r'\mathsf{stop}': r'stop\\old rule', r'j': r'inspect\\at $B$'}


class InvalidVisual(ValueError):
    pass


def require(condition, kind, detail):
    if not condition:
        raise InvalidVisual(kind + ': ' + str(detail))


def clean(text):
    return re.sub(r'(?<!\\)%[^\n]*', '', text)


def norm(text):
    return re.sub(r'\s+', ' ', clean(text)).strip()


def group(text, offset):
    while offset < len(text) and text[offset].isspace():
        offset += 1
    require(offset < len(text) and text[offset] == '{', 'parser', 'Expected literal group')
    start, depth = offset + 1, 1
    offset += 1
    while offset < len(text) and depth:
        escaped = len(text[:offset]) - len(text[:offset].rstrip('\\'))
        if escaped % 2 == 0 and text[offset] in '{}':
            depth += 1 if text[offset] == '{' else -1
        offset += 1
    require(depth == 0, 'parser', 'Unclosed literal group')
    return text[start:offset-1], offset


def loops(source):
    result, text = [], clean(source)
    for match in re.finditer(r'\\foreach\s+([^\n]+?)\s+in\s*', text):
        data, end = group(text, match.end())
        body, end = group(text, end)
        result.append((match[1].strip(), data, body))
    require(len(result) == len(re.findall(r'\\foreach\b', text)), 'parser', 'Unparsed foreach')
    return result


def formal_cell(source):
    states = {}
    for match in re.finditer(r'\\node\[state\]\s*\(([ab]\d+)\)[^\n]*?\{\$\(([on]{2});([AB]);'
                             r'[^\n]*?\)\$\\\\rank (\d+)\};', source):
        name, versions, holder, rank = match.groups()
        require(name not in states, 'formal_duplicate', name)
        states[name] = (tuple({'o': 'old', 'n': 'new'}[v] for v in versions), holder, int(rank))
    edges = re.findall(r'\\draw\[edge\]\s*\(([ab]\d+)\)--node\[action\]'
                       r'\{\$(.*?)\$\}\(([ab]\d+)\);', source)
    require(len(states) == 13 and len(edges) == 11, 'formal_inventory', '13 states / 11 edges')
    require(len(edges) == len(set(edges)), 'formal_duplicate', 'Repeated edge')
    return states, edges


def verify_cell(source, formal):
    expected_states, expected_edges = formal_cell(formal)
    require(Counter(re.findall(r'\\(?:if\w*|else|fi)\b', clean(source))) ==
            Counter({r'\ifx': 2, r'\else': 2, r'\fi': 2}),
            'cell_visibility', 'Only the two reviewed holder-dot branches are permitted')
    data = loops(source)
    require([v for v, _, _ in data] == [r'\x/\av/\bv/\holder/\r',
            r'\left/\right/\word', r'\x/\av/\bv/\holder/\r', r'\left/\right/\word'],
            'cell_loops', 'Exactly two complete state/action paths')
    actual_states, actual_edges = {}, []
    for prefix, state_loop, edge_loop in (('a', data[0], data[1]), ('b', data[2], data[3])):
        require(norm(state_loop[2]) == norm(CELL_STATE_BODY), 'cell_binding',
                'Station labels, version words, holder dot or rank rendering changed')
        require(norm(edge_loop[2]) == norm(CELL_EDGE_BODY), 'cell_binding',
                'Action label or arrow binding changed')
        positions = {}
        for index, row in enumerate(state_loop[1].split(',')):
            fields = row.strip().split('/')
            require(len(fields) == 5, 'cell_state', row)
            x, av, bv, holder, rank = fields
            point, name = Decimal(x), prefix + str(index)
            require(point not in positions, 'cell_position', 'Repeated state position')
            positions[point] = name
            actual_states[name] = ((av, bv), holder, int(rank))
        edges = re.findall(r'([^,/{]+)/([^,/{]+)/\{([^{}]+)\}', edge_loop[1])
        require(len(edges) == len(edge_loop[1].split(',')), 'cell_edge', 'Unparsed action')
        inverse = {norm(word): action for action, word in ACTION_WORDS.items()}
        for left, right, word in edges:
            require(norm(word) in inverse, 'cell_action', word)
            require(Decimal(left) in positions and Decimal(right) in positions,
                    'cell_position', 'Arrow has no matching state')
            actual_edges.append((positions[Decimal(left)], inverse[norm(word)],
                                 positions[Decimal(right)]))
    require(actual_states == expected_states, 'cell_states', 'Version / holder / rank mismatch')
    require(Counter(actual_edges) == Counter(expected_edges), 'cell_edges', 'Action or edge mismatch')
    for text in ('Entry 1: workpiece at $A$', 'Entry 2: workpiece at $B$',
                 'Joint $A+B$ transfer: never enabled.', 'two empty stations',
                 'preserves exactly one workpiece'):
        require(text in source, 'cell_explanation', text)
    return {'states': len(actual_states), 'edges': len(actual_edges),
            'comparison': 'Retained formal policy: versions, holder, rank, actions and endpoints'}


def read_csv(text):
    return list(csv.DictReader(text.splitlines()))


def complete(row):
    truth = lambda x: str(x).lower() == 'true'
    statuses = dict(entry.split(':', 1) for entry in row['statuses'].split(';') if entry)
    return (truth(row['timing_summary_eligible']) and not truth(row['invalid'])
            and not truth(row['inconsistent']) and row['completed_valid_repetitions'] == '5'
            and set(statuses) == set('12345') and set(statuses.values()) <= {'SUCCESS', 'UNREALIZABLE'}
            and len(set(statuses.values())) == 1)


def expected_pairs(summary_text, display_text):
    primary, display = {}, {}
    for target, text in ((primary, summary_text), (display, display_text)):
        for row in read_csv(text):
            key = (row['model_id'], row['target_id'], row['method_id'])
            require(key not in target, 'csv_duplicate', key)
            target[key] = row
    require(set(primary) == set(display) and len(primary) == 135,
            'csv_inventory', 'The same 135 saved cells')
    pairs, comparisons = {}, 0
    for model in MODELS.values():
        for variant in VARIANTS.values():
            rows = [primary[model, variant, method] for method in METHODS]
            if not all(complete(row) for row in rows):
                continue
            for method, row in zip(METHODS, rows):
                key = model, variant, method
                require(all(row[field] == display[key][field] for field in FIELDS),
                        'primary_identity', key)
                require(row['stage1_status'] == 'SUCCESS' and row['structure_repetition'] == '1'
                        and row['measurement_scope'] == 'solve_and_internal_check_lts', 'scope', key)
                comparisons += len(FIELDS)
            values = [Decimal(row['states_discovered']) for row in rows]
            values.extend(Decimal(row['solver_time_ms_median']) / 1000 for row in rows)
            values.extend(Decimal(rows[0]['solver_time_ms_' + s]) / 1000 for s in ('min', 'max'))
            values.extend(Decimal(rows[1]['solver_time_ms_' + s]) / 1000 for s in ('min', 'max'))
            require(0 < values[4] <= values[2] <= values[5] and 0 < values[6] <= values[3] <= values[7],
                    'time_range', key)
            values.extend(Decimal(row['peak_rss_bytes_median']) / 1048576 for row in rows)
            values.extend(Decimal(rows[0]['peak_rss_bytes_' + k]) / 1048576 for k in ('min', 'max'))
            values.extend(Decimal(rows[1]['peak_rss_bytes_' + k]) / 1048576 for k in ('min', 'max'))
            require(0 < values[10] <= values[8] <= values[11] and
                    0 < values[12] <= values[9] <= values[13], 'memory_range', key)
            pairs[model, variant] = tuple(values)
    require(len(pairs) == 14, 'pair_inventory', 'Exactly fourteen eligible pairs')
    return pairs, comparisons


def macro_body(source, name, nargs):
    pattern = r'\\newcommand\{\\' + re.escape(name) + r'\}\[' + str(nargs) + r'\]'
    matches = list(re.finditer(pattern, source))
    require(len(matches) == 1, 'plot_macro', 'One definition for ' + name)
    return group(source, matches[0].end())[0]


def verify_pairs(source, expected):
    require(norm(macro_body(source, 'RQPair', 9)) == norm(RQPAIR_BODY),
            'plot_binding', 'Reviewed state/time/median/range argument binding changed')
    require(norm(macro_body(source, 'RQFullRange', 3)) == norm(RQFULLRANGE_BODY),
            'plot_binding', 'Tenth argument must be the Direct-Full range maximum')
    require(norm(macro_body(source, 'RQMemory', 7)) == norm(RQMEMORY_BODY),
            'plot_binding', 'RSS medians and ranges must bind to the correct method')
    require([(v, norm(d), norm(b)) for v, d, b in loops(source)] == AXIS_LOOPS,
            'plot_axes', 'Logarithmic tick values or their scale mapping changed')
    matches = list(re.finditer(r'(?m)^\\RQPair((?:\{[^{}\n]*\}){10})\s*$', clean(source)))
    require(len(matches) == 14, 'plot_inventory', 'All fourteen calls are required')
    actual, positions, row_keys = {}, set(), {}
    for match in matches:
        values = re.findall(r'\{([^{}]*)\}', match[1])
        index, label = values[:2]
        require(index.isdigit() and int(index) not in positions, 'plot_row', index)
        positions.add(int(index))
        names = label.split(' / ')
        require(len(names) == 2 and names[0] in MODELS and names[1] in VARIANTS, 'plot_label', label)
        key = MODELS[names[0]], VARIANTS[names[1]]
        require(key not in actual, 'plot_duplicate', label)
        actual[key] = tuple(Decimal(value) for value in values[2:])
        row_keys[int(index)] = key
    require(positions == set(range(14)), 'plot_row', 'Every row 0--13 appears once')
    memory_matches = list(re.finditer(r'(?m)^\\RQMemory((?:\{[^{}\n]*\}){7})\s*$', clean(source)))
    require(len(memory_matches) == 14, 'memory_inventory', 'All fourteen memory calls are required')
    memory_rows = set()
    for match in memory_matches:
        values = re.findall(r'\{([^{}]*)\}', match[1])
        index = int(values[0])
        require(index in row_keys and index not in memory_rows, 'memory_row', index)
        memory_rows.add(index)
        actual[row_keys[index]] += tuple(Decimal(value) for value in values[1:])
    require(set(actual) == set(expected), 'plot_coverage', sorted(set(actual) ^ set(expected)))
    require(actual == expected, 'plot_values', [k for k in expected if actual[k] != expected[k]])
    for phrase in ('Discovered game states', 'Solver time (seconds)', 'exact first-trial count',
                   'five-run median [min--max]', 'Peak JVM RSS (MiB)',
                   'All axes logarithmic; lower is better.',
                   'sampled resident memory over the whole JVM run',
                   'not solver-only or heap usage'):
        require(phrase in source, 'plot_units', phrase)
    for phrase in (r'\fill[pairlazy] (3.1,-16) circle (2pt);',
                   r'\node[anchor=west] at (3.22,-16) {Lazy};',
                   r'\draw[pairfull,fill=white,line width=.65pt] (4.132,-16.22) rectangle (4.268,-15.78);',
                   r'\node[anchor=west] at (4.32,-16) {Direct-Full};'):
        require(norm(phrase) in norm(source), 'plot_legend', phrase)
    require(not re.search(r'\\(?:if\w*|else|fi)\b', clean(source)), 'plot_visibility', 'Conditional hiding')
    require(len(re.findall(r'\\RQPair\b', clean(source))) == 15, 'plot_calls', 'Unparsed drawing call')
    require(len(re.findall(r'\\RQMemory\b', clean(source))) == 15,
            'memory_calls', 'Unparsed memory drawing call')
    return {'pairs': len(actual), 'exact_numeric_values': len(actual) * 14,
            'units': 'First-trial integer states; raw solver milliseconds / 1000; raw process RSS bytes / 1048576',
            'timing_and_memory': 'Five valid consistent runs: median, minimum and maximum'}


def verify_placements(main, technical, secondary, promotion, policy):
    sources={'main':main.split(r'\begin{document}',1)[-1],
             'technical':technical.split(r'\begin{document}',1)[-1],
             'secondary':secondary,'promotion':promotion,'policy':policy}
    for name,source in sources.items():
        require(not re.search(r'\\(?:iffalse|iftrue|ifnum|ifx|ifdefined|unless)\b',clean(source)),
                'display_placement', name+' has conditional hiding')
    expected={
        'figures/cell_story_visual.tex': {'main':1},
        'figures/lazy_choices.tex': {'technical':1},
        'figures/rq3_outcome_grid.tex': {'secondary':1},
        'figures/rq3_paired_absolute.tex': {'main':1},
        'technical_fragments/additional_populations.tex': {'technical':1},
        'technical_fragments/promotion_cases.tex': {'technical':1},
        'figures/policy_finite_main.tex': {'policy':1},
        'technical_fragments/policy_interpretation.tex': {'technical':1},
        'technical_fragments/gsm_active_policy.tex': {'technical':1},
        'technical_fragments/gsm_entry_derivation.tex': {'main':1},
        'figures/guarantee_evidence_map.tex': {'main':1},
        'technical_fragments/ducs_cell_complete.tex': {'technical':1},
        'technical_fragments/synthesis_statement.tex': {'main':1},
        'technical_fragments/synthesis_complete_main.tex': {'main':1},
        'technical_fragments/correctness_proof.tex': {'technical':1},
        'technical_fragments/cell_residual_derivation.tex': {'technical':1},
        'technical_fragments/constructed_contracts.tex': {'technical':1},
        'technical_fragments/pc2_all_activation.tex': {'technical':1},
        'technical_fragments/activation_duty_main.tex': {'main':1},
        'technical_fragments/history_scope_main.tex': {'main':1},
        'figures/contract_pipeline_c30.tex': {'main':1},
        'figures/contract_responsibility.tex': {},
        'technical_fragments/contract_adequacy_statement.tex': {'main':1},
        'technical_fragments/contract_adequacy_proof.tex': {'technical':1},
        'technical_fragments/residual_formal.tex': {'technical':1},
        'technical_fragments/performance_scope_details.tex': {'technical':1},
        'figures/contract_interfaces_full.tex': {'technical':1},
        'figures/policy_lifetimes.tex': {'technical':1},
        'technical_fragments/ducs_cell_correspondence.tex': {'main':1},
        'technical_fragments/endpoint_interface.tex': {'main':1},
        'technical_fragments/endpoint_interface_proof.tex': {'technical':1},
        'technical_fragments/gr1_cell_interface.tex': {'technical':1},
    }
    for rel,counts in expected.items():
        pattern=r'\\(?:input|include)\{'+re.escape(rel[:-4])+r'(?:\.tex)?\}'
        for name,source in sources.items():
            require(len(re.findall(pattern,clean(source)))==counts.get(name,0),
                    'display_placement',rel+' in '+name)
    require(r'\ref{ta:policy_interpretation}' in clean(sources['main']),
            'display_placement', 'main reference to ta:policy_interpretation')
    require(clean(sources['technical']).count(r'\label{ta:policy_interpretation}') == 1,
            'display_placement', 'technical label ta:policy_interpretation')
    return {'main': [rel for rel, counts in expected.items() if counts.get('main')],
            'technical_appendix': [rel for rel, counts in expected.items()
                                   if counts.get('technical') or counts.get('secondary')
                                   or counts.get('policy')],
            'retained_unincluded': [rel for rel, counts in expected.items() if not counts],
            'all_designated_inclusions_checked': True}

def verify(paper, primary_summary):
    main = (paper/'main.tex').read_text()
    placements=verify_placements(main,(paper/'technical_appendix.tex').read_text(),
        (paper/'technical_fragments/additional_populations.tex').read_text(),
        (paper/'technical_fragments/promotion_cases.tex').read_text(),
        (paper/'technical_fragments/policy_interpretation.tex').read_text())
    display = (paper / 'build/generated/rq3-cells.csv').read_text()
    formal = (paper / 'figures/cell_policy_paths.tex').read_text()
    expected, comparisons = expected_pairs(primary_summary, display)
    cell = verify_cell((paper / 'figures/cell_story_visual.tex').read_text(), formal)
    pairs = verify_pairs((paper / 'figures/rq3_paired_absolute.tex').read_text(), expected)
    return {'status': 'PASS', 'details': {'cell': cell, 'paired_costs': pairs,
            'primary_fields_equal': comparisons, 'generators_executed': False,
            'display_placements': placements,
            'scope': 'Drawing-to-evidence consistency; visual layout and scientific proof require separate inspection.'}}


# Reviewed rendering bindings; only presentation geometry may be revised explicitly.
CELL_STATE_BODY = '\n  \\node[\\av] at (\\x,.27) {$A$ \\av\\phantom{$\\bullet$}};\n  \\node[\\bv] at (\\x,-.17) {$B$ \\bv\\phantom{$\\bullet$}};\n  \\def\\aholder{A}\\ifx\\holder\\aholder\n    \\fill (\\x+.44,.27) circle (1.7pt);\n  \\else\n    \\fill (\\x+.44,-.17) circle (1.7pt);\n  \\fi\n  \\node[ranklabel] at (\\x,-.63) {rank \\r};\n'
CELL_EDGE_BODY = '\n  \\draw[->] (\\left+.65,.05)--(\\right-.65,.05);\n  \\node[action] at ({(\\left+\\right)/2},.57) {\\word};\n'
RQPAIR_BODY = '%\n  \\pgfkeys{/pgf/fpu=true}\n  \\pgfmathparse{2.7+.5*ln(#3)/ln(10)}\n  \\pgfmathfloattofixed{\\pgfmathresult}\\let\\pairlazyx\\pgfmathresult\n  \\pgfmathparse{2.7+.5*ln(#4)/ln(10)}\n  \\pgfmathfloattofixed{\\pgfmathresult}\\let\\pairfullx\\pgfmathresult\n  \\pgfkeys{/pgf/fpu=false}\n  \\node[anchor=east] at (2.45,-#1) {#2};\n  \\draw[black!8] (2.7,-#1)--(5.7,-#1);\n  \\draw[black!8] (6.3,-#1)--(9.3,-#1);\n  \\draw[black!50] (\\pairlazyx,-#1)--(\\pairfullx,-#1);\n  \\fill[pairlazy] (\\pairlazyx,-#1) circle (2pt);\n  \\draw[pairfull,fill=white,line width=.65pt] ({\\pairfullx-.068},-#1-.22) rectangle ({\\pairfullx+.068},-#1+.22);\n  \\draw[black!50] ({6.3+.6*(ln(#5)/ln(10)+2)},-#1)--({6.3+.6*(ln(#6)/ln(10)+2)},-#1);\n  \\draw[pairlazy,line width=1pt] ({6.3+.6*(ln(#7)/ln(10)+2)},-#1)--({6.3+.6*(ln(#8)/ln(10)+2)},-#1);\n  \\fill[pairlazy] ({6.3+.6*(ln(#5)/ln(10)+2)},-#1) circle (2pt);\n  \\draw[pairfull,fill=white,line width=.65pt] ({6.3+.6*(ln(#6)/ln(10)+2)-.068},-#1-.22) rectangle ({6.3+.6*(ln(#6)/ln(10)+2)+.068},-#1+.22);\n  \\RQFullRange{#1}{#9}% reads the final tenth argument as the full-range maximum.\n'
RQFULLRANGE_BODY = '%\n  \\draw[pairfull,line width=1pt] ({6.3+.6*(ln(#2)/ln(10)+2)},-#1)--({6.3+.6*(ln(#3)/ln(10)+2)},-#1);\n'

RQMEMORY_BODY = '%\n  \\draw[black!8] (9.9,-#1)--(12.9,-#1);\n  \\draw[black!50] ({9.9+1.5*(ln(#2)/ln(10)-2)},-#1)--({9.9+1.5*(ln(#3)/ln(10)-2)},-#1);\n  \\draw[pairlazy,line width=1pt] ({9.9+1.5*(ln(#4)/ln(10)-2)},-#1)--({9.9+1.5*(ln(#5)/ln(10)-2)},-#1);\n  \\draw[pairfull,line width=1pt] ({9.9+1.5*(ln(#6)/ln(10)-2)},-#1)--({9.9+1.5*(ln(#7)/ln(10)-2)},-#1);\n  \\fill[pairlazy] ({9.9+1.5*(ln(#2)/ln(10)-2)},-#1) circle (2pt);\n  \\draw[pairfull,fill=white,line width=.65pt] ({9.9+1.5*(ln(#3)/ln(10)-2)-.068},-#1-.22) rectangle ({9.9+1.5*(ln(#3)/ln(10)-2)+.068},-#1+.22);\n'

AXIS_LOOPS = [('\\power/\\tick', '0/1,1/10,2/{$10^2$},3/{$10^3$},4/{$10^4$},5/{$10^5$},6/{$10^6$}', '\\draw ({2.7+.5*\\power},-13.65)--({2.7+.5*\\power},-13.9); \\node[anchor=north] at ({2.7+.5*\\power},-14.1) {\\tick};'), ('\\power/\\tick', '0/{.01},1/{.1},2/1,3/10,4/100,5/1000', '\\draw ({6.3+.6*\\power},-13.65)--({6.3+.6*\\power},-13.9); \\node[anchor=north] at ({6.3+.6*\\power},-14.1) {\\tick};'), ('\\power/\\tick', '0/100,1/1000,2/10000', '\\draw ({9.9+1.5*\\power},-13.65)--({9.9+1.5*\\power},-13.9); \\node[anchor=north] at ({9.9+1.5*\\power},-14.1) {\\tick};')]


def main():
    import argparse
    import json
    from read_saved_source import read_source
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.artifact_root.resolve()
    logical = 'FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/raw/rq3/summary.csv'
    summary = read_source(root, logical).decode('utf-8')
    print(json.dumps(verify(root/'paper/source', summary), ensure_ascii=False))


if __name__ == '__main__':
    main()
