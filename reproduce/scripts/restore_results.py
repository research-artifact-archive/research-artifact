#!/usr/bin/env python3
"""Verify and restore locally downloaded result assets; no network or JVM use."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import tarfile
import tempfile
from pathlib import Path


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def safe_target(root, name):
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name:
        raise ValueError('Unsafe archive path: ' + name)
    target = root / relative
    if target.resolve() != target.absolute():
        raise ValueError('Symlink in archive destination: ' + name)
    return target


def restore(root, assets, verify_only=False):
    root, assets = root.resolve(), assets.resolve()
    manifest = json.loads((root / 'result-assets.json').read_text())
    for part in manifest['parts']:
        path = assets / part['name']
        if path.stat().st_size != part['bytes'] or digest(path) != part['sha256']:
            raise ValueError('Asset identity mismatch: ' + part['name'])
    if verify_only:
        print('PASS: all result asset parts verified')
        return
    expected = {row['path']: row for row in manifest['files']}
    if len(expected) != len(manifest['files']):
        raise ValueError('Duplicate manifest path')
    seen = set()
    with tempfile.TemporaryDirectory(prefix='fgducs-restore-') as temporary:
        combined = Path(temporary) / 'results.tar.gz'
        with combined.open('wb') as out:
            for part in manifest['parts']:
                with (assets / part['name']).open('rb') as source:
                    shutil.copyfileobj(source, out)
        with tarfile.open(combined, 'r|gz') as archive:
            for member in archive:
                if not member.isfile() or member.name not in expected or member.name in seen:
                    raise ValueError('Unexpected archive entry: ' + member.name)
                record = expected[member.name]
                if member.size != record['bytes']:
                    raise ValueError('Archive file size mismatch: ' + member.name)
                target = safe_target(root, member.name)
                staged = Path(temporary) / 'current-file'
                with archive.extractfile(member) as source, staged.open('wb') as out:
                    shutil.copyfileobj(source, out)
                if digest(staged) != record['sha256']:
                    raise ValueError('Archive file digest mismatch: ' + member.name)
                if target.exists():
                    if digest(target) != record['sha256']:
                        raise ValueError('Different existing result preserved: ' + member.name)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open('xb') as out, staged.open('rb') as source:
                        shutil.copyfileobj(source, out)
                seen.add(member.name)
        if seen != set(expected):
            raise ValueError('Archive is missing manifest files')
    print('PASS: restored/verified %d original distribution files; no existing result replaced' % len(seen))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--assets', type=Path, required=True,
                        help='Directory containing every downloaded .partNNN file')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    restore(args.root.resolve(), args.assets.resolve(), args.verify_only)
