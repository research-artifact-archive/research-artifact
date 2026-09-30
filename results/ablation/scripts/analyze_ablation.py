#!/usr/bin/env python3
"""Extract first trials and E1/E2 outcomes, retaining missing and adverse results."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from ablation_common import OLD_JAR, csv_write, planned_jobs, read_json, read_trial, write_json

HERE = Path(__file__).resolve().parents[1]
XEON = HERE.parent / 'rq3_xeon'
GOOD = {'WIN', 'LOSS'}
LABELS = {'gsm': 'GSM', 'industry': 'Industry', 'metasocket': 'MetaSocket', 'powerplant': 'PowerPlant',
          'productioncell_arms1': 'PC1', 'productioncell_arms2': 'PC2', 'railcab': 'Railcab',
          'surveillance': 'Surveillance', 'workflow': 'Workflow',
          'travel_n04_k04': 'Travel(4,4)', 'travel_n04_k06': 'Travel(4,6)'}


def relpath(path):
    try:
        return str(Path(path).relative_to(HERE.parent.parent))
    except ValueError:
        return str(path)


def trial(path, old=False):
    row = read_trial(path)
    if row.get('meta_path'):
        row['meta_path'] = relpath(row['meta_path'])
    if old and row['status'] != 'NOT_RUN' and row.get('jar_sha256') != OLD_JAR:
        raise ValueError(f'Unexpected existing JAR: {path}')
    return row


def baseline(campaign, model, target, method):
    return trial(XEON / 'raw' / campaign / 'runs' / f'{model}__{target}__rep01__{method}' / 'meta.json', old=True)


def new_trial(series, job, attempt):
    return trial(HERE / 'raw' / f'{series}_mac' / attempt / 'runs' / job['job_id'] / 'meta.json')


def selected_e2(job):
    first = new_trial('e2', job, 'pass1_1200s')
    second = new_trial('e2', job, 'pass2_3600s')
    # A completed valid retry supplies the final structural measurement; the first attempt remains in trials.csv.
    if second['decision'] in GOOD:
        return second, 'pass2_3600s'
    if second['status'] != 'NOT_RUN':
        return second, 'pass2_3600s'
    return first, 'pass1_1200s'


def cells(config):
    return [(m['id'], t['id']) for m in config['models'] for t in config['targets']]


def label(model, target):
    return LABELS[model] + '/' + ('Base' if target == 'base' else target.upper())


def fmt(value):
    return f'{int(value):,}' if value not in ('', None) else '--'


def tex(value):
    return str(value).replace('_', r'\_').replace('&', r'\&').replace('%', r'\%')


def completed_metric(row, key):
    return row.get(key, '') if row.get('decision') in GOOD else ''


def outcome_text(counts):
    parts = [f'{counts.get(decision, 0)} {decision}' for decision in ('WIN', 'LOSS', 'TO')]
    for decision, description in (('RUNNING', 'running'), ('NOT_RUN', 'not run')):
        if decision == 'NOT_RUN' or counts.get(decision, 0):
            parts.append(f'{counts.get(decision, 0)} {description}')
    parts.extend(f'{count} {decision}' for decision, count in sorted(counts.items())
                 if decision not in {'WIN', 'LOSS', 'TO', 'RUNNING', 'NOT_RUN'})
    return ', '.join(parts[:-1]) + ', and ' + parts[-1]


def before_cutoff(config, key, margin=0):
    cutoff = datetime.fromisoformat(config[key])
    return (cutoff - datetime.now(timezone.utc)).total_seconds() >= margin


def state_cell(row, prefix):
    value = row[prefix + '_states']
    retry_mark = r'$^{\ddagger}$' if prefix == 'ucpruned' and row['ucpruned_attempt'] == 'pass2_3600s' else ''
    if value != '':
        return fmt(value) + (r'$^{\dagger}$' if prefix == 'df' and row['df_states_source'] == 'extended_budget_single_trial' else retry_mark)
    return tex(row.get(prefix + '_decision', '--')) + retry_mark


def query_cell(row, prefix):
    value = row[prefix + '_queries']
    retry_mark = r'$^{\ddagger}$' if prefix == 'ucpruned' and row['ucpruned_attempt'] == 'pass2_3600s' else ''
    if value != '':
        return fmt(value) + retry_mark
    status = row['df_fixed_decision'] if prefix == 'df' else row.get(prefix + '_decision', '--')
    return tex({'INTERRUPTED_NOT_RETRIED': 'INT', 'NOT_PLANNED': '--',
                'NOT_RUN': 'NR', 'RUNNING': 'Pending'}.get(status, status)) + retry_mark


def analyze_e2():
    config = read_json(HERE / 'configs/e2_mac.json')
    jobs = {(j['model_id'], j['target_id']): j for j in planned_jobs(config)}
    wide, factorial, trials, checks = [], [], [], []
    all_cells = [(m, t, False) for m, t in cells(config)] + [('travel_n04_k04', 'base', True), ('travel_n04_k06', 'base', True)]
    for model, target, reference in all_cells:
        campaign = 'rq4_travel' if reference else 'rq3'
        lazy = baseline(campaign, model, target, 'fg_ducs_otf')
        eager = baseline(campaign, model, target, 'fg_ducs_otf_eager_controllable')
        df = baseline(campaign, model, target, 'direct_full')
        extended = None
        if (model, target) in {('industry', 'r1'), ('productioncell_arms1', 'r1')} or reference:
            extended = baseline('ext1_travel_frontier' if reference else 'ext2_rq3_df_cpu', model, target, 'direct_full')
        df_state_row = df
        df_source = 'fixed_budget_first_trial'
        if df['decision'] == 'TO' and extended and extended['decision'] in GOOD:
            df_state_row = extended
            df_source = 'extended_budget_single_trial'
        if reference:
            new, attempt = {'decision': 'NOT_PLANNED', 'status': 'NOT_PLANNED'}, ''
        else:
            new, attempt = selected_e2(jobs[(model, target)])
            for pass_id in ('pass1_1200s', 'pass2_3600s'):
                raw = new_trial('e2', jobs[(model, target)], pass_id)
                if pass_id == 'pass1_1200s' or raw['status'] != 'NOT_RUN':
                    trials.append(dict(model_id=model, target_id=target, label=label(model, target), attempt=pass_id, **raw))
        row = dict(model_id=model, target_id=target, label=label(model, target), reference_only=reference,
                   lazy_decision=lazy['decision'], lazy_states=completed_metric(lazy, 'states_discovered'), lazy_queries=completed_metric(lazy, 'successor_queries'),
                   eager_decision=eager['decision'], eager_states=completed_metric(eager, 'states_discovered'), eager_queries=completed_metric(eager, 'successor_queries'),
                   df_fixed_decision=df['decision'], df_decision=df_state_row['decision'], df_states=completed_metric(df_state_row, 'states_discovered'),
                   df_queries=completed_metric(df, 'successor_queries'), df_buckets=completed_metric(df, 'buckets'), df_states_source=df_source,
                   df_states_timeout_seconds=df_state_row.get('timeout_seconds', ''), df_states_meta=df_state_row.get('meta_path', ''),
                   ucpruned_decision=new['decision'], ucpruned_states=completed_metric(new, 'states_discovered'),
                   ucpruned_buckets=completed_metric(new, 'buckets'), ucpruned_queries=completed_metric(new, 'successor_queries'),
                   ucpruned_solver_seconds_mac_reference=completed_metric(new, 'solver_seconds'), ucpruned_attempt=attempt,
                   ucpruned_jar_sha256=new.get('jar_sha256', ''), ucpruned_meta=new.get('meta_path', ''),
                   decision_check='NOT_COMPARABLE', state_bound_check='NOT_COMPARABLE', input_check='NOT_COMPARABLE',
                   ucpruned_vs_eager='NOT_COMPARABLE', ucpruned_minus_eager_states='',
                   ucpruned_minus_eager_queries='', ucpruned_minus_df_queries='', ucpruned_minus_df_buckets='')
        if new['decision'] in GOOD and lazy['decision'] in GOOD:
            row['decision_check'] = 'PASS' if new['decision'] == lazy['decision'] else 'FAIL'
        if row['ucpruned_states'] != '' and row['df_states'] != '':
            row['state_bound_check'] = 'PASS' if int(row['ucpruned_states']) <= int(row['df_states']) else 'FAIL'
        if new.get('input_sha256') and lazy.get('input_sha256'):
            row['input_check'] = 'PASS' if new['input_sha256'] == lazy['input_sha256'] else 'FAIL'
        if row['ucpruned_states'] != '' and row['eager_states'] != '':
            difference = int(row['ucpruned_states']) - int(row['eager_states'])
            row['ucpruned_minus_eager_states'] = difference
            row['ucpruned_vs_eager'] = 'EQUAL' if difference == 0 else ('MORE' if difference > 0 else 'FEWER')
        for baseline_name in ('eager', 'df'):
            if row['ucpruned_queries'] != '' and row[baseline_name + '_queries'] != '':
                row['ucpruned_minus_' + baseline_name + '_queries'] = int(row['ucpruned_queries']) - int(row[baseline_name + '_queries'])
        if row['ucpruned_buckets'] != '' and row['df_buckets'] != '':
            row['ucpruned_minus_df_buckets'] = int(row['ucpruned_buckets']) - int(row['df_buckets'])
        checks.append({k: row[k] for k in ('model_id', 'target_id', 'decision_check', 'state_bound_check', 'input_check')})
        wide.append(row)
        variants = [('OTF', False, 'not_implemented', {'decision': 'NOT_IMPLEMENTED'}, '', ''),
                    ('OTF', True, 'Lazy', lazy, 'fixed_budget_first_trial', '64g'),
                    ('OTF', True, 'Eager', eager, 'fixed_budget_first_trial', '64g'),
                    ('Full', False, 'Direct-Full', df_state_row, df_source, '64g'),
                    ('Full', True, 'Direct-Full+UC', new, attempt, '32g')]
        for exploration, pruning, name, data, source, heap in variants:
            factorial.append(dict(model_id=model, target_id=target, reference_only=reference, exploration=exploration,
                                  uc_pruning=pruning, variant=name, decision=data['decision'], states_discovered=completed_metric(data, 'states_discovered'),
                                  successor_queries='' if source == 'extended_budget_single_trial' else completed_metric(data, 'successor_queries'),
                                  buckets='' if source == 'extended_budget_single_trial' else completed_metric(data, 'buckets'),
                                  evidence_source=source, heap=heap, jar_sha256=data.get('jar_sha256', ''), meta_path=data.get('meta_path', '')))
    csv_write(HERE / 'tables/e2_comparison.csv', wide)
    csv_write(HERE / 'tables/e2_factorial.csv', factorial)
    csv_write(HERE / 'tables/e2_trials.csv', trials, list(dict.fromkeys(k for r in trials for k in r)))
    csv_write(HERE / 'tables/e2_consistency.csv', checks)
    lines = [r'% Generated from first-trial raw and the separate E2 JAR; no paper files modified.',
             r'\begin{table}[t]', r'\centering\small', r'\caption{E2 discovered states. Lazy/Eager use on-the-fly exploration with UC pruning; Direct-Full uses full construction without UC pruning; Full+UC uses full construction with UC pruning. OTF without UC pruning is not implemented. Mac E2 timing is excluded.}',
             r'\label{tab:abl-e2}', r'\begin{tabular}{lrrrr}', r'\toprule',
             r'Contract & Lazy & Eager & Direct-Full & Full+UC \\', r'\midrule']
    for row in wide:
        if row['reference_only'] and not any('Reference only' in l for l in lines):
            lines.extend([r'\midrule', r'\multicolumn{5}{l}{Reference only (outside the 27 E2 cells)} \\'])
        lines.append(tex(row['label']) + ' & ' + ' & '.join(state_cell(row, p) for p in ('lazy', 'eager', 'df', 'ucpruned')) + r' \\')
    lines.extend([r'\bottomrule', r'\end{tabular}', r'\par\footnotesize $\dagger$: Direct-Full 7,200 s extended-budget single trial; only its state count is reused. $\ddagger$: Full+UC single 3,600 s second-pass trial after its 1,200 s first-pass TO, including a second-pass TO or pending outcome. Unmarked existing counts and Full+UC outcomes use the first 1,200 s trial. TO and missing trials are retained.', r'\end{table}', ''])
    (HERE / 'tables/e2_states.tex').write_text('\n'.join(lines))
    query_lines = [r'% Generated queries: extended-budget Direct-Full queries are not reused.',
                   r'\begin{table}[t]', r'\centering\small',
                   r'\caption{E2 successor-oracle calls. Lazy/Eager use on-the-fly exploration with UC pruning; Direct-Full uses full construction without UC pruning; Full+UC uses full construction with UC pruning. Existing methods use their first fixed-budget trial.}',
                   r'\label{tab:abl-e2-queries}', r'\begin{tabular}{lrrrr}', r'\toprule',
                   r'Contract & Lazy & Eager & Direct-Full & Full+UC \\', r'\midrule']
    for row in wide:
        if row['reference_only'] and not any('Reference only' in line for line in query_lines):
            query_lines.extend([r'\midrule', r'\multicolumn{5}{l}{Reference only (outside the 27 E2 cells)} \\'])
        query_lines.append(tex(row['label']) + ' & ' + ' & '.join(query_cell(row, prefix) for prefix in ('lazy', 'eager', 'df', 'ucpruned')) + r' \\')
    query_lines.extend([
        r'\bottomrule', r'\end{tabular}',
        r'\par\footnotesize TO: timed out; INT: first trial was interrupted; NR: not yet run; Pending: in progress; --: E2 was not planned for this reference input. $\ddagger$: Full+UC single 3,600 s second-pass trial after its 1,200 s first-pass TO, including a second-pass TO or pending outcome. Unmarked existing and Full+UC trials have a 1,200 s cap. Extended-budget Direct-Full trials supply state counts only; their queries are not reused, so those Direct-Full entries remain TO here. Missing or partial counts are not estimated.',
        r'\end{table}', ''])
    (HERE / 'tables/e2_queries.tex').write_text('\n'.join(query_lines))
    (HERE / 'tables/e2_design.tex').write_text('\n'.join([
        r'% Factorial placement, separate from the state-count table.',
        r'\begin{tabular}{lll}', r'\toprule', r'Exploration & UC pruning absent & UC pruning present \\',
        r'\midrule', r'On-the-fly & Not implemented & Lazy / Eager \\',
        r'Full construction & Direct-Full & Full+UC (E2) \\', r'\bottomrule', r'\end{tabular}', '']))
    counts = Counter(r['ucpruned_decision'] for r in wide if not r['reference_only'])
    compared = [r for r in wide if r['state_bound_check'] != 'NOT_COMPARABLE']
    strict = [r for r in compared if int(r['ucpruned_states']) < int(r['df_states'])]
    equal = [r for r in compared if int(r['ucpruned_states']) == int(r['df_states'])]
    retry_pending = any(r['ucpruned_decision'] == 'TO' and r['ucpruned_attempt'] == 'pass1_1200s'
                        for r in wide if not r['reference_only'])
    provisional = (counts.get('RUNNING', 0) > 0 or
                   ((counts.get('NOT_RUN', 0) + counts.get('INCOMPLETE', 0)) > 0 and before_cutoff(config, 'deadline')) or
                   (retry_pending and before_cutoff(config, 'retry_deadline', config['retry_timeout_seconds'] + 10)))
    pc1 = next(r for r in wide if (r['model_id'], r['target_id']) == ('productioncell_arms1', 'r1'))
    pc1_text = ''
    if pc1['ucpruned_states'] != '' and pc1['eager_states'] != '' and pc1['df_states'] != '':
        new_budget = 'a 3,600 s retry' if pc1['ucpruned_attempt'] == 'pass2_3600s' else 'a 1,200 s trial'
        df_budget = ('a 7,200 s extended-budget single trial, state count only' if
                     pc1['df_states_source'] == 'extended_budget_single_trial' else 'the first 1,200 s trial')
        if len({int(pc1[key]) for key in ('ucpruned_states', 'eager_states', 'df_states')}) == 1:
            pc1_text = (f'; PC1/R1 has {fmt(pc1["ucpruned_states"])} states with Full+UC ({new_budget}), '
                        f'Eager, and Direct-Full ({df_budget})')
        else:
            pc1_text = (f'; PC1/R1 has {fmt(pc1["ucpruned_states"])} states with Full+UC ({new_budget}), '
                        f'{fmt(pc1["eager_states"])} with Eager, and {fmt(pc1["df_states"])} with Direct-Full ({df_budget})')
    more = len(compared) - len(strict) - len(equal)
    more_text = f', and more in {more}' if more else ''
    text = ('[Provisional] ' if provisional else '') + (
            'E2 adds Full+UC to the 2 x 2 exploration-by-UC-pruning comparison: Lazy/Eager occupy OTF with pruning, Direct-Full occupies full construction without pruning, and OTF without pruning remains unimplemented. '
            f'The separate Mac campaign {"currently records" if provisional else "recorded"} {outcome_text(counts)} among 27 contracts; outcomes use a 1,200 s first trial or a marked 3,600 s retry after TO. '
            f'Among {len(compared)} contracts with completed comparable state counts, Full+UC discovers fewer states than Direct-Full in {len(strict)} and the same number in {len(equal)}{more_text}{pc1_text}. '
            'Mac solver times are reference measurements only; timing comparisons require the optional Xeon campaign.\n')
    (HERE / 'tables/e2_sentences.txt').write_text(text)
    return {'outcomes': dict(counts), 'strictly_fewer_states': [r['label'] for r in strict],
            'equal_states': [r['label'] for r in equal],
            'more_states_than_eager': [r['label'] for r in wide if r['ucpruned_vs_eager'] == 'MORE'],
            'equal_states_to_eager': [r['label'] for r in wide if r['ucpruned_vs_eager'] == 'EQUAL'],
            'fewer_states_than_eager': [r['label'] for r in wide if r['ucpruned_vs_eager'] == 'FEWER'],
            'equal_states_fewer_queries_than_df': [r['label'] for r in equal if r['ucpruned_minus_df_queries'] != '' and r['ucpruned_minus_df_queries'] < 0],
            'equal_states_fewer_queries_than_eager': [r['label'] for r in wide if r['ucpruned_vs_eager'] == 'EQUAL' and r['ucpruned_minus_eager_queries'] != '' and r['ucpruned_minus_eager_queries'] < 0],
            'failures': [r for r in checks if 'FAIL' in r.values()]}


def analyze_e1():
    config = read_json(HERE / 'configs/e1_mac.json')
    rows = []
    for job in planned_jobs(config):
        model, target = job['model_id'], job['target_id']
        old = baseline('rq3', model, target, 'fg_ducs_otf')
        new = new_trial('e1', job, 'pass1_1200s')
        changed = new['decision'] != old['decision'] if new['decision'] in GOOD and old['decision'] in GOOD else ''
        rows.append(dict(model_id=model, target_id=target, label=label(model, target), merge=job['merge'],
                         original_decision=old['decision'], original_states=old.get('states_discovered', ''),
                         original_meta=old.get('meta_path', ''), decision_changed=changed,
                         **new))
    csv_write(HERE / 'tables/e1_comparison.csv', rows, list(dict.fromkeys(k for r in rows for k in r)))
    lines = [r'% Generated E1 table; R2 is excluded because it refers to individual boundaries.', r'\begin{table}[t]', r'\centering\small',
             r'\caption{E1 contract merging under unchanged Post/goal semantics. T merges transfers, B merges stop/start boundaries, and T+B applies both. Entries are decisions with discovered-state counts in parentheses.}',
             r'\label{tab:abl-e1}', r'\begin{tabular}{lllll}', r'\toprule', r'Contract & Original & T & B & T+B \\', r'\midrule']
    for model, target in cells(config):
        group = [r for r in rows if (r['model_id'], r['target_id']) == (model, target)]
        entries = [r['decision'] + (f' ({fmt(completed_metric(r, "states_discovered"))})' if completed_metric(r, 'states_discovered') != '' else '') for r in group]
        lines.append(tex(label(model, target)) + ' & ' + group[0]['original_decision'] + ' & ' + ' & '.join(tex(e) for e in entries) + r' \\')
    lines.extend([r'\bottomrule', r'\end{tabular}', r'\par\footnotesize Each merged contract is one Lazy trial with a 1,200 s cap and 32 GiB heap. R2 is excluded because it refers to individual stop/start events. Rank and losing-region size are provided in the accompanying CSV.', r'\end{table}', ''])
    (HERE / 'tables/e1_decisions.tex').write_text('\n'.join(lines))
    counts = Counter(r['decision'] for r in rows)
    changed = [r for r in rows if r['decision_changed'] is True]
    compared = [r for r in rows if r['decision_changed'] != '']
    names = sorted({r['label'] for r in changed})
    input_names = sorted({LABELS[r['model_id']] for r in changed})
    changes = ', '.join(r['label'] + '/' + r['merge'] for r in changed) or 'none among the completed comparable trials'
    provisional = (counts.get('RUNNING', 0) > 0 or
                   ((counts.get('NOT_RUN', 0) + counts.get('INCOMPLETE', 0)) > 0 and before_cutoff(config, 'deadline')))
    if changed:
        changes_text = (f'Decisions changed in {len(changed)} of {len(compared)} completed comparable merged trials, '
                        f'covering {len(names)} input/requirement pairs ({", ".join(names)}) '
                        f'across {len(input_names)} inputs ({", ".join(input_names)}). ')
    elif compared:
        compared_pairs = {(r['model_id'], r['target_id']) for r in compared}
        compared_inputs = {r['model_id'] for r in compared}
        changes_text = (f'No decisions changed among the {len(compared)} completed comparable merged trials, '
                        f'covering {len(compared_pairs)} input/requirement pairs across {len(compared_inputs)} inputs. ')
    else:
        changes_text = 'No merged trial has a completed comparable decision, so decision preservation or change cannot yet be assessed. '
    text = ('[Provisional] ' if provisional else '') + (
            f'E1 evaluates transfer merging, boundary merging, and their combination on nine inputs under Base and R1 (54 {"planned " if provisional else ""}single trials; R2 is excluded because it refers to individual stop/start events). '
            f'The separate Mac campaign {"currently records" if provisional else "recorded"} {outcome_text(counts)}; {len(compared)} trials have a completed decision comparable with the original contract. '
            + changes_text +
            'These are transformations of the update contract solved under the same Post/goal semantics; they do not constitute a DUCS encoding.\n')
    (HERE / 'tables/e1_sentences.txt').write_text(text)
    return {'outcomes': dict(counts), 'completed_comparisons': len(compared), 'changed_trials': changes,
            'changed_trial_count': len(changed), 'changed_pairs': names, 'changed_pair_count': len(names),
            'changed_inputs': input_names, 'changed_input_count': len(input_names)}


def main():
    (HERE / 'tables').mkdir(exist_ok=True)
    result = {'e2': analyze_e2(), 'e1': analyze_e1()}
    write_json(HERE / 'tables/analysis_summary.json', result)
    print(result)


if __name__ == '__main__':
    main()
