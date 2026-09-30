#!/usr/bin/env python3
"""Read-only census of actual WIN policy transfers while B remains unrecovered."""
import csv,datetime,hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]/'v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=[];details=[]
for path in sorted((BASE/'raw/series').glob('*_fine_lazy/certificate.json')):
 n,m=map(int,re.match(r'n(\d+)_m(\d+)_fine_lazy',path.parent.name).groups());data=json.loads(path.read_text());assert data['decision']=='WIN';by={q['id']:q for q in data['states']};edges=[];buckets=set();before=[]
 for s,a,t in data['strategy_edges']:
  if a.startswith('rho_'):
   physical=by[s]['physical'];broken=sum(v=='NEW' and q=='B' for v,q in physical);healthy=sum(q in ('H','HP') for v,q in physical)
   assert all(q not in ('HP','BP') for v,q in physical),'Transfer selected while a report is pending.'
   assert healthy-1>=m,'Adversarial broken result would violate floor.'
   before.append((broken,healthy))
   if broken:edges.append([s,a,t]);buckets.add((s,a))
 minhealthy=min(sum(q in ('H','HP') for v,q in s['physical']) for s in data['states']);assert minhealthy>=m
 row=dict(n=n,m=m,job=path.parent.name,certificate_states=len(data['states']),total_strategy_edges=len(data['strategy_edges']),transfer_buckets_with_unrecovered_B=len(buckets),transfer_successor_edges_with_unrecovered_B=len(edges),max_broken_before_any_transfer=max(b for b,h in before),minimum_healthy_before_any_transfer=min(h for b,h in before),minimum_physical_healthy_in_certificate=minhealthy,recovers_before_every_next_transfer=(len(buckets)==0),returned_worst_rank=max(s['rank'] for s in data['states'] if s['initial']),certificate=str(path.relative_to(BASE)),certificate_sha256=sha(path))
 rows.append(row);details.append(dict(**row,transfer_successor_edges_with_unrecovered_B_detail=edges))
assert len(rows)==15
with (HERE/'summary.csv').open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with (HERE/'review.json').open('x') as f:json.dump(dict(status='PASS',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),analyzer_sha256=sha(Path(__file__)),scope='Read-only census of original fine Lazy WIN certificates. No new trial, changed input, inferred metric, or optimality claim. Event buckets are source/action pairs; successor edges retain each outcome separately.',policies=len(rows),policies_recovering_before_each_next_transfer=sum(r['recovers_before_every_next_transfer'] for r in rows),records=details),f,indent=2);f.write('\n')
print(json.dumps(dict(status='PASS',policies=len(rows),immediate_recovery=sum(r['recovers_before_every_next_transfer'] for r in rows),csv=str(HERE/'summary.csv'))))
