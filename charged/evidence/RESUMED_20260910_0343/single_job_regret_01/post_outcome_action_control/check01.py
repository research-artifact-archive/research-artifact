from pathlib import Path
import importlib.util,json,hashlib,datetime
P=Path(__file__).resolve().parents[1];O=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("regret_control_subject",P/"run01.py");m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
inputs=json.loads((P/"run01/INPUTS.json").read_text());ix=next(i for i,x in enumerate(inputs) if (x["w"],x["kappa"],x["r"])==(5,1,2))
source=next(j for line in (P/"run01/RAW.jsonl").open() if (j:=json.loads(line))["input"]==ix and j["B"]==0)
changed=json.loads(json.dumps(source));row=next(x for x in changed["policies"] if x["cheap_failures"]==0 and x["finish"]=="cached");assert row["cost"]==1;row["finish"]="fresh"
before=m.validate(source,5,1,2);after=m.validate(changed,5,1,2);assert before and not after
r=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status="PASS",post_outcome=True,original_accepted=before,action_mutation_detected=not after,original_cost=1,mutated_action_correct_cost=6,changed_field="finish: cached -> fresh",original_four_controls_unchanged=True,new_native_samples=0,source_input=ix,source_budget=0,source_raw_sha256=hashlib.sha256((P/"run01/RAW.jsonl").read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),plan_sha256=hashlib.sha256((O/"PLAN.md").read_bytes()).hexdigest())
with (O/"RESULT.json").open("x") as f:json.dump(r,f,indent=2);f.write("\n")
print(json.dumps(r))
