"""Plot all 14 completed RQ3 pairs using PGFPlots; do not rerun measurements."""
from pathlib import Path
import csv,subprocess
here=Path(__file__).resolve().parent
rows=list(csv.DictReader((here.parents[1]/'evidence/rq3_workload14_W.csv').open()))
assert len(rows)==14 and len({(r['input'],r['variant']) for r in rows})==14
tex=[r'''\documentclass[tikz,border=2pt]{standalone}
\usepackage{pgfplots}
\usepgfplotslibrary{groupplots}
\pgfplotsset{compat=1.18}
\definecolor{baseblue}{HTML}{16689C}
\definecolor{r1orange}{HTML}{A34D15}
\definecolor{r2green}{HTML}{29774B}
\begin{document}
\begin{tikzpicture}
\begin{groupplot}[group style={group size=2 by 1,horizontal sep=1.3cm},width=7cm,height=4.7cm,xmode=log,ymode=log,xmin=4,ymin=4,xlabel={Lazy},ylabel={Direct-Full},title style={font=\small},tick label style={font=\scriptsize},label style={font=\small},legend style={font=\scriptsize,draw=none,at={(.98,.02)},anchor=south east},grid=major,grid style={gray!20},minor tick num=0]
''']
for col,title,hi in [('states','Discovered states',1000000),('queries','Successor queries',10000000)]:
 tex.append(r'\nextgroupplot[title={'+title+'},xmax='+str(hi)+',ymax='+str(hi)+']')
 tex.append(r'\addplot[gray,dashed,no marks,forget plot] coordinates {(4,4) ('+str(hi)+','+str(hi)+')};')
 for variant,marker,color in [('Base','o','baseblue'),('R1','square','r1orange'),('R2','triangle','r2green')]:
  part=[r for r in rows if r['variant']==variant]
  coords=[]
  for r in part:
   x=int(r[f'lazy_{col}_first_trial']); y=int(r[f'direct_full_{col}_first_trial']);assert y>x
   coords.append(f'({x},{y})')
  tex.append(r'\addplot[only marks,mark='+marker+',mark size=2.4pt,thick,color='+color+r',mark options={fill=white}] coordinates {'+' '.join(coords)+'};')
  if col=='states':tex.append(r'\addlegendentry{'+variant+'}')
 # Name two prominent Base cases; preserve the full set of 14 points.
 annotations=[('PC Arms=1','PC1/Base',(9,650000) if col=='states' else (20,700000)),('Industry','Industry/Base',(550,110000) if col=='states' else (5000,250000))]
 for inp,label,(lx,ly) in annotations:
  row=next(r for r in rows if r['input']==inp and r['variant']=='Base')
  xx=row[f'lazy_{col}_first_trial'];yy=row[f'direct_full_{col}_first_trial']
  tex.append(r'\draw[gray,thin] (axis cs:'+str(lx)+','+str(ly)+') -- (axis cs:'+xx+','+yy+');')
  tex.append(r'\node[anchor=west,font=\scriptsize,fill=white,inner sep=1pt] at (axis cs:'+str(lx)+','+str(ly)+') {'+label+'};')
tex.extend([r'\end{groupplot}',r'\end{tikzpicture}',r'\end{document}'])
(here/'paired_work.tex').write_text('\n'.join(tex))
with (here/'paired_work_build.log').open('w') as log:subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error','paired_work.tex'],cwd=here,stdout=log,stderr=subprocess.STDOUT,check=True)
print('14 contracts plotted with exact first-trial counts, no experiment rerun')
