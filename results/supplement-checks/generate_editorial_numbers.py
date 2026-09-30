#!/usr/bin/env python3
"""Recompute paper count macros from saved tables; no candidates or synthesis."""
import argparse, csv, json, re
from pathlib import Path


def outputs(generated, evidence):
    cells=list(csv.DictReader((generated/'rq3-cells.csv').open()))
    pairs=list(csv.DictReader((generated/'rq3-comparisons.csv').open()))
    assert len(cells)==135 and len({(r['model_id'],r['target_id'],r['method_id']) for r in cells})==135
    vals={'ApplicationContracts':len({(r['model_id'],r['target_id']) for r in cells}),
          'ApplicationModels':len({r['model_id'] for r in cells})}
    for key,method in [('Lazy','fg_ducs_otf'),('Eager','fg_ducs_otf_eager_controllable'),('UpdateFirst','fg_ducs_otf_update_first'),('DirectFull','direct_full')]:
        vals[key+'Decisions']=sum(r['effective_stage1_status'] in ('SUCCESS','UNREALIZABLE') and r['display_complete_five']=='True' for r in cells if r['method_id']==method)
    uf=[r for r in pairs if r['comparator']=='fg_ducs_otf_update_first' and r['both_complete_five']=='True']
    vals['UpdateFirstPairs']=len(uf)
    vals['UpdateFirstFaster']=sum(float(r['comparator_over_fg_median_ratio'])<1 for r in uf)
    def tex(values): return ''.join('\\newcommand{\\'+k+'}{'+str(v)+'}\n' for k,v in values.items())
    result={'editorial-numbers.tex':'% Generated from saved rq3-cells.csv and rq3-comparisons.csv.\n'+tex(vals)}
    legacy=[r for r in cells if r['method_id']=='legacy_ducs']
    assert len(legacy)==27, 'Legacy denominator must include all 27 contracts'
    wins=[r for r in legacy if r['effective_stage1_status']=='SUCCESS']
    for row in wins:
        statuses=[item.split(':',1) for item in row['statuses'].split(';')]
        assert (row['stage1_status']=='SUCCESS' and row['display_complete_five']=='True'
                and row['timing_summary_eligible']=='True' and row['completed_valid_repetitions']=='5'
                and row['invalid']=='False' and row['inconsistent']=='False'
                and sorted(statuses)==[[str(i),'SUCCESS'] for i in range(1,6)]), 'Legacy WIN lacks five valid consistent completions'
    oom=[r for r in legacy if r['effective_stage1_status']=='OOM' and r['stage1_status']=='OOM']
    capture=[r for r in legacy if r['effective_stage1_status']=='CRASH' and r['stage1_status']=='CRASH'
             and r['display_censor_reason']=='author_capture_cap']
    assert len(wins)+len(oom)+len(capture)==len(legacy), 'Unclassified Legacy outcome; do not relabel generic CRASH as N/M'
    values={'LegacyNativeWins':len(wins),'LegacyNativeOOM':len(oom),'LegacyCaptureNM':len(capture)}
    result['legacy-reference-numbers.tex']=('% Generated from saved rq3-cells.csv; native Legacy reference, not a same-game comparator.\n'
        '% WIN requires five valid identical decisions; N/M counts only CRASH annotated author_capture_cap from saved exception evidence.\n'+tex(values))
    travel=json.loads((generated/'xeon-statistics.json').read_text())['travel']
    methods=travel['methods']
    otf=[methods[k]['complete_five'] for k in ('fg_ducs_otf','fg_ducs_otf_eager_controllable','fg_ducs_otf_update_first')]
    assert len(set(otf))==1 and not travel['decision_disagreements']
    values={'TravelSettings':travel['instances'],'TravelOTFDecisions':otf[0],'TravelFullDecisions':methods['direct_full']['complete_five']}
    result['travel-editorial-numbers.tex']='% Generated from saved xeon-statistics.json; no new measurements.\n'+tex(values)
    rows=list(csv.DictReader((evidence/'r1-entry-invariant-verification.csv').open()))
    assert len({(r['model'],r['target'],r['requirement']) for r in rows})==len(rows)
    values={'RSEGuardedInvariantOccurrences':len(rows),'RSEGuardedInvariantPassed':sum(r['static_entry_invariant_condition']=='PASS' for r in rows)}
    result['rs-editorial-numbers.tex']='% From saved r1-entry-invariant-verification.csv, without rerunning synthesis.\n'+tex(values)
    return result


def definitions(text):
    entries=re.findall(r'\\newcommand\{\\(\w+)\}\{([^{}]+)\}',text)
    assert len(dict(entries))==len(entries), 'Duplicate generated macro'
    return dict(entries)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--generated',type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=Path(__file__).resolve().parent)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    for name,text in outputs(args.generated,args.evidence).items():
        saved=args.generated/name
        if saved.is_file():
            assert definitions(text)==definitions(saved.read_text()), ('paper macro mismatch',name)
        (args.output/name).write_text(text)
        if saved.is_file():
            print('PASS saved macro definitions:',name,definitions(text))
        else:
            print('GENERATED new macro file (no saved paper macro to compare):',name,definitions(text))


if __name__=='__main__': main()
