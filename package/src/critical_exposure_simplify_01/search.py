from pathlib import Path
import datetime
import fractions
import hashlib
import importlib.util
import json
import signal
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
S = ROOT.parent
REF = S / 'critical_exposure_02/study.py'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def encoded(x): return json.dumps(x, sort_keys=True, separators=(',', ':'))
def save(path, obj):
    with path.open('x') as f:
        json.dump(obj, f, sort_keys=True, indent=2)
        f.write('\n')


def prepare():
    paths = [ROOT/'search.py', ROOT/'INPUTS.json', ROOT/'PLAN.md', REF]
    save(ROOT/'MANIFEST.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        files=[dict(path=str(p.relative_to(S)), sha256=sha(p), bytes=p.stat().st_size) for p in paths],
        python=sys.executable, python_version=sys.version, python_sha256=sha(Path(sys.executable)),
        seed_count=7, unit_seconds=5, campaign_seconds=300, final_evaluation=False))


def rank(case):
    work, edges = case['work'], case['edges']
    return len(work), len(edges), sum(work), tuple(work), tuple(tuple(e) for e in edges)


def neighbors(case):
    work, edges, q = case['work'], case['edges'], case['q']
    n = len(work)
    for removed in range(n):
        remaining = [i for i in range(n) if i != removed]
        renumber = {j:i for i,j in enumerate(remaining)}
        for projected in [False, True]:
            old_edges = {tuple(e) for e in edges if removed not in e}
            if projected:
                old_edges.update((a,b) for a,t in edges if t==removed for u,b in edges if u==removed)
            new_edges = sorted([renumber[a],renumber[b]] for a,b in old_edges)
            yield dict(work=[work[j] for j in remaining],edges=new_edges,q=q), dict(kind='delete_job', job=removed, projected=projected)
    for index in range(len(edges)):
        yield dict(work=work,edges=edges[:index]+edges[index+1:],q=q), dict(kind='delete_edge',index=index)
    for index, value in enumerate(work):
        for smaller in range(1, value):
            changed = list(work)
            changed[index] = smaller
            yield dict(work=changed,edges=edges,q=q), dict(kind='reduce_work',index=index,old=value,new=smaller)


def run():
    manifest=json.loads((ROOT/'MANIFEST.json').read_text())
    for item in manifest['files']: assert sha(S/item['path'])==item['sha256']
    assert sha(Path(sys.executable))==manifest['python_sha256'] and __debug__
    assert datetime.datetime.now(datetime.timezone.utc) < datetime.datetime.fromisoformat('2026-09-08T01:40:00+00:00')
    spec=importlib.util.spec_from_file_location('common_scalar_reference', REF)
    ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
    seeds=json.loads((ROOT/'INPUTS.json').read_text())
    assert len(seeds)==7
    def alarm(signum, frame): raise TimeoutError('fixed simplification cap')
    signal.signal(signal.SIGALRM,alarm)
    save(ROOT/'RUN_STARTED.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),manifest_sha256=sha(ROOT/'MANIFEST.json')))
    start=time.monotonic();cache={};results=[];calls=0;failed=False
    with (ROOT/'RAW.jsonl').open('x') as output:
        def emit(row):
            output.write(encoded(row)+'\n');output.flush()
        def evaluate(case, cause):
            nonlocal calls,failed
            calls+=1
            key=encoded(case)
            if key in cache:
                item=cache[key]
                emit(dict(id=calls,status='CACHED_REFERENCE',source_id=item['id'],cause=cause,case=case))
                return item
            row=dict(id=calls,case=case,cause=cause)
            before=time.monotonic();left=300-(before-start)
            if left<=0:
                row.update(status='NOT_RUN');failed=True;emit(row);raise TimeoutError('campaign exhausted')
            signal.setitimer(signal.ITIMER_REAL,min(5,left))
            try:
                cp=[[2*w,case['q']*w] for w in case['work']]
                cap=max(4,sum((p+c-1)//c for c,p in cp))
                values,fixed,orders,order_count=ref.finite_reference(dict(cp=cp,edges=case['edges']),cap)
                assert all(v<=f for v,f in zip(values,fixed))
                assert values[-1]==sum(p for c,p in cp)
                gaps=[f-v for v,f in zip(values,fixed)]
                base=sum(c for c,p in cp)
                relative=[fractions.Fraction(g,base+f) for g,f in zip(gaps,fixed)]
                at=max(range(len(relative)),key=lambda b:relative[b])
                row.update(status='SUCCESS',values=values,fixed_values=fixed,best_fixed_orders=orders,
                    topological_orders=order_count,maximum_gap=max(gaps),earliest_gap_budget=next((b for b,g in enumerate(gaps) if g),None),
                    maximum_relative_gap=[relative[at].numerator,relative[at].denominator],maximum_relative_gap_budget=at,
                    normal_work=base)
            except TimeoutError:
                row.update(status='TIMEOUT',error=traceback.format_exc());failed=True
            except AssertionError:
                row.update(status='FAILURE',error=traceback.format_exc());failed=True
            except Exception:
                row.update(status='INVALID',error=traceback.format_exc());failed=True
            finally:
                signal.setitimer(signal.ITIMER_REAL,0)
                row['seconds']=time.monotonic()-before
                emit(row)
            cache[key]=row
            if failed: raise RuntimeError('stop after adverse search unit')
            return row
        for seed in seeds:
            state=dict(seed_id=seed['id'],status='NOT_RUN')
            results.append(state)
            if failed: continue
            case=dict(work=seed['work'],edges=seed['case']['edges'],q=seed['lambda_fraction'][0])
            try:
                current=evaluate(case,dict(seed=seed['id'],kind='seed'))
                assert current['maximum_gap']>0
                path=[current['id']]
                while True:
                    best=current
                    for candidate,move in neighbors(current['case']):
                        if not candidate['work']: continue
                        tested=evaluate(candidate,dict(seed=seed['id'],parent=current['id'],move=move))
                        if tested['maximum_gap']>0 and rank(tested['case'])<rank(best['case']): best=tested
                    if best is current: break
                    emit(dict(status='SELECTED_SUCCESSOR',seed=seed['id'],parent=current['id'],selected=best['id']))
                    current=best;path.append(current['id'])
                state.update(status='SUCCESS',path=path,selected=current)
                print(dict(seed=seed['id'],calls=calls,unique=len(cache),selected=current['case'],budget=current['earliest_gap_budget']),flush=True)
            except Exception:
                failed=True
                state.update(status='STOPPED_AFTER_ADVERSE',error=traceback.format_exc(),last_selected=current if 'current' in locals() else None)
    save(ROOT/'SUMMARY.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),seconds=time.monotonic()-start,
        calls=calls,unique_cases=len(cache),results=results,raw_sha256=sha(ROOT/'RAW.jsonl'),final_evaluation=False))


if __name__=='__main__': {'prepare':prepare,'run':run}[sys.argv[1]]()
