#!/usr/bin/env python3
"""Compare E4-1 merges with unchanged inputs and separately classified manual restrictions."""
from collections import Counter
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[3]
EXPERIMENTS = HERE.parents[1]
sys.path.insert(0, str(EXPERIMENTS / 'ablation_20260928/scripts'))
from ablation_common import OLD_JAR, csv_write, planned_jobs, read_json, read_trial, sha256, write_json

GOOD = {'WIN', 'LOSS'}
LABELS = {'pc_separation_local_fg': 'Cell separation/local',
          'pc_separation_global_product': 'Cell separation/product',
          'pc_neutral_local_fg': 'Cell neutral/local',
          'pc_neutral_global_product': 'Cell neutral/product',
          'branching_separation': 'Branch separation', 'branching_neutral': 'Branch neutral',
          'requirement_boundary_separation': 'Boundary separation',
          'requirement_boundary_neutral': 'Boundary neutral'}


def relative(path):
    return str(Path(path).relative_to(ROOT))


def read(meta):
    row = read_trial(meta)
    if row.get('meta_path'):
        row['meta_path'] = relative(meta)
    return row


def prior(model, method='full_fg'):
    meta = EXPERIMENTS / 'semantic_revision_20260914/rq2/raw/runs' / f'{model}__base__rep01__{method}' / 'meta.json'
    row = read(meta)
    assert row['decision'] in GOOD and not row['validation_errors'], (model, method, row)
    assert row['jar_sha256'] == OLD_JAR
    return row


def relation(left, right):
    if left not in GOOD or right not in GOOD:
        return 'NOT_COMPARABLE'
    return 'SAME' if left == right else 'DIFFERENT'


def manual_refs(model, merge):
    if model.endswith('local_fg'):
        yield (model.replace('local_fg', 'global_product'), 'full_fg',
               'MATCH' if merge in {'transfers', 'both'} else 'MISMATCH',
               'transfer-product restriction only; full-game isomorphism is not claimed' if merge in {'transfers', 'both'}
               else 'boundary merging leaves the two local transfer events separate')
    elif model.endswith('global_product'):
        yield (model, 'full_fg', 'NOT_APPLICABLE', 'already a single global-product transfer; control input, no new granularity restriction')
    elif model.startswith('requirement_boundary'):
        yield (model, 'requirement_block', 'MISMATCH',
               'one stop and one start: boundary merging only renames them and preserves their gap; requirement_block additionally restricts the gap')
    else:
        for method in ('fixed_script_a', 'fixed_script_b'):
            yield (model, method, 'NOT_APPLICABLE', 'fixed scripts restrict observation-dependent action choice; event merging does not impose this restriction')


def decision_cell(row, states_key='states_discovered', decision_key='decision'):
    decision = row[decision_key]
    states = row.get(states_key, '')
    return decision + (f' ({int(states):,})' if decision in GOOD and states != '' else '')


