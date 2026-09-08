"""One-shot fixed final semantic run. The final manifest is required."""
from pathlib import Path
import collections,datetime,hashlib,json,resource,signal,sys,time,traceback
from evaluate_final import evaluate
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc)
def save(name,data):
    with (ROOT/name).open('x') as f:json.dump(data,f,indent=2);f.write('\n')
def timeout(signum,frame):raise TimeoutError('per-unit 10 second deadline')
def main():
    assert not sys.flags.optimize,'assertions must be enabled'
    manifest=json.loads((ROOT/'MANIFEST.json').read_text())
    for f in manifest['files']:assert sha(Path(f['path']))==f['sha256'],f['path']
    assert sys.executable==manifest['python'] and sha(Path(sys.executable))==manifest['python_sha256']
    cases=json.loads((ROOT/'INPUTS.json').read_text());expected=json.loads((ROOT/'DENOMINATORS.json').read_text())
    assert len(cases)==4232 and len({c['id'] for c in cases})==4232
    save('RUN_STARTED.json',dict(utc=now().isoformat(),manifest_sha256=sha(ROOT/'MANIFEST.json')))
    artifacts=ROOT/'artifacts';artifacts.mkdir()
    start=time.monotonic();signal.signal(signal.SIGALRM,timeout);rows=[]
    with (ROOT/'RAW.jsonl').open('x') as raw:
        for index,case in enumerate(cases):
            t=time.monotonic();row=dict(input_id=case['id'],group=case['group'])
            if t-start>=180 or now()>=datetime.datetime(2026,9,8,0,50,tzinfo=datetime.timezone.utc):
                row.update(status='NOT_RUN',reason='total_or_session_deadline')
            else:
                try:
                    signal.alarm(10);result,encoded=evaluate(case);row.update(result)
                    assert {k:row[k] for k in ('states','actions','outcomes')}==case['expected_structure']
                    with (artifacts/(case['id']+'.json')).open('xb') as f:f.write(encoded)
                except TimeoutError as e:row.update(status='TIMEOUT',error=str(e))
                except AssertionError as e:row.update(status='FAILURE',error=repr(e),traceback=traceback.format_exc())
                except Exception as e:row.update(status='INVALID',error=repr(e),traceback=traceback.format_exc())
                finally:signal.alarm(0)
            row['unit_elapsed_seconds']=time.monotonic()-t
            rows.append(row);raw.write(json.dumps(row,separators=(',',':'))+'\n');raw.flush()
            if (index+1)%512==0:print(json.dumps(dict(completed=index+1,elapsed=time.monotonic()-start,outcomes=dict(collections.Counter(r['status'] for r in rows)))),flush=True)
    totals={k:sum(r.get(k,0) for r in rows) for k in ('states','actions','outcomes','policy_cells','invariant_cells')}
    summary=dict(utc=now().isoformat(),planned=len(cases),recorded=len(rows),
        terminal_outcomes={s:sum(r['status']==s for r in rows) for s in ('SUCCESS','FAILURE','TIMEOUT','INVALID','NOT_RUN')},
        groups={g:dict(collections.Counter(r['status'] for r in rows if r['group']==g)) for g in ('independent_regression','dependent')},
        routes=dict(collections.Counter(r.get('route','unavailable') for r in rows)),
        lemma_checks=dict(sum((collections.Counter(r.get('lemma_checks',{})) for r in rows),collections.Counter())),
        completed_root_values=sum(len(r.get('roots',[])) for r in rows),totals=totals,
        all_structural_units_accounted=all(totals[k]==expected['structural_totals'][k] for k in expected['structural_totals']),
        elapsed_seconds=time.monotonic()-start,raw_sha256=sha(ROOT/'RAW.jsonl'),
        process_peak_rss_native_units=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        process_peak_rss_units='bytes on recorded Darwin platform',
        final_evaluation=True,application_evidence=False,novelty_established=False,
        adverse=[r for r in rows if r['status']!='SUCCESS'])
    save('SUMMARY.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
