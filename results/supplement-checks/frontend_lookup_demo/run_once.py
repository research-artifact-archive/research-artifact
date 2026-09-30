#!/usr/bin/env python3
"""27 separate frontend-only JVM attempts; fixed 18:25 JST aggregate deadline."""
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = Path(__import__("os").environ["FGDUCS_PACKAGE_ROOT"]) if "FGDUCS_PACKAGE_ROOT" in __import__("os").environ else next(p for p in HERE.parents if (p / "Implementation/Experiment/Models").is_dir())
SUBMISSION = ROOT / "FSE2027_SUBMISSION_20260914"
JAVA_HOME = Path("/opt/homebrew/opt/openjdk@17")
JAR = SUBMISSION / "experiments/rq3_xeon/bundle/Implementation/Source Code/maven-root/mtsa/target/mtsa-1.0-SNAPSHOT.jar"
EXPECTED_JAR = "fbdc25f58d5441ed906d408a94b7414c9d9c3ed35e2ebce22d9751729967ba07"
DEADLINE = dt.datetime(2026, 9, 22, 9, 25, tzinfo=dt.timezone.utc)


def digest(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""): h.update(chunk)
    return h.hexdigest()


def relative(p): return str(p.relative_to(ROOT))


def main():
    config = json.loads((SUBMISSION / "experiments/rq3_xeon/configs/rq3.json").read_text())
    original = json.loads((SUBMISSION / "experiments/rq3_xeon/raw/rq3/environment.json").read_text())
    assert digest(JAR) == EXPECTED_JAR
    assert not (HERE / "runs").exists(), "Saved campaign exists; no overwrite/retry."
    for model in config["models"]:
        assert digest(ROOT / model["path"]) == original["model_input_bytes"][model["path"]]
    classes = HERE / "classes"; classes.mkdir(exist_ok=True)
    compile_command = [str(JAVA_HOME / "bin/javac"), "-cp", relative(JAR), "-d", relative(classes), relative(HERE / "FrontendLookupExport.java")]
    compile_result = subprocess.run(compile_command, cwd=ROOT, capture_output=True, text=True, timeout=60)
    (HERE / "compile.log").write_text("COMMAND=" + json.dumps(compile_command) + "\n" + compile_result.stdout + compile_result.stderr + "\nEXIT=" + str(compile_result.returncode) + "\n")
    compile_result.check_returncode()
    version = subprocess.run([str(JAVA_HOME / "bin/java"), "-version"], capture_output=True, text=True, check=True).stderr.strip()
    runs = HERE / "runs"; runs.mkdir()
    rows = []
    for model in config["models"]:
        for target in config["targets"]:
            case = model["id"] + "__" + target["id"]
            folder = runs / case; folder.mkdir()
            remaining = (DEADLINE - dt.datetime.now(dt.timezone.utc)).total_seconds()
            if remaining <= 0:
                meta = dict(case=case, model=model["id"], target=target["id"], attempt=0,
                            status="NOT_RUN_AGGREGATE_DEADLINE", exit_code=None)
            else:
                command = [str(JAVA_HOME / "bin/java"), "-Xmx2g", "-Djava.awt.headless=true",
                           "-Dmtsa.evaluation.enabled=false", "-cp", os.pathsep.join([relative(classes), relative(JAR)]),
                           "ltsa.lts.FrontendLookupExport", model["path"], "UpdCont_OTF_FG" + target["suffix"],
                           relative(folder / "lookup.json")]
                meta = dict(case=case, model=model["id"], target=target["id"], attempt=1, status="RUNNING",
                            input=model["path"], input_sha256=digest(ROOT / model["path"]),
                            jar=relative(JAR), jar_sha256=EXPECTED_JAR, java_version=version,
                            exporter_sha256=digest(HERE / "FrontendLookupExport.java"), command=command,
                            timeout_seconds=min(120, remaining), aggregate_deadline_utc=DEADLINE.isoformat(),
                            started_at_utc=dt.datetime.now(dt.timezone.utc).isoformat())
                (folder / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
                start = time.monotonic()
                try:
                    with (folder / "stdout.txt").open("xb") as out, (folder / "stderr.txt").open("xb") as err:
                        result = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err, timeout=min(120, remaining))
                    meta.update(exit_code=result.returncode, status="EXPORTED" if result.returncode == 0 and (folder / "lookup.json").exists() else "FAILED")
                except subprocess.TimeoutExpired:
                    meta.update(exit_code=None, status="TIMEOUT")
                meta["elapsed_context_only_not_performance_data"] = time.monotonic() - start
                meta["finished_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
            meta["saved_files"] = {f.name: dict(bytes=f.stat().st_size, sha256=digest(f)) for f in sorted(folder.iterdir()) if f.name != "meta.json"}
            (folder / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
            row = {k: meta[k] for k in ("case", "model", "target", "attempt", "status", "exit_code")}
            rows.append(row)
            with (HERE / "run_summary.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(row)); writer.writeheader(); writer.writerows(rows)
            print(case, meta["status"], meta["exit_code"], flush=True)
    assert digest(JAR) == EXPECTED_JAR
    for model in config["models"]:
        assert digest(ROOT / model["path"]) == original["model_input_bytes"][model["path"]]


if __name__ == "__main__": main()