def main():
    config = read_json(HERE / 'configs/e4_1_mac.json')
    inputs = {r['model_id']: r for r in read_json(HERE / 'inputs/input_manifest.json')}
    rows, comparisons, bases = [], [], []
    for model in config['models']:
        base = prior(model['id'])
        source = inputs[model['id']]
        assert base['input_sha256'] == source['source_sha256'] == sha256(ROOT / source['copy_path'])
        bases.append(dict(model_id=model['id'], label=LABELS[model['id']], evidence='existing none/full_fg first trial', **base))
    for job in planned_jobs(config):
        model, merge = job['model_id'], job['merge']
        old = prior(model)
        row = read(HERE / 'raw/single_1200s/runs' / job['job_id'] / 'meta.json')
        source = inputs[model]
        input_check = 'PASS' if row.get('input_sha256') == source['copy_sha256'] else 'NOT_RUN' if row['decision'] == 'NOT_RUN' else 'FAIL'
        rows.append(dict(model_id=model, label=LABELS[model], merge=merge,
                         source_path=source['source_path'], copy_path=source['copy_path'],
                         source_sha256=source['source_sha256'], copy_sha256=source['copy_sha256'], input_check=input_check,
                         none_decision=old['decision'], none_states=old['states_discovered'], none_jar_sha256=old['jar_sha256'],
                         none_meta=old['meta_path'], none_decision_relation=relation(row['decision'], old['decision']), **row))
        for manual_model, method, match, reason in manual_refs(model, merge):
            manual = prior(manual_model, method)
            measured = relation(row['decision'], manual['decision'])
            conclusion = 'NOT_APPLICABLE' if match == 'NOT_APPLICABLE' else ('DIFFERENT_CONSTRAINTS_' + measured if match == 'MISMATCH' else measured)
            comparisons.append(dict(model_id=model, merge=merge, automatic_decision=row['decision'],
                                    automatic_meta=row.get('meta_path', ''), manual_model_id=manual_model, manual_method=method,
                                    manual_decision=manual['decision'], manual_meta=manual['meta_path'],
                                    manual_jar_sha256=manual['jar_sha256'], manual_input_sha256=manual['input_sha256'],
                                    constraint_match=match, constraint_reason=reason,
                                    measured_decision_relation=measured, comparison_conclusion=conclusion))
    out = HERE / 'tables'
    csv_write(out / 'e4_1_trials.csv', rows, list(dict.fromkeys(k for r in rows for k in r)))
    csv_write(out / 'e4_1_none_baselines.csv', bases, list(dict.fromkeys(k for r in bases for k in r)))
    csv_write(out / 'e4_1_manual_comparison.csv', comparisons)
    lines = [r'\begin{table}[t]', r'\centering\small',
             r'\caption{E4-1: unchanged RQ2 fixtures under automatic contract merging. Entries are decisions (discovered states). T merges transfers; B merges stop events together and start events together; T+B applies both.}',
             r'\begin{tabular}{lrrrr}', r'\toprule', r'Fixture & None (existing) & T & B & T+B \\', r'\midrule']
    for model in config['models']:
        group = [r for r in rows if r['model_id'] == model['id']]
        old = next(r for r in bases if r['model_id'] == model['id'])
        lines.append(LABELS[model['id']] + ' & ' + decision_cell(old) + ' & ' + ' & '.join(decision_cell(r) for r in group) + r' \\')
    lines += [r'\bottomrule', r'\end{tabular}',
              r'\par\footnotesize New merges use the fixed E1 JAR, 32 GiB, one trial, and a 1,200 s cap. None reuses the validated original full\_fg trial (original JAR, 2 GiB, 60 s cap); no timing comparison is made. The boundary fixtures have one stop and one start, so their gap remains. Rank and returned losing-certificate size are in the CSV.', r'\end{table}', '']
    (out / 'e4_1_decisions.tex').write_text('\n'.join(lines))
    manual_lines = [r'\begin{table}[t]', r'\centering\small',
                    r'\caption{Manual restrictions are compared separately from constraint correspondence. Automatic columns are T/B/T+B decisions; agreement alone does not establish equal constraints.}',
                    r'\begin{tabular}{llll}', r'\toprule', r'Fixture & Automatic & Manual reference & Constraint relation \\', r'\midrule']
    for model in config['models']:
        model_id = model['id']; group = [r for r in rows if r['model_id'] == model_id]
        auto = '/'.join(r['decision'] for r in group)
        comp = [r for r in comparisons if r['model_id'] == model_id and r['merge'] == 'transfers']
        if model_id.endswith('local_fg'):
            manual_text = 'Product: ' + comp[0]['manual_decision']; match = 'T,T+B: product; B: mismatch'
        elif model_id.endswith('global_product'):
            manual_text = 'Product: ' + comp[0]['manual_decision']; match = 'Already-global control'
        elif model_id.startswith('requirement_boundary'):
            manual_text = 'Block: ' + comp[0]['manual_decision']; match = 'Mismatch: gap retained'
        else:
            manual_text = 'Fixed A/B: ' + '/'.join(r['manual_decision'] for r in comp); match = 'Not applicable'
        manual_lines.append(LABELS[model_id] + ' & ' + auto + ' & ' + manual_text + ' & ' + match + r' \\')
    manual_lines += [r'\bottomrule', r'\end{tabular}',
                     r'\par\footnotesize Cell correspondence concerns the product transfer restriction and its decision, not a proof of full-game isomorphism. Requirement-block additionally constrains the stop/start gap; B does not. Fixed scripts restrict observation-dependent choices, which contract merging does not restrict. Manual decisions reuse the semantic-revision RQ2 raw. All provenance and per-mode relations are in the CSV.', r'\end{table}', '']
    (out / 'e4_1_manual_comparison.tex').write_text('\n'.join(manual_lines))
    result = dict(outcomes=dict(Counter(r['decision'] for r in rows)),
                  none_changed=[r['model_id'] + '/' + r['merge'] for r in rows if r['none_decision_relation'] == 'DIFFERENT'],
                  constraint_relations=dict(Counter(r['constraint_match'] for r in comparisons)),
                  manual_comparison_conclusions=dict(Counter(r['comparison_conclusion'] for r in comparisons)),
                  validation_failures=[r['model_id'] + '/' + r['merge'] for r in rows if r['decision'] in GOOD and (r['validation_errors'] or r['input_check'] != 'PASS')])
    write_json(out / 'summary.json', result)
    print(result)


if __name__ == '__main__':
    main()
