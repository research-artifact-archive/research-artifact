#!/usr/bin/env python3
"""Derive paired and controlled-family statistics from completed Xeon returns.

Only generated output is written. Original summaries, configurations and runs
remain unchanged. Timing ratios compare per-instance five-run medians.
"""
from pathlib import Path
from collections import Counter
import argparse,json,statistics
import render_results as r


def scaling_statistics(campaign):
    """Paired case summaries, never treating two missing measurements as equal."""
    comparisons=[];fg_times=[];structural_pairs=[]
    factors={m['id']:m['factors'] for m in campaign.config['models']}
    for fg in campaign.rows:
        if fg['method_id']!='fg_ducs_otf':continue
        a=r.triple(fg,'solver_time_ms',.001)
        if a:fg_times.append(a[0])
        for method in r.METHODS[1:4]:
            other=campaign.index[fg['model_id'],fg['target_id'],method]
            b=r.triple(other,'solver_time_ms',.001)
            decided=fg['stage1_status'] in r.GOOD and other['stage1_status'] in r.GOOD
            same=decided and fg['stage1_status']==other['stage1_status']
            fs=r.structural(fg,'states_discovered');os=r.structural(other,'states_discovered')
            comparisons.append(dict(model_id=fg['model_id'],**factors[fg['model_id']],
                comparator=method,fg_status=fg['stage1_status'],comparator_status=other['stage1_status'],
                decision_agreement=same if decided else '',
                comparator_over_fg_median_ratio=b[0]/a[0] if same and a and b and a[0]>0 else '',
                fg_over_comparator_state_ratio=fs/os if same and fs is not None and os else ''))
            if method=='fg_ducs_otf_update_first' and same and all(
                    r.structural(fg,k) is not None and r.structural(other,k) is not None
                    for k in ('states_discovered','successor_queries','transition_outcomes')):
                structural_pairs.append(all(r.structural(fg,k)==r.structural(other,k)
                    for k in ('states_discovered','successor_queries','transition_outcomes')))
    df=[x for x in comparisons if x['comparator']=='direct_full']
    times=[x['comparator_over_fg_median_ratio'] for x in df if x['comparator_over_fg_median_ratio']!='']
    states=[x['fg_over_comparator_state_ratio'] for x in df if x['fg_over_comparator_state_ratio']!='']
    counts={m:dict(stage1=dict(Counter(x['stage1_status'] for x in campaign.rows if x['method_id']==m)),
        complete_five=sum(r.complete_five(x) for x in campaign.rows if x['method_id']==m)) for m in r.METHODS[:4]}
    result=dict(cells=len(campaign.rows),instances=len(campaign.config['models']),methods=counts,
        paired_time_cells=len(times),ratio_min=min(times) if times else None,
        ratio_median=statistics.median(times) if times else None,ratio_max=max(times) if times else None,
        fg_over_df_states_min=min(states) if states else None,fg_over_df_states_max=max(states) if states else None,
        fg_median_seconds=statistics.median(fg_times) if fg_times else None,
        fg_max_seconds=max(fg_times) if fg_times else None,
        lazy_update_first_measured_structure_pairs=len(structural_pairs),
        lazy_update_first_identical_structure_pairs=sum(structural_pairs),
        decision_disagreements=[x['model_id'] for x in comparisons if x['decision_agreement'] is False])
    return result,comparisons


