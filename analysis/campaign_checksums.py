#!/usr/bin/env python3
"""Write or verify deterministic SHA-256 checksums for a campaign folder."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import List, Sequence, Tuple


CHECKSUM_NAME = "SHA256SUMS"
READY_NAME = "READY_TO_COPY.txt"


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    return parser.parse_args(arguments)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def campaign_files(campaign: Path) -> List[Path]:
    files: List[Path] = []
    for path in campaign.rglob("*"):
        if path.is_symlink():
            raise ValueError("campaign contains a symlink: " + str(path))
        if not path.is_file():
            continue
        if path.parent == campaign and path.name in {
                CHECKSUM_NAME, CHECKSUM_NAME + ".tmp", READY_NAME}:
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(campaign).as_posix())


def records(campaign: Path) -> List[Tuple[str, str]]:
    return [
        (sha256_file(path), path.relative_to(campaign).as_posix())
        for path in campaign_files(campaign)
    ]


def write_checksums(campaign: Path) -> int:
    rows = records(campaign)
    if not rows:
        raise ValueError("campaign contains no files")
    destination = campaign / CHECKSUM_NAME
    temporary = campaign / (CHECKSUM_NAME + ".tmp")
    temporary.write_text(
        "".join("%s  %s\n" % row for row in rows),
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(destination)
    return len(rows)


def parsed_checksums(path: Path) -> List[Tuple[str, str]]:
    if not path.is_file() or path.is_symlink():
        raise ValueError("missing checksum file: " + str(path))
    result: List[Tuple[str, str]] = []
    for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1):
        if "  " not in line:
            raise ValueError("invalid checksum line %d" % number)
        digest, relative = line.split("  ", 1)
        if len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest):
            raise ValueError("invalid digest on line %d" % number)
        if not relative or Path(relative).is_absolute() or "\\" in relative:
            raise ValueError("invalid relative path on line %d" % number)
        result.append((digest, relative))
    if len({relative for _, relative in result}) != len(result):
        raise ValueError("checksum file contains duplicate paths")
    return result


def check_checksums(campaign: Path) -> int:
    expected = parsed_checksums(campaign / CHECKSUM_NAME)
    actual = records(campaign)
    if expected != actual:
        expected_map = dict((relative, digest) for digest, relative in expected)
        actual_map = dict((relative, digest) for digest, relative in actual)
        missing = sorted(set(expected_map).difference(actual_map))
        extra = sorted(set(actual_map).difference(expected_map))
        changed = sorted(
            relative
            for relative in set(expected_map).intersection(actual_map)
            if expected_map[relative] != actual_map[relative]
        )
        raise ValueError(
            "checksum mismatch: missing=%s extra=%s changed=%s"
            % (missing, extra, changed)
        )
    return len(actual)


def main(arguments: Sequence[str] | None = None) -> int:
    args = parse_arguments(arguments)
    campaign = args.campaign.resolve()
    if not campaign.is_dir() or campaign.is_symlink():
        print("CHECKSUM FAIL: unsafe campaign directory: " + str(campaign),
              file=sys.stderr)
        return 2
    try:
        count = (
            write_checksums(campaign)
            if args.write
            else check_checksums(campaign)
        )
    except (OSError, ValueError) as error:
        print("CHECKSUM FAIL: " + str(error), file=sys.stderr)
        return 2
    print("CHECKSUM PASS: files=%d campaign=%s" % (count, campaign))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
