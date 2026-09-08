#!/usr/bin/env python3
"""Verify the complete distribution inventory and all recorded hashes."""
import json
from pathlib import Path
from prepare_release import ROOT, digest, inventory


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    manifest = json.loads((ROOT / "RELEASE_MANIFEST.json").read_text())
    expected = {r["path"]: r for r in manifest["files"]}
    require(len(expected) == len(manifest["files"]), "duplicate manifest entries")
    actual = {p.relative_to(ROOT).as_posix(): p for p in inventory()}
    require(set(expected) == set(actual), "release inventory mismatch")
    sums = {}
    for line in (ROOT / "SHA256SUMS").read_text().splitlines():
        h, name = line.split("  ", 1)
        require(name not in sums, "duplicate checksum entry")
        sums[name] = h
    require(set(sums) == set(expected) | {"RELEASE_MANIFEST.json"}, "checksum inventory mismatch")
    for name, row in expected.items():
        path = actual[name]
        require(path.stat().st_size == row["bytes"], "size mismatch: " + name)
        require(digest(path) == row["sha256"] == sums[name], "hash mismatch: " + name)
    require(digest(ROOT / "RELEASE_MANIFEST.json") == sums["RELEASE_MANIFEST.json"],
            "release manifest hash mismatch")
    require(digest(ROOT / "package/MANIFEST.json") == manifest["frozen_package_manifest_sha256"],
            "frozen package manifest mismatch")
    print(json.dumps({"release_verified": True, "files": len(expected) + 2,
                      "scientific_sample_increase": False}))


if __name__ == "__main__":
    main()
