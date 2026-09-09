"""Replay every fixed order against direct policy work and checked greedy output."""
from pathlib import Path
import hashlib,importlib.util,json,sys
HERE=Path(__file__).resolve().parent;OUT=Path(sys.argv[2]);DATA=HERE/'evidence/RESUMED_20260909_0056/charged_universal_order_01';sys.path.insert(0,str(DATA))
spec=importlib.util.spec_from_file_location('universal_order_study',DATA/'study.py');study=importlib.util.module_from_spec(spec);spec.loader.exec_module(study)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if not __debug__:raise SystemExit('Assertions must be enabled.')
prior=read(DATA/'attempt01/SUMMARY.json');assert prior['status']=='SUCCESS' and prior['cases']==5519 and prior['orders']==86662 and prior['order_pairs']==2773184
result=study.evaluate(OUT/'fresh',cap=180);assert result['status']=='SUCCESS'
for name in ['ORDERS.jsonl','CASES.json','CONTROLS.json']:assert sha(OUT/'fresh'/name)==sha(DATA/'attempt01'/name),name
summary=dict(status='SUCCESS',stage='universal-order',quick=False,cases=5519,orders=86662,order_pairs=2773184,observed_input_cases=5421,new_authored_input_cases=96,other_cases=2,controls=7,native_measurements=0,new_evaluation_samples=0,scope='fixed-policy order optimum and direct work equations; no full-program or scalar guarantee')
with (OUT/'SUMMARY.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
print(json.dumps(summary),flush=True)
