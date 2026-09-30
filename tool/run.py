#!/usr/bin/env python3
"""Run one finite contract; archive a checked policy or losing certificate."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
args=sys.argv[1:]
if '--driver-source' not in args:
    args+=['--driver-source',str(ROOT/'results/granularity/e6/common')]
out=None
if '--output' in args and args.index('--output')+1<len(args):
    out=Path(args[args.index('--output')+1])
existed=out is not None and (out.exists() or out.is_symlink())
code=subprocess.call([sys.executable,str(ROOT/'reproduce/scripts/run_finite.py'),*args])
if out is not None and not existed and code in (0,2) and (out/'replication.json').is_file():
    record=json.loads((out/'replication.json').read_text())
    if record.get('status') in ('CHECKED_WIN','CHECKED_LOSS'):
        subprocess.run([sys.executable,str(ROOT/'tool/view_result.py'),'--result',str(out/'result.json'),'--output',str(out/'report.html')],check=True)
raise SystemExit(code)
