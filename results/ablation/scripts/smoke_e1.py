#!/usr/bin/env python3
"""Separate low-heap GSM CLI smoke before E1, outside the evidence campaign."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

from ablation_common import planned_jobs, read_json, read_trial, sha256, write_json
from run_ablation import execution_lock, run_trial

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[2]


def main():
    config = read_json(HERE / 'configs/e1_mac.json')
    config['java_heap'] = '2g'
    provenance = read_json(ROOT / config['jar_metadata'])
    if sha256(ROOT / config['classpath']) != provenance['jar_sha256']:
        raise RuntimeError('Smoke JAR does not match metadata')
    jobs = [copy.deepcopy(j) for j in planned_jobs(config) if j['model_id'] == 'gsm' and j['target_id'] == 'base']
    none = copy.deepcopy(jobs[0])
    none.update(job_id='gsm__base__rep01__lazy_merge_none', merge='none', method_id='lazy_merge_none')
    none['jvm_properties']['mtsa.otf.contractMerge'] = 'none'
    jobs.insert(0, none)
    campaign = HERE / 'build/smoke/e1_gsm_cli'
    rows = []
    with execution_lock(ROOT / config['results_root'] / 'ablation.lock'):
        for job in jobs:
            result = run_trial(config, job, 60, 'smoke_60s_2g', campaign, ROOT, provenance)
            rows.append(dict(merge=job['merge'], **result))
            print('E1 CLI smoke', job['merge'], result['decision'], result.get('states_discovered', ''), result.get('failure_reason', ''), flush=True)
    original = read_trial(HERE.parent / 'rq3_xeon/raw/rq3/runs/gsm__base__rep01__fg_ducs_otf/meta.json')
    none_equal = all(rows[0].get(k) == original.get(k) for k in ['decision', 'states_discovered', 'successor_queries', 'worst_completion_rank', 'input_sha256'])
    result = dict(smoke_rows=rows, none_matches_existing_first_trial=none_equal,
                  separate_from_campaign=True, heap='2g', timeout_seconds=60)
    write_json(campaign / 'smoke_results.json', result)
    if not none_equal or any(r['decision'] not in {'WIN', 'LOSS'} for r in rows):
        print('E1 CLI smoke requires investigation; campaign not started.', flush=True)
        return 2
    print('E1 CLI smoke passed, including none vs existing first-trial metrics.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
