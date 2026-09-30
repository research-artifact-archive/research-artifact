#!/usr/bin/env python3
"""Input-only audit of the preregistered error-label repair. No solver/results are read."""
from pathlib import Path
import copy
import hashlib
import json
HERE=Path(__file__).resolve().parent
INITIAL=HERE.parent/'e4_2'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    checks=[]
    for n in range(2,11):
        name=f'cell_n{n:02d}.json';old_path=INITIAL/'inputs'/name;new_path=HERE/'inputs'/name
        old=json.loads(old_path.read_text());new=json.loads(new_path.read_text());expected=copy.deepcopy(old)
        stations=old['stations']; moves=['m_'+s for s in stations]
        if n>=5:
            one=expected['requirements']['one'];one['error']='ERR_ONE';one['states'][-1]='ERR_ONE'
            one['omitted_transitions']='stutter; ERR_ONE absorbs every alphabet event'
            for e in one['changes']:
                if e[1] != moves[(stations.index(e[0])+1)%n]:e[2]='ERR_ONE'
        else:assert old_path.read_bytes()==new_path.read_bytes(),(n,'n2..4 bytes changed')
        assert new==expected,(n,'change outside exact one-error label repair')
        for name,monitor in new['requirements'].items():
            states=monitor['states'];assert len(states)==len(set(states)),(n,name,'duplicate states')
            assert monitor['error'] in states and monitor['initial']!=monitor['error']
            for q,event,target in monitor['changes']:
                assert q in states and target in states and event in monitor['alphabet']
            assert len({(q,a) for q,a,t in monitor['changes']})==len(monitor['changes'])
        one=new['requirements']['one'];assert one['error'] not in stations
        table={(q,a):t for q,a,t in one['changes']}
        for i,holder in enumerate(stations):
            # The Java adapter initializes one at the holder name for each all-old one-product root.
            assert holder in one['states'] and holder!=one['error']
            for j,event in enumerate(moves):
                target=stations[j] if j==(i+1)%n else one['error']
                assert table[holder,event]==target
        checks.append(dict(n=n,original_sha256=sha(old_path),corrected_sha256=sha(new_path),n2_to_n4_byte_identity=sha(old_path)==sha(new_path) if n<5 else None,exact_diff_scope='only one error name/declaration, erroneous transition targets, and corresponding description' if n>=5 else 'no input difference',all_monitor_states_unique=True,holder_error_disjoint=True,all_one_initializer_states_nonerror=True))
    for name in ('CellRingDriver.java','FixedCellReference.java','run_cell_ring.py','run-e4-2-mac.sh','verify_cell_ring.py','validate_generated_endpoints.py'):
        assert (INITIAL/name).read_bytes()==(HERE/name).read_bytes(),('code unexpectedly changed',name)
    out=HERE/'validation'/'correction_scope.json';out.parent.mkdir(exist_ok=True)
    with out.open('x') as f:json.dump({'status':'PASS','performed_before_corrected_series':True,'meaning':'Faithful representation of n normal holder states plus a distinct error state. Original invalid contracts had no solver outcomes for n>=5. All physical LTSs, transfers, normal monitor behavior, initializer values, endpoints, and solver settings are unchanged.','rows':checks},f,indent=2)
    print('PASS: exact input correction scope, n2..4 byte identity, all state identifiers/type conditions, and unchanged adapter/settings')
if __name__=='__main__':main()
