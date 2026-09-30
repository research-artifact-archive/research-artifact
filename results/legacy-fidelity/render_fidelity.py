#!/usr/bin/env python3
"""Validate returned reference campaigns and render S4; never run either solver."""
from pathlib import Path
import argparse, collections, csv, hashlib, io, json, sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'rq3_xeon/scripts'))
from render_results import Campaign, complete_five, read_csv, tex, write_csv
from collect_legacy_fidelity import collect
TOOLS = ('published', 'fork')
PARSER = {'gsm_supplied': 'T_NO_UPDATE_WHILE_SEND', 'gsm_empty': 'T_NO_UPDATE_WHILE_SEND',
          'powerplant_supplied': 'LeavesPumpOn'}


def csv_bytes(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def classify(row, stderr):
    """Display annotations require the specific saved exception and stack evidence."""
    if row['fork_stage1_status'] != 'CRASH':
        if row['decision_agreement'] != 'MATCH':
            return row['decision_agreement'], '', ''
        same = all(row['published_' + k] == row['fork_' + k] for k in ('states', 'transitions'))
        return ('MATCH' if same else 'SIZE-MISMATCH'), '', ''
    model = row['model_id']
    if model in PARSER:
        message = 'ltsa.lts.LTSException: name already defined  ' + PARSER[model]
        if message in stderr and 'LTSCompiler.validateUniqueProcessName' in stderr:
            return 'N/M', 'fork parser', message
    if model.startswith('surveillance_'):
        message = 'java.lang.IllegalArgumentException: Derived old-action authority is inconsistent: weather.old'
        if message in stderr and 'M9TraditionalSafetySemanticsSnapshot' in stderr:
            return 'N/M', 'instrumentation', message
    raise ValueError('Unclassified CRASH: ' + model)


def generate(raw_root, config_root, output):
    campaigns = {}; repetition_sizes = {}
    for tool in TOOLS:
        expected = json.loads((config_root / ('legacy_fidelity_' + tool + '.json')).read_text())
        campaign = Campaign(raw_root / ('legacy_fidelity_' + tool), 'xeon', expected)
        if campaign.config != expected:
            raise ValueError('Returned/executed config mismatch: ' + tool)
        campaigns[tool] = campaign
        original_config_hash = hashlib.sha256((campaign.path / 'config.json').read_bytes()).hexdigest()
        for saved in read_csv(campaign.path / 'raw_runs.csv'):
            if saved['process_status'].startswith('SKIPPED_'):
                continue
            meta = json.loads((campaign.path / 'runs' / saved['job_id'] / 'meta.json').read_text())
            if meta['config_sha256'] != original_config_hash:
                raise ValueError('Executed config digest differs: ' + saved['job_id'])
            if meta['classpath']['sha256'] != expected['required_classpath_sha256']:
                raise ValueError('Wrong fixed tool: ' + saved['job_id'])
            if meta['timeout_seconds'] != expected['timeout_seconds'] or '-Xmx64g' not in meta['command']:
                raise ValueError('Wrong cap: ' + saved['job_id'])
            model_path = config_root.parent / saved['model_path'].replace('\\', '/')
            if hashlib.sha256(model_path.read_bytes()).hexdigest() != meta['input_model']['sha256']:
                raise ValueError('Input digest differs: ' + saved['job_id'])
        for row in campaign.rows:
            if row['stage1_status'] == 'SUCCESS' and not complete_five(row):
                raise ValueError('Successful reference cell lacks five consistent trials')
            trials = [r for r in read_csv(campaign.path / 'raw_runs.csv')
                      if (r['model_id'], r['target_id']) == (row['model_id'], row['target_id'])
                      and r['process_status'] == 'SUCCESS']
            sizes = {(r['output_controller_states'], r['output_controller_transitions']) for r in trials}
            repetition_sizes[(tool, row['model_id'], row['target_id'])] = {int(r['repetition']): (r['output_controller_states'], r['output_controller_transitions']) for r in trials}
    rows = collect(HERE, raw_root, config_root)
    # Keep the deployed collector byte format unchanged for the eventual Xeon comparison.
    local_csv = raw_root / 'legacy_fidelity_comparison.local.csv'
    contents = csv_bytes(rows)
    if local_csv.exists() and local_csv.read_bytes() != contents:
        raise ValueError('Existing local comparison differs; preserve it for investigation')
    if not local_csv.exists(): local_csv.write_bytes(contents)
    xeon_csv = raw_root / 'legacy_fidelity_comparison.csv'
    byte_check = 'pending Xeon-produced collector file'
    if xeon_csv.exists():
        if xeon_csv.read_bytes() != contents: raise ValueError('Xeon/local collector byte mismatch')
        byte_check = 'PASS: Xeon/local collector byte equality'
    models = {m['id']: m for m in campaigns['published'].config['models']}
    initial = {(r['model_id'], r['target_id']): r for r in campaigns['fork'].initial}
    for row in rows:
        first = initial[(row['model_id'], row['target_id'])]
        stderr = campaigns['fork'].path / 'runs' / first['job_id'] / 'stderr.txt'
        decision, reason, exception = classify(row, stderr.read_text() if stderr.exists() else '')
        row.update(display_comparison=decision, censor_reason=reason, exception_message=exception)
        for tool in TOOLS:
            row[tool + '_display_status'] = 'N/M (' + reason + ')' if tool == 'fork' and reason else row[tool + '_stage1_status']
        for tool in TOOLS:
            sizes = repetition_sizes[(tool, row['model_id'], row['target_id'])]
            row[tool + '_size_varies'] = len(set(sizes.values())) > 1
            for rep in range(1, 6):
                values = sizes.get(rep, ('', ''))
                row[tool + '_rep' + str(rep) + '_states'], row[tool + '_rep' + str(rep) + '_transitions'] = values
        model = models[row['model_id']]
        row['family'] = model['family']
        row['label'] = model['family'] + ' / ' + (row['target_id'].upper() if model['family'] == 'MetaSocket' else row['condition'])
    counts = collections.Counter(r['display_comparison'] for r in rows)
    reasons = collections.Counter(r['censor_reason'] for r in rows if r['censor_reason'])
    rail = next(r for r in rows if r['model_id'] == 'railcab_supplied')
    stats = dict(conditions=len(rows), families=len({r['family'] for r in rows}),
        published_wins=sum(r['published_decision'] == 'WIN' for r in rows),
        fork_wins=sum(r['fork_decision'] == 'WIN' for r in rows),
        size_matches=counts['MATCH'], size_mismatches=counts['SIZE-MISMATCH'],
        unmeasured=counts['N/M'], parser_nm=reasons['fork parser'], instrumentation_nm=reasons['instrumentation'],
        railcab_state_delta=int(rail['published_states']) - int(rail['fork_states']),
        railcab_transition_delta=int(rail['published_transitions']) - int(rail['fork_transitions']),
        collector_byte_check=byte_check,
        size_variable_tool_conditions=sum(row[tool + '_size_varies'] for row in rows for tool in TOOLS))
    slots = [r for c in campaigns.values() for r in read_csv(c.path / 'raw_runs.csv')]
    stats['planned_slots'] = len(slots)
    stats['executed_trials'] = sum(not r['process_status'].startswith('SKIPPED_') for r in slots)
    stats['skipped_slots'] = len(slots) - stats['executed_trials']
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / 'legacy-fidelity-reference.csv', rows)
    (output / 'legacy-fidelity-analysis.json').write_text(json.dumps(stats, indent=2) + '\n')
    macros = {'Conditions': 'conditions', 'Families': 'families', 'PublishedWins': 'published_wins',
        'ForkWins': 'fork_wins', 'SizeMatches': 'size_matches', 'SizeMismatches': 'size_mismatches',
        'Unmeasured': 'unmeasured', 'ParserNM': 'parser_nm', 'InstrumentationNM': 'instrumentation_nm',
        'RailcabStateDelta': 'railcab_state_delta', 'RailcabTransitionDelta': 'railcab_transition_delta'}
    (output / 'legacy-fidelity-stats.tex').write_text('% Generated from validated Xeon raw; do not edit.\n' +
        '\n'.join(r'\newcommand{\LF' + name + '}{' + str(stats[key]) + '}' for name, key in macros.items()) + '\n')
    lines = [r'\begingroup\small\setlength{\tabcolsep}{3pt}',
        r'\begin{longtable}{@{}p{.29\linewidth}p{.20\linewidth}p{.25\linewidth}p{.20\linewidth}@{}}',
        r'\caption{Separate monolithic reference experiment: all 21 conditions. S denotes SUCCESS (controller returned); sizes are first-trial states/transitions. Each completed cell has five consistent SUCCESS decisions; sizes may vary across repetitions (below). N/M labels annotate raw CRASH records, without changing them.}\label{tab:legacy-fidelity}\\',
        r'\toprule Input / condition & Original-source lab build & Fork legacy path & Comparison\\\midrule\endfirsthead',
        r'\toprule Input / condition & Original-source lab build & Fork legacy path & Comparison\\\midrule\endhead',
        r'\bottomrule\endfoot']
    for row in rows:
        cells = [tex(row['label']).replace(' / ', r'\newline ')]
        for tool in TOOLS:
            if tool == 'fork' and row['censor_reason']:
                cells.append(r'N/M\newline (' + tex(row['censor_reason']) + ')')
            else:
                cells.append('S ' + format(int(row[tool + '_states']), ',') + '/' + format(int(row[tool + '_transitions']), ','))
        cells.append(tex(row['display_comparison']).replace('SIZE-MISMATCH', r'SIZE-\newline MISMATCH'))
        lines.append(' & '.join(cells) + r'\\')
    lines += [r'\end{longtable}\endgroup',
        'The two campaigns retain ' + str(stats['planned_slots']) + ' planned slots: ' + str(stats['executed_trials']) +
        ' executed trials and ' + str(stats['skipped_slots']) + ' explicit skips following the five fork exceptions. ' +
        'Those exceptions occur before a legacy GR decision and give no evidence of legacy synthesis capability or failure.']
    for reason in ('fork parser', 'instrumentation'):
        messages = sorted({r['exception_message'] for r in rows if r['censor_reason'] == reason})
        lines.append(r'\paragraph{Saved exception text: ' + tex(reason) + '.}')
        for message in messages:
            # Split only at the original message separator; printed text remains literal.
            exc, message = message.split(': ', 1)
            lines.append(r'\noindent\texttt{' + tex(exc) + r':}\par\noindent\texttt{' + tex(message).replace('  ', r'\ \ ') + r'}\par')
    lines += [r'\begin{center}\small', r'\begin{tabular}{@{}llrrrrr@{}}\toprule',
        r'Tool & Condition & Rep. 1 & Rep. 2 & Rep. 3 & Rep. 4 & Rep. 5\\\midrule']
    for row in rows:
        for tool in TOOLS:
            if row[tool + '_size_varies']:
                values = [row[tool + '_rep' + str(rep) + '_states'] + '/' + row[tool + '_rep' + str(rep) + '_transitions'] for rep in range(1, 6)]
                lines.append(' & '.join(['Lab build' if tool == 'published' else 'Fork', tex(row['label'])] + values) + r'\\')
    lines += [r'\bottomrule\end{tabular}\end{center}',
        'These are all ' + str(stats['size_variable_tool_conditions']) + ' tool/condition cells whose returned controller sizes vary across the five successful trials; other completed cells retain their first-trial sizes. The fifteen size matches and the five-state Railcab difference in the main text compare first trials only. In particular, the Railcab supplied lab-build trial 4 returns the same size as fork trial 1; a persistent tool-specific size difference or controller equivalence is not established.']
    (output / 'legacy-fidelity-reference.tex').write_text('\n'.join(lines) + '\n')
    lines = [r'\begingroup\scriptsize\setlength{\tabcolsep}{3pt}',
        r'\begin{longtable}{@{}p{.25\linewidth}rrrr@{}}',
        r'\caption{Reference measurements only. End-to-end JVM wall seconds and sampled process peak RSS (GiB): median [min,max] only for five complete, consistent runs. No cross-tool ratios are computed.}\label{tab:legacy-fidelity-resources}\\',
        r'\toprule Input / condition & Lab wall (s) & Fork wall (s) & Lab RSS (GiB) & Fork RSS (GiB)\\\midrule\endfirsthead',
        r'\toprule Input / condition & Lab wall (s) & Fork wall (s) & Lab RSS (GiB) & Fork RSS (GiB)\\\midrule\endhead',r'\bottomrule\endfoot']
    for row in rows:
        cells = [tex(row['label']).replace(' / ', r'\newline ')]
        for metric, scale in (('elapsed_monotonic_seconds', 1), ('peak_rss_bytes', 1 / 1024**3)):
            for tool in TOOLS:
                values = [row[tool + '_' + metric + '_' + s] for s in ('median', 'min', 'max')]
                cells.append('%.3g [%.3g, %.3g]' % tuple(float(v)*scale for v in values) if all(values) else 'N/M')
        lines.append(' & '.join(cells) + r'\\')
    lines += [r'\end{longtable}\endgroup',
        r'Internal times have different scopes: the lab-build adapter includes compilation, continued compilation and composition, whereas the fork exposes its solve-control-problem interval. The table instead uses end-to-end JVM wall time as reference information; these tools do not solve identical FG games and their times are not ratioed. The fork exceptions have one actual trial followed by four explicit skips; no median is reported.']
    (output / 'legacy-fidelity-resources.tex').write_text('\n'.join(lines) + '\n')
    print(json.dumps(stats, indent=2))
    return stats


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw-root', type=Path, default=HERE / 'raw/xeon')
    p.add_argument('--config-root', type=Path, default=HERE / 'bundle_delta/configs')
    p.add_argument('--output', type=Path, default=HERE.parents[1] / 'paper/build/generated')
    a = p.parse_args(); generate(a.raw_root, a.config_root, a.output)

if __name__ == '__main__': main()
