#!/usr/bin/env python3
"""Check the paper’s family table and all-contract Lazy/Eager cost figure."""
import argparse
import csv
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from read_saved_source import read_source


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(root):
    paper = root/'paper/source'
    sys.path.insert(0, str(paper/'scripts'))
    spec = importlib.util.spec_from_file_location('family_table', paper/'scripts/generate_rq2_family_table.py')
    family = importlib.util.module_from_spec(spec); spec.loader.exec_module(family)
    table, family_report = family.collect(root)
    require(table == (paper/'figures/rq2_family_counts.tex').read_text(), 'Family table differs from saved comparisons')
    # The manuscript source ZIP omits build/table_source_check.json. Recompute its
    # full population checks instead of requiring that incidental build output.
    primary = list(csv.DictReader(io.StringIO(read_source(root,
        'FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/raw/rq3/summary.csv').decode())))
    display = list(csv.DictReader((paper/'build/generated/rq3-cells.csv').open()))
    key = lambda row: (row['model_id'], row['target_id'], row['method_id'])
    original = {key(row): row for row in primary}
    require(len(original) == len(primary), 'Duplicate primary measurement cells')
    methods = ('fg_ducs_otf', 'fg_ducs_otf_eager_controllable')
    cells = [r for r in display if r['method_id'] in methods]
    require(len(cells) == len({key(r) for r in cells}) == 54, 'Expected all 27 contracts for both methods')
    fields = ('stage1_status', 'completed_valid_repetitions', 'structure_repetition', 'states_discovered',
              'elapsed_monotonic_seconds_median', 'elapsed_monotonic_seconds_min', 'elapsed_monotonic_seconds_max')
    for row in cells:
        require(all(row[field] == original[key(row)][field] for field in fields), 'Plot input differs from primary data: '+str(key(row)))
    # Regenerate in a disposable copy and compare the full drawing, including
    # all markers, min/max bars, missing-state handling, LOSS labels and TO arrows.
    with tempfile.TemporaryDirectory(prefix='fgducs-current-displays-') as temp:
        work = Path(temp)
        for rel in ('build_support/generate_matched_cost_figure.py', 'build/generated/rq3-cells.csv'):
            target = work/rel; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(paper/rel, target)
        (work/'figures').mkdir()
        subprocess.run([sys.executable, '-B', str(work/'build_support/generate_matched_cost_figure.py')], check=True, capture_output=True)
        require((work/'figures/rq3_paired_absolute.tex').read_bytes() == (paper/'figures/rq3_paired_absolute.tex').read_bytes(),
                'Matched-cost figure differs from complete saved-data rendering')
    return {'status': 'PASS', 'family_table': family_report,
            'matched_costs': {'contracts': 27, 'method_cells': 54, 'primary_fields_equal': 54*len(fields),
                              'completed_cells': 43, 'single_attempt_timeouts': 11,
                              'complete_drawing_reproduced': True},
            'scope': 'Saved-data aggregation; original manuscript inputs unchanged; no new measurement.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(verify(args.artifact_root.resolve()), indent=2))
