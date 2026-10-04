#!/usr/bin/env python3
"""Render saved Lazy/Eager results; no synthesis, timing trial, or imputation."""
from pathlib import Path
import csv, math
ROOT=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((ROOT/'build/generated/rq3-cells.csv').open()))
models=[('gsm','GSM'),('industry','Industry'),('metasocket','MetaSocket'),('powerplant','PowerPlant'),('productioncell_arms1','PC1'),('productioncell_arms2','PC2'),('railcab','Railcab'),('surveillance','Surveillance'),('workflow','Workflow')]
methods=[('fg_ducs_otf','lazy',.065),('fg_ducs_otf_eager_controllable','eager',-.065)]
lookup={(r['model_id'],r['target_id'],r['method_id']):r for r in rows}
lines=[r'% Generated from the unchanged rq3-cells.csv. All 27 contracts appear.',r'\begin{figure}[!htbp]',r'\centering',r'\begin{tikzpicture}[x=1cm,y=1cm,font=\footnotesize]',r'\definecolor{lazy}{RGB}{25,89,135}',r'\definecolor{eager}{RGB}{159,72,20}']
def add(x):lines.append(x)
def xpos(value,start,kind):
 if kind=='time':return start+3*math.log10(value/.5)/math.log10(1500/.5)
 return start+3*math.log10(value)/7
completed=0;censored=0
for kind,origin,title in [('time',0,'Total JVM time (seconds)'),('states',-4.40,'Discovered game states (first trial)')]:
 add(r'\node[anchor=west,font=\footnotesize\bfseries] at (2,'+str(origin+1.12)+') {'+title+'};')
 for j,(variant,vlabel) in enumerate([('base','Base'),('r1','R1'),('r2','R2')]):
  start=2+3.7*j
  add(r'\node[font=\footnotesize\bfseries] at ('+str(start+1.5)+','+str(origin+.57)+') {'+vlabel+'};')
  for i,(model,label) in enumerate(models):
   y=origin-.30*i
   if j==0:add(r'\node[anchor=east] at (1.83,'+str(y)+') {'+label+'};')
   add(fr'\draw[black!9] ({start},{y})--({start+3},{y});')
   pair=[]
   for method,color,dy in methods:
    r=lookup[(model,variant,method)];status=r['stage1_status'];yy=y+dy
    assert status in ('SUCCESS','UNREALIZABLE','TIMEOUT')
    if status=='TIMEOUT':
     assert r['states_discovered']=='' and r['elapsed_monotonic_seconds_median']==''
     if kind=='time':
      censored+=1;x=xpos(1200,start,kind)
      add(fr'\draw[{color},line width=.8pt] ({x-.065:.5f},{yy-.050:.5f})--({x:.5f},{yy:.5f})--({x-.065:.5f},{yy+.050:.5f});')
     continue
    assert r['completed_valid_repetitions']=='5' and r['structure_repetition']=='1'
    if kind=='time':
     completed+=1;v=float(r['elapsed_monotonic_seconds_median']);lo=float(r['elapsed_monotonic_seconds_min']);hi=float(r['elapsed_monotonic_seconds_max']);assert lo<=v<=hi<1200
     add(f'% {model}/{variant}/{color}: JVM median/min/max = {v}/{lo}/{hi}')
     add(fr'\draw[{color},line width=.7pt] ({xpos(lo,start,kind):.5f},{yy:.5f})--({xpos(hi,start,kind):.5f},{yy:.5f});')
    else:
     v=int(r['states_discovered']);assert 1<=v<=10**7
     add(f'% {model}/{variant}/{color}: first-trial states = {v}')
    x=xpos(v,start,kind);pair.append((x,yy))
    if color=='lazy':add(fr'\fill[lazy] ({x:.5f},{yy:.5f}) circle (1.45pt);')
    else:add(fr'\draw[eager,fill=white,line width=.65pt] ({x-.048:.5f},{yy-.048:.5f}) rectangle ({x+.048:.5f},{yy+.048:.5f});')
    if status=='UNREALIZABLE':add(fr'\node[font=\scriptsize,anchor=south west,inner sep=1pt] at ({x:.5f},{yy:.5f}) {{$\dagger$}};')
   # The two markers are vertically offset so nearly equal costs remain visible.
  axis=origin-2.72
  add(fr'\draw ({start},{axis})--({start+3},{axis});')
  ticks=[(1,'1'),(10,'10'),(100,'100'),(1200,'1,200')] if kind=='time' else [(1,'1'),(100,r'$10^2$'),(10000,r'$10^4$'),(1000000,r'$10^6$')]
  for value,label in ticks:
   x=xpos(value,start,kind)
   add(fr'\draw ({x:.5f},{axis})--({x:.5f},{axis-.055});')
   add(fr'\node[anchor=north,font=\scriptsize,inner sep=1pt] at ({x:.5f},{axis-.075}) {{{label}}};')
assert (completed,censored)==(43,11)
add(r'\fill[lazy] (2,-7.67) circle (1.45pt);')
add(r'\node[anchor=west] at (2.13,-7.67) {Lazy};')
add(r'\draw[eager,fill=white,line width=.65pt] (3.55,-7.718) rectangle (3.646,-7.622);')
add(r'\node[anchor=west] at (3.78,-7.67) {Eager};')
add(r'\draw[black,line width=.8pt] (5.08,-7.72)--(5.145,-7.67)--(5.08,-7.62);')
add(r'\node[anchor=west] at (5.25,-7.67) {TO at 1,200 s};')
add(r'\node[anchor=west,font=\scriptsize] at (8.3,-7.67) {Logarithmic axes; lower is better.};')
add(r'\end{tikzpicture}')
add(r'\caption{All 27 contracts under the same UC pruning. Completed times are five-run medians with min--max bars, including preparation, solving, checking and other JVM work. TO arrows mark one capped attempt, not a median or a solver-time bound; no state count is imputed. $\dagger$ is Industry/R1 LOSS; other completed points are WIN.}')
add(r'\label{fig:rq3-paired-absolute}')
add(r'\Description{Three columns show Base, R1 and R2 for all nine adapted inputs. Upper panels show complete JVM time, lower panels show first-trial discovered states. Lazy decides 26 contracts including Industry R1 LOSS; Eager decides 17. Their 17 common completions have both markers; nine contracts have only a Lazy completion; PC2 R2 times out with both. All 11 timeouts have capped-attempt arrows in the time panels and no imputed state markers.}')
add(r'\end{figure}')
(ROOT/'figures/rq3_paired_absolute.tex').write_text('\n'.join(lines)+'\n')
print('Saved-only plot:',completed,'complete cells;',censored,'single capped attempts; 27 contracts')