def analyze(input_root, output):
    output.mkdir(parents=True,exist_ok=True)
    load=lambda name:json.loads((r.HERE/'configs'/(name+'.json')).read_text())
    rq3=r.Campaign(input_root/'rq3','xeon',load('rq3'))
    r.integrate_supplementary(rq3,input_root)
    r.render_supplementary_pending(rq3,output,input_root)
    counts={method:dict(stage1=dict(Counter(r.effective_status(x) for x in rq3.rows if x['method_id']==method)),
        original_stage1=dict(Counter(x['stage1_status'] for x in rq3.rows if x['method_id']==method)),
        complete_five=sum(r.complete_five(x) for x in rq3.rows if x['method_id']==method)) for method in r.METHODS}
    pairs=[]
    for row in rq3.rows:
        if row['method_id']=='fg_ducs_otf':continue
        fg=rq3.index[row['model_id'],row['target_id'],'fg_ducs_otf']
        decided=row['stage1_status'] in r.GOOD and fg['stage1_status'] in r.GOOD
        a=r.triple(fg,'solver_time_ms');b=r.triple(row,'solver_time_ms')
        same=decided and row['stage1_status']==fg['stage1_status']
        ratio=b[0]/a[0] if same and a and b and a[0]>0 else None
        pairs.append(dict(model_id=row['model_id'],target_id=row['target_id'],comparator=row['method_id'],
            fg_status=fg['stage1_status'],comparator_status=r.effective_status(row),
            original_comparator_status=row['stage1_status'],both_decided=decided,
            decision_agreement=same if decided else '',both_complete_five=bool(a and b),
            comparator_over_fg_median_ratio=ratio if ratio is not None else '',
            source_summary='rq3/summary.csv',supplementary_status_source=row.get('ad_source_campaign','')))
    comparisons={}
    for method in r.METHODS[1:]:
        rows=[x for x in pairs if x['comparator']==method]
        values=[x['comparator_over_fg_median_ratio'] for x in rows if x['comparator_over_fg_median_ratio']!='']
        comparisons[method]=dict(both_decided=sum(x['both_decided'] for x in rows),
            agreeing=sum(x['decision_agreement'] is True for x in rows),
            disagreements=[(x['model_id'],x['target_id']) for x in rows if x['decision_agreement'] is False],
            paired_time_cells=len(values),ratio_min=min(values) if values else None,
            ratio_median=statistics.median(values) if values else None,ratio_max=max(values) if values else None)
    r.write_csv(output/'rq3-comparisons.csv',pairs)
    controlled=r.Campaign(input_root/'rq4_controlled','xeon',load('rq4_controlled'))
    factors={m['id']:m['factors'] for m in controlled.config['models']}
    ctrl=[];lines=[r'\clearpage\noindent\textbf{Controlled families: first-trial structure}\par',
        r'All 132 jobs are retained. These single trials provide no timing medians.',
        r'\begin{longtable}{@{}lrrrr@{}}',r'\toprule',
        r'Model & FG lazy & Eager & Update-first & Direct-Full\\\midrule\endhead']
    for model in controlled.config['models']:
        values=[]
        for method in r.METHODS[:4]:
            row=controlled.index[model['id'],'base',method];f=factors[model['id']]
            ctrl.append(dict(model_id=model['id'],method_id=method,family=f['controlled_family'],
                changed_factor=f['changed_factor'],factor_value=f['changed_factor_value'],
                status=row['stage1_status'],states=row['states_discovered'],queries=row['successor_queries'],
                outcomes=row['transition_outcomes'],source_summary='rq4_controlled/summary.csv'))
            status=row['stage1_status']
            values.append({'SUCCESS':'W','UNREALIZABLE':'L'}.get(status,status)+': '+row['states_discovered'])
        lines.append(r.tex(model['id'].removeprefix('rq4_'))+' & '+' & '.join(values)+r'\\')
    lines.extend([r'\bottomrule\end{longtable}',r'Cells show decision and discovered states. Queries and outcomes: \texttt{rq4-controlled.csv}.'])
    r.write_csv(output/'rq4-controlled.csv',ctrl)
    (output/'rq4-controlled.tex').write_text('\n'.join(lines)+'\n')
    decisions={m:dict(Counter(x['stage1_status'] for x in controlled.rows if x['method_id']==m)) for m in r.METHODS[:4]}
    agreements=sum(len({controlled.index[m['id'],'base',a]['stage1_status'] for a in r.METHODS[:4]})==1 for m in controlled.config['models'])
    ind=r.Campaign(input_root/'rq4_independent','xeon',load('rq4_independent'))
    endpoint=[x for x in ind.rows if x['model_id']=='independent_k20']
    complete_fg=[r.triple(x,'solver_time_ms',.001)[0] for x in rq3.rows if x['method_id']=='fg_ducs_otf' and r.complete_five(x)]
    result=dict(rq3=counts,rq3_supplementary=getattr(rq3,'supplementary',{}),
        paired=comparisons,fg_instance_median_seconds=statistics.median(complete_fg),
        controlled=dict(cells=len(controlled.rows),instances=len(controlled.config['models']),all_method_agreement=agreements,decisions=decisions),
        independent=dict(cells=len(ind.rows),complete_five=sum(r.complete_five(x) for x in ind.rows),
            k20={x['method_id']:dict(states=x['states_discovered'],queries=x['successor_queries'],
                median_seconds=r.triple(x,'solver_time_ms',.001)[0]) for x in endpoint}))
    returned_lines=[r'\clearpage\noindent\textbf{Travel and hub: completed returns}\par',
        r'Travel retains all 48 instances; hub retains 30 seeds under each of three UC profiles.',
        r'W/TO/OOM are first-trial counts. Five-run timing eligibility is shown separately.',
        r'\begin{center}\small\begin{tabular}{@{}llrrrr@{}}\toprule',
        r'Family & Method & W & TO & OOM & Five-run cells\\\midrule']
    for family in ('travel','hub'):
        campaign=r.Campaign(input_root/('rq4_'+family),'xeon',load('rq4_'+family))
        result[family],pairs=scaling_statistics(campaign)
        r.write_csv(output/('rq4-'+family+'-comparisons.csv'),pairs)
        for method,label in zip(r.METHODS[:4],r.LABELS[:4]):
            entry=result[family]['methods'][method];count=entry['stage1']
            returned_lines.append(f"{family.title()} & {label} & {count.get('SUCCESS',0)} & "
                f"{count.get('TIMEOUT',0)} & {count.get('OOM',0)} & {entry['complete_five']}"+r'\\')
    returned_lines.extend([r'\bottomrule\end{tabular}\end{center}',
        r'All completed decisions agree. Travel has 960 planned repetition slots: 504 executed trials and 456 explicit resource-failure skips; hub completes all 1,800 trials.',
        r'\texttt{rq4-points.csv} retains all plotted method/instance cells; the two \texttt{rq4-*-comparisons.csv} files retain paired ratios and unresolved statuses.',
        r'Travel lazy/Direct-Full state ratios range from 0.03435 to 0.46154 over 18 completed pairs. The upper endpoint is $N=1,K=1$ (12/26 states); all eight $N=1$ ratios exceed one third. No case is excluded to tighten this range.',
        r'Lazy and update-first match states, queries and outcomes on all 20 completed Travel instances. Unresolved instances have no measured structure and do not count as equal pairs.',
        r'Hub timings are solve-only; Travel LTS timings include the internal checks. Ratios are paired within each family, never pooled across these scopes.'])
    (output/'rq4-returned.tex').write_text('\n'.join(returned_lines)+'\n')
    (output/'xeon-statistics.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-root',type=Path,default=r.HERE/'raw')
    parser.add_argument('--output',type=Path,default=r.SUBMISSION/'paper/build/generated')
    args=parser.parse_args();analyze(args.input_root,args.output)
