from pathlib import Path
import copy,datetime,hashlib,json,subprocess,sys
import oracle_hardened,oracle_session_hardened,value_certificate_hardened,values_certificate_hardened
ROOT=Path(__file__).resolve().parent
files=['HARDENING_PLAN.md','harden_check.py','oracle_hardened.py','oracle_session_hardened.py','value_certificate_hardened.py','values_certificate_hardened.py','INPUTS.json','SESSION_RAW.jsonl']
def record(p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
with (ROOT/'HARDENING_MANIFEST.json').open('x') as f:json.dump(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=[record(ROOT/x) for x in files]),f,indent=2)
inputs=json.loads((ROOT/'INPUTS.json').read_text());old={r['id']:r for r in map(json.loads,(ROOT/'SESSION_RAW.jsonl').read_text().splitlines())};selected=inputs[:8]+inputs[-10:];rows=[]
for u in selected:
 r=oracle_session_hardened.solve_many(u['case'],u['budgets']);report=values_certificate_hardened.check(json.loads(json.dumps(r['artifact'])));assert r['values']==report['values']==old[u['id']]['values']
 for b in u['budgets']:
  one=oracle_hardened.solve(u['case'],b);scan=value_certificate_hardened.check(one['artifact']);assert one['value']==scan['value']==old[u['id']]['values'][u['budgets'].index(b)]
 rows.append(dict(id=u['id'],status='SUCCESS',roots=len(u['budgets'])))
for name in ['oracle_hardened','oracle_session_hardened','value_certificate_hardened','values_certificate_hardened']:
 p=subprocess.run([sys.executable,'-O','-c',f'import {name}'],cwd=ROOT,capture_output=True,text=True,timeout=5);assert p.returncode!=0 and 'assertions-enabled Python is required' in p.stderr;rows.append(dict(id='optimized-'+name,status='REJECTED',exit=p.returncode))
case=dict(cp=[[1,1]],edges=[]);bad=[dict(case,extra=0),dict(cp=[(1,1)],edges=[]),dict(cp=[[1,1]],edges=())]
for j,c in enumerate(bad):
 for name,fn in [('single',lambda:oracle_hardened.solve(c,1)),('session',lambda:oracle_session_hardened.solve_many(c,[1]))]:
  try:fn()
  except (AssertionError,TypeError,ValueError):rows.append(dict(id=f'schema-{name}-{j}',status='REJECTED'))
  else:raise AssertionError(('acceptedbad',c))
with (ROOT/'HARDENING_RAW.json').open('x') as f:json.dump(rows,f,indent=2)
print(dict(canonical_units=len(selected),canonical_roots=sum(r.get('roots',0) for r in rows),rejected=sum(r['status']=='REJECTED' for r in rows)))
