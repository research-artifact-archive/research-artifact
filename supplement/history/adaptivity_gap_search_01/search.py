import datetime, fractions, hashlib, json, pathlib, random, signal, sys, time, traceback

ROOT = pathlib.Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'dependency_curves_01' / 'curves.py'
sys.path.insert(0, str(SOURCE.parent))
import curves


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def orders(case):
    pred = curves.predecessors(case)
    def visit(s, prefix):
        if not s:
            yield prefix
        else:
            for j in curves.available(s, pred):
                yield from visit(s ^ (1 << j), prefix + [j])
    return list(visit((1 << len(case['cp'])) - 1, []))


def ordered(cp, order):
    profile = curves.ZERO
    for j in reversed(order):
        c, p = cp[j]
        profile = curves.lower(curves.shift_value(profile, p), curves.floor_slopes(profile, c))
    return profile


def evaluate(case):
    compiled = curves.compile_case(case)
    adaptive = compiled['curves'][compiled['full']]
    candidates = orders(case)
    all_profiles = [dict(order=o, profile=ordered(case['cp'], o)) for o in candidates]
    fixed = all_profiles[0]['profile']
    for row in all_profiles[1:]:
        fixed = curves.lower(fixed, row['profile'])
    boundaries = sorted({r[0] for r in adaptive} | {r[0] for r in fixed})
    base = sum(c for c, p in case['cp'])
    score = fractions.Fraction(0)
    witness = 0
    points = []
    for b in boundaries:
        v = curves.at(adaptive, b)
        f = curves.at(fixed, b)
        assert v <= f, (b, v, f)
        ratio = fractions.Fraction(f - v, base + f)
        points.append([b, v, f])
        if ratio > score:
            score, witness = ratio, b
    return dict(status='SUCCESS', score=[score.numerator, score.denominator],
                score_float=float(score), witness_budget=witness, normal=base,
                v_profile=adaptive, f_profile=fixed, points=points,
                order_profiles=all_profiles, states=compiled['states'])


def fresh(rng, n, chain, step):
    if n == 4 and chain == 0 and step == 0:
        return dict(cp=[[2,4],[11,13],[1,16],[3,9]], edges=[[0,2],[0,3],[1,2]],
                    mutation_order=[0,1,2,3], origin='observed_intro')
    if n == 5 and chain == 0 and step == 0:
        return dict(cp=[[4,23],[10,4],[3,10],[8,7],[7,17]], edges=[[1,2],[4,1],[4,2]],
                    mutation_order=[0,3,4,1,2], origin='observed_native_final47')
    return dict(cp=[[rng.randint(1,32), rng.randint(0,128)] for _ in range(n)],
                edges=[[a,b] for a in range(n) for b in range(a+1,n) if rng.random()<.3],
                mutation_order=list(range(n)), origin='new_random_block')


