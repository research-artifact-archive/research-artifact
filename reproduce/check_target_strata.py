#!/usr/bin/env python3
"""Check the displayed target-stratum ratios against saved primary evidence.

The populations are conditional on five completed valid repetitions for both
methods. Different target populations do not isolate a causal requirement effect.
No solver, generator, TeX build or new benchmark is run.
"""
from decimal import Decimal
import json
from pathlib import Path
from statistics import median

import check_visual_evidence as base
from read_saved_source import read_source


def verify_text(main, primary, display):
    pairs, comparisons = base.expected_pairs(primary, display)
    result = {}
    for target, count in (('base', 5), ('r1', 3), ('r2', 6)):
        members = sorted((model, values) for (model, variant), values in pairs.items()
                         if variant == target)
        base.require(len(members) == count, 'stratum_population', target)
        states = median(values[1] / values[0] for _, values in members)
        solver = median(values[3] / values[2] for _, values in members)
        result[target] = {
            'completed_pairs': count, 'models': [model for model, _ in members],
            'median_state_ratio': str(states), 'median_solver_ratio': str(solver),
            'display_state_ratio': str(states.quantize(Decimal('.01'))),
            'display_solver_ratio': str(solver.quantize(Decimal('.01'))),
        }
    state_display = '/'.join(row['display_state_ratio'] for row in result.values())
    solver_display = '/'.join(row['display_solver_ratio'] for row in result.values())
    expected = ("Base/R1/R2's 5/3/6 pairs give median state ratios "
                + state_display + ' and solver ratios ' + solver_display + '.')
    base.require(base.norm(base.clean(main)).count(base.norm(expected)) == 1,
                 'stratum_statement', 'One exact statement derived from saved data')
    qualifier = ("different completed populations do not isolate interval requirements' effect.")
    base.require(base.norm(qualifier) in base.norm(base.clean(main)),
                 'stratum_scope', 'Conditional populations, not a causal effect')
    return {'status': 'PASS', 'details': {'targets': result, 'statement': expected,
            'primary_fields_equal': comparisons,
            'scope': 'Conditional descriptive ratios across different completed populations; no causal effect or new experiment.'}}


def verify(root):
    paper = root/'paper/source'
    logical = 'FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/raw/rq3/summary.csv'
    primary = read_source(root, logical).decode('utf-8')
    return verify_text((paper/'technical_fragments/additional_populations.tex').read_text(), primary,
                       (paper/'build/generated/rq3-cells.csv').read_text())


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(verify(args.artifact_root.resolve()), indent=2))


if __name__ == '__main__':
    main()
