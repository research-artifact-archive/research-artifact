#!/usr/bin/env python3
"""Independent finite JSON interpreter, strong attractor, and certificate audit.

No Java invocation, imports of generators, or reuse of solver transitions.
This is a validation implementation, not a replacement experimental solver.
"""
import argparse,csv,hashlib,itertools,json,time,traceback
from collections import defaultdict,deque
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

E6=Path(__file__).resolve().parents[1]

def physical(x):return tuple(tuple(t) for t in x)
def state(p,t,pending):return (physical(p),tuple(sorted(t.items())),frozenset(pending))
def from_json(s):return state(s['physical'],s['testers'],s['pending'])
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def reachable(lts):
    edges=defaultdict(set)
    for u,a,v in lts['edges']:edges[u].add(v)
    seen={lts['initial']};queue=deque(seen)
    while queue:
        for v in edges[queue.popleft()]-seen:seen.add(v);queue.append(v)
    return seen

class Model:
    def __init__(self,data,merge):
        assert data['schema']=='fg-ducs-witness-v1'
        assert merge in ('none','transfers','boundaries','both')
        assert merge=='none' or not data.get('generated_contract_mode')
        self.data=data;self.merge=merge
        self.components=data['components'];self.req={r['id']:r for r in data['requirements']}
        self.ordinary=set(data['ordinary']);self.control=set(data['controllable'])
        self.label={a:a for a in self.ordinary}
        for c in self.components:
            self.label[c['transfer_action']]='ablation.merge.transfers' if merge in ('transfers','both') else c['transfer_action']
        for r in self.req.values():
            if r['role']!='interval':
                self.label[r['update_action']]=('ablation.merge.stops' if r['role']=='old' else 'ablation.merge.starts') if merge in ('boundaries','both') else r['update_action']
        self.members=defaultdict(list)
        for a,b in self.label.items():self.members[b].append(a)
        self.updates=set(self.label.values())-self.ordinary
        assert not self.ordinary.intersection(self.updates)
        self.transfers=defaultdict(list);self.boundaries=defaultdict(list)
        for i,c in enumerate(self.components):self.transfers[self.label[c['transfer_action']]].append(i)
        for r in self.req.values():
            if r['role']!='interval':self.boundaries[self.label[r['update_action']]].append(r['id'])
        assert not set(self.transfers).intersection(self.boundaries)
        self.pre={a:set() for a in self.updates}
        for before,after in data['precedence']:self.pre[self.label[after]].add(self.label[before])
        changed=True
        while changed:
            changed=False
            for a in self.pre:
                old=set(self.pre[a])
                for b in old:self.pre[a]|=self.pre[b]
                changed |= old!=self.pre[a]
        assert all(a not in p for a,p in self.pre.items()),'Collapsed/cyclic precedence is invalid, not LOSS'
        self.lts=[]
        for c in self.components:
            versions={}
            for version in ('old','new'):
                l=c[version];edges=defaultdict(set)
                for u,a,v in l['edges']:edges[u,a].add(v)
                versions[version.upper()]=(set(l['states']),{a for u,a,v in l['edges']},edges)
            self.lts.append(versions)
        self.tests={};self.errors={};self.activation={};self.newids=[]
        self.language_checks=0;self.commutation_checks=0
        for rid,r in self.req.items():
            t=r['tester'];self.tests[rid]={(u,a):v for u,a,v in t['changes']};self.errors[rid]=set(t['errors'])
            if r['role']=='new':self.newids.append(rid)
            for group in self.members.values():
                for a,b in itertools.combinations(group,2):
                    for q in t['states']:
                        self.commutation_checks+=1
                        assert self.single(rid,self.single(rid,q,a),b)==self.single(rid,self.single(rid,q,b),a),(rid,a,b,'noncommuting')
            if r['role']!='old':
                self.activation[rid]={physical(e['physical']):e['tester_state'] for e in r['activation']['entries']}
                assert len(self.activation[rid])==len(r['activation']['entries'])
                rt=r['activation'].get('residual',t)
                for entry in r['activation']['entries']:self.check_language(rid,entry['tester_state'],rt,entry['residual_state'])
        self.newids.sort();self.goals=set();self.roots=set()
        old=data['endpoints']['old'];new=data['endpoints']['new']
        for name in reachable(old['lts']):
            proj=old['projection'][name];p=physical(proj['physical']);testers=dict(proj['testers'])
            for rid,r in self.req.items():
                if r['role']=='interval':testers[rid]=self.activation[rid][p]
            self.roots.add(state(p,testers,self.updates))
        for name in reachable(new['lts']).intersection(new['loadable']):
            proj=new['projection'][name];self.goals.add((physical(proj['physical']),tuple((r,proj['testers'][r]) for r in self.newids)))
        assert self.roots and self.goals
        self.normal_cache={};self.post_cache={};self.goal_cache={};self.safe_cache={}
        for root in self.roots:assert self.valid(root) and self.safe(root)
    def single(self,rid,q,a):return self.tests[rid].get((q,a),q)
    def step(self,rid,q,a):
        for old in self.members[a]:q=self.single(rid,q,old)
        return q
    def check_language(self,rid,initial,residual,residual_initial):
        changes={(u,a):v for u,a,v in residual['changes']};errors=set(residual['errors'])
        seen={(initial,residual_initial)};queue=deque(seen)
        while queue:
            q,r=queue.popleft();assert (q in self.errors[rid])==(r in errors),(rid,'residual bad-prefix mismatch')
            for members in self.members.values():
                nq,nr=q,r
                for a in members:nq=self.single(rid,nq,a);nr=changes.get((nr,a),nr)
                pair=nq,nr
                if pair not in seen:seen.add(pair);queue.append(pair)
        self.language_checks+=1
    def valid(self,s):
        p,t,pending=s;t=dict(t)
        if len(p)!=len(self.components) or not pending<=self.updates or not set(t)<=set(self.req):return False
        for i,(v,q) in enumerate(p):
            if v not in self.lts[i] or q not in self.lts[i][v][0]:return False
            if (v=='OLD') != (self.label[self.components[i]['transfer_action']] in pending):return False
        for rid,r in self.req.items():
            active=(r['role']=='interval' or (self.label[r['update_action']] in pending if r['role']=='old' else self.label[r['update_action']] not in pending))
            if (rid in t)!=active:return False
            if active and t[rid] not in r['tester']['states']:return False
        return True
    def safe(self,s):
        if s not in self.safe_cache:self.safe_cache[s]=self.valid(s) and all(q not in self.errors[r] for r,q in s[1])
        return self.safe_cache[s]
    def normal(self,p):
        if p in self.normal_cache:return self.normal_cache[p]
        out={}
        for a in self.ordinary:
            choices=[];owner=False
            for i,(v,q) in enumerate(p):
                states,alphabet,index=self.lts[i][v]
                if a in alphabet:
                    owner=True;choices.append([(v,target) for target in index[q,a]])
                else:choices.append([(v,q)])
            if owner and all(choices):out[a]=frozenset(itertools.product(*choices))
        self.normal_cache[p]=out;return out
    def goal(self,s):
        if s in self.goal_cache:return self.goal_cache[s]
        p,t,pending=s;t=dict(t)
        result=(not pending and self.safe(s) and all(v=='NEW' for v,q in p) and not(set(self.normal(p))-self.control)
                and (p,tuple((r,t[r]) for r in self.newids)) in self.goals)
        self.goal_cache[s]=result;return result
    def post(self,s):
        if s in self.post_cache:return self.post_cache[s]
        assert self.valid(s)
        p,t,pending=s;t=dict(t);normal=self.normal(p);out={}
        for a,ps in normal.items():
            stepped={r:self.step(r,q,a) for r,q in t.items()}
            out[a]=frozenset(state(v,stepped,pending) for v in ps)
        if not(set(normal)-self.control):
            for a in pending:
                if self.pre[a].intersection(pending):continue
                positions=self.transfers.get(a,[]);boundaries=self.boundaries.get(a,[])
                assert positions or boundaries
                if positions:
                    choices=[]
                    for i,(v,q) in enumerate(p):
                        if i in positions:
                            assert v=='OLD'
                            choices.append([('NEW',z) for z in self.components[i]['transfer'].get(q,[])])
                        else:choices.append([(v,q)])
                    if not all(choices):continue
                    ps=itertools.product(*choices)
                else:ps=[p]
                stopped={rid for rid in boundaries if self.req[rid]['role']=='old'}
                started={rid for rid in boundaries if self.req[rid]['role']=='new'}
                if not stopped<=set(t) or started.intersection(t):continue
                if any(p not in self.activation[r] for r in started):continue
                nt={rid:self.step(rid,q,a) for rid,q in t.items() if rid not in stopped}
                nt.update({rid:self.activation[rid][p] for rid in started})
                out[a]=frozenset(state(v,nt,pending-{a}) for v in ps)
        self.post_cache[s]=out;return out
    def enumerate(self):
        seen=set(self.roots);queue=deque(seen);graph={}
        while queue:
            s=queue.popleft()
            if not self.safe(s) or self.goal(s):continue
            buckets=self.post(s);graph[s]=buckets
            for successors in buckets.values():
                for t in successors-seen:seen.add(t);queue.append(t)
            assert len(seen)<=1000000,'Independent audit cap, not a solver timeout'
        return seen,graph
    def solve(self,seen,graph):
        ranks={s:0 for s in seen if self.goal(s)};iterations=0
        while True:
            promoted={};iterations+=1
            for s,buckets in graph.items():
                if s in ranks:continue
                uc=[ps for a,ps in buckets.items() if a not in self.control and a not in self.updates]
                if uc:
                    targets=set().union(*uc)
                    if targets<=ranks.keys():promoted[s]=1+max(ranks[t] for t in targets)
                else:
                    complete=[1+max(ranks[t] for t in targets) for targets in buckets.values() if targets and targets<=ranks.keys()]
                    if complete:promoted[s]=min(complete)
            if not promoted:break
            ranks.update(promoted)
        return ranks,iterations
    def certificate(self,proof,seen,ranks):
        byid={s['id']:from_json(s) for s in proof['states']};nodes=set(byid.values())
        assert len(nodes)==len(byid)==len(proof['states'])
        assert nodes<=seen,'Certificate state outside independently reachable terminalized game'
        for raw in proof['states']:
            s=byid[raw['id']]
            assert raw['safe']==self.safe(s) and raw['goal']==self.goal(s) and raw['initial']==(s in self.roots)
        edge_count=0
        if proof['decision']=='WIN':
            assert self.roots<=nodes and nodes<=ranks.keys()
            given_ranks={byid[s['id']]:s['rank'] for s in proof['states']}
            edges=defaultdict(lambda:defaultdict(set))
            for u,a,v in proof['strategy_edges']:edges[byid[u]][a].add(byid[v]);edge_count+=1
            for s in nodes:
                assert self.safe(s)
                if self.goal(s):assert given_ranks[s]==0;continue
                assert given_ranks[s]>0 and edges[s]
                buckets=self.post(s)
                uc={a for a in buckets if a not in self.control and a not in self.updates}
                assert uc<=edges[s].keys(),'Missing uncontrollable policy bucket'
                for a,targets in edges[s].items():
                    assert a in buckets and targets==buckets[a],'Incomplete or invented policy bucket'
                    assert all(given_ranks[t]<given_ranks[s] for t in targets)
                assert given_ranks[s]>=ranks[s],'Returned bound below independently minimal bound'
        else:
            assert self.roots.intersection(nodes) and not nodes.intersection(ranks),'Invalid losing region'
            for s in nodes:
                assert not self.goal(s)
                if not self.safe(s):continue
                buckets=self.post(s)
                uc=[targets for a,targets in buckets.items() if a not in self.control and a not in self.updates]
                if uc:assert any(targets.intersection(nodes) for targets in uc),'No UC losing response'
                else:assert all(targets.intersection(nodes) for targets in buckets.values()),'A C bucket escapes loss region'
        return dict(status='PASS',certificate_states=len(nodes),strategy_edges=edge_count)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--families',nargs='+',default=['rolling/v1','canary/v1','policy/v2','db_rolling/v2','rolling_audit/v1']);args=ap.parse_args()
    start=time.monotonic();report=dict(status='RUNNING',started_at=datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),checker_sha256=sha(Path(__file__)),method='Independent Python JSON Post interpreter and synchronous strong-attractor layers; generated inputs and raw read-only; no Java/generator import.',audits=[],sources=[])
    try:
        cache={}
        for family in args.families:
            base=E6/family;rows=list(csv.DictReader((base/'summary.csv').open()))
            for row in rows:
                assert row['decision'] in ('WIN','LOSS')
                path=base/row['input'];key=(sha(path),row['merge'])
                if key not in cache:
                    model=Model(json.loads(path.read_text()),row['merge']);seen,graph=model.enumerate();ranks,iterations=model.solve(seen,graph)
                    cache[key]=(model,seen,graph,ranks,iterations)
                    report['sources'].append(dict(input=str(path.relative_to(E6)),sha256=key[0],merge=key[1]))
                model,seen,graph,ranks,iterations=cache[key]
                decision='WIN' if model.roots<=ranks.keys() else 'LOSS'
                assert row['decision']==decision,(family,row['job_id'],'decision differs')
                proof=json.loads((base/row['certificate_file']).read_text());audit=model.certificate(proof,seen,ranks)
                if row['solver']=='direct_full':
                    assert len(seen)==int(row['states_discovered']),(family,row['job_id'],'DF states differ',len(seen),row['states_discovered'])
                    assert len(graph)==int(row['states_expanded']),(family,row['job_id'],'DF expansions differ')
                    assert sum(len(b) for b in graph.values())==int(row['enabled_buckets']),(family,row['job_id'],'DF buckets differ')
                    assert sum(len(ts) for b in graph.values() for ts in b.values())==int(row['materialized_transitions']),(family,row['job_id'],'DF outcomes differ')
                audit.update(family=family,job=row['job_id'],decision=decision,full_states=len(seen),full_expanded=len(graph),strong_winning_states=len(ranks),iterations=iterations,
                    minimum_worst_root_rank=max(ranks[s] for s in model.roots) if decision=='WIN' else None,
                    activation_language_checks=model.language_checks,merge_commutation_checks=model.commutation_checks)
                report['audits'].append(audit)
            print(json.dumps(dict(family=family,status='PASS',audited_jobs=len(rows))),flush=True)
        report['status']='PASS';report['distinct_input_merge_games']=len(cache)
    except BaseException as e:
        report['status']='FAIL';report['error']=str(e);report['traceback']=traceback.format_exc()
    report['elapsed_seconds']=time.monotonic()-start;report['finished_at']=datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('audits','sources','traceback')}))
    return report['status']!='PASS'
if __name__=='__main__':raise SystemExit(main())
