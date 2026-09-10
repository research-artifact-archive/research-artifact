from pathlib import Path
from functools import lru_cache
from itertools import permutations, product
from collections import Counter
import datetime, hashlib, json, time, traceback
import check01 as base

D = Path(__file__).resolve().parent
START = time.monotonic()
DEADLINE = START + 180


def bounded():
    if time.monotonic() > DEADLINE:
        raise TimeoutError('180-second order comparator cap')


def fixed_order_frontier(order, w, B):
    @lru_cache(None)
    def f(k, b):
        bounded()
        if k == len(order) or b == 0:
            return ((0, 0),)
        wi = w[order[k]]
        same, less = f(k + 1, b), f(k + 1, b - 1)
        candidates = {(e, l + wi) for e, l in same}
        candidates.update((max(a, wi + c), max(d, wi + e)) for a, d in same for c, e in less)
        # Sort by extra work, keep strictly decreasing protected work.
        frontier = []
        best = float('inf')
        for e, l in sorted(candidates):
            if l < best:
                frontier.append((e, l))
                best = l
        return tuple(frontier)
    return f(0, B)


def nondominated(candidates):
    result, best = [], float('inf')
    for e, ell in sorted(set(candidates)):
        if ell < best:
            result.append((e, ell))
            best = ell
    return result


def compare(adaptive, restricted):
    assert all(any(a <= x and b <= y for a, b in adaptive) for x, y in restricted), (adaptive, restricted)
    return [v for v in adaptive if not any(x <= v[0] and y <= v[1] for x, y in restricted)]


def main():
    receipt = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'protocol_sha256': base.sha(D / 'ORDER_PROTOCOL02.md'), 'script_sha256': base.sha(Path(__file__)),
               'original_script_sha256': base.sha(D / 'check01.py'),
               'original_summary_sha256': base.sha(D / 'SUMMARY01.json'),
               'original_frontiers_sha256': base.sha(D / 'known_frontiers01.jsonl'), 'cap_seconds': 180}
    (D / 'ORDER_START02.json').write_text(json.dumps(receipt, indent=2) + '\n')
    counts, strict_counts, independent = Counter(), Counter(), {}
    rows = 0
    with (D / 'order_comparisons02.jsonl').open('x') as out:
        for line in (D / 'known_frontiers01.jsonl').open():
            old = json.loads(line)
            inp = old['input']
            w, edges, B = tuple(inp['works']), inp['edges'], inp['B']
            adaptive = [(x['E'], x['L']) for x in old['result']['frontier']]
            if not edges:
                independent[(w, B)] = adaptive
            row = {'case': old['case'], 'input': inp}
            try:
                if time.monotonic() > DEADLINE:
                    row.update(status='NOT_EXECUTED')
                else:
                    by_order = []
                    for order in permutations(range(len(w))):
                        pos = {i: k for k, i in enumerate(order)}
                        if all(pos[a] < pos[b] for a, b in edges):
                            by_order.append((order, fixed_order_frontier(order, w, B)))
                    restricted = nondominated(v for order, front in by_order for v in front)
                    strict = compare(adaptive, restricted)
                    assert B > 1 or not strict, ('one-write control failure', inp, adaptive, restricted)
                    row.update(status='SUCCESS', adaptive=adaptive, fixed_order_union=restricted,
                               orders=len(by_order), strict_adaptive_pairs=strict)
                    if strict:
                        row['fixed_order_frontiers'] = by_order
                        row['adaptive_witnesses'] = [x for x in old['result']['frontier'] if (x['E'], x['L']) in strict]
                        strict_counts[f'B{B}'] += 1
            except TimeoutError:
                row.update(status='TIMEOUT', error=traceback.format_exc())
            except AssertionError:
                row.update(status='FAILURE', error=traceback.format_exc())
            except Exception:
                row.update(status='INVALID', error=traceback.format_exc())
            counts[row['status']] += 1
            out.write(json.dumps(row, separators=(',', ':')) + '\n')
            rows += 1
            if rows % 5000 == 0:
                print(json.dumps({'rows': rows, 'counts': counts, 'strict': strict_counts, 'seconds': time.monotonic() - START}), flush=True)
    asc_counts, asc_strict = Counter(), 0
    with (D / 'ascending_comparisons02.jsonl').open('x') as out:
        for n in range(1, 6):
            for w in product((1, 2, 4), repeat=n):
                oracle = base.Oracle(w, ()) if n == 5 else None
                order = sorted(range(n), key=lambda i: (w[i], i))
                for B in range(n + 1):
                    row = {'input': {'works': w, 'B': B}, 'order': order}
                    try:
                        if time.monotonic() > DEADLINE:
                            row.update(status='NOT_EXECUTED')
                        else:
                            adaptive = sorted(oracle.known(oracle.full, B)) if n == 5 else independent[(w, B)]
                            restricted = fixed_order_frontier(order, w, B)
                            strict = compare(adaptive, restricted)
                            row.update(status='SUCCESS', adaptive=adaptive, ascending=restricted, strict_adaptive_pairs=strict)
                            asc_strict += bool(strict)
                            if strict and oracle:
                                row['adaptive_witnesses'] = [{'pair': v, 'tree': oracle.known(oracle.full, B)[v]} for v in strict]
                    except TimeoutError:
                        row.update(status='TIMEOUT', error=traceback.format_exc())
                    except AssertionError:
                        row.update(status='FAILURE', error=traceback.format_exc())
                    except Exception:
                        row.update(status='INVALID', error=traceback.format_exc())
                    asc_counts[row['status']] += 1
                    out.write(json.dumps(row, separators=(',', ':')) + '\n')
    receipt.update(finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), seconds=time.monotonic() - START,
                   counts=counts, strict_adaptive_order_counts=strict_counts, ascending_counts=asc_counts,
                   strict_vs_ascending=asc_strict, expected_counts={'order': 26844, 'ascending': 2004},
                   outputs={name: base.sha(D / name) for name in ['order_comparisons02.jsonl', 'ascending_comparisons02.jsonl']})
    receipt['status'] = 'SUCCESS' if counts == {'SUCCESS': 26844} and asc_counts == {'SUCCESS': 2004} else 'NON_SUCCESS'
    (D / 'ORDER_SUMMARY02.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
