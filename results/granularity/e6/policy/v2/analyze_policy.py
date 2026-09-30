#!/usr/bin/env python3
"""Read-only certificate audit and policy-specific handoff tables."""
import csv
import hashlib
import json
from pathlib import Path
P = Path(__file__).resolve().parent


def read(job, name='result.json'):
    return json.loads((P/'raw/series'/job/name).read_text())


def main():
    rows = list(csv.DictReader((P/'summary.csv').open()))
    index = {r['job_id']: r for r in rows}
    issues = []
    for merge in ('none', 'transfers'):
        job = 'policy_fine_' + merge + '_lazy'
        proof = read(job, 'certificate.json')
        for state in proof['states']:
            active = state['testers']
            expected = ''.join('1' if r in active else '0' for r in ('old_audit','new_audit','old_role','new_role'))
            if active['coverage_and_exclusion'] != expected:
                issues.append('Active requirement/interval state mismatch: ' + job)
    for job in ('policy_fine_boundaries_lazy','policy_generated_coarse_none_lazy'):
        result = read(job)
        assert result['decision'] == 'LOSS'
        for root in result['loss_summary']['initial_examples']:
            buckets = {b['action']:b for b in root['enabled_action_buckets']}
            for action in ('ablation.merge.starts','ablation.merge.stops'):
                bucket = buckets[action]
                if bucket['unsafe_outcomes'] != bucket['outcomes'] or not bucket['outcomes']:
                    issues.append('Merged boundary does not immediately violate interval: ' + action)
                for successor in bucket['unsafe_outcome_examples']:
                    if successor['testers']['coverage_and_exclusion'] != 'ERROR':
                        issues.append('Wrong unsafe mechanism')
    generated = read('policy_generated_coarse_none_lazy')
    automated = read('policy_fine_boundaries_lazy')
    equality = dict(comparison='generated global boundaries vs E1 boundaries',
                    generated_decision=generated['decision'], automatic_decision=automated['decision'],
                    generated_states=generated['states_discovered'], automatic_states=automated['states_discovered'],
                    decision_equal=generated['decision']==automated['decision'],
                    states_equal=generated['states_discovered']==automated['states_discovered'],
                    reachable_post_equality=generated['game_equivalence']['status'])
    assert equality['decision_equal'] and equality['states_equal'] and equality['reachable_post_equality']=='PASS'
    with (P/'tables/merge_equality.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=equality);w.writeheader();w.writerow(equality)
    classes=[]
    for mode in ('transfers','boundaries','both'):
        r=index['policy_fine_'+mode+'_lazy'];fine=index['policy_fine_none_lazy']
        classes.append(dict(family='Policy',merge=mode,fine_decision=fine['decision'],merged_decision=r['decision'],
                            classification='witness' if r['decision']=='LOSS' else 'both_WIN',
                            fine_states=fine['states_discovered'],merged_states=r['states_discovered']))
    with (P/'tables/comparison.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=classes[0]);w.writeheader();w.writerows(classes)
    report=dict(status='FAIL' if issues else 'PASS',issues=issues,merge_equality=equality,
                mechanism='Merged starts introduce exclusive-role overlap; merged stops introduce an audit gap. Both enabled buckets lead directly to interval ERROR at every initial root.',
                interpretation='One boundary witness, not two independent examples for boundaries and both; transfers is a null control.',
                rank_note='Lazy rank 6 and Direct-Full rank 5 are bounds of different returned certificates, not inconsistent optimal ranks.')
    (P/'validation/certificate_mechanism_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    (P/'tables/policy_comparison.tex').write_text('''% E6 constructed Policy(2); certificate ranks are not claimed optimal.
\\begin{tabular}{lrrrr}
\\toprule
Contract & Decision & States & Rank & Losing certificate \\\\
\\midrule
Fine (Lazy) & WIN & 24 & 6 & -- \\\\
Fine (Direct-Full) & WIN & 129 & 5 & -- \\\\
Transfer merge & WIN & 24 & 6 & -- \\\\
Boundary merge & LOSS & 16 & -- & 16 \\\\
Both merges & LOSS & 16 & -- & 16 \\\\
Generated global boundaries & LOSS & 16 & -- & 16 \\\\
\\bottomrule
\\end{tabular}
''')
    print(json.dumps(report))
    return bool(issues)


if __name__=='__main__':raise SystemExit(main())
