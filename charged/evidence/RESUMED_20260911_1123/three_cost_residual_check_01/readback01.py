"""Post-run integrity/count readback only. No oracle/formula execution or new trials."""
import gzip
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as src:
        for block in iter(lambda:src.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

def main():
    freeze=json.loads((BASE/'FREEZE01.json').read_text())
    receipt=json.loads((BASE/'run01/RECEIPT01.json').read_text())
    assert digest(BASE/'FREEZE01.json')==receipt['freeze_sha256']
    for name,meta in freeze['files'].items():
        assert digest(BASE/name)==meta['sha256'],name
    for name,meta in receipt['raw_files'].items():
        assert digest(BASE/'run01'/name)==meta['sha256'],name
    catalog=json.loads((BASE/'catalog01.json').read_text())
    graphs=json.loads((BASE/'graphs01.json').read_text())
    counts=dict(games=0,policies=0,leaves=0,modes=0,failed=0,negative_ell_probes=0,prefix_probes=0)
    witnesses=[]
    with (BASE/'population01.jsonl').open() as population, \
         gzip.open(BASE/'run01/RAW01.jsonl.gz','rt') as rawfile, \
         gzip.open(BASE/'run01/COMPARISONS01.jsonl.gz','rt') as comparisons:
        for index,line in enumerate(population):
            game=json.loads(line)
            raw=json.loads(next(rawfile))
            cmp=json.loads(next(comparisons))
            assert game['id']==raw['id']==cmp['id']==index
            cat=catalog[game['catalog']]
            assert len(raw['policies'])==len(cat['policies'])
            for pid,record in enumerate(raw['policies']):
                assert record[0]==pid
                assert len(record[2])==len(cat['policies'][pid]['leaves'])
                counts['leaves']+=len(record[2])
            counts['games']+=1
            counts['policies']+=len(raw['policies'])
            counts['modes']+=len(raw['mode_limits'])
            counts['failed']+=bool(cmp['failures'])
            counts['negative_ell_probes']+=cmp['negative_ell_probes']
            counts['prefix_probes']+=len(cmp['actual_prefix_probes'])
            if (cat['n']==2 and graphs[cat['graph']]['edges']==[[0,1]] and cat['D']==1
                    and game['k']==0 and game['types'] in ([6,3],[3,6])):
                witnesses.append(dict(game=game,graph=graphs[cat['graph']],
                    actual_benchmark=raw['benchmark_curve'],actual_state_limit=raw['state_limit'],
                    actual_mode_limits=raw['mode_limits'],comparison=cmp,
                    evidence_selection='POST_RUN_EXPLANATORY_READBACK_NOT_AN_ADDITIONAL_TRIAL'))
        assert rawfile.readline()=='' and comparisons.readline()==''
    for key in ('games','policies','leaves','modes'):
        assert counts[key]==freeze['expected'][key]
    for key in ('failed','negative_ell_probes','prefix_probes'):
        assert counts[key]==receipt[key]
    assert len(witnesses)==2
    result=dict(status='INTEGRITY_AND_DENOMINATOR_READBACK_OK',utc=datetime.now(timezone.utc).isoformat(),
        counts=counts,freeze_sha256=digest(BASE/'FREEZE01.json'),run_receipt_sha256=digest(BASE/'run01/RECEIPT01.json'),
        readback_code_sha256=digest(Path(__file__)),new_scientific_trials=0,
        inputs_code_and_raw_hashes_unchanged=True,explanatory_witnesses=witnesses)
    with (BASE/'READBACK01.json').open('x') as out:
        json.dump(result,out,indent=2,sort_keys=True)
        out.write('\n')
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':
    main()
