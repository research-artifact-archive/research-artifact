"""CSV-only derivation of local LOSS evidence and source/compiled domain checks."""
from e5_common import *

def derive(rows,components):
    loss=[]
    for row in rows:
        if row['decision']!='LOSS':continue
        summary=json.loads(row['losing_certificate_summary']);examples=summary.get('initial_examples',[])
        uc=[];allc=[];disabled=set();obstructions=[]
        for i,example in enumerate(examples,1):
            actions=example.get('enabled_action_buckets',[])
            u=[a['action'] for a in actions if not a['controllable'] and a['outcomes_in_certificate_region']>0]
            c=[a for a in actions if a['controllable']]
            if u:uc.append({'sample':i,'actions':u})
            if c and all(a['outcomes_in_certificate_region']>0 for a in c):allc.append(i)
            disabled.update(d['component_id'] for d in example.get('pending_transfer_disabled_by_local_domain',[]))
            obstructions.append(example.get('local_obstruction',''))
        reason=(f"The checked certificate contains {summary['region_states']} discovered states ({summary['unsafe_region_states']} unsafe), including {summary['losing_initial_states']}/{summary['initial_states']} initial states; among its {len(examples)} reported root examples (at most {summary['initial_examples_limit']}), {len(uc)} have an enabled uncontrollable action with an outcome in the certificate and {len(allc)} have a nonempty set of enabled controllable actions all with such an outcome, while locally disabled pending-transfer components observed in these samples are {', '.join(sorted(disabled)) or 'none'} (local closure evidence, not a complete causal explanation).")
        loss.append(dict(schedule_index=row['schedule_index'],model_id=row['model_id'],target_id=row['target_id'],method_id=row['method_id'],region_states=summary['region_states'],unsafe_region_states=summary['unsafe_region_states'],initial_states=summary['initial_states'],losing_initial_states=summary['losing_initial_states'],sample_count=len(examples),sample_limit=summary['initial_examples_limit'],uc_samples_with_losing_outcome=json.dumps(uc),all_enabled_c_have_losing_outcome_samples=json.dumps(allc),sample_local_obstructions=json.dumps(obstructions),disabled_pending_transfer_components=';'.join(sorted(disabled)),reason=reason,certificate_json=row['losing_certificate_summary'],meta_path=row['meta_path']))
    csv_write(E5/'tables/loss_reasons.csv',loss,list(loss[0]) if loss else ['schedule_index','model_id','target_id','method_id','reason'])
    source=list(csv.DictReader((E5/'tables/source_domains.csv').open()));index={(r['model_id'],int(r['component_index'])):r for r in source};checks=[]
    mapping={'old_physical_states':'source_old_physical_states','original_physical_domain_states':'source_original_physical_domain_states','original_physical_pairs':'source_original_physical_pairs','retained_physical_domain_states':'source_retained_physical_domain_states','retained_physical_pairs':'source_retained_physical_pairs'}
    for component in components:
        # The compiled adapter explicitly labels components as index:old-process-name.
        cindex=int(component['component_id'].split(':',1)[0]);s=index[(component['model_id'],cindex)]
        mismatches=[field for field,sfield in mapping.items() if int(component[field])!=int(s[sfield])]
        checks.append(dict(schedule_index=component['schedule_index'],model_id=component['model_id'],target_id=component['target_id'],method_id=component['method_id'],component_id=component['component_id'],source_relation=s['relation'],check='FAIL' if mismatches else 'PASS',mismatched_fields=';'.join(mismatches),source_initial_label=s['old_initial_label'],compiled_initial_physical_state=component['old_initial_physical_state'],comparison_scope=component['comparison_scope'],**{field:component[field] for field in mapping}))
    csv_write(E5/'tables/domain_checks.csv',checks,list(checks[0]) if checks else ['schedule_index','model_id','target_id','method_id','component_id','check'])
    census_shape_errors=[]
    for row in rows:
        if not row['components_json']:continue
        reported=json.loads(row['components_json']);expected=[r for r in source if r['model_id']==row['model_id']]
        ids=[int(c['component_id'].split(':',1)[0]) for c in reported]
        if sorted(ids)!=list(range(len(expected))):census_shape_errors.append(row['meta_path'])
    summary=dict(component_comparisons=len(checks),passed=sum(r['check']=='PASS' for r in checks),failed=sum(r['check']=='FAIL' for r in checks)+len(census_shape_errors),census_shape_errors=census_shape_errors,models_observed=sorted({r['model_id'] for r in checks}),scope='Independent source inventory/parsed relation counts versus actual compiled raw-projection counts; observer-augmented counts are not predicted by source counts.')
    write_json(E5/'tables/domain_checks.json',summary)
    domain_lines=[r'\begin{tabular}{llrl}',r'\toprule',r'Input & Per-component retained/original & Sum & Compiled check \\',r'\midrule']
    for model in read_json(CONFIG)['models']:
        src=[r for r in source if r['model_id']==model['id']]
        observed=[r for r in checks if r['model_id']==model['id']]
        checked_trials={r['schedule_index'] for r in observed if r['check']=='PASS'}
        failures=sum(r['check']=='FAIL' for r in observed)
        ratio=', '.join(r['source_retained_physical_pairs']+'/'+r['source_original_physical_pairs'] for r in src)
        total=str(sum(int(r['source_retained_physical_pairs']) for r in src))+'/'+str(sum(int(r['source_original_physical_pairs']) for r in src))
        check=(str(failures)+' mismatches') if failures else (str(len(checked_trials))+'/6 trials matched' if observed else 'Source audit only')
        domain_lines.append(' & '.join([LABELS[model['id']],ratio,total,check])+r' \\')
    domain_lines.extend([r'\bottomrule',r'\end{tabular}',r'{\par\smallskip\footnotesize Pair counts are from the independent source audit of the nine byte-identical copied inputs; retained sources are the old physical initial states. Components follow their source order; Sum adds their pair counts. The last column reports completed trial contexts whose compiled raw-projection counts matched the source audit (six scheduled contexts per input). Unmeasured contexts are not filled with source counts. Observer-augmented pair counts remain separate in CSV; these counts do not imply safety, uncontrollable progress, quiescence, or a winning contract.}'])
    (E5/'tables/table_e5_domains.tex').write_text('\n'.join(domain_lines)+'\n')
    return {'loss_reason_rows':len(loss),'domain_comparisons':summary}
