#!/usr/bin/env python3
"""Run one separate qualitative Railcab/R1 policy export; never a timing sample.

Uses the original campaign JAR, input, solver properties and heap limit. Changes
only the local Java executable and output paths/format, and requests the typed
handoff bundle. This exports the complete winning certificate, not the complete
reachable game. Refuses to overwrite a previous attempt. No performance summary
or old raw result is modified. Do not treat a modeled policy as a runtime proof.
"""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = Path(__import__("os").environ["FGDUCS_PACKAGE_ROOT"]) if "FGDUCS_PACKAGE_ROOT" in __import__("os").environ else next(p for p in HERE.parents if (p / "Implementation/Experiment/Models").is_dir())
CAMPAIGN = ROOT / "FSE2027_SUBMISSION_20260914/experiments/rq3_xeon"
SOURCE_META = CAMPAIGN / "raw/rq3/runs/railcab__r1__rep01__fg_ducs_otf/meta.json"
JAR = CAMPAIGN / "bundle/Implementation/Source Code/maven-root/mtsa/target/mtsa-1.0-SNAPSHOT.jar"
MODEL = ROOT / "Implementation/Experiment/Models/Railcab_FG.lts"


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def relative(path):
    return str(path.relative_to(ROOT))


def main():
    assert not (HERE / "meta.json").exists(), "A demo attempt is already recorded; no retry."
    original = json.loads(SOURCE_META.read_text())
    assert digest(JAR) == original["classpath"]["sha256"]
    assert digest(MODEL) == original["input_model"]["sha256"]
    java = shutil.which("java")
    assert java, "An existing Java installation is required."
    version = subprocess.run([java, "-version"], text=True, capture_output=True, check=True)
    command = list(original["command"])
    command[0] = java
    changes = {"-cp": relative(JAR), "--lts": relative(MODEL),
               "--output": relative(HERE / "output.txt"),
               "--transitions": relative(HERE / "transitions.txt"),
               "--transition-output": "full"}
    for option, value in changes.items():
        command[command.index(option) + 1] = value
    command += ["--deployment-output", relative(HERE / "handoff-bundle.json")]
    assert "--game-output" not in command
    assert [a for a in command if a.startswith("-D") or a.startswith("-Xmx")] == [
        a for a in original["command"] if a.startswith("-D") or a.startswith("-Xmx")]
    meta = {"purpose": "single qualitative model-policy illustration; excluded from all timing/performance summaries",
            "attempt": 1, "source_meta": relative(SOURCE_META),
            "jar": relative(JAR), "jar_sha256": digest(JAR),
            "input": relative(MODEL), "input_sha256": digest(MODEL),
            "java_version": version.stderr.strip(),
            "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
            "command": command, "timeout_seconds": 1200,
            "started_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "running", "semantic_and_solver_properties_equal_to_source": True,
            "output_difference": "Full FSP plus complete typed winning-certificate/handoff bundle; no complete-game export.",
            "scope": "Model-level evidence only; does not establish actual runtime or physical-system assumptions."}
    with (HERE / "meta.json").open("x", encoding="utf-8") as stream:
        json.dump(meta, stream, indent=2)
        stream.write("\n")
    start = time.monotonic()
    try:
        with (HERE / "stdout.txt").open("xb") as stdout, (HERE / "stderr.txt").open("xb") as stderr:
            completed = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr, timeout=1200)
        meta["exit_code"] = completed.returncode
        meta["status"] = "completed" if completed.returncode == 0 else "nonzero_exit"
    except subprocess.TimeoutExpired:
        meta["status"] = "timeout"
        meta["exit_code"] = None
    except Exception as error:
        meta["status"] = "launch_or_wrapper_error"
        meta["error"] = repr(error)
        raise
    finally:
        meta["elapsed_seconds_context_only_not_performance_data"] = time.monotonic() - start
        meta["finished_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        meta["saved_files"] = {p.name: {"bytes": p.stat().st_size, "sha256": digest(p)}
                               for p in sorted(HERE.iterdir()) if p.is_file() and p.name != "meta.json"}
        (HERE / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print("Single qualitative attempt:", meta["status"], "exit:", meta.get("exit_code"))
    print("Outputs:", ", ".join(meta["saved_files"]))


if __name__ == "__main__":
    main()
