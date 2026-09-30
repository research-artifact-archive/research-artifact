#!/usr/bin/env python3
"""One frozen-CLI attempt per quiescent-goal fixture; never performance data."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = Path(__import__("os").environ["FGDUCS_PACKAGE_ROOT"]) if "FGDUCS_PACKAGE_ROOT" in __import__("os").environ else next(p for p in HERE.parents if (p / "Implementation/Experiment/Models").is_dir())
JAR = ROOT / "FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/bundle/Implementation/Source Code/maven-root/mtsa/target/mtsa-1.0-SNAPSHOT.jar"
JAVA = "/opt/homebrew/opt/openjdk@17/bin/java"
JAR_SHA256 = "fbdc25f58d5441ed906d408a94b7414c9d9c3ed35e2ebce22d9751729967ba07"
CASES = {
    "persistent_uc": ("N0 = (idle -> N0 | spin -> N0).", "C0 = (idle -> C0 | spin -> C0).", (0,)),
    "finite_uc_all_targets": ("N0 = (idle -> N0 | step -> N1),\nN1 = (idle -> N1).", "C0 = (idle -> C0 | step -> C1),\nC1 = (idle -> C1).", (0, 1)),
    "finite_uc_nonquiescent_target_only": ("N0 = (idle -> N0 | step -> N1),\nN1 = (idle -> N1).", "C0 = (idle -> C0 | step -> C1),\nC1 = (idle -> C1).", (0,)),
}
MODEL = """// Qualitative quiescent-goal fixture; no monitors or dependencies.
set ControllableActions = {idle}
TEST_OLD = O,
O = (idle -> O).
TEST_NEW = N0,
NEW_ENV_BODY
||OldEnvironment = (TEST_OLD).
||NewEnvironment = (TEST_NEW).
relation R_TEST_FG = {
  O@TEST_OLD = reconfigure_TEST -> N0@TEST_NEW
}
OLD_C = (idle -> OLD_C).
NEW_C = C0,
NEW_CTRL_BODY
||OldController = (OLD_C).
||NewController = (NEW_C).
controllerSpec OldSpec = { controllable = {ControllableActions} }
controllerSpec NewSpec = { controllable = {ControllableActions} }
updatingController QuiescentGoalCheck = {
  oldController = OldController,
  newController = NewController,
  oldEnvironment = {TEST_OLD},
  newEnvironment = {TEST_NEW},
  mapRelation = {R_TEST_FG},
  oldGoal = OldSpec,
  newGoal = NewSpec,
  loadable_new_states = {SELECTOR},
  nonblocking,
  revised_on_the_fly,
  fine_grained
}
||UPDATE_CONTROLLER_OTF_FG = QuiescentGoalCheck.
"""


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def rel(path):
    return str(path.relative_to(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    assert all(not (HERE / case / "meta.json").exists() for case in CASES), "Attempt already saved."
    for case, (env, ctrl, selection) in CASES.items():
        out = HERE / case
        out.mkdir(exist_ok=True)
        text = MODEL.replace("NEW_ENV_BODY", env).replace("NEW_CTRL_BODY", ctrl).replace("SELECTOR", ", ".join(map(str, selection)))
        model = out / "model.lts"
        if model.exists():
            assert model.read_text() == text, "Prepared input differs."
        else:
            model.write_text(text)
    if args.prepare_only:
        print("Prepared three inputs; no Java synthesis executed.")
        return
    assert digest(JAR) == JAR_SHA256
    version = subprocess.run([JAVA, "-version"], text=True, capture_output=True, check=True)
    for case, (_, _, selection) in CASES.items():
        out = HERE / case
        model = out / "model.lts"
        command = [JAVA, "-Djava.awt.headless=true", "-Dmtsa.evaluation.enabled=true",
                   "-Dmtsa.otf.controllableActionOrder=endpoint_guided",
                   "-Dmtsa.otf.guidedQueryLimit=0", "-Dmtsa.otf.guidedStateLimit=0",
                   "-Dmtsa.otf.lazyControllableBuckets=true",
                   "-Dmtsa.revised.otf.independentVerification=true",
                   "-Dmtsa.revised.otf.independentVerificationMode=exhaustive",
                   "-Dmtsa.revised.otf.independentStateLimit=1000",
                   "-Dmtsa.revised.otf.independentQueryLimit=10000",
                   "-Dmtsa.revised.otf.solver=otf", "-Xmx512m", "-cp", rel(JAR),
                   "ltsa.updatingControllers.cli.SingleCompositionRunner",
                   "--lts", rel(model), "--target", "UPDATE_CONTROLLER_OTF_FG",
                   "--output", rel(out / "output.txt"),
                   "--transitions", rel(out / "transitions.txt"), "--transition-output", "full",
                   "--deployment-output", rel(out / "handoff-bundle.json"),
                   "--game-output", rel(out / "independent-game-bundle.json")]
        meta = {"purpose": "qualitative quiescent-goal test only; excluded from all performance statistics",
                "attempt": 1, "case": case, "selector_indices": selection,
                "jar": rel(JAR), "jar_sha256": JAR_SHA256,
                "input": rel(model), "input_sha256": digest(model),
                "java_version": version.stderr.strip(), "platform": platform.platform(),
                "command": command, "timeout_seconds": 120,
                "started_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "status": "running"}
        (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
        started = time.monotonic()
        try:
            with (out / "stdout.txt").open("xb") as stdout, (out / "stderr.txt").open("xb") as stderr:
                result = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr, timeout=120)
            meta.update(status="finished", exit_code=result.returncode)
        except subprocess.TimeoutExpired:
            meta.update(status="timeout", exit_code=None)
        finally:
            meta["elapsed_context_only_not_performance_data"] = time.monotonic() - started
            meta["finished_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            meta["saved_files"] = {p.name: {"bytes": p.stat().st_size, "sha256": digest(p)}
                                   for p in sorted(out.iterdir()) if p.name != "meta.json"}
            (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
        print(case, meta["status"], "exit", meta["exit_code"], flush=True)


if __name__ == "__main__":
    main()
