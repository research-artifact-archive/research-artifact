#!/usr/bin/env python3
"""Fetch verified binaries into a package copy; never publish or replace a different binary."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import tempfile
import urllib.request
from pathlib import Path

MAVEN = Path('Implementation/Source Code/maven-root')
ASSETS = {
    'mtsa': {
        'filename': 'mtsa-1.0-SNAPSHOT.jar',
        'bytes': 698961879,
        'sha256': 'fbdc25f58d5441ed906d408a94b7414c9d9c3ed35e2ebce22d9751729967ba07',
        'destinations': [MAVEN / 'mtsa/target/mtsa-1.0-SNAPSHOT.jar'],
    },
    'synoptic': {
        'filename': 'synoptic-1.0.jar',
        'bytes': 109442641,
        'sha256': '21d8611a1f07ae744b436f7e7228d2233896f79b3568a42c96f2886f2eb59f69',
        'destinations': [MAVEN / 'mtsa/lib/synoptic/synoptic/1.0/synoptic-1.0.jar',
                         MAVEN / 'locallib/synoptic.jar'],
        'upstream': 'https://git.exactas.uba.ar/lafhis/mtsa/-/raw/d10ba71f092dc9645a80d2752bd089691f158156/maven-root/mtsa/lib/synoptic/synoptic/1.0/synoptic-1.0.jar',
    },
}
# Exact upstream local dependencies. These are obtained directly, not republished.
ASSETS['local_1'] = {'filename': 'classes.jar',
 'bytes': 844395,
 'sha256': 'd6c47472c91540ef9c704ede7e56f7a76191f46e5b3a6c10931cdd9449ebeb6f',
 'upstream': 'https://git.exactas.uba.ar/lafhis/mtsa/-/raw/d10ba71f092dc9645a80d2752bd089691f158156/maven-root/locallib/classes.jar'}
ASSETS['local_1']['destinations'] = [MAVEN / p for p in ['locallib/classes.jar', 'mtsa/lib/lejos/nxt/1.0/nxt-1.0.jar']]
ASSETS['local_2'] = {'filename': 'com.microsoft.z3.jar',
 'bytes': 134028,
 'sha256': 'fe6211caef2d29a932a8660892dcfa8ad4731021c689d39ba2b789cbf3095866',
 'upstream': 'https://git.exactas.uba.ar/lafhis/mtsa/-/raw/d10ba71f092dc9645a80d2752bd089691f158156/maven-root/locallib/com.microsoft.z3.jar'}
ASSETS['local_2']['destinations'] = [MAVEN / p for p in ['locallib/com.microsoft.z3.jar', 'mtsa/lib/com/microsoft/z3/1.0/z3-1.0.jar']]
ASSETS['local_3'] = {'filename': 'ev3classes.jar',
 'bytes': 846515,
 'sha256': '61c58309499c6827357f2060c5ea1862a8fe0f358bfceda7acbf7ad8fa28b653',
 'upstream': 'https://git.exactas.uba.ar/lafhis/mtsa/-/raw/d10ba71f092dc9645a80d2752bd089691f158156/maven-root/locallib/ev3classes.jar'}
ASSETS['local_3']['destinations'] = [MAVEN / p for p in ['locallib/ev3classes.jar', 'mtsa/lib/ev3classes/ev3classes/0.1/ev3classes-0.1.jar']]
ASSETS['local_4'] = {'filename': 'jargs.jar',
 'bytes': 11238,
 'sha256': '61f9ef3ee41b96fddc104ee0e2b247679d5e8cf4f3ab06d60e06516eb7afeb15',
 'upstream': 'https://git.exactas.uba.ar/lafhis/mtsa/-/raw/d10ba71f092dc9645a80d2752bd089691f158156/maven-root/locallib/jargs.jar'}
ASSETS['local_4']['destinations'] = [MAVEN / p for p in ['locallib/jargs.jar', 'mtsa/lib/jargs/jargs/1.0/jargs-1.0.jar']]
ASSETS['local_5'] = {'filename': 'javacv.jar',
 'bytes': 1093839,
 'sha256': 'dbffbf559f8bde4b8893c8a89bbea1aa1939799eb9ffde02acb23a16fbda5053',
 'upstream': 'https://git.exactas.uba.ar/lafhis/mtsa/-/raw/d10ba71f092dc9645a80d2752bd089691f158156/maven-root/locallib/javacv.jar'}
ASSETS['local_5']['destinations'] = [MAVEN / p for p in ['locallib/javacv.jar', 'mtsa/lib/javacv/javacv/1.0/javacv-1.0.jar']]
ASSETS['local_6'] = {'filename': 'jgraphx.jar',
 'bytes': 623397,
 'sha256': '52864848346f8ab3cd20e3c6dfdb961a60d8f741f6646ccdf3dd65506a63171a',
 'upstream': 'https://git.exactas.uba.ar/lafhis/mtsa/-/raw/d10ba71f092dc9645a80d2752bd089691f158156/maven-root/locallib/jgraphx.jar'}
ASSETS['local_6']['destinations'] = [MAVEN / p for p in ['locallib/jgraphx.jar', 'mtsa/lib/jgraphx/jgraphx/0.1/jgraphx-0.1.jar']]
ASSETS['local_7'] = {'filename': 'pccomm.jar',
 'bytes': 412476,
 'sha256': 'ec919e4fb24d21f68c2fc1bca42d44f0d51a306cade06f36ed74f96fd679b7b5',
 'upstream': 'https://git.exactas.uba.ar/lafhis/mtsa/-/raw/d10ba71f092dc9645a80d2752bd089691f158156/maven-root/locallib/pccomm.jar'}
ASSETS['local_7']['destinations'] = [MAVEN / p for p in ['locallib/pccomm.jar', 'mtsa/lib/pccomm/pccomm/0.1/pccomm-0.1.jar']]
ASSETS['local_8'] = {'filename': 'scenebeans.jar',
 'bytes': 193167,
 'sha256': '9c0d4bd6654baf32043b84114a587ff56fe8122cbac52d49f381ab44f21d71ac',
 'upstream': 'https://git.exactas.uba.ar/lafhis/mtsa/-/raw/d10ba71f092dc9645a80d2752bd089691f158156/maven-root/locallib/scenebeans.jar'}
ASSETS['local_8']['destinations'] = [MAVEN / p for p in ['locallib/scenebeans.jar']]
ASSETS['local_9'] = {'filename': 'yadrone_032.jar',
 'bytes': 551998,
 'sha256': '7ff37d30df93c4e0dcbd7808cd6ca8cfc73cfbeb20d9a25fe9d3d6ea152a57f3',
 'upstream': 'https://git.exactas.uba.ar/lafhis/mtsa/-/raw/d10ba71f092dc9645a80d2752bd089691f158156/maven-root/locallib/yadrone_032.jar'}
ASSETS['local_9']['destinations'] = [MAVEN / p for p in ['locallib/yadrone_032.jar', 'mtsa/lib/jadrone/jadrone/0.32/jadrone-0.32.jar']]
ASSETS['local_10'] = {'filename': 'SceneBeans-1.0.0.jar',
 'bytes': 221453,
 'sha256': '71dba7dccc453c6f2975296d6ad79ccd6718b941de4991d27993db33ca95ee31',
 'upstream': 'https://git.exactas.uba.ar/lafhis/mtsa/-/raw/d10ba71f092dc9645a80d2752bd089691f158156/maven-root/mtsa/lib/uk/ac/ic/SceneBeans/1.0.0/SceneBeans-1.0.0.jar'}
ASSETS['local_10']['destinations'] = [MAVEN / p for p in ['mtsa/lib/uk/ac/ic/SceneBeans/1.0.0/SceneBeans-1.0.0.jar']]

def verify(path: Path, asset: dict) -> None:
    if path.stat().st_size != asset['bytes']:
        raise ValueError('Unexpected binary size: ' + str(path))
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    if digest.hexdigest() != asset['sha256']:
        raise ValueError('SHA-256 mismatch: ' + str(path))


def install(source: Path, root: Path, asset: dict) -> None:
    # Check every existing destination before changing any destination.
    verify(source, asset)
    destinations = [root / relative for relative in asset['destinations']]
    for target in destinations:
        if target.exists():
            verify(target, asset)
    for target in destinations:
        if target.exists():
            print('Already verified:', target.relative_to(root))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix='.part', delete=False) as out:
            temporary = Path(out.name)
        try:
            shutil.copyfile(source, temporary)
            verify(temporary, asset)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        print('Installed verified binary:', target.relative_to(root))


def restore_metadata(root: Path) -> None:
    manifest = root / 'dependency-metadata/files.json'
    if not manifest.exists():
        return  # Original local layout already contains the metadata.
    for row in json.loads(manifest.read_text()):
        relative = Path(row['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe metadata destination')
        source = manifest.parent / row['file']
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != row['sha256']:
            raise ValueError('Dependency metadata hash mismatch')
        target = root / relative
        if target.exists():
            if target.read_bytes() != data:
                raise ValueError('Different existing metadata: '+str(relative))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asset', choices=[*ASSETS, 'dependencies'], required=True)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    sources = parser.add_mutually_exclusive_group()
    sources.add_argument('--source-file', type=Path, help='Import a lawfully obtained exact binary')
    sources.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    if args.asset == 'dependencies' and args.source_file:
        parser.error('Use individual --asset names with --source-file')
    root = args.root.resolve()
    if not args.verify_only:restore_metadata(root)
    names = [name for name in ASSETS if name != 'mtsa'] if args.asset == 'dependencies' else [args.asset]
    for name in names:
        asset = ASSETS[name]
        if args.verify_only:
            for relative in asset['destinations']:
                verify(root / relative, asset)
            print('PASS:', name, asset['sha256'])
            continue
        if args.source_file:
            install(args.source_file.resolve(), root, asset)
            continue
        if 'upstream' in asset:
            url = asset['upstream']
        else:
            parser.error('The shaded MTSA JAR is not distributed: build the included sources or import an existing exact --source-file; see README and NOTICE')
        # Upstream acquisition establishes file identity, not redistribution permission.
        with tempfile.TemporaryDirectory(prefix='fgducs-asset-') as directory:
            source = Path(directory) / asset['filename']
            request = urllib.request.Request(url, headers={'User-Agent': 'FG-DUCS-replication'})
            with urllib.request.urlopen(request, timeout=180) as response, source.open('wb') as out:
                shutil.copyfileobj(response, out, length=1024 * 1024)
            install(source, root, asset)


if __name__ == '__main__':
    main()
