"""Read-only verification of the five displayed Cell requirement bands.

Expected monitor values come from the retained formal policy, independently of
the drawn band coordinates. No candidate code, generators or solvers execute.
"""
from decimal import Decimal
from pathlib import Path
import re

import check_visual_evidence as base

require = base.require

RENDERING = r'''
  \draw[draw=black!45,fill=#4,rounded corners=1pt] (#1,#3) rectangle (#2,{#3-.32});
  \node[font=\footnotesize] at ({(#1+#2)/2},{#3-.16}) {#5};
'''
LABELS = {
    'Old rule: inspection forbidden': ('old', 'black!7', Decimal('-.91')),
    'New: inspection pending': ('pending', 'orange!13', Decimal('-1.32')),
    'New: inspection clear': ('clear', 'blue!10', Decimal('-1.32')),
    r'New: clear ($B$ empty at new-start)': ('clear', 'blue!10', Decimal('-1.32')),
}


def formal_monitors(formal):
    states, edges = base.formal_cell(formal)
    result = {}
    pattern = (r'\\node\[state\]\s*\(([ab]\d+)\)[^\n]*?'
               r'\{\$\([on]{2};[AB];([^\n]+?)\)\$\\\\rank \d+\};')
    for match in re.finditer(pattern, base.clean(formal)):
        name, monitors = match.groups()
        monitors = monitors.replace('{', '').replace('}', '')
        require(name not in result and len(monitors) == 2, 'band_formal', name)
        old, new = monitors
        require(old in ('k', '-') and new in ('c', 'd', '-'), 'band_formal', monitors)
        result[name] = {'old_active': old == 'k', 'new_active': new != '-',
                        'inspection': {'c': 'clear', 'd': 'pending', '-': 'inactive'}[new]}
    require(set(result) == set(states), 'band_formal', 'All thirteen formal monitor pairs')
    return result, edges


def bands_in(text):
    bands = []
    for match in re.finditer(r'\\CellRuleBand\b', text):
        offset, fields = match.end(), []
        for _ in range(5):
            value, offset = base.group(text, offset)
            fields.append(value)
        left, right, y, color, label = fields
        require(label in LABELS, 'band_label', label)
        kind, wanted_color, wanted_y = LABELS[label]
        a, b, h = Decimal(left), Decimal(right), Decimal(y)
        require(all(n.is_finite() for n in (a, b, h)) and a < b,
                'band_geometry', fields)
        require(color == wanted_color and h == wanted_y, 'band_binding', fields)
        bands.append({'kind': kind, 'left': a, 'right': b})
    return bands


def verify_bands(source, formal):
    text = base.clean(source)
    require(base.norm(base.macro_body(text, 'CellRuleBand', 5)) == base.norm(RENDERING),
            'band_binding', 'Reviewed coordinate/fill/label rendering changed')
    require(len(re.findall(r'\\(?:newcommand|renewcommand|providecommand)\{\\CellRuleBand\}', text)) == 1,
            'band_binding', 'Exactly one band macro definition')
    require(len(re.findall(r'\\CellRuleBand\b', text)) == 6,
            'band_inventory', 'Five calls plus one definition')
    scope = r'\begin{scope}[yshift=-3.42cm]'
    require(text.count(scope) == 1 and text.count(r'\end{scope}') == 1,
            'band_scope', 'One reviewed second-path scope')
    upper, lower = text.split(scope)
    lower, tail = lower.split(r'\end{scope}')
    # The macro definition occurs before the figure: strip it before call parsing.
    definition = re.search(r'\\newcommand\{\\CellRuleBand\}\[5\]', upper)
    _, end = base.group(upper, definition.end())
    upper = upper[:definition.start()] + upper[end:]
    require(not re.search(r'\\CellRuleBand\b', tail), 'band_scope', 'Band outside either path')
    by_path = {'a': bands_in(upper), 'b': bands_in(lower)}
    require([b['kind'] for b in by_path['a']] == ['old', 'pending', 'clear']
            and [b['kind'] for b in by_path['b']] == ['old', 'clear'],
            'band_inventory', 'Three upper and two lower requirement bands')
    state_loops = [loop for loop in base.loops(text) if loop[0] == r'\x/\av/\bv/\holder/\r']
    require(len(state_loops) == 2, 'band_states', 'Two complete state paths')
    points = {}
    for prefix, loop in zip(('a', 'b'), state_loops):
        for index, row in enumerate(loop[1].split(',')):
            fields = row.strip().split('/')
            require(len(fields) == 5, 'band_states', row)
            points[prefix + str(index)] = Decimal(fields[0])
    expected, edges = formal_monitors(formal)
    require(set(points) == set(expected), 'band_states', 'The thirteen formal vertices')
    actual = {}
    for name, x in points.items():
        require(x.is_finite(), 'band_states', name)
        covering = [band['kind'] for band in by_path[name[0]] if band['left'] <= x <= band['right']]
        old = [kind for kind in covering if kind == 'old']
        new = [kind for kind in covering if kind != 'old']
        require(len(old) <= 1 and len(new) <= 1, 'band_overlap', name)
        actual[name] = {'old_active': bool(old), 'new_active': bool(new),
                        'inspection': new[0] if new else 'inactive'}
    require(actual == expected, 'band_states', [name for name in expected if actual[name] != expected[name]])
    boundaries = {}
    for prefix in ('a', 'b'):
        midpoints = {action: (points[left] + points[right]) / 2
                     for left, action, right in edges if left.startswith(prefix)}
        start, stop = midpoints[r'\mathsf{start}'], midpoints[r'\mathsf{stop}']
        require(start == Decimal('4.5') and stop == Decimal('6.3'), 'band_boundary', prefix)
        old, first_new = by_path[prefix][:2]
        require(old['right'] == stop and first_new['left'] == start,
                'band_boundary', prefix + ': new-start/old-stop')
        require(old['left'] == min(x for name, x in points.items() if name.startswith(prefix)) - Decimal('.62'),
                'band_boundary', prefix + ': old entry coverage')
        require(by_path[prefix][-1]['right'] == max(x for name, x in points.items() if name.startswith(prefix)) + Decimal('.62'),
                'band_boundary', prefix + ': new target coverage')
        boundaries[prefix] = {'start': str(start), 'stop': str(stop)}
        if prefix == 'a':
            inspect = midpoints['j']
            require(inspect == Decimal('8.1') and first_new['right'] == inspect
                    and by_path[prefix][2]['left'] == inspect,
                    'band_boundary', 'Inspection alone clears pending at 8.1')
            boundaries[prefix]['inspect'] = str(inspect)
    return {'band_count': 5, 'vertices': 13, 'formal_edges': len(edges),
            'actual_vertex_monitors': actual, 'command_midpoint_boundaries': boundaries,
            'comparison': 'Band coverage decoded independently against retained formal monitor pairs',
            'candidate_code_executed': False, 'visual_layout': 'REVIEW_REQUIRED'}


def verify(root):
    paper = root/'paper/source'
    formal = (paper/'figures/cell_policy_paths.tex').read_text()
    return {'status': 'PASS', 'details': verify_bands(
        (paper/'figures/cell_story_visual.tex').read_text(), formal)}


def main():
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(verify(args.artifact_root.resolve()), indent=2))


if __name__ == '__main__':
    main()
