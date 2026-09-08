"""Fixed developer controls for the newly strict general certificate boundary."""
import copy,datetime,hashlib,json
from pathlib import Path
import evaluate,structure
ROOT=Path(__file__).resolve().parent
def save(name,data):
    with (ROOT/name).open('x') as f:json.dump(data,f,indent=2);f.write('\n')
def main():
    base=json.loads(json.dumps(evaluate.hybrid.compile_case(dict(cp=[[2,3],[1,2],[2,1]],edges=[[0,1]]))))
    assert base['route']=='ideal';full=str(base['full'])
    units=[dict(id='valid',expected='ACCEPT',data=base)]
    def add(name,edit):
        data=copy.deepcopy(base);edit(data);units.append(dict(id=name,expected='REJECT',data=data))
    add('missing_root',lambda d:d['curves'].pop(full))
    add('missing_child',lambda d:d['curves'].pop('0'))
    add('only_empty_curve',lambda d:d.update(curves={'0':[[0,0,0]]},actions={}))
    add('extra_unreachable_curve',lambda d:d['curves'].update({'1':[[0,0,0]]}))
    add('noncanonical_mask_key',lambda d:d['curves'].update({'00':d['curves'].pop('0')}))
    add('false_root_metadata',lambda d:d.update(full=0))
    add('false_state_count',lambda d:d.update(states=0))
    add('false_segment_count',lambda d:d.update(segments=0))
    add('false_root_segment_count',lambda d:d.update(root_segments=0))
    add('wrong_schema',lambda d:d.update(schema='other'))
    add('wrong_route',lambda d:d.update(route='ordered'))
    add('missing_action',lambda d:d['actions'].pop(full))
    add('extra_goal_action',lambda d:d['actions'].update({'0':dict(available=[],fast=0)}))
    add('nonready_available',lambda d:d['actions'][full].update(available=[0,1,2]))
    add('wrong_fast_tie',lambda d:d['actions'][full].update(fast=2))
    add('boolean_cost',lambda d:d['input']['cp'][0].__setitem__(0,True))
    add('negative_premium',lambda d:d['input']['cp'][0].__setitem__(1,-1))
    add('duplicate_edge',lambda d:d['input']['edges'].append([0,1]))
    add('cyclic_edge',lambda d:d['input']['edges'].append([1,0]))
    add('wrong_zero',lambda d:d['curves'][full][0].__setitem__(1,1))
    add('negative_slope',lambda d:d['curves'][full][0].__setitem__(2,-1))
    add('discontinuous_profile',lambda d:d['curves'][full][-1].__setitem__(0,d['curves'][full][-1][0]+1))
    add('wrong_tail_mass',lambda d:d['curves'][full][-1].__setitem__(1,99))
    add('shape_valid_wrong_bellman',lambda d:d['curves'].__setitem__(full,[[0,0,1],[6,6,0]]))
    # Keep the shape-valid false curve's count metadata internally consistent.
    wrong=units[-1]['data'];wrong['segments']=sum(map(len,wrong['curves'].values()));wrong['root_segments']=2
    save('CONTROL_INPUTS.json',units)
    paths=[Path(__file__),ROOT/'structure.py',ROOT/'CONTROL_INPUTS.json',ROOT.parent/'dependency_curves_01/checker.py']
    save('CONTROL_MANIFEST.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),units=len(units),files=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths],scope='development controls; no final corpus'))
    rows=[]
    for unit in units:
        stage='shape'
        try:
            structure.check(unit['data']);stage='bellman';result=evaluate.bellman.check(unit['data'])
            accepted=not result['violations'];detail=result
        except (AssertionError,TypeError,KeyError,ValueError,IndexError) as e:accepted=False;detail=repr(e)
        actual='ACCEPT' if accepted else 'REJECT'
        rows.append(dict(id=unit['id'],status='SUCCESS' if actual==unit['expected'] else 'FAILURE',expected=unit['expected'],actual=actual,stage=stage,detail=detail))
    save('CONTROL_RAW.json',rows)
    summary=dict(planned=len(rows),outcomes={s:sum(r['status']==s for r in rows) for s in ['SUCCESS','FAILURE']},negative_controls=len(rows)-1)
    save('CONTROL_SUMMARY.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
