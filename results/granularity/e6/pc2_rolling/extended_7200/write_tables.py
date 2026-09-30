#!/usr/bin/env python3
"""LaTeX rendering of observed old/new budget rows; no value substitution."""
from pathlib import Path
import csv, json

HERE=Path(__file__).resolve().parent
rows=list(csv.DictReader((HERE/'tables/host_budget_comparison.csv').open()))
assert len(rows)==5
labels={'lazy_none':'Lazy / fine','lazy_transfers':'Lazy / merged','direct_full_none':'Full / fine'}
lines=[r'\begin{table}[ht]',r'\centering',r'\small',r'\begin{tabular}{llrlrrrrr}',
       r'\toprule',r'Host / heap & Variant & Budget (s) & Result & States & Queries & Rank & $|L|$ & Solve+check (s) \\',r'\midrule']
for row in rows:
    def val(k):return f'{int(row[k]):,}' if row[k] else '--'
    status=row['status'].replace('_',r'\_')
    t=f"{float(row['solve_and_internal_check_seconds']):.3f}" if row['solve_and_internal_check_seconds'] else '--'
    lines.append(' & '.join(['Mac / 32g',labels[row['job_id']],f"{int(row['timeout_seconds']):,}",status,
        val('states_discovered'),val('successor_queries'),val('worst_completion_rank'),val('losing_region_states'),t])+r' \\')
lines += [r'\bottomrule',r'\end{tabular}',
 r'\caption{PC2 calibration-setting variant with separate single-trial budgets. The original 1,200\,s rows are retained unchanged; the two 7,200\,s rows are newly authorized trials in fixed order. Full/fine uses Direct-Full with no contract merge. Each timeout applies to the whole JVM, while the reported time is solve plus internal certificate checking. Missing completion counters remain blank. Rank is the maximum returned WIN-certificate rank and $L$ is the returned discovered-state LOSS certificate, not necessarily the full losing region. Mac times are reference values. No Xeon measurements are represented.}',
 r'\label{tab:pc2-extended-budget}',r'\end{table}']
fragment='\n'.join(lines)+'\n'
(HERE/'tables/s4_pc2_extended_budget.tex').write_text(fragment)
standalone='\n'.join([r'\documentclass{article}',r'\usepackage[a4paper,landscape,margin=16mm]{geometry}',r'\usepackage{booktabs}',r'\begin{document}',fragment,
 r'\noindent The fixed solver JAR, diagnostic class and input are byte-identical across these Mac rows. The new campaign changes the budget and output directory only. The existing Xeon plan has a separate 200g heap and is recorded as NOT\_COLLECTED outside this observed table.',r'\end{document}',''])
(HERE/'tables/table_check.tex').write_text(standalone)
print(json.dumps({'status':'GENERATED','rows':len(rows),'tex':'tables/table_check.tex','compilation':'not yet checked'}))
