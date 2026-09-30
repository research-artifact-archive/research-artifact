#!/usr/bin/env python3
"""Generate vector ME timeline prototypes from measured certificate paths."""
import json,html,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent;E6=D.parents[1]
BLUE='#235b83';GREEN='#1d755a';RED='#b0373e';INK='#192a36';GRAY='#5f6d75'
def txt(x,y,text,size=19,color=INK,anchor='middle',weight='normal'):
 return f'<text x="{x}" y="{y}" fill="{color}" text-anchor="{anchor}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" font-weight="{weight}">{html.escape(str(text))}</text>'
def line(x,y,xx,yy,color=INK,width=2,arrow=False,dash=False):
 assert y==yy
 end=xx-12 if arrow else xx
 result=f'<rect x="{x}" y="{y-width/2}" width="{end-x}" height="{width}" fill="{color}"/>'
 if arrow:result+=f'<polygon points="{xx},{y} {xx-12},{y-5} {xx-12},{y+5}" fill="{color}"/>'
 return result

def start(height,title):
 return [f'<svg xmlns="http://www.w3.org/2000/svg" width="1240" height="{height}" viewBox="0 0 1240 {height}">','<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#192a36"/></marker></defs>',f'<rect width="1240" height="{height}" fill="white"/>',txt(44,43,title,25,anchor='start',weight='bold')]
def write(name,parts):
 (D/name).write_text('\n'.join(parts+['</svg>'])+'\n')
pathfile=E6/'rolling/v1/validation/me_path.json';path=json.loads(pathfile.read_text())['path'];assert len(path)==5
s=start(485,'Rolling(2,1): replace locally, retain one ready replica')
s += [txt(44,77,'Measured fine policy: WIN; remaining rank falls from 4 to 0.',17,GRAY,'start')]
xs=[220+220*i for i in range(5)];y=154
s += [txt(44,y+6,'Fine',20,BLUE,'start','bold')]
labels={'rho_1':'replace 1','ready_1':'ready 1 (UC)','rho_2':'replace 2','ready_2':'ready 2 (UC)'}
for i,item in enumerate(path):
 x=xs[i];q=item['state'];ready=sum(v=='ready' for ver,v in q['physical']);rank=q['rank']
 if i:
  s += [line(xs[i-1]+9,y,x-11,y,arrow=True),txt((xs[i-1]+x)/2,y-20,labels[item['action']],18)]
 s += [f'<circle cx="{x}" cy="{y}" r="6" fill="{BLUE}"/>',txt(x,y+37,f'rank {rank}',18),txt(x,y+65,f'{ready} ready',17,GRAY)]
s += [line(xs[0],249,xs[-1],249,GREEN,8),txt((xs[0]+xs[-1])/2,282,'Interval requirement: at least one replica ready',18,GREEN),txt(44,338,'All at once',20,RED,'start','bold'),line(220,332,610,332,arrow=True),txt(415,310,'replace both',19),f'<circle cx="220" cy="332" r="6" fill="{BLUE}"/>',txt(220,369,'2 ready',17,GRAY),f'<rect x="624" y="309" width="180" height="50" rx="7" fill="#fff0ef" stroke="{RED}" stroke-width="2"/>',txt(714,341,'ERROR: 0 ready',19,RED),txt(850,342,'LOSS',21,RED,weight='bold'),txt(44,433,'Readiness is uncontrollable and finitely completing in this abstraction; the line is an event order, not elapsed time.',16,GRAY,'start'),txt(44,461,'Source: checked Rolling fine policy; generated product transfer agrees with E1 contractMerge=transfers.',16,GRAY,'start')]
write('rolling_me.svg',s)
file=E6/'rolling_audit/v1/tables/me_six_step_path.json';raw=json.loads(file.read_text())
path=raw['path'];assert len(path)==7
s=start(640,'Rolling(2,1) + Audit: a checked six-step completion path')
s += [txt(44,77,'One old-unlogged root of the Lazy certificate. The complete policy has worst rank 7; Direct-Full returns 6.',17,GRAY,'start')]
xs=[240+142*i for i in range(7)];y=159
s += [txt(44,y+6,'Fine',20,BLUE,'start','bold')]
labels={'start_audit_new':'start new audit','stop_audit_old':'stop old audit','rho_1':'replace 1','ready_1':'ready 1 (UC)','rho_2':'replace 2','ready_2':'ready 2 (UC)'}
for i,item in enumerate(path):
 x=xs[i];physical=json.loads(item['physical']);ready=sum(q=='ready' for ver,q in physical)
 if i:s += [line(xs[i-1]+7,y,x-10,y,arrow=True),txt((xs[i-1]+x)/2,y-22,labels[item['event']],15)]
 s += [f'<circle cx="{x}" cy="{y}" r="5" fill="{BLUE}"/>',txt(x,y+35,f"rank {item['rank']}",17),txt(x,y+60,f'{ready} ready',16,GRAY)]
# Bars extend to the event tick at which the corresponding monitor changes.
s += [txt(44,269,'Old audit active',18,anchor='start'),line(xs[0],264,xs[2],264,BLUE,8),txt(44,312,'New audit active',18,anchor='start'),line(xs[1],307,xs[-1],307,GREEN,8),txt(44,356,'One interval',18,anchor='start'),line(xs[0],351,xs[-1],351,INK,7),txt((xs[0]+xs[-1])/2,383,'ready count ≥ 1  AND  at least one audit rule active',17,GRAY),txt(44,438,'Transfer merge',19,RED,'start','bold'),line(260,432,607,432,arrow=True),txt(435,414,'both replicas enter booting',17),txt(635,438,'0 ready → LOSS',19,RED,'start'),txt(44,492,'Boundary merge',19,BLUE,'start','bold'),txt(260,492,'one start + one stop: only renaming; start-before-stop remains possible → WIN',17,BLUE,'start'),txt(44,554,'Audit testers require their own log event before each service; the new tester is initialized unlogged.',16,GRAY,'start'),txt(44,582,'The availability and no-audit-gap clauses form one interval tester. There is no added precedence edge.',16,GRAY,'start'),txt(44,610,'Measured certificate path; event order only. This candidate does not demonstrate boundary-granularity loss.',16,GRAY,'start')]
write('rolling_audit_me.svg',s)
report={'scope':'Vector prototypes generated from measured certificate traces; no manuscript file edited.',
 'inputs':[{'path':str(f.relative_to(E6)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in [pathfile,file]],
 'figures':['rolling_me.svg','rolling_audit_me.svg']}
(D/'provenance.json').write_text(json.dumps(report,indent=2)+'\n')
