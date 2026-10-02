#!/usr/bin/env python3
"""Check the paper's display inputs against saved evidence; never run a solver."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

GENERATORS = (
    'generate_pc2_case_macros.py',
    'generate_pc2_trace_macros.py',
    'generate_rq2_family_table.py',
    'generate_rq3_outcome_grid.py',
    'generate_rq3_paired_plot.py',
)
DISPLAY_FILES = (
    'main.tex',
    'technical_appendix.tex',
    'technical_fragments/additional_populations.tex',
    'technical_fragments/promotion_cases.tex',
    'build/generated/pc2-case-macros.tex',
    'build/generated/pc2-trace-macros.tex',
    'figures/rq2_family_counts.tex',
    'figures/rq3_outcome_grid.tex',
    'figures/rq3_paired_absolute.tex',
    'figures/cell_story_visual.tex',
    'figures/cell_policy_paths.tex',
    'figures/policy_lifetimes.tex',
    'figures/pc2_saved_path.tex',
    'technical_fragments/pc2_history_boundary.tex',
    'build/generated/rq3-cells.csv',
    'figures/policy_finite_main.tex',
    'technical_fragments/gsm_active_policy.tex',
    'technical_fragments/gsm_entry_derivation.tex',
    'figures/guarantee_evidence_map.tex',
    'technical_fragments/ducs_cell_complete.tex',
    'technical_fragments/synthesis_statement.tex',
    'technical_fragments/synthesis_complete_main.tex',
    'technical_fragments/correctness_proof.tex',
    'technical_fragments/cell_residual_derivation.tex',
    'technical_fragments/constructed_contracts.tex',
    'technical_fragments/work_accounting.tex',
    'technical_fragments/initializer_semantics.tex',
    'technical_fragments/activation_duty_main.tex',
    'technical_fragments/history_scope_main.tex',
    'technical_fragments/history_checks.tex',
    'technical_fragments/pc2_all_activation.tex',
    'figures/contract_pipeline_c30.tex',
    'figures/contract_responsibility.tex',
    'technical_fragments/contract_adequacy_statement.tex',
    'technical_fragments/contract_adequacy_proof.tex',
    'technical_fragments/residual_formal.tex',
    'technical_fragments/performance_scope_details.tex',
    'figures/contract_interfaces_full.tex',
    'technical_fragments/ducs_cell_correspondence.tex',
    'technical_fragments/endpoint_interface.tex',
    'technical_fragments/endpoint_interface_proof.tex',
    'technical_fragments/gr1_cell_interface.tex',
)


def snapshot(paper):
    return {name: hashlib.sha256((paper/name).read_bytes()).hexdigest()
            for name in DISPLAY_FILES}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, help='Optional new JSON report file')
    args = parser.parse_args()
    if args.output is not None and args.output.exists():
        parser.error('Choose a new report file')
    root = args.artifact_root.resolve()
    paper = root/'paper/source'
    before = snapshot(paper)
    commands = [(name, [sys.executable, '-B', str(paper/'scripts'/name), '--check'])
                for name in GENERATORS]
    commands.extend([
        ('visual_evidence', [sys.executable, '-B', str(root/'reproduce/check_visual_evidence.py'),
                             '--artifact-root', str(root)]),
        ('outcome_grid', [sys.executable, '-B', str(root/'reproduce/check_outcome_grid.py'),
                          '--tex', str(paper/'figures/rq3_outcome_grid.tex'),
                          '--csv', str(paper/'build/generated/rq3-cells.csv'), '--self-test']),
        ('requirement_bands', [sys.executable, '-B', str(root/'reproduce/check_requirement_bands.py'),
                               '--artifact-root', str(root)]),
        ('target_strata', [sys.executable, '-B', str(root/'reproduce/check_target_strata.py'),
                           '--artifact-root', str(root)]),
        ('policy_evidence', [sys.executable, '-B', str(root/'reproduce/check_policy_evidence.py'),
                             '--artifact-root', str(root)]),
        ('pc2_saved_path', [sys.executable, '-B', str(root/'reproduce/check_pc2_saved_path.py'),
                            '--artifact-root', str(root)]),
        ('pc2_histories', [sys.executable, '-B', str(root/'reproduce/check_pc2_histories.py'),
                           '--artifact-root', str(root)]),
        ('pc2_active_suffix', [sys.executable, '-B', str(root/'reproduce/check_pc2_active_suffix.py'),
                               '--repository', str(root)]),
        ('pc2_all_active_obligations', [sys.executable, '-B', str(root/'reproduce/check_pc2_all_act_saved.py'),
                                       '--artifact-root', str(root)]),
    ])
    results = []
    for name, command in commands:
        run = subprocess.run(command, cwd=paper, text=True, capture_output=True)
        results.append({'check': name, 'status': 'PASS' if run.returncode == 0 else 'FAIL',
                        'stdout': run.stdout, 'stderr': run.stderr})
        print(results[-1]['status'] + ': ' + name, flush=True)
    unchanged = snapshot(paper) == before
    passed = unchanged and all(row['status'] == 'PASS' for row in results)
    report = {'status': 'PASS' if passed else 'FAIL', 'checks': results,
              'display_files_unchanged': unchanged,
              'scope': 'Saved-data reproduction and drawing consistency; no Java, network or new benchmark.'}
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as stream:
            json.dump(report, stream, indent=2); stream.write('\n')
    if not passed:
        for row in results:
            if row['status'] == 'FAIL':
                print(row['stdout'] + row['stderr'], file=sys.stderr)
        raise SystemExit('FAIL: a display check failed or modified a display input')
    print('PASS: all fourteen display and saved-policy checks; input files unchanged.')


if __name__ == '__main__':
    main()
