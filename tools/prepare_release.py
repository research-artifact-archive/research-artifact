#!/usr/bin/env python3
"""Create deterministic release hashes without editing the frozen package."""
from pathlib import Path
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {"SHA256SUMS", "RELEASE_MANIFEST.json"}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inventory():
    paths = []
    for directory, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__"}
                   and not (Path(directory) == ROOT and d == "work")]
        for name in files:
            path = Path(directory) / name
            relative = path.relative_to(ROOT).as_posix()
            if relative in EXCLUDED or name == ".DS_Store" or name.endswith(".pyc"):
                continue
            if path.is_symlink():
                raise RuntimeError("symlinks are not distributed: " + relative)
            paths.append(path)
    return sorted(paths)


def main():
    files = [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size,
              "sha256": digest(p)} for p in inventory()]
    manifest = {"schema": "anonymous-retry-artifact-release-v1", "files": files,
                "frozen_package_manifest_sha256": digest(ROOT / "package/MANIFEST.json"),
                "scientific_sample_increase": False}
    path = ROOT / "RELEASE_MANIFEST.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    sums = [(r["path"], r["sha256"]) for r in files]
    sums.append((path.name, digest(path)))
    (ROOT / "SHA256SUMS").write_text("".join(f"{h}  {p}\n" for p, h in sorted(sums)))
    print(json.dumps({"release_files": len(files) + 2, "package_manifest":
                      manifest["frozen_package_manifest_sha256"]}))


if __name__ == "__main__":
    main()