def mutate(rng, parent):
    case = json.loads(json.dumps(parent))
    n = len(case['cp'])
    if rng.random() < .15:
        positions = sorted(rng.sample(range(n), 2))
        edge = [case['mutation_order'][p] for p in positions]
        if edge in case['edges']:
            case['edges'].remove(edge)
        else:
            case['edges'].append(edge)
        case['edges'].sort()
        case['origin'] = 'edge_mutation'
    else:
        j, k, mode = rng.randrange(n), rng.randrange(2), rng.randrange(5)
        old = case['cp'][j][k]
        new = [old-1, old+1, old*2, old//2, rng.randint(1 if k==0 else 0, 256 if k==0 else 1024)][mode]
        case['cp'][j][k] = max(1 if k==0 else 0, min(256 if k==0 else 1024, new))
        case['origin'] = 'price_mutation'
    return case


def alarm(signum, frame):
    raise TimeoutError('predeclared slot/campaign cap')


def run():
    paths = [ROOT/'PLAN.md', ROOT/'search.py', SOURCE]
    save(ROOT/'MANIFEST.json', dict(stage='EXPLORATORY_ADAPTIVE_SEARCH_BEFORE_RUN',
         seed=202609080336, slots=12288, slot_seconds=2, total_seconds=180,
         files=[dict(path=str(p), sha256=sha(p)) for p in paths],
         python=sys.version, executable=sys.executable,
         utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    save(ROOT/'RUN_STARTED.json', dict(manifest_sha256=sha(ROOT/'MANIFEST.json'),
         utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    rng = random.Random(202609080336)
    counts = {s:0 for s in ('SUCCESS','FAILURE','TIMEOUT','INVALID','NOT_RUN')}
    start = time.monotonic()
    bests, all_scores = [], []
    signal.signal(signal.SIGALRM, alarm)
    with (ROOT/'INPUTS.jsonl').open('x') as inputs, (ROOT/'RAW.jsonl').open('x') as raw:
        for n in (3,4,5):
            for chain in range(8):
                incumbent, current_score, current_id = None, fractions.Fraction(-1), None
                chain_best = None
                for step in range(512):
                    identity = f'n{n}-chain{chain}-step{step:03d}'
                    t = time.monotonic()
                    if t-start >= 180:
                        row = dict(id=identity, n=n, chain=chain, step=step, status='NOT_RUN', reason='campaign cap')
                    else:
                        reset = step%128==0 or incumbent is None
                        case = fresh(rng,n,chain,step) if reset else mutate(rng,incumbent)
                        if reset:
                            current_score = fractions.Fraction(-1)
                            current_id = None
                        input_row = dict(id=identity, n=n, chain=chain, step=step, parent=current_id,
                                         reset=reset, case=case)
                        inputs.write(json.dumps(input_row,separators=(',',':'))+'\n');inputs.flush()
                        signal.setitimer(signal.ITIMER_REAL, min(2,180-(t-start)))
                        try:
                            row = dict(id=identity, n=n, chain=chain, step=step, **evaluate(case))
                        except TimeoutError as e:
                            row = dict(id=identity, n=n, chain=chain, step=step, status='TIMEOUT', error=str(e))
                        except AssertionError:
                            row = dict(id=identity, n=n, chain=chain, step=step, status='FAILURE', error=traceback.format_exc())
                        except Exception:
                            row = dict(id=identity, n=n, chain=chain, step=step, status='INVALID', error=traceback.format_exc())
                        finally:
                            signal.setitimer(signal.ITIMER_REAL,0)
                        if row['status']=='SUCCESS':
                            score = fractions.Fraction(*row['score'])
                            row['accepted'] = score >= current_score
                            if row['accepted']:
                                incumbent, current_score, current_id = case, score, identity
                            summary = dict(id=identity, case=case, score=row['score'],
                                           budget=row['witness_budget'], normal=row['normal'],
                                           v=curves.at(row['v_profile'],row['witness_budget']),
                                           f=curves.at(row['f_profile'],row['witness_budget']))
                            if chain_best is None or score>fractions.Fraction(*chain_best['score']):
                                chain_best = summary
                            all_scores.append((n,score))
                    row['elapsed_seconds']=time.monotonic()-t
                    counts[row['status']]+=1
                    raw.write(json.dumps(row,separators=(',',':'))+'\n');raw.flush()
                bests.append(chain_best)
                print(json.dumps(dict(n=n,chain=chain,best=chain_best,elapsed=time.monotonic()-start)),flush=True)
    ranked = sorted([r for r in bests if r],key=lambda r:fractions.Fraction(*r['score']),reverse=True)
    result = dict(slots=12288,status_counts=counts,chain_bests=bests,strongest=ranked[:8],
                  strict_successes=sum(s>0 for _,s in all_scores),
                  by_n={str(n):dict(successes=sum(k==n for k,_ in all_scores),
                         strict=sum(k==n and s>0 for k,s in all_scores)) for n in (3,4,5)},
                  elapsed_seconds=time.monotonic()-start,raw_sha256=sha(ROOT/'RAW.jsonl'),
                  inputs_sha256=sha(ROOT/'INPUTS.jsonl'))
    save(ROOT/'SUMMARY.json',result)
    print(json.dumps(dict(status_counts=counts,strongest=ranked[:2],elapsed=result['elapsed_seconds'])),flush=True)


if __name__=='__main__':
    run()
