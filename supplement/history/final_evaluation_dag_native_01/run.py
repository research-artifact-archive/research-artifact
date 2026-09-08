"""Native fixed run/check; original dependency development runner preserved."""
from pathlib import Path
import collections,datetime,hashlib,json,subprocess,sys,time,traceback
import prepare
ROOT=Path(__file__).resolve().parent
save=prepare.save;now=prepare.now;sha=prepare.sha;expected=prepare.dev.expected
def run():
    m=json.loads((ROOT/'MANIFEST.json').read_text())
    assert not sys.flags.optimize
    assert sha(Path(m['java']))==m['java_sha256'] and sha(Path(m['javac']))==m['javac_sha256']
    assert sys.executable==m['python'] and sha(Path(sys.executable))==m['python_sha256']
    for entry in m['files']:assert sha(Path(entry['path']))==entry['sha256'],entry['path']
    assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime(2026,9,8,0,50,tzinfo=datetime.timezone.utc)
    save('RUN_STARTED.json',dict(start=now(),manifest_sha256=sha(ROOT/'MANIFEST.json')))
    t=time.monotonic();receipt=dict(start=now(),compile=None,execute=None)
    try:
        c=subprocess.run(m['compile_argv'],capture_output=True,text=True,timeout=30);receipt['compile']=dict(returncode=c.returncode,stdout=c.stdout,stderr=c.stderr)
        if c.returncode:return
        save('CLASS_RECEIPT.json',dict(created=now(),files=[dict(path=str(p),sha256=sha(p)) for p in sorted((ROOT/'classes').glob('*.class'))]))
        with (ROOT/'RAW.jsonl').open('xb') as out,(ROOT/'STDERR.txt').open('xb') as err:
            try:
                p=subprocess.run(m['execute_argv'],stdout=out,stderr=err,timeout=120);receipt['execute']=dict(returncode=p.returncode,timeout=False)
            except subprocess.TimeoutExpired:receipt['execute']=dict(returncode=None,timeout=True)
    except subprocess.TimeoutExpired as e:receipt['compile']=dict(returncode=None,timeout=True,stdout=str(e.stdout),stderr=str(e.stderr))
    finally:
        receipt.update(end=now(),elapsed_seconds=time.monotonic()-t)
        if (ROOT/'RAW.jsonl').exists():receipt['raw_sha256']=sha(ROOT/'RAW.jsonl')
        save('RUN_RECEIPT.json',receipt);print(receipt)

def check():
    data=json.loads((ROOT/'INPUTS.json').read_text());seen=collections.defaultdict(list);parse=[]
    if (ROOT/'RAW.jsonl').exists():
        for index,line in enumerate((ROOT/'RAW.jsonl').read_text().splitlines()):
            try:r=json.loads(line);seen[r['id']].append(r)
            except Exception as e:parse.append(dict(line=index,error=repr(e)))
    counts=collections.Counter();adverse=[];good={}
    for u in data['units']:
        rows=seen.pop(u['id'],[]);issues=[]
        if not rows:status='NOT_RUN'
        elif len(rows)!=1:status='INVALID'
        else:
            row=rows[0];status=row['status'];e=expected(data['cases'][u['case']],u);assert e==u['expected']
            if status=='SUCCESS':
                issues=[dict(field=k,expected=v,actual=row.get(k)) for k,v in e.items() if row.get(k)!=v]
                if issues:status='FAILURE'
                else:good[u['id']]=row
        counts[status]+=1
        if status!='SUCCESS':adverse.append(dict(id=u['id'],status=status,issues=issues,raw=rows))
    comparisons=[];gaps=[]
    groups=collections.defaultdict(list)
    for u in data['units']:groups[u['cell'],u['kind']].append(u)
    for cell in data['cells']:
        row={k:v for k,v in cell.items() if k!='policies'};row['policies']={}
        for p in cell['policies']:
            us=groups[cell['id'],p['kind']];value=max(good[u['id']]['cost'] for u in us) if all(u['id'] in good for u in us) else None
            row['policies'][p['kind']]=dict(actual_max=value,expected_max=p['expected_max'],units=len(us),model_excess=p['abstract_worst'])
            if value is not None and value!=p['expected_max']:gaps.append(dict(cell=cell['id'],kind=p['kind'],actual=value,expected=p['expected_max']))
        comparisons.append(row)
    result=dict(created=now(),denominator=len(data['units']),status=dict(counts),parse_errors=parse,unexpected_ids=list(seen),
        adverse_units=adverse,maximum_disagreements=gaps,comparison=comparisons,
        run_receipt=json.loads((ROOT/'RUN_RECEIPT.json').read_text()),raw_sha256=sha(ROOT/'RAW.jsonl') if (ROOT/'RAW.jsonl').exists() else None,final_evaluation=True)
    save('SUMMARY.json',result);print({k:result[k] for k in ['denominator','status','parse_errors','unexpected_ids','maximum_disagreements','raw_sha256']})

if __name__=='__main__':{'run':run,'check':check}[sys.argv[1]]()
