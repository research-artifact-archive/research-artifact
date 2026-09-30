#!/usr/bin/env python3
"""Derive complete E5 tables from frozen schedule and preserved raw only."""
import sys
sys.dont_write_bytecode=True
from collections import Counter
from e5_common import *


def category(a,b):
    return {('WIN','LOSS'):'witness',('LOSS','LOSS'):'bothLOSS',('WIN','WIN'):'null'}.get((a,b),'other')


def other_detail(a,b):
    if (a,b)==('LOSS','WIN'):return 'reversal_LOSS_WIN'
    if 'INVALID' in (a,b):return 'invalid'
    if any(x in ('TO','NOT_RUN','NOT_RUN_DEADLINE','RUNNING','INCOMPLETE') for x in (a,b)):return 'incomplete'
    if any(x not in ('WIN','LOSS') for x in (a,b)):return 'error'
    return ''


def cell(row,metric='states_discovered'):
    d=row['decision']
    if d in ('WIN','LOSS'):return d+' / '+str(row.get(metric,''))
    return tex({'NOT_RUN_DEADLINE':'NR','NOT_RUN':'Pending','RUNNING':'Running'}.get(d,d))


def collect():
    config=read_json(CONFIG);plan=list(jobs(config));baseline=baseline_rows();rows=[];components=[]
    for index,job in enumerate(plan,1):
        row=dict(schedule_index=index,model_id=job['model_id'],model_label=LABELS[job['model_id']],target_id=job['target_id'],method_id=job['method_id'],merge=job['merge'],solver=job['solver'],**trial(job),**baseline[(job['model_id'],job['target_id'])])
        rows.append(row)
        if row['components_json']:
            try:
                for c in json.loads(row['components_json']):
                    components.append(dict(schedule_index=index,model_id=job['model_id'],target_id=job['target_id'],method_id=job['method_id'],decision=row['decision'],**c,meta_path=row['meta_path']))
            except (ValueError,TypeError):pass
    by={(r['model_id'],r['target_id'],r['method_id']):r for r in rows};pairs=[]
    for m in config['models']:
        for t in config['targets']:
            key=(m['id'],t['id']);a=by[key+('lazy_none_initial',)];b=by[key+('lazy_transfers_initial',)];d=by[key+('df_none_initial',)]
            cat=category(a['decision'],b['decision']);reason=f"Initial-domain Lazy none={a['decision']}; transfers={b['decision']}."
            if cat=='witness':reason+=' This pair witnesses a decision change under transfer merging.'
            elif cat=='bothLOSS':reason+=' Both transformed contracts have checked losing certificates.'
            elif cat=='null':reason+=' Both transformed contracts have checked winning policies.'
            else:reason+=' Kept outside the three requested groups; no missing or adverse result is discarded.'
            comparable=a['decision'] in ('WIN','LOSS') and d['decision'] in ('WIN','LOSS')
            pairs.append(dict(model_id=m['id'],model_label=LABELS[m['id']],target_id=t['id'],category=cat,other_detail=other_detail(a['decision'],b['decision']),none_decision=a['decision'],transfers_decision=b['decision'],df_decision=d['decision'],df_lazy_decision_check=('PASS' if a['decision']==d['decision'] else 'FAIL') if comparable else 'NOT_COMPARABLE',none_states=a.get('states_discovered',''),transfers_states=b.get('states_discovered',''),df_states=d.get('states_discovered',''),none_queries=a.get('successor_queries',''),transfers_queries=b.get('successor_queries',''),df_queries=d.get('successor_queries',''),none_rank=a.get('worst_completion_rank',''),transfers_rank=b.get('worst_completion_rank',''),df_rank=d.get('worst_completion_rank',''),none_losing_region=a.get('losing_region_states',''),transfers_losing_region=b.get('losing_region_states',''),df_losing_region=d.get('losing_region_states',''),reason=reason,**baseline[key]))
    models=[]
    for model in config['models']:
        ps=[p for p in pairs if p['model_id']==model['id']]
        models.append(dict(model_id=model['id'],model_label=LABELS[model['id']],base_category=ps[0]['category'],r1_category=ps[1]['category'],witness_pairs=sum(p['category']=='witness' for p in ps),bothLOSS_pairs=sum(p['category']=='bothLOSS' for p in ps),null_pairs=sum(p['category']=='null' for p in ps),other_pairs=sum(p['category']=='other' for p in ps)))
    tables=E5/'tables'
    for name,data in [('results',rows),('pairs',pairs),('models',models),('components',components)]:
        columns=list(dict.fromkeys(k for row in data for k in row)) if data else ['schedule_index','model_id','target_id','method_id','component_id']
        csv_write(tables/(name+'.csv'),data,columns)
    terminal=all(r['decision'] not in ('NOT_RUN','RUNNING') for r in rows)
    counts=Counter(p['category'] for p in pairs);dcounts=Counter(r['decision'] for r in rows)
    errs=[{'schedule_index':r['schedule_index'],'errors':r['validation_errors']} for r in rows if r['validation_errors']]
    berrors=[{'model_id':p['model_id'],'target_id':p['target_id'],'errors':p['original_validation_errors']} for p in pairs if p['original_validation_errors']]
    summary=dict(provisional=not terminal,planned_cells=54,planned_pairs=18,planned_models=9,decision_counts=dict(dcounts),pair_categories=dict(counts),other_subcategories=dict(Counter(p['other_detail'] for p in pairs if p['category']=='other')),category_names={cat:[p['model_label']+'/'+('Base' if p['target_id']=='base' else 'R1') for p in pairs if p['category']==cat] for cat in ('witness','bothLOSS','null','other')},validation_errors=errs,baseline_validation_errors=berrors,df_lazy_comparable=sum(p['df_lazy_decision_check']!='NOT_COMPARABLE' for p in pairs),df_lazy_mismatches=[p['model_id']+'/'+p['target_id'] for p in pairs if p['df_lazy_decision_check']=='FAIL'],unit='18 model/requirement pairs; model-level incidence is separately reported, not substituted for pair counts')
    summary['none_initial_vs_original']={
        'comparable_pairs':sum(p['none_decision'] in ('WIN','LOSS') and p['original_decision'] in ('WIN','LOSS') for p in pairs),
        'changed_pairs':[p['model_label']+'/'+('Base' if p['target_id']=='base' else 'R1') for p in pairs if p['none_decision'] in ('WIN','LOSS') and p['original_decision'] in ('WIN','LOSS') and p['none_decision']!=p['original_decision']],
        'scope':'New initial-domain restriction versus existing unrestricted original contract; distinct from separate-versus-merged E5 classification.'}
    from evidence_tables import derive
    summary.update(derive(rows,components))
    write_json(tables/'summary.json',summary)
    header='% E5 constructed initial-state transfer-domain variants; all 18 input/requirement pairs.\n'
    lines=[header,r'\begin{tabular}{llrrrrl}',r'\toprule',r'Input & Req. & Original & None & Transfers & DF none & Group \\',r'\midrule']
    for p in pairs:
        key=(p['model_id'],p['target_id']);a=by[key+('lazy_none_initial',)];b=by[key+('lazy_transfers_initial',)];d=by[key+('df_none_initial',)]
        lines.append(' & '.join([tex(p['model_label']),'Base' if p['target_id']=='base' else 'R1',p['original_decision']+' / '+p['original_states'],cell(a),cell(b),cell(d),(p['category'] if p['category']!='other' else {'reversal_LOSS_WIN':'Reverse','incomplete':'Incomplete','invalid':'Invalid','error':'Error'}[p['other_detail']])])+r' \\')
    lines.extend([r'\bottomrule',r'\end{tabular}',r'{\par\smallskip\footnotesize Entries show decision / discovered states. Original uses the existing unmodified-contract Lazy first trial; the three new columns use initial-state restricted transfer relations. Each started cell uses one Mac trial with a 1,200\,s limit and 32\,GiB heap. TO and NR denote timeout and not started before the predeclared cutoff. No retries or substitutions.}'])
    (tables/'table_e5_states.tex').write_text('\n'.join(lines)+'\n')
    lines=[header,r'\begin{tabular}{llrrrrrr}',r'\toprule',r'Input & Req. & N queries & T queries & DF queries & N rank/$|L|$ & T rank/$|L|$ & DF rank/$|L|$ \\',r'\midrule']
    for p in pairs:
        key=(p['model_id'],p['target_id']);rs=[by[key+(method,)] for method in ('lazy_none_initial','lazy_transfers_initial','df_none_initial')]
        val=lambda r,k:r.get(k,'') if r['decision'] in ('WIN','LOSS') else cell(r)
        lines.append(' & '.join([tex(p['model_label']),'Base' if p['target_id']=='base' else 'R1']+[val(r,'successor_queries') for r in rs]+[val(r,'worst_completion_rank' if r['decision']=='WIN' else 'losing_region_states') for r in rs])+r' \\')
    lines.extend([r'\bottomrule',r'\end{tabular}',r'{\par\smallskip\footnotesize N = Lazy none, T = Lazy transfers, DF = Direct-Full none, all with initial-state restricted transfer relations. WIN reports the returned policy completion-rank bound; LOSS reports the returned losing-certificate size over discovered states, not the maximum losing region of the complete game. Mac solver time is available in CSV as a reference only.}'])
    (tables/'table_e5_metrics.tex').write_text('\n'.join(lines)+'\n')
    names=summary['category_names'];listnames=lambda cat:', '.join(names[cat]) or 'none'
    prefix='Provisional: ' if not terminal else ''
    df_clause=(f"Direct-Full and Lazy agree on {summary['df_lazy_comparable']-len(summary['df_lazy_mismatches'])} of {summary['df_lazy_comparable']} completed comparable none-initial pairs" if summary['df_lazy_comparable'] else 'no none-initial pair has yet completed with both solvers' if not terminal else 'no none-initial pair completed with both solvers')
    text=(prefix+'We uniformly restricted each transfer relation to the old component\'s physical initial state before comparing separate and merged transfer events under the same Post and goal semantics. '
          +f"Across 18 model/requirement pairs, the checked results contain {counts['witness']} separate-WIN/merged-LOSS witnesses ({listnames('witness')}), {counts['bothLOSS']} both-LOSS pairs ({listnames('bothLOSS')}), and {counts['null']} both-WIN null results ({listnames('null')}); {counts['other']} pairs remain outside these groups ({listnames('other')}). "
          +f"The 54 scheduled single trials currently contain "+', '.join(f'{v} {k}' for k,v in sorted(dcounts.items()))+'; '+df_clause+'. '
          +'These are constructed initial-state variants, not a claim about quiescence or application prevalence, and contract merging is not itself a DUCS encoding.\n')
    if terminal:text=text.replace('currently contain','contain')
    (tables/'e5_sentences.txt').write_text(text)
    return summary

if __name__=='__main__':print(json.dumps(collect(),indent=2))
