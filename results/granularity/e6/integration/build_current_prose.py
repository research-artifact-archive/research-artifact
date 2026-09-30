#!/usr/bin/env python3
"""Derive compact handoff prose from the current checked index, without a solver.

This produces a reviewable draft; the parent ledger is updated only after the
authorized extension is terminal. It does not claim that the deadline is past.
"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import csv,json,hashlib

E6=Path(__file__).resolve().parents[1]
OUT=E6/'integration'
status=json.loads((OUT/'status.json').read_text())
records=list(csv.DictReader((E6/'results_index.csv').open()))
c=status['main_pair_counts']; pc=next(r for r in records if r['family']=='PC2-Rolling')
count=sum(c.values())
assert not c['unexpected'],'An unexpected decision pair requires an explicit new explanation'
incomplete=(f", with {c['incomplete']} unresolved PC2 comparison" if c['incomplete'] else '')
rq2=[
 f"Across {count} main constructed comparisons, the fine and merged contracts yield {c['witness']} WIN/LOSS, {c['both_loss']} LOSS/LOSS and {c['both_win']} WIN/WIN pairs{incomplete}; these are counts of constructed comparisons, not prevalence estimates.",
 "All 70 Rolling cells satisfy WIN iff k <= n-m, while all 15 Canary pairs separate fine replacement with recovery from a product transfer with adversarial outcomes.",
 "Policy(2) separates requirement-specific from global boundaries and DB-Rolling separates secondary-only local from joint replacement, whereas singleton-boundary Rolling+Audit and backpressure Threads retain their null results.",
 "These constructed mechanisms supplement the unchanged E1 result of no decision changes in 54 comparisons over nine inherited application inputs under Base and R1, and the merge transformations are not claimed to encode DUCS."
]
intro=[
 "Kubernetes Deployment rollouts and MongoDB's Community-to-Enterprise replica-set migration update replicas in stages and wait for readiness or rejoining.",
 "Such procedures motivate contracts that distinguish local replacement, possible transfer outcomes, and requirement activation periods, rather than presupposing one simultaneous update."
]
threat="The operationally motivated variants and constructed witnesses establish existence, not prevalence, and their finite startup, reporting, recovery and election assumptions limit transfer to real deployments."
pc_lines=[
 f"Measured: fine Lazy {pc['fine_decision']} at {pc['fine_timeout_seconds']}s, merged Lazy {pc['merged_decision']} at {pc['merged_timeout_seconds']}s, fine Direct-Full {pc['direct_full_status']} at {pc['direct_full_timeout_seconds']}s, all Mac, 32g; original 1200s merged/Full timeouts are retained as separate rows.",
 "Independent: all 81 reachable states of the supplied old controller/plant product satisfy both raw transfer domains, and 16 have no enabled physical UC action; the empty-domain hypothesis is false, while the joint CAL/CAL successor violates the availability interval."
]
if pc.get('xeon_fine_status'):
    pc_lines.append(f"Received Xeon, 200g/7200s: fine Lazy {pc['xeon_fine_status']}, whole JVM {pc['xeon_fine_whole_jvm_seconds']}s, peak RSS {pc['xeon_fine_peak_rss_gib']}GiB; merged Lazy {pc['xeon_merged_status']}, {pc['xeon_merged_whole_jvm_seconds']}s/{pc['xeon_merged_peak_rss_gib']}GiB; fine Direct-Full {pc['xeon_direct_full_status']}, {pc['xeon_direct_full_whole_jvm_seconds']}s/{pc['xeon_direct_full_peak_rss_gib']}GiB. The fine decision and state/query/rank counters agree with Mac; raw exit codes and runtime class hashes are unavailable. These separate host rows do not add comparison pairs or justify cross-host timing comparisons.")
extended={k:pc.get(k+'_extended_7200_status','NOT_REGISTERED') for k in ('merged','direct_full')}
if any(v in ('RUNNING','NOT_STARTED') for v in extended.values()):
    pc_lines.append('The separately authorized 7200s extension is still unfinished: '+json.dumps(extended,sort_keys=True)+'. No expected decision is substituted.')
now=datetime.now(ZoneInfo('Asia/Tokyo'))
final=status['status']=='FINAL_WITH_LIMITATIONS'
if final:
    authorization=json.loads((OUT/'early_finalization_authorization.json').read_text()) if (OUT/'early_finalization_authorization.json').exists() else {}
    assert now>=datetime(2026,9,30,10,0,tzinfo=ZoneInfo('Asia/Tokyo')) or (authorization.get('schema')=='e6-early-finalization-authorization-v1' and authorization.get('status')=='AUTHORIZED_BY_EXPLICIT_USER_INSTRUCTION' and authorization.get('campaign')=='E6' and datetime.fromisoformat(authorization['authorized_at_jst'])<=now)
stage='Final handoff authorized by the explicit PI/user instruction; the PC2 measurement remains unresolved.' if final else 'This is a draft until the real deadline or an explicit early-finalization instruction.'
lines=['# Current concise handoff prose','',f"Generated at {now.isoformat()}; index status {status['status']}. {stage}",'','## RQ2 — four sentences','', ' '.join(rq2),'','## Introduction — two sentences','', ' '.join(intro),'', 'Citations: `e6_kubernetes_deployments`, `e6_mongodb_enterprise_replica_set`; verified scope in `primary_source_scope.md`.','','## Threats — one sentence','',threat,'','## PC2 measured and independent statements (keep separate)','',*pc_lines,'','## Separate populations','']
for name,counts in status['by_population'].items():
    if name in ('scale_extension','assumption_control','reference_e4'):
        lines.append(f"- `{name}`: "+', '.join(f'{k}={v}' for k,v in counts.items())+'.')
lines+=['','The scale extension and E4 reference witnesses do not increase the 55 main comparisons. Canary intervention controls are likewise separate. Native certificate ranks are returned bounds, not necessarily optimal ranks. Mac timings are not compared with Xeon timings.','']
(OUT/'CURRENT_HANDOFF_PROSE.md').write_text('\n'.join(lines))
(OUT/'current_prose_provenance.json').write_text(json.dumps(dict(status='FINAL_WITH_LIMITATIONS' if final else 'DRAFT',index_sha256=hashlib.sha256((E6/'results_index.csv').read_bytes()).hexdigest(),main_pair_counts=c,pc2_extension=extended,source_status_timestamp=status['generated_at'],rq2_sentence_count=4,introduction_sentence_count=2,threats_sentence_count=1),indent=2)+'\n')
print(json.dumps(dict(main_pair_counts=c,pc2_extension=extended)))
