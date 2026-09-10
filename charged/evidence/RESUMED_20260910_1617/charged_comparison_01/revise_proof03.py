from pathlib import Path
import hashlib,json
from datetime import datetime,timezone
D=Path(__file__).resolve().parent
p=D/'PROOF02.md';s=p.read_text()
assert hashlib.sha256(p.read_bytes()).hexdigest()=='038a67a51c9dbb37fc943917a56c12e840d322ea0956d3fb020b35878de4306c'
s=s.replace('This is the second author proof version, following the first fixed corroboration and Cost10 criticism.', 'This is the third author proof version, restoring the admitted old-raw-snapshot case after the clarification error documented in PROOF02_ERRATUM.md.')
s=s.replace('The charged common start supplies no free computed records.', 'The charged common start supplies no free computed records, but may supply old raw snapshots. Computing from such an old snapshot is charged and can produce an already-stale record even on a no-write run.')
s=s.replace('Let F contain the jobs whose whole bodies are protected on this path, with all paid preparations accounted for.', 'Let F contain the jobs whose whole bodies are protected on this path, including fresh and already-stale cached completion, with all paid preparations accounted for.')
old='Classify its matching cached completions as C and its fresh completions as the complement. Correctly formed target records do not become stale on a no-write run; initial preparations are charged. Even if an enlarged interface admitted an initially stale record, its cached completion would pay at least a fresh completion in both coordinates, provided mandatory computation remains charged.'
new='Classify its matching cached completions as C and its fresh or already-stale cached completions as the complement. A record computed from a supplied old raw snapshot may already be stale without a new write. Its cached completion pays the whole protected body, its guarded charge and its comparison charge; every associated preparation is also charged. It therefore pays at least a fresh completion in both coordinates.'
assert old in s;s=s.replace(old,new)
o=D/'PROOF03.md';assert not o.exists();o.write_text(s)
r={'utc':datetime.now(timezone.utc).isoformat(),'predecessor_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'proof03_sha256':hashlib.sha256(o.read_bytes()).hexdigest(),'reason':'restore stale records computed from admitted old raw snapshots on the no-write lower-bound execution','formula_changes':False,'first_fixed_run_changed':False}
(D/'PROOF03_RECEIPT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
