#!/usr/bin/env python3
"""Create the small main-paper table solely from the checked comparison index."""
from pathlib import Path
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo
import csv, hashlib, json

E6=Path(__file__).resolve().parents[1]
OUT=E6/'integration'
INDEX=E6/'results_index.csv'
records=list(csv.DictReader(INDEX.open()))
def family(name): return [r for r in records if r['family']==name]
def classes(rows): return dict(Counter(r['class'] for r in rows))
def one(name,params): return next(r for r in family(name) if r['params']==params)
def escape(s): return s.replace('_',r'\_').replace('&',r'\&')

cell=family('Cell_n'); rolling=family('Rolling'); canary=family('Canary')
policy=family('Policy'); db=family('DB-Rolling'); pc=family('PC2-Rolling'); threads=family('Threads')
assert classes(cell)=={'witness':9} and sorted(int(r['params'][2:]) for r in cell)==list(range(2,11))
assert classes(rolling)=={'witness':15} and sum(int(r['threshold_tested_k_count']) for r in rolling)==70
assert all(r['threshold_check']=='PASS' for r in rolling)
assert classes(canary)=={'witness':15} and classes(policy)=={'witness':1}
assert classes(db)=={'witness':1,'both_loss':1}
assert classes(threads)=={'both_win':10,'both_loss':10}
assert one('DB-Rolling','n=3;m=2')['class']=='witness'
assert one('DB-Rolling','n=3;m=3')['class']=='both_loss'
assert len(pc)==1

specs=[
 ('Cell_n',r'Cell$_n$','M1','L1,L3','W','L',r'$n=2\ldots10$ (E4)',cell,'../e4_2_corrected/table_s1_cell_ring.tex;../e4_2_corrected/table_s4_cell_ring.tex'),
 ('Rolling',r'Rolling$(n,m,k)$','M2','L1,L3','W','L',r'W iff $k\le n-m$',rolling,'rolling/v1/tables/threshold.csv;rolling/v1/tables/results.tex;rolling_scale/v1/tables/scale_table.tex'),
 ('Canary','Canary','M3','L1,L2,L3','W','L',r'set-valued; recovery',canary,'canary/v1/tables/table_canary.tex'),
 ('Policy',r'Policy$(2)$','M4','boundary','W','L',r'opposing boundary orders',policy,'policy/v2/tables/policy_comparison.tex'),
 ('DB-Rolling','DB-Rolling','M1,M2','L1,L3','W/L','L/L',r'$m=2/3$, respectively',db,'db_rolling/v2/tables/db_comparison.tex'),
 ('PC2-Rolling','PC2-Rolling','M2','pending',pc[0]['fine_decision'][0],pc[0]['merged_decision'] if pc[0]['merged_decision'] not in ('WIN','LOSS') else pc[0]['merged_decision'][0],r'merged cap: '+pc[0].get('merged_timeout_seconds','1200')+r'\,s',pc,'pc2_rolling/v2/tables/s4_pc2_calibration.tex;pc2_rolling/extended_7200/tables/host_budget_comparison.csv;pc2_rolling/xeon_20260929_2344/tables/host_budget_comparison.csv'),
 ('Threads','Threads (control)','M1*','control','W/L','W/L',r'backpressure/saturation',threads,'threads/v1/tables/table_threads_states.tex')
]
if pc[0]['class']=='witness':
    s=list(specs[5]);s[3]='L1';specs[5]=tuple(s)

provenance=[]
body=[r'\begingroup',r'\scriptsize',r'\setlength{\tabcolsep}{2.1pt}',r'\renewcommand{\arraystretch}{1.04}',r'\begin{tabular}{@{}lllcclcc@{}}',r'\toprule',r'Family & Mechanism & Evidence & Fine & All & Threshold or control & E1 & v3 \\',r'\midrule']
for name,label,mechanism,contribution,fine,merged,criterion,rs,details in specs:
    assert all((E6/q).exists() for q in details.split(';')), details
    eq='P' if all(r['e1_merge_equivalence']=='PASS' for r in rs) else '--'
    v3='P' if all(r['independent_v3']=='PASS' for r in rs) else '--'
    body.append(' & '.join([label,mechanism,contribution,fine,merged,criterion,eq,v3])+r' \\')
    provenance.append(dict(family=name,index_rows=len(rs),params=' | '.join(r['params'] for r in rs),classes=json.dumps(classes(rs),sort_keys=True),fine_display=fine,all_display=merged,e1_column=eq,v3_column=v3,detail_tables=details,comparison_modes=';'.join(sorted(set(r['comparison'] for r in rs))),index_sha256=hashlib.sha256(INDEX.read_bytes()).hexdigest()))
