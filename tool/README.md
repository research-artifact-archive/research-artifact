# Build and run FG-DUCS

Use **Python 3.10+**, a **64-bit JDK 17**, **Maven**, and **Git**. A source build downloads dependencies from their upstream locations; allow several minutes and several GB of disk. No solver or third-party JAR is redistributed. [LICENSE](../LICENSE) and [NOTICE](../NOTICE) explain the source and dependency terms.

### 1. Build the finite-example solver

Run commands from this repository's root. Use a new output directory for each build and run:

```sh
python3 tool/build.py --variant e1 --output work/e1
```

This verifies and copies the source into a work area, applies the complete E1 source patch, downloads hash-checked upstream dependencies, and builds the JAR. The E1 variant provides the explicit finite-model adapter and merging operations used in the granularity experiments. `baseline`, `e2` and `e5` select the other measured source variants. Each patch is applied to a fresh baseline, never on top of another patch. The build compiles tests but skips their execution.

### 2. Run the small Rolling example

```sh
python3 tool/run.py \
  --jar "work/e1/Implementation/Source Code/maven-root/mtsa/target/mtsa-1.0-SNAPSHOT.jar" \
  --input results/granularity/e6/rolling/v1/inputs/rolling_n02_m01_k01.json \
  --merge none --output work/rolling-fine
```

There are two replicas and at least one must remain ready. Updating one replica, waiting for its ready report, and then updating the other permits safe completion. The expected result is **WIN**. Open `work/rolling-fine/report.html` in a browser. This offline viewer shows the actual recorded decision, checks, policy actions, ranks and searchable certificate states.

![Actual local WIN result from a public-source build](../docs/images/rolling-win.jpg)

Now run the same input with its transfer events merged:

```sh
python3 tool/run.py \
  --jar "work/e1/Implementation/Source Code/maven-root/mtsa/target/mtsa-1.0-SNAPSHOT.jar" \
  --input results/granularity/e6/rolling/v1/inputs/rolling_n02_m01_k01.json \
  --merge transfers --output work/rolling-merged
```

The expected result is **LOSS**: simultaneously starting both replicas violates the availability tester. Open `work/rolling-merged/report.html` to inspect its losing-region evidence.

[Screenshot of the actual local LOSS result](../docs/images/rolling-loss.jpg). The report includes every saved certificate state and the sampled losing-entry action buckets.

The runner defaults to a **2 GiB heap** and **60-second whole-JVM limit**. `--heap`, `--timeout`, `--solver lazy|direct_full`, and `--merge none|transfers|boundaries|both` make the choice explicit. Exit 0 means checked WIN; checked LOSS uses exit 2. Because argument errors also use exit 2, inspect `replication.json` for `CHECKED_LOSS`. A timeout uses exit 124. Each fresh output preserves `input.json`, `result.json`, `certificate.json`, logs, the actual JAR/input/certificate hashes, run configuration and `report.html`. A local source build is not asserted byte-identical to a measured JAR; new runs are not added to paper timings.

The screenshots above come from actual local functional runs of the published source. The viewer verifies the certificate file digest and decision match; its displayed semantic PASS values are those recorded by the native checkers. Viewing a report does not rerun those checks. You can also render an existing finite result with:

```sh
python3 tool/view_result.py --result path/to/result.json --output new-report.html
```

### 3. Supply your own contract or use the inherited GUI

Start from the small JSON example and read the [finite input schema](../results/granularity/e6/common/SCHEMA.md) and [input guide](../docs/INPUTS.md). Encode all transfer outcomes and the exact requirement lifetimes. Do not use the model's physical initial state as a substitute for all admitted old entries. Merging can invalidate a contract if it collapses strict precedence or noncommuting monitor observations; such cases must remain INVALID.

For the inherited FSP frontend and Java GUI, build the baseline and launch it:

```sh
python3 tool/build.py --variant baseline --output work/baseline
java -jar "work/baseline/Implementation/Source Code/maven-root/mtsa/target/mtsa-1.0-SNAPSHOT.jar"
```

Open `tool/models/GSM_FG.lts`, choose `UPDATE_CONTROLLER_OTF_FG`, and click **Compose (`||`)**. The file's opening comments identify the R1/R2 target variants. **Transitions**, **Draw** and **Animation** inspect the result. The GUI is the existing MTSA frontend; the browser screenshots above show the new result viewer for the explicit finite-model runner. A headless inherited-model example is documented in [reproduction details](../docs/REPRODUCTION.md).


Return to the [paper and reading routes](../README.md) or the [reproduction guide](../docs/REPRODUCTION.md).
