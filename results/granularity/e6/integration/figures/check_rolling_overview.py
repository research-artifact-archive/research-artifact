#!/usr/bin/env python3
"""Check the proposed timeline against the preserved certificate trace."""
from pathlib import Path
import hashlib, json, re

HERE=Path(__file__).resolve().parent
E6=HERE.parents[1]
diagram=HERE/'rolling_overview.tex'
trace=E6/'rolling/v1/validation/me_path.json'
path=json.loads(trace.read_text())['path']
text=diagram.read_text()
match=re.search(r'\\foreach \\x/\\event/\\r/\\q in \{(.+?)\} \{',text)
assert match
items=re.findall(r'[\d.]+/\{\$(.*?)\$\}/(\d+)/(\d+)',match[1])
events=[(event.replace(r'\rho_', 'rho_').replace(r'\mathit{ready}_','ready_'),int(rank),int(ready)) for event,rank,ready in items]
expected=[]
for entry in path[1:]:
    state=entry['state']
    expected.append((entry['action'],state['rank'],sum(local=='ready' for version,local in state['physical'])))
assert events==expected,(events,expected)
assert path[0]['state']['rank']==4 and len(path)==5
assert path[-1]['state']['goal'] and path[-1]['state']['rank']==0
assert all(x['state']['safe'] and int(x['state']['testers']['availability'][1:])>=1 for x in path)
assert 'rank $4$' in text and 'both booting' in text and '$0$ ready' in text
assert r'$\rho_{\{1,2\}}$' in text
assert 'old\\\\requirement' not in text and 'new\\\\requirement' not in text
report=dict(status='PASS',figure_sha256=hashlib.sha256(diagram.read_bytes()).hexdigest(),trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),checked_events=[x[0] for x in expected],checked_ranks=[path[0]['state']['rank']]+[x[1] for x in expected],checked_ready_counts=[2]+[x[2] for x in expected],scope='Exact events, ranks, readiness counts and one interval lifetime from the preserved path. The existing Cell diagram checker is not invoked or weakened. Full certificate correctness is covered by E1 and independent v3 reports.')
(HERE/'rolling_overview_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
