#!/usr/bin/env python3
"""Verify saved data and regenerate semantic/result checks, without running Java."""
from pathlib import Path
import argparse,subprocess,sys,json
from materialize import materialize
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
if out.exists():p.error('Choose a fresh output directory')
out.mkdir(parents=True);w=materialize(out/'workspace')
subprocess.run([sys.executable,str(w/'quickstart.py'),'--root',str(w),'--output',str(out/'core')],check=True)
report=json.loads((out/'core/quickstart-report.json').read_text())
if any(x['status']!='PASS' for x in report['checks']):raise SystemExit('Incomplete: install Matplotlib and use a fresh output directory. SKIP is not PASS.')
subprocess.run([sys.executable,str(w/'evidence/reproduce_supplement.py'),'--package',str(w),'--output',str(out/'supplement')],check=True)
extra=Path(__file__).resolve().parent/'check_extensions.py'
if extra.exists():subprocess.run([sys.executable,str(extra),'--workspace',str(w),'--output',str(out/'extensions.json')],check=True)
displays=Path(__file__).resolve().parent/'check_paper_displays.py'
if displays.exists():subprocess.run([sys.executable,str(displays),'--output',str(out/'paper-displays.json')],check=True)
added=Path(__file__).resolve().parent/'check_added_analyses.py'
subprocess.run([sys.executable, '-B', str(added), '--output', str(out/'added-analyses')], check=True)
print('PASS: saved-evidence reproduction completed. No benchmark rerun was performed.')
