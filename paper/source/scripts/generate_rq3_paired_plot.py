"""Plot all fixed-budget Lazy/Direct-Full completed pairs from saved evidence."""
import argparse
import csv
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    'gsm': 'GSM', 'industry': 'Industry', 'metasocket': 'MetaSocket',
    'powerplant': 'PowerPlant', 'productioncell_arms1': 'PC1',
    'productioncell_arms2': 'PC2', 'railcab': 'Railcab',
    'surveillance': 'Surveillance', 'workflow': 'Workflow',
}
VARIANTS = {'base': 'Base', 'r1': 'R1', 'r2': 'R2'}
METHODS = ('fg_ducs_otf', 'direct_full')


def source_pairs():
    rows = list(csv.DictReader((ROOT / 'build/generated/rq3-cells.csv').open()))
    cells = {(r['model_id'], r['target_id'], r['method_id']): r for r in rows}
    assert len(cells) == len(rows) == 135
    pairs = []
    for model in LABELS:
        for variant in VARIANTS:
            pair = [cells[model, variant, method] for method in METHODS]
            if not all(r['display_complete_five'] == 'True' for r in pair):
                continue
            assert all(r['completed_valid_repetitions'] == '5' for r in pair)
            assert all(r['effective_stage1_status'] == 'SUCCESS' for r in pair)
            assert all(r['structure_repetition'] == '1' for r in pair)
            assert all(r['measurement_scope'] == 'solve_and_internal_check_lts' for r in pair)
            pairs.append((model, variant, pair))
    assert len(pairs) == 14
    return pairs


def seconds(row, suffix):
    # The source column is milliseconds. Do not convert the already scaled
    # display_solver_time_ms_* columns a second time.
    return str(Decimal(row['solver_time_ms_' + suffix]) / Decimal(1000))


def render():
    lines = [r'''% Saved evidence only: every completed fixed-budget Lazy/Direct-Full pair.
\begin{figure}[!htbp]
\centering
\begin{tikzpicture}[x=1cm,y=.31cm,font=\footnotesize]
\definecolor{pairlazy}{RGB}{25,89,135}
\definecolor{pairfull}{RGB}{159,72,20}
% Exact input values are kept in the drawing calls below. Both x axes are log10.
\newcommand{\RQPair}[9]{%
  \pgfkeys{/pgf/fpu=true}
  \pgfmathparse{2.8+.6*ln(#3)/ln(10)}
  \pgfmathfloattofixed{\pgfmathresult}\let\pairlazyx\pgfmathresult
  \pgfmathparse{2.8+.6*ln(#4)/ln(10)}
  \pgfmathfloattofixed{\pgfmathresult}\let\pairfullx\pgfmathresult
  \pgfkeys{/pgf/fpu=false}
  \node[anchor=east] at (2.55,-#1) {#2};
  \draw[black!8] (2.8,-#1)--(6.4,-#1);
  \draw[black!8] (7.1,-#1)--(10.7,-#1);
  \draw[black!50] (\pairlazyx,-#1)--(\pairfullx,-#1);
  \fill[pairlazy] (\pairlazyx,-#1) circle (2pt);
  \draw[pairfull,fill=white,line width=.65pt] ({\pairfullx-.068},-#1-.22) rectangle ({\pairfullx+.068},-#1+.22);
  \draw[black!50] ({7.1+.72*(ln(#5)/ln(10)+2)},-#1)--({7.1+.72*(ln(#6)/ln(10)+2)},-#1);
  \draw[pairlazy,line width=1pt] ({7.1+.72*(ln(#7)/ln(10)+2)},-#1)--({7.1+.72*(ln(#8)/ln(10)+2)},-#1);
  \fill[pairlazy] ({7.1+.72*(ln(#5)/ln(10)+2)},-#1) circle (2pt);
  \draw[pairfull,fill=white,line width=.65pt] ({7.1+.72*(ln(#6)/ln(10)+2)-.068},-#1-.22) rectangle ({7.1+.72*(ln(#6)/ln(10)+2)+.068},-#1+.22);
  \RQFullRange{#1}{#9}% reads the final tenth argument as the full-range maximum.
}
\newcommand{\RQFullRange}[3]{%
  \draw[pairfull,line width=1pt] ({7.1+.72*(ln(#2)/ln(10)+2)},-#1)--({7.1+.72*(ln(#3)/ln(10)+2)},-#1);
}
\node[font=\small\bfseries] at (4.6,1.65) {Discovered game states};
\node[font=\small\bfseries] at (8.9,1.65) {Solver time (seconds)};
\node at (4.6,.72) {exact first-trial count};
\node at (8.9,.72) {five-run median [min--max]};''']
    for i, (model, variant, (lazy, full)) in enumerate(source_pairs()):
        values = [i, LABELS[model] + ' / ' + VARIANTS[variant],
                  lazy['states_discovered'], full['states_discovered'],
                  seconds(lazy, 'median'), seconds(full, 'median'),
                  seconds(lazy, 'min'), seconds(lazy, 'max'),
                  seconds(full, 'min'), seconds(full, 'max')]
        lines.append(r'\RQPair' + ''.join('{' + str(v) + '}' for v in values))
    lines.append(r'''\draw (2.8,-13.65)--(6.4,-13.65);
\foreach \power/\tick in {0/1,1/10,2/{$10^2$},3/{$10^3$},4/{$10^4$},5/{$10^5$},6/{$10^6$}}{
  \draw ({2.8+.6*\power},-13.65)--({2.8+.6*\power},-13.9);
  \node[anchor=north] at ({2.8+.6*\power},-14.1) {\tick};
}
\draw (7.1,-13.65)--(10.7,-13.65);
\foreach \power/\tick in {0/{.01},1/{.1},2/1,3/10,4/100,5/1000}{
  \draw ({7.1+.72*\power},-13.65)--({7.1+.72*\power},-13.9);
  \node[anchor=north] at ({7.1+.72*\power},-14.1) {\tick};
}
\fill[pairlazy] (3.1,-16) circle (2pt);
\node[anchor=west] at (3.22,-16) {Lazy};
\draw[pairfull,fill=white,line width=.65pt] (4.132,-16.22) rectangle (4.268,-15.78);
\node[anchor=west] at (4.32,-16) {Direct-Full};
\node[anchor=west] at (6.6,-16) {Both axes logarithmic; lower is better.};
\end{tikzpicture}
\caption{Absolute costs for all \FixedDirectFullPairs{} completed Lazy/Direct-Full pairs. Each row is WIN/WIN; Lazy explores fewer states and uses less solver time, with varying gaps. Solver time includes checking but excludes frontend, endpoint preparation and JVM startup. The other 13 Direct-Full contracts time out (Figure~\ref{fig:rq3-outcomes}); they have no point here. This compares complete same-game procedures, not one isolated search factor.}
\label{fig:rq3-paired-absolute}
\Description{Paired plots show game-state counts and solver seconds for all 14 contracts completed by both Lazy and Direct-Full. Lazy is lower on both axes for every row. Direct-Full timeouts, and contracts with no paired result, are shown in the separate all-outcome grid.}
\end{figure}
''')
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    target = ROOT / 'figures/rq3_paired_absolute.tex'
    output = render()
    if args.check:
        assert target.read_text() == output, 'Saved drawing differs from fixed CSV'
        print('PASS: all 14 paired rows and exact plotting values match saved evidence.')
    else:
        target.write_text(output)
        print('Saved paired plot with all 14 complete pairs; no solver executed.')
