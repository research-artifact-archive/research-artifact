#!/usr/bin/env python3
"""Rebuild and verify FG-DUCS from a pinned official MTSA source archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple


PROJECT_PREFIXES = ("ltsa/", "MTSTools/", "MTSSynthesis/")
REGISTERED_SCOPE_PREFIXES = (
    "ltsa/lts/NativeUpdatingContractLoader",
    "ltsa/updatingControllers/otf/",
    "ltsa/updatingControllers/cli/",
)
DEBUG_ONLY_DIFFERENCES = (
    "MTSTools/ac/ic/doc/mtstools/model/operations/DCS/Compositional/BitMatrix.class",
    "MTSTools/ac/ic/doc/mtstools/model/operations/DCS/Compositional/TransitiveClosureUtils.class",
    "MTSTools/ac/ic/doc/mtstools/model/operations/DCS/nonblocking/DirectedControllerSynthesisNonBlocking$HeuristicMode.class",
    "MTSTools/ac/ic/doc/mtstools/model/operations/DCS/nonblocking/DirectedControllerSynthesisNonBlocking.class",
    "ltsa/updatingControllers/synthesis/UpdatingEnvironmentGenerator.class",
)
FIXED_MODELS = (
    "GSM_FG.lts",
    "Industry_FG.lts",
    "MetaSocket_FG.lts",
    "PowerPlant_FG.lts",
    "ProductionCell_Arms=1_FG.lts",
    "ProductionCell_Arms=2_FG.lts",
    "Railcab_FG.lts",
    "Surveillance_FG.lts",
    "Workflow_FG.lts",
)
FIXED_MODEL_SHA256 = {
    "GSM_FG.lts": "5f4af5b4eafda24516f0653b194f7296799036fc9fe873ac0ce100e0009ae7f4",
    "Industry_FG.lts": "d8bd82a0ad6eeedc4986a688076fe4646f03a665a41a8c6c5f6cbfbd3b2506dd",
    "MetaSocket_FG.lts": "3b8a500a0d3ab1b19141c226e29fad8c43de4d3e7fb890e7cd94eeaa570c9c5f",
    "PowerPlant_FG.lts": "580c2eeb4589d83a4e8177f5339c43d1186707a8ad3601628cb66bf983f1201e",
    "ProductionCell_Arms=1_FG.lts": "4134c3c40a8bfbfc5794e0f9cafdfc9ac2a733f7b91a38a0c6cc908c8dc0bdeb",
    "ProductionCell_Arms=2_FG.lts": "117210fa93185f5a814ad7debbdfcde00720019312c4ef68446a844700084e43",
    "Railcab_FG.lts": "4494c9fb0f7fdf0ee00c1dfdd3a8204fa080cff4ed0bb5d0e8f87c4607b70e7a",
    "Surveillance_FG.lts": "e33b056d19dda9ca03c2ba1be51f5663ac9419b065354e66ddf0a06f4868b2e8",
    "Workflow_FG.lts": "ee6733295443ca86b9035f093aad699434ba1228e67d0d2d49ed9c9e1956e8a1",
}
FORBIDDEN_SELECTIVE_SOURCES: tuple[str, ...] = ()
FORBIDDEN_SELECTIVE_CLASSES = tuple(
    path[len("src/main/java/") : -len(".java")] + ".class"
    for path in FORBIDDEN_SELECTIVE_SOURCES
)
TARGETED_TESTS = (
    "ltsa.lts.CompactStateReachableStateLabelTest",
    "ltsa.lts.MappingEnvironmentGeneratorErrorRenumberTest",
    "ltsa.lts.NativePostFrontendContractFactsRunnerTest",
    "ltsa.lts.NativeSourceDependencyFactsRunnerTest",
    "ltsa.lts.UpdatingControllersDefinitionParserTest",
    "ltsa.updatingControllers.UpdatingControllerEvaluationRecorderTest",
    "ltsa.updatingControllers.cli.SingleCompositionRunnerOutcomeTest",
    "ltsa.updatingControllers.otf.ActivationSpecTest",
    "ltsa.updatingControllers.otf.CompactStrongGameTest",
    "ltsa.updatingControllers.otf.DirectFullStrongSolverTest",
    "ltsa.updatingControllers.otf.EndpointContractValidatorTest",
    "ltsa.updatingControllers.otf.ExperimentModelsRevisedOtfIntegrationTest",
    "ltsa.updatingControllers.otf.FineGrainedOtfDucsTest",
    "ltsa.updatingControllers.otf.IndependentExplicitStrongSolverTest",
    "ltsa.updatingControllers.otf.LoadableEndpointSubsetTest",
    "ltsa.updatingControllers.otf.MtsaRevisedOtfDucsAdapterPrecedenceTest",
    "ltsa.updatingControllers.otf.OtfDucsSynthesizerTest",
    "ltsa.updatingControllers.otf.UpdatePolicyRestrictionTest",
    "ltsa.updatingControllers.structures.UpdateProtocolSpecTest",
)


class RebuildError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    input_bytes: bytes | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    print("+ " + " ".join(command), flush=True)
    return subprocess.run(
        list(command),
        cwd=str(cwd) if cwd else None,
        env=dict(env) if env else None,
        input=input_bytes,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        check=True,
    )


def download(url: str, destination: Path, expected_sha: str, expected_size: int) -> None:
    if destination.is_file():
        if destination.stat().st_size != expected_size or sha256_file(destination) != expected_sha:
            raise RebuildError("cached archive fails size/SHA-256 verification")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".partial-" + str(os.getpid()))
    try:
        with urllib.request.urlopen(url) as response, partial.open("wb") as target:
            shutil.copyfileobj(response, target, length=1024 * 1024)
        if partial.stat().st_size != expected_size or sha256_file(partial) != expected_sha:
            raise RebuildError("downloaded archive fails size/SHA-256 verification")
        os.replace(partial, destination)
    finally:
        if partial.exists():
            partial.unlink()


def safe_extract(archive: Path, destination: Path) -> None:
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or "\\" in member.name:
                raise RebuildError("unsafe archive member: " + member.name)
            if member.issym() or member.islnk():
                raise RebuildError("archive links are not accepted: " + member.name)
            if not (member.isfile() or member.isdir()):
                raise RebuildError("archive special entry is not accepted: " + member.name)
        bundle.extractall(destination)


def locate_models(source_rebuild: Path, explicit: Path | None) -> Path:
    candidates = []
    if explicit is not None:
        candidates.append(explicit)
    candidates.extend(
        [
            source_rebuild.parents[1] / "models/fixed",
            source_rebuild.parents[1] / "models",
            source_rebuild.parent / "artifact/Implementation/Experiment/Models",
            source_rebuild.parent / "Implementation/Experiment/Models",
            source_rebuild.parents[1] / "Implementation/Experiment/Models",
        ]
    )
    for candidate in candidates:
        if all((candidate / name).is_file() for name in FIXED_MODELS):
            return candidate
    raise RebuildError("cannot locate the nine fixed .lts models")


def java_environment(java_home: Path, maven: str) -> Dict[str, str]:
    java = java_home / ("bin/java.exe" if os.name == "nt" else "bin/java")
    javap = java_home / ("bin/javap.exe" if os.name == "nt" else "bin/javap")
    if not java.is_file() or not javap.is_file():
        raise RebuildError("--java-home does not contain java and javap")
    env = dict(os.environ)
    env["JAVA_HOME"] = str(java_home)
    env["PATH"] = str(java.parent) + os.pathsep + env.get("PATH", "")
    java_output = run([str(java), "-version"], env=env, capture=True).stdout.decode(
        "utf-8", "replace"
    )
    if not re.search(r'version "17(?:\.|\")', java_output):
        raise RebuildError("FG-DUCS source rebuild requires JDK 17")
    maven_output = run([maven, "-version"], env=env, capture=True).stdout.decode(
        "utf-8", "replace"
    )
    if not re.search(r"Java version:\s*17(?:\.|,)", maven_output):
        raise RebuildError("Maven is not using JDK 17")
    return env


def apply_overlay(source_rebuild: Path, source_root: Path, manifest: Mapping[str, object]) -> None:
    payload = manifest["payload"]
    assert isinstance(payload, dict)
    patch_path = source_rebuild / str(payload["patch_path"])
    if sha256_file(patch_path) != payload["patch_sha256"]:
        raise RebuildError("source patch SHA-256 mismatch")
    patch = patch_path.read_bytes()
    run(["git", "apply", "--check", "--whitespace=nowarn", "-"], cwd=source_root, input_bytes=patch)
    run(["git", "apply", "--whitespace=nowarn", "-"], cwd=source_root, input_bytes=patch)

    added = manifest["added_files"]
    assert isinstance(added, list)
    for raw in added:
        assert isinstance(raw, dict)
        relative = PurePosixPath(str(raw["path"]))
        source = source_rebuild / "added" / Path(*relative.parts)
        target = source_root / Path(*relative.parts)
        if target.exists():
            raise RebuildError("new overlay file already exists upstream: " + str(relative))
        if sha256_file(source) != raw["sha256"]:
            raise RebuildError("new overlay file SHA-256 mismatch: " + str(relative))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    entries = list(added) + list(manifest["patched_files"])
    for raw in entries:
        assert isinstance(raw, dict)
        relative = PurePosixPath(str(raw["path"]))
        target = source_root / Path(*relative.parts)
        expected = raw.get("sha256", raw.get("result_sha256"))
        if not target.is_file() or sha256_file(target) != expected:
            raise RebuildError("post-overlay verification failed: " + str(relative))


def count_tests(report_root: Path) -> Tuple[int, int, int, int]:
    tests = failures = errors = skipped = 0
    for report in report_root.glob("TEST-*.xml"):
        root = ET.parse(report).getroot()
        tests += int(root.attrib.get("tests", "0"))
        failures += int(root.attrib.get("failures", "0"))
        errors += int(root.attrib.get("errors", "0"))
        skipped += int(root.attrib.get("skipped", "0"))
    return tests, failures, errors, skipped


def project_classes(path: Path) -> Dict[str, bytes]:
    with zipfile.ZipFile(path, "r") as archive:
        return {
            name: archive.read(name)
            for name in archive.namelist()
            if name.endswith(".class") and name.startswith(PROJECT_PREFIXES)
        }


def verify_selective_implementations_absent(project: Path, jar: Path | None = None) -> None:
    present_sources = [path for path in FORBIDDEN_SELECTIVE_SOURCES if (project / path).exists()]
    if present_sources:
        raise RebuildError(
            "excluded selective source implementation is present: "
            + ", ".join(present_sources)
        )
    if jar is None:
        return
    with zipfile.ZipFile(jar, "r") as archive:
        entries = set(archive.namelist())
    present_classes = []
    for expected in FORBIDDEN_SELECTIVE_CLASSES:
        stem = expected[:-len(".class")]
        if expected in entries or any(name.startswith(stem + "$") for name in entries):
            present_classes.append(expected)
    if present_classes:
        raise RebuildError(
            "excluded selective class implementation is present: "
            + ", ".join(present_classes)
        )


def javap_class(java_home: Path, jar: Path, entry: str) -> bytes:
    executable = java_home / ("bin/javap.exe" if os.name == "nt" else "bin/javap")
    class_name = entry[:-6].replace("/", ".")
    return run(
        [
            str(executable),
            "-classpath",
            str(jar),
            "-c",
            "-p",
            "-s",
            "-constants",
            class_name,
        ],
        capture=True,
    ).stdout


def compare_registered_runtime(java_home: Path, built: Path, registered: Path) -> dict:
    actual = project_classes(built)
    expected = project_classes(registered)
    scoped = sorted(
        name for name in actual if name.startswith(REGISTERED_SCOPE_PREFIXES)
    )
    if not scoped or any(name not in expected for name in scoped):
        raise RebuildError("registered runtime lacks a retained proposal/CLI class")
    mismatches = sorted(name for name in scoped if actual[name] != expected[name])
    if mismatches:
        raise RebuildError(
            "retained proposal/CLI class mismatch: " + ", ".join(mismatches)
        )
    for entry in DEBUG_ONLY_DIFFERENCES:
        if javap_class(java_home, built, entry) != javap_class(java_home, registered, entry):
            raise RebuildError("debug-only class changed executable disassembly: " + entry)
    return {
        "retained_proposal_cli_class_count": len(scoped),
        "retained_proposal_cli_raw_byte_identical": len(scoped),
        "audited_debug_only_disassembly_identical": len(DEBUG_ONLY_DIFFERENCES),
        "javap_flags": "-c -p -s -constants",
    }


def main() -> int:
    source_rebuild = Path(__file__).resolve().parent
    manifest = json.loads((source_rebuild / "OVERLAY_MANIFEST.json").read_text(encoding="utf-8"))
    upstream = manifest["upstream"]
    parser = argparse.ArgumentParser()
    parser.add_argument("--java-home", type=Path, required=True)
    parser.add_argument("--maven", default="mvn.cmd" if os.name == "nt" else "mvn")
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--models", type=Path)
    parser.add_argument("--registered-runtime", type=Path)
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-smoke", action="store_true")
    args = parser.parse_args()

    work_parent = (
        args.work_dir or (source_rebuild.parents[1] / "work/source-rebuild")
    ).resolve()
    work_parent.mkdir(parents=True, exist_ok=True)
    archive = (args.archive or (work_parent / "downloads/mtsa-v1.1.0.tar.gz")).resolve()
    download(
        str(upstream["archive_url"]),
        archive,
        str(upstream["archive_sha256"]),
        int(upstream["archive_size_bytes"]),
    )
    run_root = Path(tempfile.mkdtemp(prefix="build-", dir=work_parent))
    safe_extract(archive, run_root)
    extracted = run_root / "mtsa-v1.1.0"
    project = extracted / "maven-root/mtsa"
    if not project.is_dir():
        raise RebuildError("pinned archive has an unexpected layout")
    apply_overlay(source_rebuild, extracted, manifest)
    verify_selective_implementations_absent(project)

    models = locate_models(source_rebuild, args.models.resolve() if args.models else None)
    staged_models = extracted / "Implementation/Experiment/Models"
    staged_models.mkdir(parents=True, exist_ok=True)
    fixed_model_sha256 = {}
    for name in FIXED_MODELS:
        source_model = models / name
        source_sha256 = sha256_file(source_model)
        if source_sha256 != FIXED_MODEL_SHA256[name]:
            raise RebuildError("registered fixed-model SHA-256 mismatch: " + name)
        staged_model = staged_models / name
        shutil.copyfile(source_model, staged_model)
        if sha256_file(staged_model) != source_sha256:
            raise RebuildError("fixed model changed while staging: " + name)
        fixed_model_sha256[name] = source_sha256

    java_home = args.java_home.resolve()
    env = java_environment(java_home, args.maven)
    run(
        [
            args.maven,
            "-q",
            "-Djava.awt.headless=true",
            "-Djacoco.skip=true",
            "-DskipTests",
            "-Denv.maxmem=4g",
            "clean",
            "package",
        ],
        cwd=project,
        env=env,
    )
    jar = project / "target/mtsa-1.0-SNAPSHOT.jar"
    if not jar.is_file():
        raise RebuildError("Maven did not produce the expected JAR")
    verify_selective_implementations_absent(project, jar)

    tests = None
    if not args.skip_tests:
        run(
            [
                args.maven,
                "-q",
                "-Djava.awt.headless=true",
                "-Djacoco.skip=true",
                "-Dfork.number=0",
                "-Dthread.count=1",
                "-Dparallel=none",
                "-Denv.maxmem=4g",
                "-Dmtsa.revised.otf.integration=true",
                "-Dtest=" + ",".join(TARGETED_TESTS),
                "test",
            ],
            cwd=project,
            env=env,
        )
        tests = count_tests(project / "target/surefire-reports")
        if tests != (101, 0, 0, 0):
            raise RebuildError("targeted test totals are not 101/0/0/0: " + repr(tests))

    smoke = None
    native_factorization_smoke = None
    if not args.skip_smoke:
        output = run_root / "smoke-output.txt"
        transitions = run_root / "smoke-transitions.txt"
        java = java_home / ("bin/java.exe" if os.name == "nt" else "bin/java")
        run(
            [
                str(java),
                "-Djava.awt.headless=true",
                "-Xmx2g",
                "-cp",
                str(jar),
                "ltsa.updatingControllers.cli.SingleCompositionRunner",
                "--lts",
                str(staged_models / "GSM_FG.lts"),
                "--target",
                "UPDATE_CONTROLLER_OTF_FG",
                "--output",
                str(output),
                "--transitions",
                str(transitions),
                "--transition-output",
                "summary",
            ],
            cwd=project,
            env=env,
        )
        text = output.read_text(encoding="utf-8")
        csv_index = text.find("EVALUATION DATA CSV")
        summary_index = text.find("EVALUATION SUMMARY")
        if "Revised OTF-DUCS result: WINNING" not in text or not (0 <= csv_index < summary_index):
            raise RebuildError("CLI smoke output does not satisfy the registered contract")
        smoke = "PASS"

        native_bundle = run_root / "native-factorization-smoke.json"
        run(
            [
                str(java),
                "-Djava.awt.headless=true",
                "-Xmx6g",
                "-cp",
                str(jar),
                "ltsa.updatingControllers.cli.NativePartitionRunner",
                "--lts",
                str(staged_models / "ProductionCell_Arms=2_FG.lts"),
                "--definition",
                "UpdCont_OTF_FG",
                "--output",
                str(native_bundle),
            ],
            cwd=project,
            env=env,
        )
        native = json.loads(native_bundle.read_text(encoding="utf-8"))
        if not (
            native.get("schema_version") == "fg-ducs-native-tier-a-result-v4"
            and native.get("factor_status") == "NONTRIVIAL_SOURCE_NATIVE"
            and native.get("solve_status") == "PRODUCER_VERIFIED_REFINED_WIN"
            and native.get("component_partition") == [[0], [1]]
            and native.get("terminal_product_verified") is True
            and native.get("global_mixed_game_materialized") is False
            and native.get("global_mixed_state_count") == 0
            and native.get("global_mixed_post_query_count") == 0
        ):
            raise RebuildError("native factorization smoke does not satisfy the registered boundary")
        structural_checker = source_rebuild.parent / "analysis/check_native_refined_bundle.py"
        checked = run(
            [sys.executable, "-I", "-S", "-B", str(structural_checker), str(native_bundle)],
            cwd=source_rebuild.parent,
            capture=True,
        )
        structural_report = json.loads(checked.stdout.decode("utf-8"))
        if structural_report.get("solve_status") != "STRUCTURALLY_CHECKED_PRODUCER_WITNESS":
            raise RebuildError("native factorization structural smoke differs")
        native_factorization_smoke = {
            "status": "PASS",
            "source": "ProductionCell_Arms=2_FG.lts",
            "definition": "UpdCont_OTF_FG",
            "factor_status": native["factor_status"],
            "solve_status": native["solve_status"],
            "partition": native["component_partition"],
            "global_mixed_state_count": native["global_mixed_state_count"],
            "global_mixed_post_query_count": native["global_mixed_post_query_count"],
            "bundle_sha256": sha256_file(native_bundle),
            "structural_report": structural_report,
        }

    class_binding = None
    if args.registered_runtime is not None:
        class_binding = compare_registered_runtime(
            java_home, jar, args.registered_runtime.resolve()
        )

    attestation = {
        "schema_version": "fg-ducs-source-rebuild-result-v1",
        "source_root": str(project),
        "built_jar": str(jar),
        "built_jar_sha256": sha256_file(jar),
        "fixed_model_sha256": fixed_model_sha256,
        "selective_implementation_audit": {
            "forbidden_class_entries_absent": len(FORBIDDEN_SELECTIVE_CLASSES),
            "forbidden_source_files_absent": len(FORBIDDEN_SELECTIVE_SOURCES),
        },
        "targeted_tests": tests,
        "smoke": smoke,
        "native_factorization_smoke": native_factorization_smoke,
        "registered_runtime_comparison": class_binding,
    }
    result = run_root / "SOURCE_REBUILD_RESULT.json"
    result.write_text(json.dumps(attestation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(attestation, indent=2, sort_keys=True))
    print("Source rebuild completed: " + str(run_root))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RebuildError, subprocess.CalledProcessError) as error:
        print("SOURCE REBUILD FAILED: " + str(error), file=sys.stderr)
        raise SystemExit(2)
