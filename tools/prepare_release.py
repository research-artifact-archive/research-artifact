#!/usr/bin/env python3
"""Regenerate the root checksum inventory for the public artifact."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PATH_PARTS = {".git", "backup", "__pycache__", ".DS_Store"}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> int:
    files: list[Path] = []
    for path in sorted(ROOT.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(ROOT)
        if (
            any(part in FORBIDDEN_PATH_PARTS for part in relative.parts)
            or relative.as_posix() == "SHA256SUMS"
        ):
            continue
        if path.is_symlink():
            raise SystemExit(f"symlink is forbidden: {relative.as_posix()}")
        if path.is_file():
            files.append(path)
    lines = [f"{digest(path)}  {path.relative_to(ROOT).as_posix()}" for path in files]
    target = ROOT / "SHA256SUMS"
    temporary = ROOT / "SHA256SUMS.tmp"
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(target)
    print(f"wrote SHA256SUMS for {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
