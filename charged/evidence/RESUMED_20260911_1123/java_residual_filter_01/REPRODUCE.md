# Reproduce the adopted v2 result

The frozen, actually executed commands and tool paths are in attempt02/*_RECEIPT.json. run01.py/run02.py preserve the original absolute time cutoff and reject an existing attempt directory; they are historical execution supervisors, not reusable after the cutoff.

For a later explicitly authorized reproduction, use a fresh output directory and Java17/Python3, from this package directory. These commands use only standard libraries. Do not compile the old top-level ResidualFilter.java together with v2/ResidualFilter.java. Existing inputs and prior attempts must remain unchanged.

```sh
mkdir reproduction01
mkdir reproduction01/classes
javac --release 17 -Xlint:all -d reproduction01/classes v2/ResidualFilter.java Json.java FilterDriver.java NativeIntegration.java
java -cp reproduction01/classes FilterDriver FILTER_INPUTS.tsv > reproduction01/filter.jsonl
java -cp reproduction01/classes NativeIntegration NATIVE_INPUTS.tsv > reproduction01/native.jsonl
python3 -B compare.py reproduction01
java -cp reproduction01/classes FilterDriver HEAP_STRUCTURE_INPUTS.tsv > reproduction01/heap.stdout
python3 -B heap_structure.py compare reproduction01
```

NativeIntegration has its own115s process deadline,2s gate-future bound and2s writer-shutdown bound. The original supervisors additionally bounded compile30s/filter60s/native120s/comparison120s and reaped all processes. Supply equivalent process limits when packaging a reproduction runner. A successful semantic reproduction yields COMPARISON.json status SUCCESS (498 filter rows,996 native paths,48 native roots,discrepancies0), and HEAP_COMPARISON.json SUCCESS (2 extra heap regression roots). Do not add repeated counts as new independent evidence.

PROTOCOL.md, REVISION02.md, all fixed input files, v2/ResidualFilter.java, Json.java, FilterDriver.java, NativeIntegration.java, reference.py, compare.py, heap_structure.py and their hashes are the minimum interpretation/reproduction content. generate_inputs.py records input-generation provenance; do not regenerate into the original directory. Source/freezing receipts include local filesystem paths and are local author records; any public copy is managed separately by the root writer under the project's anonymity rules.
