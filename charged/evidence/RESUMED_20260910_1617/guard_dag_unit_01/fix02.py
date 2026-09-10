from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((D/'INPUT_FIX_RECEIPT01.json').read_text())
files={n:dict(sha256=sha(D/n),bytes=(D/n).stat().st_size) for n in ['CANDIDATE01.md','PRIMARY_ATTRIBUTION01.md','PROTOCOL02.md','fix02.py','check02.py','INPUTS01.json']}
assert sha(D/'INPUTS01.json')==old['files']['INPUTS01.json']['sha256']
assert not(D/'run01').exists() and not(D/'run02').exists()
with (D/'INPUT_FIX_RECEIPT02.json').open('x') as f:json.dump(dict(utc=datetime.now(timezone.utc).isoformat(),counts=old['counts'],files=files,inherited_checker_sha256=sha(D.parent/'charged_comparison_01/check04.py'),predecessor_fix_sha256=sha(D/'INPUT_FIX_RECEIPT01.json'),predecessor_unexecuted=True,results_observed_before_fix=False),f,indent=2);f.write('\n')
print(json.dumps(old['counts']))
