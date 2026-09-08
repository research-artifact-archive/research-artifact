import datetime, hashlib, itertools, json, pathlib, signal, time, traceback

ROOT = pathlib.Path(__file__).resolve().parent


def save(p, value):
    with p.open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write('\n')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def scalar(case, B):
    cp, edges = case['cp'], case['edges']
    n = len(cp)
    full = (1 << n)-1
    table = [[0]*(1 << n) for _ in range(B+1)]
    choices = {}
    for b in range(1, B+1):
        for s in range(1, 1 << n):
            options = []
            for i, (c,p) in enumerate(cp):
                if s & (1 << i) and not any(v==i and s & (1 << u) for u,v in edges):
                    child = s ^ (1 << i)
                    options.append((p+table[b][child],i,'protected'))
                    options.append((max(table[b][child],c+table[b-1][s]),i,'fast'))
            best = min(x[0] for x in options)
            table[b][s] = best
            choices[f'{s}:{b}'] = [list(x[1:]) for x in options if x[0]==best]
    order_tables = []
    for order in itertools.permutations(range(n)):
        pos = {x:k for k,x in enumerate(order)}
        if not all(pos[u]<pos[v] for u,v in edges):
            continue
        f = [[0]*(n+1) for _ in range(B+1)]
        for b in range(1,B+1):
            for k in range(n-1,-1,-1):
                c,p=cp[order[k]]
                f[b][k] = min(p+f[b][k+1],max(f[b][k+1],c+f[b-1][k]))
        order_tables.append(dict(order=list(order),roots=[f[b][0] for b in range(B+1)]))
    values = [row[full] for row in table]
    fixed = [min(r['roots'][b] for r in order_tables) for b in range(B+1)]
    return dict(adaptive=values, fixed=fixed, order_tables=order_tables, choices=choices,
                table=table, normal=sum(c for c,p in cp))


def at(profile,b):
    row = max((x for x in profile if x[0]<=b),key=lambda x:x[0])
    return row[1]+(b-row[0])*row[2]


def alarm(sig,frame):
    raise TimeoutError('fixed selected check cap')


def run():
    summary=json.loads((ROOT/'SUMMARY.json').read_text())
    selected={r['id']:r for r in summary['chain_bests'] if r}
    rows={}
    for line in (ROOT/'RAW.jsonl').open():
        r=json.loads(line)
        if r['id'] in selected: rows[r['id']]=r
    cases=[dict(id=r['id'],case=r['case'],B=max(4,r['budget']+2),
                old_v=rows[r['id']]['v_profile'],old_f=rows[r['id']]['f_profile']) for r in selected.values()]
    for k in (1,2,3,7,101,2**40):
        cases.append(dict(id=f'family-k{k}',family_k=k,B=4,
             case=dict(cp=[[3*k,2*k],[7*k,2*k],[5*k,6*k],[k,2*k]],edges=[[0,1],[0,2],[1,3]])))
    save(ROOT/'SELECTED_INPUTS.json',cases)
    files=['SELECTED_CHECK_PLAN.md','scalar_check.py','SELECTED_INPUTS.json','SUMMARY.json','RAW.jsonl']
    save(ROOT/'SELECTED_MANIFEST.json',dict(units=len(cases),unit_seconds=2,total_seconds=30,
         utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         files=[dict(path=f,sha256=sha(ROOT/f)) for f in files]))
    start=time.monotonic();results=[]
    signal.signal(signal.SIGALRM,alarm)
    with (ROOT/'SELECTED_RAW.jsonl').open('x') as raw:
        for unit in cases:
            t=time.monotonic()
            if t-start>=30:
                result=dict(id=unit['id'],status='NOT_RUN')
            else:
                signal.setitimer(signal.ITIMER_REAL,min(2,30-(t-start)))
                try:
                    value=scalar(unit['case'],unit['B'])
                    assert all(v<=f for v,f in zip(value['adaptive'],value['fixed']))
                    if 'family_k' in unit:
                        k=unit['family_k']
                        assert value['adaptive'][2]==8*k,value
                        assert value['fixed'][2]==10*k,value
                        assert value['normal']==16*k,value
                    else:
                        assert value['adaptive']==[at(unit['old_v'],b) for b in range(unit['B']+1)],value
                        assert value['fixed']==[at(unit['old_f'],b) for b in range(unit['B']+1)],value
                    result=dict(id=unit['id'],status='SUCCESS',**value)
                except AssertionError:
                    result=dict(id=unit['id'],status='FAILURE',error=traceback.format_exc())
                except TimeoutError:
                    result=dict(id=unit['id'],status='TIMEOUT')
                except Exception:
                    result=dict(id=unit['id'],status='INVALID',error=traceback.format_exc())
                finally:signal.setitimer(signal.ITIMER_REAL,0)
            result['elapsed_seconds']=time.monotonic()-t
            results.append(result)
            raw.write(json.dumps(result,separators=(',',':'))+'\n');raw.flush()
    report=dict(units=len(cases),status_counts={s:sum(r['status']==s for r in results) for s in
          ['SUCCESS','FAILURE','TIMEOUT','INVALID','NOT_RUN']},
          elapsed_seconds=time.monotonic()-start,raw_sha256=sha(ROOT/'SELECTED_RAW.jsonl'),
          roots=sum(len(r.get('adaptive',[])) for r in results))
    save(ROOT/'SELECTED_SUMMARY.json',report)
    print(json.dumps(report,indent=2))
    print(json.dumps(next(r for r in results if r['id']=='family-k1'),indent=2))


if __name__=='__main__':run()
