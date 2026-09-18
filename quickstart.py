#!/usr/bin/env python3
"""Check the paper's saved evidence without Java, network access, or input edits.

All writable checkers run in a fresh, minimal package copy. Missing archived
evidence is SKIP; a failed check or different preserved value is FAIL.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

SUB = Path('FSE2027_SUBMISSION_20260914')
EXP = SUB / 'experiments'
SEM = EXP / 'semantic_revision_20260914'
RQ3 = EXP / 'rq3_xeon'
GEN = SUB / 'paper/build/generated'


class Unavailable(Exception):
    """An optional archived input or plotting dependency is absent."""


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def rows(path):
    with path.open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def equal(actual, expected, label='value'):
    if actual != expected:
        raise ValueError(f'{label}: expected {expected!r}; observed {actual!r}')


def compare_rows(actual, expected, keys, ignored=()):
    """Match all regenerated fields, preserving the complete case denominator."""
    a = {tuple(r[k] for k in keys): r for r in actual}
    b = {tuple(r[k] for k in keys): r for r in expected}
    equal(len(a), len(actual), 'unique regenerated keys')
    equal(len(b), len(expected), 'unique saved keys')
    equal(set(a), set(b), 'case keys')
    fields = set().union(*(r.keys() for r in actual)) - set(ignored)
    for key in a:
        for field in fields:
            equal(a[key].get(field, ''), b[key].get(field, ''), f'{key}/{field}')
    return len(a)


def fresh_output(path):
    if path.exists():
        raise FileExistsError('Output already exists; choose a new --output directory: ' + str(path))
    path.mkdir(parents=True, exist_ok=False)
    return path


def safe_relative(value):
    p = Path(value)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError('Expected a package-relative path: ' + str(value))
    return p


class Quickstart:
    def __init__(self, root, output):
        self.root = root.resolve()
        self.output = fresh_output(output.resolve())
        self.started = datetime.now(timezone.utc).isoformat()
        self.clock = time.monotonic()
        self.run = self.output / ('run-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
        self.work = self.run / 'workspace'
        self.logs = self.run / 'logs'
        self.logs.mkdir(parents=True)
        self.work.mkdir()
        self.records = []
        self.source_hashes = {}
        self.manifest = json.loads((self.root / 'result-assets.json').read_text()) if (self.root / 'result-assets.json').is_file() else None
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED='0',
                        MPLBACKEND='Agg', MPLCONFIGDIR=str(self.run / 'matplotlib-cache'))

    def clean(self, value):
        return str(value).replace(str(self.output), '<OUTPUT>').replace(str(self.root), '<PACKAGE>').replace(str(Path.home()), '<USER_HOME>')

    def copy(self, relative):
        relative = safe_relative(relative)
        source, target = self.root / relative, self.work / relative
        if not source.is_file():
            raise FileNotFoundError('Required package file is missing: ' + str(relative))
        if not source.resolve().is_relative_to(self.root):
            raise ValueError('Input symlink escapes the package: ' + str(relative))
        before = digest(source)
        if target.exists():
            equal(digest(target), before, 'duplicate input copy')
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)  # Never a hard link to preserved evidence.
        self.source_hashes[relative] = before
        return target

    def tree(self, relative, pattern='*'):
        source = self.root / relative
        if not source.is_dir():
            raise FileNotFoundError('Required package directory is missing: ' + str(relative))
        for p in sorted(source.rglob(pattern)):
            if p.is_file() and not ({'__pycache__', '.git'} & set(p.parts)) and p.suffix not in {'.pyc', '.jar', '.class'}:
                self.copy(p.relative_to(self.root))

    def action(self, key, claim, expected, function):
        start = time.monotonic()
        try:
            observed = function()
            status = 'PASS'
        except Unavailable as error:
            status, observed = 'SKIP', self.clean(error)
        except Exception as error:
            status, observed = 'FAIL', self.clean(type(error).__name__ + ': ' + str(error))
        self.records.append(dict(check=key, claim=claim, expected=expected, observed=str(observed),
                                 status=status, elapsed_seconds=round(time.monotonic() - start, 3)))
        print(status + ': ' + claim + ' — ' + str(observed), flush=True)

    def command(self, key, script, *arguments):
        command = [sys.executable, '-B', str(script), *map(str, arguments)]
        start = time.monotonic()
        timeout = False
        try:
            result = subprocess.run(command, cwd=self.work, env=self.env, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            captured, returncode = result.stdout, result.returncode
        except subprocess.TimeoutExpired as error:
            captured, returncode, timeout = error.stdout or '', 'TIMEOUT', True
            if isinstance(captured, bytes):
                captured = captured.decode('utf-8', errors='replace')
        text = self.clean(captured)
        with (self.logs / (key + '.log')).open('x', encoding='utf-8') as stream:
            stream.write('COMMAND: ' + self.clean(json.dumps(command)) + '\n')
            stream.write(text)
            stream.write(f'\nEXIT: {returncode}\nELAPSED_SECONDS: {time.monotonic()-start:.3f}\n')
        if timeout or returncode:
            raise RuntimeError(f'{key} exited {returncode}; see {key}.log')
        return text

    def prepare_validation(self):
        for name in ('check_package.py', 'fetch_assets.py', 'reproduce_validation.py'):
            self.copy(Path(name))
        self.tree(SEM)
        self.tree(Path('Implementation/Experiment/FSE2027/scripts'), '*.py')
        for phase in ('rq1', 'rq2'):
            config = json.loads((self.work / SEM / phase / 'raw/config.json').read_text())
            for model in config['models']:
                self.copy(Path(model['path']))

    def saved_package(self):
        self.prepare_validation()
        result = json.loads(self.command('saved-package', self.work / 'check_package.py'))
        equal(result['rq1']['jobs'], 92, 'saved RQ1 jobs')
        equal(result['rq2']['jobs'], 14, 'saved RQ2 jobs')
        return '92 RQ1 + 14 RQ2 jobs; saved decisions, certificates and raw metadata agree'

    def derive(self, phase):
        if not (self.work / 'reproduce_validation.py').is_file():
            self.prepare_validation()
        out = self.work / 'replication' / (phase + '-oracle')
        self.command(phase + '-derive', self.work / 'reproduce_validation.py', phase, '--derive-only', '--output', out)
        if phase == 'rq1':
            generated = rows(out / 'summary.csv')
            count = compare_rows(generated, rows(self.root / SEM / 'oracle/summary.csv'), ('stratum', 'model_id'), ('source',))
            counts = dict(Counter(x['expected_decision'] for x in generated))
            equal(counts, {'realizable': 18, 'unrealizable': 24, 'invalid_input': 4}, 'RQ1 oracle decisions')
            return f'{count} models: 18 WIN / 24 LOSS / 4 INVALID; all derived fields match'
        generated = rows(out / 'expected.csv')
        count = compare_rows(generated, rows(self.root / SEM / 'rq2/expected.csv'), ('model_id', 'method_id'))
        equal(dict(Counter(x['expected_decision'] for x in generated)), {'WIN': 10, 'LOSS': 4}, 'RQ2 oracle decisions')
        return f'{count} jobs: 10 WIN / 4 LOSS; all derived fields match'

    def witnesses(self):
        module = EXP / 'paper_witnesses'
        self.tree(module, '*.py')
        out = self.work / 'replication/paper-witnesses'
        self.command('paper-witnesses', self.work / module / 'check_witnesses.py', '--output', out)
        data = {r['case']: r for r in rows(out / 'summary.csv')}
        equal((data['W_cell_full']['states'], data['W_cell_full']['buckets']), ('56', '392'), 'fine cell closure')
        equal((data['W_cell_bulk']['states'], data['W_cell_bulk']['buckets']), ('10', '60'), 'bulk cell closure')
        policy = json.loads((out / 'W_cell_policy.json').read_text())
        equal((policy['retained_states'], policy['retained_edges']), (13, 11), 'cell policy')
        return 'Cell 56/392 vs bulk 10/60; policy 13 states/11 edges; branching and boundary restrictions checked'

    def diagrams(self):
        module = EXP / 'paper_witnesses'
        self.tree(module, '*.py')
        self.tree(SUB / 'paper/figures', 'witness_*.tex')
        self.tree(Path('Implementation/Experiment/FSE2027/rq2-formal-witness/models'), '*.lts')
        text = self.command('paper-diagrams', self.work / module / 'check_diagrams.py')
        for marker in ('PASS: all drawn', 'PASS dashed transfers:', 'PASS RQ2 mapRelation:'):
            if marker not in text:
                raise ValueError('Missing diagram check: ' + marker)
        return 'Figure edges, five transfer pairs, mapRelation selections and 13/11 policy match (scoped projections)'

    def rs_coverage(self):
        module = EXP / 'rs_coverage'
        self.tree(module, '*.py')
        self.copy(module / 'summary.csv')  # Strict append-only comparison is retained.
        self.tree(module / 'raw/expanded-predicates', '*.json')
        out = self.run / 'rs-generated'
        # Missing campaign raw gives unmeasured contract-census fields in this
        # new output only. Do not copy its previous contract CSV into workspace.
        self.command('rs-coverage', self.work / module / 'check_coverage.py', '--output', out,
                     '--raw-root', self.root / RQ3 / 'raw')
        generated = rows(out / 'rs-requirements.csv')
        compare_rows(generated, rows(self.root / module / 'summary.csv'), ('model', 'target', 'kind', 'requirement'))
        counts = (sum(r['exact_residual_certified'] == 'True' for r in generated),
                  sum(r['rs_A_exact'] == 'True' for r in generated),
                  sum(r['rs_E_ah_exact'] == 'True' for r in generated))
        equal(counts, (0, 138, 89), 'H/A/entry-scoped counts')
        return 'H 0/273; A inclusion 138/138 (equality conditional); entry-scoped exact 89/135; 46 unverified'

    def monolithic(self):
        module = EXP / 'industry_r1_legacy_monolithic_check'
        self.tree(module, '*.py')
        self.copy(module / '2017-TSE-Industry_T_Empty_active.lts')
        text = self.command('monolithic', self.work / module / 'check_legacy_product.py')
        for pattern in (r'BEGIN hotSwapIn meta states/edges 33093 257314',
                        r'BEGIN beginUpdate meta states/edges 14763 99676', r'UC spoiler:'):
            if not re.search(pattern, text):
                raise ValueError('Missing static reconstruction evidence: ' + pattern)
        return 'Meta products 33093/257314 and 14763/99676; safety pruning and UC spoiling loop checked'

    def archived(self, prefixes):
        """Missing archives are SKIP; present bytes differing from manifest fail."""
        if self.manifest is None:
            raise Unavailable('result-assets.json is absent; archived input completeness cannot be checked')
        records = [r for r in self.manifest['files'] if any(r['path'].startswith(str(p).replace(os.sep, '/') + '/') for p in prefixes)]
        if not records:
            raise Unavailable('No corresponding archived records are listed in result-assets.json')
        missing = []
        for record in records:
            rel = safe_relative(record['path']);p = self.root / rel
            if not p.is_file():
                missing.append(record['path']);continue
            value = digest(p)
            equal((p.stat().st_size, value), (record['bytes'], record['sha256']), 'archive identity: ' + str(rel))
            self.source_hashes[rel] = value
        if missing:
            raise Unavailable(f'{len(missing)}/{len(records)} archived files absent; restore every result asset first')
        return len(records)

    def variant(self):
        module = EXP / 'industry_r1_contract_variant'
        base = RQ3 / 'raw/industry-r1-independent'
        self.archived([module / 'raw', base])
        self.tree(module, '*.py');self.tree(module / 'inputs', '*.lts')
        self.copy(Path('Implementation/Experiment/Models/Industry_FG.lts'))
        for rel in (module / 'raw/environment.json', module / 'raw/independent-game.json',
                    base / 'environment.json', base / 'independent-game.json', base / 'graph-analysis.json'):
            self.copy(rel)
        self.command('contract-variant', self.work / module / 'check_variant.py')
        data = json.loads((self.work / module / 'raw/contract-variant-analysis.json').read_text())
        equal((data['decision'], data['initial_states'], data['winning_initial_states'], data['original_losing_initial_states']),
              ('WIN', 131, 131, 42), 'variant root correspondence')
        equal(data['all_root_rank_certificate_verified'], True, 'variant rank certificate')
        return '131/131 variant roots WIN; original 42 losing roots retained; all UC responses/ranks checked'

    def figures(self):
        names = ('rq3', 'rq4_independent', 'rq4_controlled', 'rq4_travel', 'rq4_hub',
                 'rq3_supplement_workflow_r2_direct_full', 'rq3_supplement_pc_arms2_r2_fg_3600')
        self.archived([RQ3 / 'raw' / name for name in names])
        if importlib.util.find_spec('matplotlib') is None:
            raise Unavailable('Restored evidence is present; Matplotlib is not installed in this Python')
        self.tree(RQ3 / 'scripts', '*.py');self.tree(RQ3 / 'configs', '*.json')
        self.tree(EXP / 'rq3_supplement/configs', '*.json')
        out = self.run / 'rq3-rq4-generated'
        self.command('render-results', self.work / RQ3 / 'scripts/render_results.py', '--mode', 'xeon',
                     '--input-root', self.root / RQ3 / 'raw', '--output', out)
        self.command('analyze-results', self.work / RQ3 / 'scripts/analyze_results.py',
                     '--input-root', self.root / RQ3 / 'raw', '--output', out)
        stats = json.loads((out / 'xeon-statistics.json').read_text())
        expected = json.loads((self.root / GEN / 'xeon-statistics.json').read_text())
        for method, counts in [('fg_ducs_otf', {'SUCCESS': 25, 'UNREALIZABLE': 1, 'TIMEOUT': 1}),
                               ('direct_full', {'SUCCESS': 14, 'TIMEOUT': 13}),
                               ('legacy_ducs', {'SUCCESS': 9, 'OOM': 13, 'CRASH': 5})]:
            equal(stats['rq3'][method]['stage1'], counts, method + ' statuses')
        for key in ('rq3', 'paired', 'controlled', 'independent', 'travel', 'hub'):
            equal(stats[key], expected[key], 'regenerated statistics: ' + key)
        compare_rows(rows(out / 'rq3-comparisons.csv'), rows(self.root / GEN / 'rq3-comparisons.csv'),
                     ('model_id', 'target_id', 'comparator'))
        equal(len(rows(out / 'rq3-cells.csv')), 135, 'complete table cell denominator')
        figure = out / 'rq4-scaling-combined.pdf'
        if not figure.is_file() or figure.stat().st_size == 0:
            raise ValueError('Combined scaling figure missing')
        ratio = stats['paired']['direct_full']
        return ('135 cells; FG 25 WIN/1 LOSS/1 TO; DF 14 WIN/13 TO; Legacy 9 WIN/13 OOM/5 N/M; '
                f'DF/FG completed-pair solver ratio {ratio["ratio_min"]:.5g}–{ratio["ratio_max"]:.5g}; full saved summaries match')

    def originals_unchanged(self):
        for rel, before in self.source_hashes.items():
            equal(digest(self.root / rel), before, 'preserved input: ' + str(rel))
        return f'{len(self.source_hashes)} checked source/evidence files unchanged (SHA-256)'

    def finish(self):
        elapsed = time.monotonic() - self.clock
        failed = any(r['status'] == 'FAIL' for r in self.records)
        skipped = sum(r['status'] == 'SKIP' for r in self.records)
        status = 'FAIL' if failed else ('PASS with unavailable checks skipped' if skipped else 'PASS')
        def cell(value):
            return self.clean(value).replace('|', '\\|').replace('\n', ' ')
        text = ('# Quick-start reproduction report\n\n'
                f'Result: **{status}**. Elapsed: **{elapsed:.3f} seconds**. Started (UTC): {self.started}.\n\n'
                'These are saved-evidence checks and independent finite-model derivations. No JVM synthesis, network request, '
                'or benchmark timing rerun was performed. SKIP establishes no claim; restore the archived assets and/or install '
                'Matplotlib to enable the listed optional checks. A source-built JAR is intentionally outside this no-Java check.\n\n'
                '| Claim | Expected | Observed | Status | Seconds |\n|---|---|---|---|---:|\n')
        for r in self.records:
            text += '| ' + ' | '.join(cell(r[k]) for k in ('claim', 'expected', 'observed', 'status', 'elapsed_seconds')) + ' |\n'
        text += '\nLogs and generated evidence: `' + self.run.relative_to(self.output).as_posix() + '/`. Existing package outputs were not used as write destinations.\n'
        (self.output / 'quickstart-report.md').write_text(text, encoding='utf-8')
        (self.output / 'quickstart-report.json').write_text(json.dumps(dict(status=status, elapsed_seconds=elapsed,
                started_utc=self.started, checks=self.records), indent=2) + '\n', encoding='utf-8')
        print('\n' + text)
        return 1 if failed else 0

    def execute(self):
        for key, claim, expected, function in [
            ('saved', 'Saved RQ1/RQ2 evidence', '92 + 14 jobs; all saved decisions/checks agree', self.saved_package),
            ('rq1', 'RQ1 independent derivation', '46 models; 18 WIN / 24 LOSS / 4 INVALID', lambda: self.derive('rq1')),
            ('rq2', 'RQ2 independent derivation', '14 jobs; 10 WIN / 4 LOSS', lambda: self.derive('rq2')),
            ('witnesses', 'Paper finite witnesses', 'fine/bulk separation, branch and boundary witnesses, policy 13/11', self.witnesses),
            ('diagrams', 'Figures 1 and 2', 'all declared edges/transfers and scoped fixture correspondences', self.diagrams),
            ('rs', 'Residual-soundness coverage', 'H 0/273; A 138/138; entry-scoped exact 89/135', self.rs_coverage),
            ('monolithic', 'Monolithic static cross-check', 'two meta products and uncontrollable spoiling loop', self.monolithic),
            ('variant', 'Separate Industry contract variant', '131/131 WIN; original 42 losing entries preserved', self.variant),
            ('figures', 'Table 3 / Figure 3 and comparisons', '135 cells; FG 25/1/1, DF 14/13, Legacy 9/13/5; saved ratio ranges', self.figures),
            ('unchanged', 'Preserved inputs', 'all inspected/copied evidence unchanged', self.originals_unchanged),
        ]:
            self.action(key, claim, expected, function)
        return self.finish()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parent, help='distributed package root')
    p.add_argument('--output', type=Path, help='new output directory (default: PACKAGE/replication)')
    a = p.parse_args()
    root = a.root.resolve()
    if not (root / SEM).is_dir():
        p.error('Use the distributed package root containing FSE2027_SUBMISSION_20260914/experiments')
    output = a.output if a.output is not None else root / 'replication'
    try:
        return Quickstart(root, output).execute()
    except (FileExistsError, ValueError, OSError) as error:
        p.exit(2, str(error) + '\n')


if __name__ == '__main__':
    sys.exit(main())
