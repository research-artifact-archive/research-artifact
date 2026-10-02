#!/usr/bin/env python3
"""Reproduce the all13 PC2 static report and compare every saved result field."""
import argparse
import json
from pathlib import Path
from check_pc2_all_act import analyze, CERTIFICATE, SOURCE
from read_saved_source import read_source


def verify(root):
    actual = analyze(json.loads(read_source(root, CERTIFICATE.as_posix())), read_source(root, SOURCE.as_posix()).decode('utf-8'))
    saved = json.loads((root / 'results/pc2-all-active-obligations.json').read_text())
    if json.loads(json.dumps(actual)) != saved:
        raise ValueError('Saved all13 report differs from independently recomputed source/graph analysis')
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = verify(args.artifact_root.resolve())
    print(json.dumps({'status': 'PASS', 'requirements': len(result['active_obligations']), 'entries': result['saved_population']['entries'], 'observer_edges_checked': result['observer_interpretation']['source_observer_edges_checked'], 'stored_report_matches': True, 'endpoint_verification': 'assumed supplied endpoint', 'new_experiments': False}))


if __name__ == '__main__':
    main()
