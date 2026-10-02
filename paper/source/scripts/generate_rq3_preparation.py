"""Summarize existing fixed-budget preparation fields; never execute synthesis."""
import argparse
from collections import defaultdict
from contextlib import contextmanager
import csv
from decimal import Decimal
import gzip
import io
from pathlib import Path
import shutil
from statistics import median
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    'gsm': 'GSM', 'industry': 'Industry', 'metasocket': 'MetaSocket',
    'powerplant': 'PowerPlant', 'productioncell_arms1': 'PC1',
    'productioncell_arms2': 'PC2', 'railcab': 'Railcab',
    'surveillance': 'Surveillance', 'workflow': 'Workflow',
}
METHODS = {
    'fg_ducs_otf': 'Lazy', 'fg_ducs_otf_eager_controllable': 'Eager',
    'fg_ducs_otf_update_first': 'Update-first', 'direct_full': 'Direct-Full',
}
KEYS = ('definition_prepare_total_time', 'revised_preparation_time',
        'revised_reachable_physical_states_for_activation')
MEMBER = 'FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/raw/rq3/metrics_long.csv.gz'


@contextmanager
def metrics_stream(explicit):
    if explicit:
        with Path(explicit).open(newline='') as source:
            yield source
        return
    # The public package stores the original CSV in a split tar.gz. Reading it
    # in a temporary stream avoids creating a second copy in the repository.
    artifact = next((p for p in ROOT.parents
                     if (p/'results/archives/raw-results.tar.gz.part000').is_file()), None)
    if artifact is None:
        raise ValueError('Pass --metrics pointing to a materialized metrics_long.csv')
    with tempfile.TemporaryFile() as joined:
        for part in sorted((artifact/'results/archives').glob('raw-results.tar.gz.part*')):
            with part.open('rb') as source:
                shutil.copyfileobj(source, joined)
        joined.seek(0)
        with tarfile.open(fileobj=joined, mode='r|gz') as archive:
            for member in archive:
                if member.name == MEMBER:
                    with archive.extractfile(member) as compressed:
                        with gzip.GzipFile(fileobj=compressed) as unpacked:
                            with io.TextIOWrapper(unpacked, encoding='utf-8', newline='') as source:
                                yield source
                    return
    raise ValueError('Missing original metrics CSV in the public archive')


def collect(explicit):
    cells = {(r['model_id'], r['target_id'], r['method_id']): r
             for r in csv.DictReader((ROOT/'build/generated/rq3-cells.csv').open())}
    assert len(cells) == 135
    values = defaultdict(dict)
    with metrics_stream(explicit) as source:
        for row in csv.DictReader(source):
            cell = row['model_id'], row['target_id'], row['method_id']
            if cell not in cells or cell[2] not in METHODS or row['metric_key'] not in KEYS:
                continue
            assert row['completed'] == 'True' and row['process_status'] in ('SUCCESS', 'UNREALIZABLE')
            assert cells[cell]['display_complete_five'] == 'True'
            run = cell + (int(row['repetition']),)
            key = row['metric_key']
            assert key not in values[run], (run, key)
            assert row['unit'] == ('states' if key == KEYS[2] else 'ms'), row['unit']
            values[run][key] = Decimal(row['value'])
    assert len(values) == 405
    records = []
    for model in MODELS:
        for variant in ('base', 'r1', 'r2'):
            closure_counts = set()
            for method in METHODS:
                cell = model, variant, method
                complete = cells[cell]['display_complete_five'] == 'True'
                runs = [values[cell + (rep,)] for rep in range(1, 6)
                        if cell + (rep,) in values]
                assert len(runs) == (5 if complete else 0), cell
                rec = dict(model_id=model, target_id=variant, method_id=method,
                           status='complete' if complete else cells[cell]['effective_stage1_status'],
                           repetitions=len(runs), closure_states='')
                for prefix, key in zip(('definition_seconds', 'adapter_seconds'), KEYS[:2]):
                    data = [r[key]/1000 for r in runs]
                    for stat, func in (('median', median), ('min', min), ('max', max)):
                        rec[prefix+'_'+stat] = str(func(data)) if data else ''
                if runs:
                    assert all(set(r) == set(KEYS) for r in runs)
                    counts = {r[KEYS[2]] for r in runs}
                    assert len(counts) == 1
                    closure_counts |= counts
                    rec['closure_states'] = str(int(next(iter(counts))))
                records.append(rec)
            assert len(closure_counts) <= 1, (model, variant, closure_counts)
    assert sum(r['repetitions'] == 5 for r in records) == 81
    return records


def number(text):
    return f'{Decimal(text):.3f}'.removeprefix('0')


def timing(row, prefix):
    if row['status'] != 'complete':
        return r'TO$^{\dagger}$' if (row['model_id'], row['target_id'], row['method_id']) == (
            'workflow', 'r2', 'direct_full') else 'TO'
    return r'\PrepTime' + ''.join('{'+number(row[prefix+'_'+stat])+'}'
                                 for stat in ('median', 'min', 'max'))


def render(records, prefix, closure):
    rows = {(r['model_id'], r['target_id'], r['method_id']): r for r in records}
    lines = [r'% Generated from the original fixed-budget metrics CSV; seconds.',
             r'\begingroup\footnotesize\setlength{\tabcolsep}{3pt}',
             r'\newcommand{\PrepTime}[3]{#1\,{\scriptsize[#2--#3]}}',
             r'\begin{tabular}{@{}l' + ('r' if closure else '') + r'rrrr@{}}\toprule',
             'Contract' + (' & Closure' if closure else '') +
             r' & Lazy & Eager & Update-first & Direct-Full\\\midrule']
    for i, model in enumerate(MODELS):
        if i:
            lines.append(r'\addlinespace[3pt]')
        for variant in ('base', 'r1', 'r2'):
            group = [rows[model, variant, method] for method in METHODS]
            fields = [MODELS[model]+' / '+('Base' if variant == 'base' else variant.upper())]
            if closure:
                states = {r['closure_states'] for r in group if r['closure_states']}
                fields.append(f'{int(next(iter(states))):,}' if states else '--')
            fields.extend(timing(r, prefix) for r in group)
            lines.append(' & '.join(fields)+r'\\')
    lines.extend([r'\bottomrule\end{tabular}\endgroup', ''])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metrics', type=Path, help='Original materialized metrics_long.csv')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    rows = collect(args.metrics)
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader(); writer.writerows(rows)
    outputs = {'rq3-preparation.csv': stream.getvalue(),
               'rq3-definition-times.tex': render(rows, 'definition_seconds', False),
               'rq3-adapter-times.tex': render(rows, 'adapter_seconds', True)}
    for name, data in outputs.items():
        target = ROOT/'build/generated'/name
        if args.check:
            assert target.read_text() == data, 'Saved preparation display differs: '+name
        else:
            target.write_text(data)
    print('PASS: 27 contracts, 108 method cells, 405 completed runs; all missing phase values retained.')


if __name__ == '__main__':
    main()
