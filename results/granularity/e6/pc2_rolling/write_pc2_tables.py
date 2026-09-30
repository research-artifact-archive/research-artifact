#!/usr/bin/env python3
"""Derived handoff table, generated only after the fixed series terminates."""
import csv,json
from pathlib import Path
P=Path(__file__).resolve().parent;V=P/'v2';assert (V/'raw/runner_finished.json').exists()
rows=list(csv.DictReader((V/'tables/results.csv').open()));assert len(rows)==3
labels={'lazy_none':'Lazy / fine','lazy_transfers':'Lazy / merged transfers','direct_full_none':'Direct-Full / fine'}
lines=[r'\begin{table}[t]',r'\centering',r'\small',r'\begin{tabular}{lrrrrrr}',r'\toprule',r'Variant & Result & States & Queries & Rank & $|L|$ & Solve+check (s) \\',r'\midrule']
for r in rows:
 def value(k):return format(int(r[k]),',') if r[k] else '--'
 time=f"{float(r['solve_and_internal_check_seconds']):.3f}" if r['solve_and_internal_check_seconds'] else '--'
 lines.append(' & '.join([labels[r['job_id']],r['status'],value('states_discovered'),value('successor_queries'),value('worst_completion_rank'),value('losing_region_states'),time])+r' \\')
lines += [r'\bottomrule',r'\end{tabular}',r'\caption{PC2 calibration-setting variant, preserving the original 12 old and 12 new safety requirements and ordinary plant transitions. A new endpoint availability requirement and an update-interval availability requirement allow at most one arm in the added calibration state. Each fixed-E1 run has a 1,200\,s whole-JVM limit and 32\,GB heap. Time includes the internal certificate checker and is a Mac reference value only. TO is retained as an incomplete decision; unavailable counters are not inferred. Rank is the maximum returned certificate rank; $L$ is the discovered-state losing certificate.}',r'\label{tab:e6-pc2-calibration}',r'\end{table}']
fragment='\n'.join(lines)+'\n';(V/'tables/s4_pc2_calibration.tex').write_text(fragment)
text=(r'\documentclass{article}'+'\n'+r'\usepackage[margin=18mm]{geometry}'+'\n'+r'\usepackage{booktabs}'+'\n'+r'\begin{document}'+'\n'+fragment+'\n'+r'\noindent The fixed CLI reports generated transition outcomes, but does not directly instrument distinct enabled buckets. Full-certificate export replays are validation only and are excluded from this performance table.'+'\n'+r'\end{document}'+'\n')
(V/'tables/pc2_table_check.tex').write_text(text)
print('Derived PC2 table and standalone check document written.')
