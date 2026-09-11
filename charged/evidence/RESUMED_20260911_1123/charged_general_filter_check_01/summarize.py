"""Read-only evidence checks and coverage aggregation; no target execution."""
import collections
import csv
import datetime
import hashlib
import json
from pathlib import Path
import signal

HERE = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_rows(p):
    with p.open() as f:
        for line in f:
            yield json.loads(line)


def main():
    def alarm(*args):
        raise TimeoutError('60-second summary watchdog')
    signal.signal(signal.SIGALRM, alarm)
    signal.alarm(60)
    pre = json.loads((HERE / 'SUMMARY_FREEZE.json').read_text())
    for name, expected in pre['files'].items():
        assert sha(HERE / name) == expected, name
    receipts = {}
    for attempt, families in [('attempt01', ['initial', 'policies', 'named', 'invalid', 'streams']),
                              ('attempt02', ['streams'])]:
        directory = HERE / attempt
        freeze = json.loads((directory / 'FREEZE.json').read_text())
        for name, expected in freeze['files'].items():
            assert sha(directory / name) == expected, name
        for name, expected in freeze.get('predecessor_hashes', {}).items():
            assert sha(HERE / 'attempt01' / name) == expected, name
        for family in families:
            r = json.loads((directory / (family + '_RECEIPT.json')).read_text())
            assert sha(directory / 'FREEZE.json') == r['freeze_sha256']
            assert sha(directory / (family + '_RAW.jsonl')) == r['raw_sha256']
            assert sha(directory / (family + '_FAILURES.jsonl')) == r['failures_sha256']
            receipts[attempt + '/' + family] = r
    counts = collections.Counter()
    for row in read_rows(HERE / 'attempt01/initial_RAW.jsonl'):
        counts['initial_states'] += 1
        counts['initial_viable' if row['viable'] else 'initial_unsafe'] += 1
        counts['initial_query_pairs'] += len(row['queries'])
        for q in row['queries']:
            counts['initial_actions'] += len(q['actions'])
            for action in q['actions']:
                counts['initial_actions_' + action['result']] += 1
    ir = receipts['attempt01/initial']['counts']
    assert counts['initial_states'] == ir['inputs_completed'] == 42260
    assert counts['initial_query_pairs'] == ir['query_pairs'] == 192540
    assert counts['initial_actions'] == 577620
    assert counts['initial_actions_completed'] == ir['permitted_actions_completed']
    assert counts['initial_actions_rejected-unchanged'] == ir['forbidden_actions_rejected']
    for row in read_rows(HERE / 'attempt01/policies_RAW.jsonl'):
        counts['policy_prefixes'] += 1
        if row['terminal']:
            counts['policy_leaves'] += 1
    pr = receipts['attempt01/policies']['counts']
    assert counts['policy_prefixes'] == pr['policy_prefixes'] == 20655
    assert counts['policy_leaves'] == pr['policy_leaves'] == 13341
    counts['policy_edges'] = counts['policy_prefixes'] - pr['inputs_completed']
    assert counts['policy_edges'] == pr['policy_edges'] == 20396
    for family in ['named', 'invalid']:
        count = sum(1 for _ in read_rows(HERE / ('attempt01/' + family + '_RAW.jsonl')))
        assert count == receipts['attempt01/' + family]['counts']['raw_rows']
    sources = {}
    for attempt in ('attempt01', 'attempt02'):
        rows = list(read_rows(HERE / (attempt + '/streams_RAW.jsonl')))
        sources[attempt] = {
            'steps': {(row['id'], row['index']): row for row in rows if row['phase'] == 'step'},
            'constructors': {row['id']: row for row in rows if row['phase'] == 'constructor'},
            'terminals': {row['id']: row for row in rows if row['phase'] == 'terminal'},
        }
        assert len(rows) == receipts[attempt + '/streams']['counts']['raw_rows']
        assert len(sources[attempt]['steps']) == receipts[attempt + '/streams']['counts']['stream_steps']
    a, b = sources['attempt01'], sources['attempt02']
    overlap = a['steps'].keys() & b['steps'].keys()
    for key in overlap:
        assert a['steps'][key] == b['steps'][key], ('repeated prefix changed', key)
    assert len(overlap) == 2638
    assert receipts['attempt01/streams']['status'] == 'TIMEOUT'
    assert receipts['attempt02/streams']['status'] == 'PASS'
    inputs = [c for c in read_rows(HERE / 'attempt01/inputs.jsonl') if c['family'] == 'streams']
    assert len(a['terminals']) == 37
    assert len(b['terminals']) == 2
    assert not (a['terminals'].keys() & b['terminals'].keys())
    assert a['terminals'].keys() | b['terminals'].keys() == {c['id'] for c in inputs}
    table = []
    maxima = collections.defaultdict(int)
    for case in inputs:
        src = a if case['id'] in a['terminals'] else b
        rows = [src['steps'][case['id'], i] for i in range(len(case['order']))]
        ctor = src['constructors'][case['id']]
        assert len(rows) == len(case['order'])
        record = dict(id=case['id'], name=case['name'], n=ctor['n'], initial_k=case['k'],
            source_attempt='attempt01' if src is a else 'attempt02',
            steps=len(rows), constructor_comparisons=ctor['operations']['comparisons'],
            constructor_swaps=ctor['operations']['swaps'], constructor_line_events=ctor['operations']['line_events'],
            persistent_array_slots=ctor['persistent_array_slots'])
        for phase, key in [('query', 'query'), ('complete', 'completion')]:
            for counter in ['comparisons', 'swaps', 'line_events']:
                record[phase + '_max_' + counter] = max(row[key]['operations'].get(counter, 0) for row in rows)
                maxima[phase + ':' + counter] = max(maxima[phase + ':' + counter], record[phase + '_max_' + counter])
            record[phase + '_max_repairs'] = max(row[key]['operations'].get('calls:_up', 0) +
                                                row[key]['operations'].get('calls:_down', 0) for row in rows)
            maxima[phase + ':repairs'] = max(maxima[phase + ':repairs'], record[phase + '_max_repairs'])
        for counter in ['comparisons', 'swaps', 'line_events']:
            maxima['constructor:' + counter] = max(maxima['constructor:' + counter], ctor['operations'][counter])
        table.append(record)
    steps = sum(row['steps'] for row in table)
    assert steps == 20478
    result = dict(status='COVERAGE_COMPLETE_WITH_PRESERVED_ATTEMPT01_TIMEOUT',
        target_sha256=receipts['attempt01/initial']['target_sha256'],
        family_statuses={k: r['status'] for k, r in receipts.items()}, raw_counts=dict(counts),
        stream_coverage=dict(planned_series=39, distinct_completed_series=39, planned_distinct_steps=steps,
            completed_distinct_steps=steps, attempt01_completed_series=37, attempt01_started_series=38,
            attempt01_completed_steps=16972, attempt01_unfinished_series=2, attempt01_unstarted_series=1,
            attempt01_unexecuted_steps=steps-16972, attempt02_series=2, attempt02_steps=6144,
            repeated_prefix_steps=len(overlap), repeated_prefix_identical=True, currently_missing_steps=0),
        operation_maxima=dict(maxima), all_frozen_and_predecessor_hashes_verified=True,
        target_assertion_failures=0, retained_timeouts=1,
        interpretation='Author-generated semantic checks; no independent-workload, native-cost or latency claim.')
    with (HERE / 'SUMMARY.json').open('x') as out:
        json.dump(result, out, indent=2, sort_keys=True)
    with (HERE / 'STREAM_OPERATIONS.csv').open('x', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    with (HERE / 'SUMMARY_RECEIPT.json').open('x') as out:
        json.dump(dict(status='PASS', finished_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            summary_freeze_sha256=sha(HERE / 'SUMMARY_FREEZE.json'),
            outputs={name: sha(HERE / name) for name in ['SUMMARY.json', 'STREAM_OPERATIONS.csv']},
            target_executions=0), out, indent=2, sort_keys=True)
    signal.alarm(0)
    print(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps([r for r in table if r['n'] == 4096], indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