body += [r'\bottomrule',r'\end{tabular}',r'\endgroup']
legend=(r'\par\vspace{2pt}{\scriptsize W/L: WIN/LOSS. All: transfers (Policy: boundaries). '
        r'P: PASS; --: other validation scope (S1/S4). '
        r'E1/v3: merge equivalence/independent game; *: idle/progress control. Rolling Fine/All: $k=1/n$.}')
caption=r'Constructed comparisons, not prevalence estimates. Details: S1/S4.'
fragment='\n'.join([r'% Generated from results_index.csv; no timings are compared across hosts.',r'\begin{table}[t]',r'\centering',r'\caption{'+caption+'}',r'\label{tab:rq2-constructed}',*body,legend,r'\end{table}'])+'\n'
(OUT/'table_rq2_main.tex').write_text(fragment)
with (OUT/'table_rq2_main_provenance.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(provenance[0]));w.writeheader();w.writerows(provenance)

# Native acmart preview embeds the fragment because the native compiler accepts
# one source document. The assertion measures caption + body + note + spacing.
preview=r'''\documentclass[acmsmall,screen,review,anonymous]{acmart}
\setcopyright{none}
\acmDOI{}
\acmISBN{}
\begin{document}
\newsavebox{\rqtable}
\newsavebox{\rqbody}
\sbox{\rqbody}{'''+ '\n'.join(body)+r'''}
\ifdim\wd\rqbody>\textwidth
\PackageError{e6}{Table exceeds text width}{Reduce column spacing without dropping results.}
\fi
\setbox\rqtable=\vbox{\hsize=\textwidth
\centering
\captionof{table}{'''+caption+'}\n'+r'\usebox{\rqbody}'+'\n'+legend+r'''
}
\ifdim\dimexpr\ht\rqtable+\dp\rqtable+12pt\relax>.25\textheight
\PackageError{e6}{Table height \the\dimexpr\ht\rqtable+\dp\rqtable+12pt\relax exceeds quarter text page \the\dimexpr\textheight/4\relax}{Reduce the table layout without dropping results.}
\fi
\noindent\usebox{\rqtable}
\par\medskip
\footnotesize Width: \the\textwidth. Table height including 12pt allowance:
\the\dimexpr\ht\rqtable+\dp\rqtable+12pt\relax.
Quarter text height: \the\dimexpr\textheight/4\relax.
\end{document}
'''
(OUT/'table_rq2_main_preview.tex').write_text(preview)
report=dict(status='PASS',generated_at=datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),source='results_index.csv',index_sha256=hashlib.sha256(INDEX.read_bytes()).hexdigest(),rows=7,index_comparisons=sum(len(s[-2]) for s in specs),threshold_cells=sum(int(r['threshold_tested_k_count']) for r in rolling),population_note='Nine Cell_n E4 references are excluded from E6 counts; Audit, scale, and Canary assumption controls have separate tables.',validation_note='P is emitted only for explicit PASS; no E6 v3 PASS is assigned to the FSP PC2 route or old E4 adapter.',native_compile='PENDING',table_sha256=hashlib.sha256(fragment.encode()).hexdigest())
native=OUT/'native_layout_checks.json'
if native.exists():
    for item in json.loads(native.read_text()).get('checks',[]):
        if item['path']=='integration/table_rq2_main_preview.tex' and item['sha256']==hashlib.sha256((OUT/'table_rq2_main_preview.tex').read_bytes()).hexdigest() and item['native_compile']=='PASS':
            report['native_compile']='PASS'
            report['native_layout_check']='integration/native_layout_checks.json'
(OUT/'table_rq2_main_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
