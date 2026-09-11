"""Stage59: full fixed actual-price policy-tree oracle, then formula comparison."""
from pathlib import Path
import gzip,json,shutil,sys,time
from replay04_common import *

def main():
    stage,out=sys.argv[1],Path(sys.argv[2]).resolve();assert stage=='three-cost-residual';arm(175);start=time.monotonic()
    root=out/'fixed';root.mkdir();mapping=unpack(root,['three_cost_residual_check_01'])
    directory='three_cost_residual_check_01';fixed=root/directory
    freeze=check_freeze(root,mapping,directory,'FREEZE01.json')
    assert freeze['expected']['games']==157465
    work=out/'working';work.mkdir()
    for p in fixed.iterdir():
        if p.is_file():shutil.copyfile(p,work/p.name)
    runner=work/'run01.py'
    edit(runner,'deadline = datetime(2026,9,11,4,55,tzinfo=timezone.utc).timestamp()','deadline = time.time()+165',out/'adaptations')
    # The historical freeze remains in fixed/. A separately identified replay
    # freeze binds the projected copies and modified deadline in working/.
    shutil.copyfile(work/'FREEZE01.json',out/'HISTORICAL_FREEZE01.json')
    for name,meta in freeze['files'].items():
        meta.update(sha256=digest(work/name),bytes=(work/name).stat().st_size)
    freeze['replay_only']=True
    freeze['historical_freeze_public_sha256']=digest(fixed/'FREEZE01.json')
    (work/'FREEZE01.json').write_text(json.dumps(freeze,indent=2)+'\n')
    diff=''.join(difflib.unified_diff((fixed/'FREEZE01.json').read_text().splitlines(True),(work/'FREEZE01.json').read_text().splitlines(True),fromfile='historical/FREEZE01.json',tofile='working/REPLAY_FREEZE01.json'))
    (out/'adaptations/FREEZE01.diff').write_text(diff)
    save(out/'REPLAY_PROTOCOL.json',dict(stage=stage,games=157465,policy_leaves=7964521,timeout_seconds=165,original_freeze_untouched=True,working_freeze_sha256=digest(work/'FREEZE01.json'),replay_only=True))
    run([sys.executable,'-B',str(runner)],out/'oracle-process',165)
    a=json.loads((work/'run01/RECEIPT01.json').read_text());b=json.loads((fixed/'run01/RECEIPT01.json').read_text())
    keys=['status','planned','completed','passed','failed','timeout','invalid','not_run','policies','leaves','modes','benchmark_comparisons','prefix_probes','negative_ell_probes','failure_items','child_processes_spawned','frozen_files_unchanged']
    for k in keys:assert a[k]==b[k],k
    assert a['status']=='COMPLETE_NO_DISAGREEMENT'
    decoded={}
    for name in ['RAW01.jsonl.gz','COMPARISONS01.jsonl.gz']:
        h=hashlib.sha256();old=hashlib.sha256()
        with gzip.open(work/'run01'/name,'rb') as f,gzip.open(fixed/'run01'/name,'rb') as g:
            for block in iter(lambda:f.read(1048576),b''):h.update(block)
            for block in iter(lambda:g.read(1048576),b''):old.update(block)
        assert h.digest()==old.digest(),name;decoded[name]=h.hexdigest()
    save(out/'SUMMARY.json',dict(status='SUCCESS',stage=stage,seconds=time.monotonic()-start,scientific_counts={k:a[k] for k in keys},decoded_raw_sha256=decoded,full_raw_equal=True,replay_only=True,new_evaluation_population=False,new_native_measurements=0))
if __name__=='__main__':main()
