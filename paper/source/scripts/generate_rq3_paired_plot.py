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


def mebibytes(row, suffix):
    return str(Decimal(row['peak_rss_bytes_' + suffix]) / Decimal(1048576))


def render():
    lines = [r'''% Saved evidence only: every completed fixed-budget Lazy/Direct-Full pair.
\begin{figure}[!htbp]
\centering
\begin{tikzpicture}[x=1cm,y=.31cm,font=\footnotesize]
\definecolor{pairlazy}{RGB}{25,89,135}
\definecolor{pairfull}{RGB}{159,72,20}
% Exact input values are kept in the drawing calls below. All three x axes are log10.
\newcommand{\RQPair}[9]{%
  \pgfkeys{/pgf/fpu=true}
  \pgfmathparse{2.7+.5*ln(#3)/ln(10)}
  \pgfmathfloattofixed{\pgfmathresult}\let\pairlazyx\pgfmathresult
  \pgfmathparse{2.7+.5*ln(#4)/ln(10)}
  \pgfmathfloattofixed{\pgfmathresult}\let\pairfullx\pgfmathresult
  \pgfkeys{/pgf/fpu=false}
  \node[anchor=east] at (2.45,-#1) {#2};
  \draw[black!8] (2.7,-#1)--(5.7,-#1);
  \draw[black!8] (6.3,-#1)--(9.3,-#1);
  \draw[black!50] (\pairlazyx,-#1)--(\pairfullx,-#1);
  \fill[pairlazy] (\pairlazyx,-#1) circle (2pt);
  \draw[pairfull,fill=white,line width=.65pt] ({\pairfullx-.068},-#1-.22) rectangle ({\pairfullx+.068},-#1+.22);
  \draw[black!50] ({6.3+.6*(ln(#5)/ln(10)+2)},-#1)--({6.3+.6*(ln(#6)/ln(10)+2)},-#1);
  \draw[pairlazy,line width=1pt] ({6.3+.6*(ln(#7)/ln(10)+2)},-#1)--({6.3+.6*(ln(#8)/ln(10)+2)},-#1);
  \fill[pairlazy] ({6.3+.6*(ln(#5)/ln(10)+2)},-#1) circle (2pt);
  \draw[pairfull,fill=white,line width=.65pt] ({6.3+.6*(ln(#6)/ln(10)+2)-.068},-#1-.22) rectangle ({6.3+.6*(ln(#6)/ln(10)+2)+.068},-#1+.22);
  \RQFullRange{#1}{#9}% reads the final tenth argument as the full-range maximum.
}
\newcommand{\RQFullRange}[3]{%
  \draw[pairfull,line width=1pt] ({6.3+.6*(ln(#2)/ln(10)+2)},-#1)--({6.3+.6*(ln(#3)/ln(10)+2)},-#1);
}
\node[font=\footnotesize\bfseries] at (4.2,1.65) {Discovered game states};
\node[font=\footnotesize\bfseries] at (7.8,1.65) {Solver time (seconds)};
\node[font=\scriptsize] at (4.2,.72) {exact first-trial count};
\node[font=\scriptsize] at (7.8,.72) {five-run median [min--max]};
\node[font=\footnotesize\bfseries] at (11.4,1.65) {Peak JVM RSS (MiB)};
\node[font=\scriptsize] at (11.4,.72) {five-run median [min--max]};
\newcommand{\RQMemory}[7]{%
  \draw[black!8] (9.9,-#1)--(12.9,-#1);
  \draw[black!50] ({9.9+1.5*(ln(#2)/ln(10)-2)},-#1)--({9.9+1.5*(ln(#3)/ln(10)-2)},-#1);
  \draw[pairlazy,line width=1pt] ({9.9+1.5*(ln(#4)/ln(10)-2)},-#1)--({9.9+1.5*(ln(#5)/ln(10)-2)},-#1);
  \draw[pairfull,line width=1pt] ({9.9+1.5*(ln(#6)/ln(10)-2)},-#1)--({9.9+1.5*(ln(#7)/ln(10)-2)},-#1);
  \fill[pairlazy] ({9.9+1.5*(ln(#2)/ln(10)-2)},-#1) circle (2pt);
  \draw[pairfull,fill=white,line width=.65pt] ({9.9+1.5*(ln(#3)/ln(10)-2)-.068},-#1-.22) rectangle ({9.9+1.5*(ln(#3)/ln(10)-2)+.068},-#1+.22);
}''']
    for i, (model, variant, (lazy, full)) in enumerate(source_pairs()):
        values = [i, LABELS[model] + ' / ' + VARIANTS[variant],
                  lazy['states_discovered'], full['states_discovered'],
                  seconds(lazy, 'median'), seconds(full, 'median'),
                  seconds(lazy, 'min'), seconds(lazy, 'max'),
                  seconds(full, 'min'), seconds(full, 'max')]
        lines.append(r'\RQPair' + ''.join('{' + str(v) + '}' for v in values))
        memory = [i, mebibytes(lazy, 'median'), mebibytes(full, 'median'),
                  mebibytes(lazy, 'min'), mebibytes(lazy, 'max'),
                  mebibytes(full, 'min'), mebibytes(full, 'max')]
        lines.append(r'\RQMemory' + ''.join('{' + str(v) + '}' for v in memory))
    lines.append(r'''\draw (2.7,-13.65)--(5.7,-13.65);
\foreach \power/\tick in {0/1,1/10,2/{$10^2$},3/{$10^3$},4/{$10^4$},5/{$10^5$},6/{$10^6$}}{
  \draw ({2.7+.5*\power},-13.65)--({2.7+.5*\power},-13.9);
  \node[anchor=north] at ({2.7+.5*\power},-14.1) {\tick};
}
\draw (6.3,-13.65)--(9.3,-13.65);
\foreach \power/\tick in {0/{.01},1/{.1},2/1,3/10,4/100,5/1000}{
  \draw ({6.3+.6*\power},-13.65)--({6.3+.6*\power},-13.9);
  \node[anchor=north] at ({6.3+.6*\power},-14.1) {\tick};
}
\draw (9.9,-13.65)--(12.9,-13.65);
\foreach \power/\tick in {0/100,1/1000,2/10000}{
  \draw ({9.9+1.5*\power},-13.65)--({9.9+1.5*\power},-13.9);
  \node[anchor=north] at ({9.9+1.5*\power},-14.1) {\tick};
}
\fill[pairlazy] (3.1,-16) circle (2pt);
\node[anchor=west] at (3.22,-16) {Lazy};
\draw[pairfull,fill=white,line width=.65pt] (4.132,-16.22) rectangle (4.268,-15.78);
\node[anchor=west] at (4.32,-16) {Direct-Full};
\node[anchor=west] at (6.6,-16) {All axes logarithmic; lower is better.};
\end{tikzpicture}
\caption{All \FixedDirectFullPairs{} completed WIN/WIN pairs. Solver time includes checks and excludes frontend, endpoint preparation and JVM startup. Resident set size (RSS) is sampled over whole JVM runs and does not measure heap use. The other 13 Direct-Full contracts time out and are omitted (Figure~\ref{fig:rq3-outcomes}~\cite{FGDUCSAnonymousArtifact}). This compares procedures.}
\label{fig:rq3-paired-absolute}
\Description{Paired plots show game-state counts, solver seconds and sampled peak JVM resident memory in MiB for all 14 contracts completed by both Lazy and Direct-Full. Lazy has a lower state count and lower solver-time and RSS medians for every row; ranges can overlap. Direct-Full timeouts, and contracts with no paired result, are shown in the separate all-outcome grid.}
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
        print('PASS: all 14 paired rows and exact state, time and RSS plotting values match saved evidence.')
    else:
        target.write_text(output)
        print('Saved paired plot with all 14 complete pairs; no solver executed.')
