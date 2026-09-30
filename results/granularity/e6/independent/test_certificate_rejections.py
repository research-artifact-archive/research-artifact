#!/usr/bin/env python3
"""In-memory negative tests for the independent auditor; no measured files edited."""
import copy,json
from pathlib import Path
from check_games import E6,Model,sha

checks=[]
def fixture(folder,job):
    base=E6/folder
    config=json.loads((base/'config.json').read_text());spec=next(j for j in config['jobs'] if j['id']==job)
    model=Model(json.loads((base/spec['input']).read_text()),spec['merge'])
    seen,graph=model.enumerate();ranks,_=model.solve(seen,graph)
    proof=json.loads((base/'raw/series'/job/'certificate.json').read_text())
    assert model.certificate(proof,seen,ranks)['status']=='PASS'
    return model,seen,ranks,proof

def reject(name,fixture,mutation):
    model,seen,ranks,original=fixture;proof=copy.deepcopy(original);mutation(proof)
    try:model.certificate(proof,seen,ranks)
    except (AssertionError,KeyError) as e:checks.append(dict(name=name,result='REJECTED',diagnostic=str(e)))
    else:raise AssertionError('Invalid proof accepted: '+name)

canary=fixture('canary/v1','n02_m01_fine_lazy')
reject('remove one adversarial transfer outcome',canary,lambda p:p['strategy_edges'].pop(next(i for i,e in enumerate(p['strategy_edges']) if e[1].startswith('rho_'))))
reject('remove uncontrollable report edge',canary,lambda p:p['strategy_edges'].pop(next(i for i,e in enumerate(p['strategy_edges']) if 'report' in e[1])))
reject('make a root rank zero',canary,lambda p:next(s for s in p['states'] if s['initial']).__setitem__('rank',0))
reject('invent safe flag',canary,lambda p:p['states'][0].__setitem__('safe',False))
reject('invent goal flag at a root',canary,lambda p:next(s for s in p['states'] if s['initial']).__setitem__('goal',True))
loss=fixture('rolling/v1','rolling_n02_m01_k02_lazy')
reject('remove the unsafe losing response',loss,lambda p:p.__setitem__('states',[s for s in p['states'] if s['safe']]))
reject('remove all losing initial states',loss,lambda p:p.__setitem__('states',[s for s in p['states'] if not s['initial']]))
result=dict(status='PASS',scope='Mutation controls on copied certificates only; all unmodified certificates first accepted.',checker_sha256=sha(Path(__file__).with_name('check_games.py')),checks=checks)
with (Path(__file__).parent/'mutation_controls.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result,indent=2))
