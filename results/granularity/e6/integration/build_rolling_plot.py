#!/usr/bin/env python3
"""Make a standalone PGFPlots figure and structural-size table from measured CSV."""
import csv,json,hashlib
from pathlib import Path
E6=Path(__file__).resolve().parents[1];OUT=E6/'integration/figures'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert (E6/'rolling_scale/v1/raw/runner_finished.json').exists(),'Wait for the preregistered series to finish'
data={};sources=[]
for family in ('rolling/v1','rolling_scale/v1'):
    path=E6/family/'summary.csv';rows=list(csv.DictReader(path.open()));sources.append(dict(path=str(path.relative_to(E6)),sha256=sha(path)))
    for row in rows:
        params=json.loads(row['parameters']);n,m,k=(params[x] for x in ('n','m','k'))
        if k!=1 or row['merge']!='none' or m not in (1,n-1):continue
        key=(n,m,row['solver']);assert key not in data;data[key]=(row,family)
records=[];coordinates={name:[] for name in ('lo_lazy','lo_full','hi_lazy','hi_full')};failures=[]
for n in range(2,17):
    for floor,m in [('lo',1),('hi',n-1)]:
        for solver,label in [('lazy','lazy'),('direct_full','full')]:
            row,family=data[n,m,solver]
            if row['decision']=='WIN':
                coordinates[floor+'_'+label].append((n,int(row['states_discovered'])))
            else:failures.append(dict(n=n,m=m,solver=solver,status=row['decision']))
        row,family=data[n,m,'lazy'];path=E6/family/row['input'];model=read(path)
        if floor=='hi' and m==1:continue
        df=data[n,m,'direct_full'][0]
        records.append(dict(n=n,m=m,input=str(path.relative_to(E6)),input_sha256=sha(path),input_bytes=path.stat().st_size,
          components=len(model['components']),old_local_states=sum(len(c['old']['states']) for c in model['components']),new_local_states=sum(len(c['new']['states']) for c in model['components']),
          interval_tester_states=sum(len(r['tester']['states']) for r in model['requirements']),interval_explicit_changes=sum(len(r['tester']['changes']) for r in model['requirements']),
          ordinary_labels=len(model['ordinary']),transfer_labels=len({c['transfer_action'] for c in model['components']}),
          lazy_status=row['decision'],lazy_states=row['states_discovered'],full_status=df['decision'],full_states=df['states_discovered']))
for row in records:
    assert row['old_local_states']==row['n'] and row['new_local_states']==2*row['n']
    assert row['interval_tester_states']==row['n']-row['m']+2
    assert row['interval_explicit_changes']==2*row['n']*(row['n']-row['m']+1)
with (OUT/'rolling_structural_sizes.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
lines=[r'\documentclass[10pt]{article}',r'\usepackage[margin=16mm]{geometry}',r'\usepackage{pgfplots}',r'\pgfplotsset{compat=1.18}',r'\pagestyle{empty}',r'\begin{document}',r'\begin{center}',r'{\large Rolling: discovered states for individual replacement}\par\medskip',r'\begin{tikzpicture}']
for i,(floor,title) in enumerate([('lo',r'$m=1$'),('hi',r'$m=n-1$')]):
    shift='0cm' if i==0 else '8.25cm'
    lines.append(r'\begin{axis}[at={('+shift+r',0)},anchor=south west,width=8cm,height=8cm,title={'+title+r'},xlabel={Replicas $n$},ylabel={Discovered states},ymode=log,log basis y=10,xmin=1.5,xmax=16.5,ymin=4,ymax=1000000,xtick={2,4,6,8,10,12,14,16},ytick={10,100,1000,10000,100000,1000000},grid=major,grid style={gray!20},legend pos=north west,legend style={font=\small,draw=none},tick label style={font=\small}]')
    for label,legend,style in [('lazy','Lazy','blue!70!black,mark=*,mark size=1.8pt'),('full','Direct-Full','orange!75!black,mark=square*,mark size=1.8pt')]:
        coords=' '.join(f'({n},{states})' for n,states in coordinates[floor+'_'+label])
        lines.extend([r'\addplot+[thick,'+style+r'] coordinates {'+coords+'};',r'\addlegendentry{'+legend+'}'])
    omitted=[x for x in failures if x['m']==(1 if floor=='lo' else x['n']-1)]
    if omitted:
        notes=[('Full' if x['solver']=='direct_full' else 'Lazy')+f': n={x["n"]} '+x['status'].replace('_',r'\_') for x in omitted]
        lines.append(r'\node[anchor=north east,font=\scriptsize,align=right,fill=white] at (rel axis cs:0.98,0.98) {'+r'\\'.join(notes)+'};')
    lines.append(r'\end{axis}')
lines += [r'\end{tikzpicture}',r'\end{center}',r'\noindent All plotted points are completed single-trial measurements with the same fixed E1 solver JAR. Both availability extremes are shown; no analytical values fill a missing point. The vertical axes are logarithmic. Rank and adverse outcomes remain in the complete CSV tables.',r'\par\medskip\noindent Each component has one old and two new local states. The interval tester has $n-m+2$ states and $2n(n-m+1)$ explicitly listed changes, so the input representation is polynomial in $n$. The full-game state-count formula $(n+2)2^{n-1}$ is checked separately against observations, and is not substituted for them.']
if failures:lines.append(r'\par\medskip\noindent Uncompleted points are omitted from the curves and retained with exact statuses in \texttt{rolling\_structural\_sizes.csv}.')
lines.append(r'\end{document}')
target=OUT/'rolling_state_counts.tex';target.write_text('\n'.join(lines)+'\n')
report=dict(status='BUILT_FROM_MEASUREMENTS',sources=sources,script_sha256=sha(Path(__file__)),figure_sha256=sha(target),omitted_uncompleted_points=failures,points={k:len(v) for k,v in coordinates.items()},structural_rows=len(records))
(OUT/'rolling_plot_provenance.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
