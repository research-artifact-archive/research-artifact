"""Render the existing fixed-budget outcomes; never execute a solver."""
import argparse
from collections import Counter
import csv
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
METHODS = [
    ('fg_ducs_otf', 'Lazy', 'Lazy'),
    ('fg_ducs_otf_update_first', 'Update-first', 'UpdateFirst'),
    ('fg_ducs_otf_eager_controllable', 'Eager', 'Eager'),
    ('direct_full', 'Direct-Full', 'DirectFull'),
]
MODELS = [
    ('gsm', 'GSM'), ('industry', 'Industry'), ('metasocket', 'MetaSocket'),
    ('powerplant', 'PowerPlant'), ('productioncell_arms1', 'PC1'),
    ('productioncell_arms2', 'PC2'), ('railcab', 'Railcab'),
    ('surveillance', 'Surveillance'), ('workflow', 'Workflow'),
]
TARGETS = [('base', 'B'), ('r1', 'R1'), ('r2', 'R2')]
STYLE = {'SUCCESS': ('win', 'W', 'Win'),
         'UNREALIZABLE': ('loss', 'L', 'Loss'),
         'TIMEOUT': ('timeout', 'T', 'TO')}

def render():
    rows = list(csv.DictReader((ROOT / 'build/generated/rq3-cells.csv').open()))
    macros = dict(re.findall(r'\\newcommand\{\\([A-Za-z]+)\}\{([^{}]*)\}',
                            (ROOT / 'build/generated/base-v3-fixed-macros.tex').read_text()))
    cells = {}
    for row in rows:
        if row['method_id'] not in {x[0] for x in METHODS}:
            continue
        key = row['method_id'], row['model_id'], row['target_id']
        assert key not in cells, key
        assert row['effective_stage1_status'] in STYLE, row
        cells[key] = row['effective_stage1_status']
    assert len(cells) == 108
    for method, _, macro in METHODS:
        counts = Counter(value for key, value in cells.items() if key[0] == method)
        for status, (_, _, suffix) in STYLE.items():
            assert counts[status] == int(macros['Fixed' + macro + suffix])
    
    lines = [r'''% Generated from the fixed rq3-cells.csv and checked against its outcome macros.
\begin{figure}[!htbp]
\centering
\begin{tikzpicture}[x=.48cm,y=.39cm,font=\small,
    cell/.style={draw=white,minimum width=4.5mm,minimum height=3.6mm,inner sep=0pt,font=\footnotesize},
    win/.style={cell,fill=blue!13,text=black},
    loss/.style={cell,fill=orange!38,text=black},
    timeout/.style={cell,fill=black!9,text=black}]
\node[anchor=east,font=\footnotesize] at (-.7,.75) {Adapted input};''']
    for group, (method, label, _) in enumerate(METHODS):
        x = group * 3.55
        lines.append(rf'\node[font=\small\bfseries] at ({x+1:.2f},1.45) {{{label}}};')
        for col, (_, target) in enumerate(TARGETS):
            lines.append(rf'\node[font=\footnotesize] at ({x+col:.2f},.75) {{{target}}};')
        for row_index, (model, _) in enumerate(MODELS):
            for col, (target, _) in enumerate(TARGETS):
                style, letter, _ = STYLE[cells[method, model, target]]
                lines.append(rf'\node[{style}] at ({x+col:.2f},{-row_index:.2f}) {{{letter}}};')
    for row_index, (_, label) in enumerate(MODELS):
        lines.append(rf'\node[anchor=east] at (-.7,{-row_index:.2f}) {{{label}}};')
    lines.append(r'''\node[anchor=west,font=\footnotesize] at (-3.2,-9.25)
  {W: WIN \quad L: LOSS \quad T: timeout \qquad B: Base; R1/R2: interval variants};
\end{tikzpicture}
\caption{Every fixed-budget contract--method outcome. Each tile is one of the same
\ApplicationModels{} inputs $\times$ three requirement variants, under a
1,200~s cap and 64~GiB heap. WIN and LOSS are completed decisions; timeout leaves
feasibility unresolved. The methods change exploration, keeping entries,
successors and goals fixed. The comparison evaluates complete exploration procedures.
Workflow/R2's Direct-Full tile uses the recorded same-setting timeout after
interruption; both attempts are retained.}
\label{fig:rq3-outcomes}
\Description{A grid of all 27 contracts for each of four methods. Lazy has 25 WIN,
one LOSS at Industry R1 and one timeout at PC2 R2. Update-first has 23 WIN, one LOSS
and three timeouts. Eager has 17 WIN and ten timeouts. Direct-Full has 14 WIN and
13 timeouts. Every completed paired decision agrees.}
\end{figure}
''')
    output = '\n'.join(lines)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    target = ROOT / 'figures/rq3_outcome_grid.tex'
    output = render()
    if args.check:
        assert target.read_text() == output, 'Saved outcome grid differs from fixed evidence'
        print('PASS: all 108 outcome cells match fixed evidence and outcome macros.')
    else:
        target.write_text(output)
        print('Saved 108 outcome cells; all counts match fixed evidence macros.')
