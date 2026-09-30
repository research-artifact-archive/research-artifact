#!/usr/bin/env python3
"""Verify the public files and restore a fresh executable research workspace."""
from pathlib import Path
import argparse, hashlib, json, shutil, tarfile, tempfile, gzip
ROOT=Path(__file__).resolve().parents[1]
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def safe(root,rel):
    p=Path(rel)
    if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe relative path: '+str(rel))
    return root/p
def checked(path,row):
    if path.stat().st_size!=row['bytes'] or sha(path)!=row['sha256']:raise ValueError('File digest mismatch: '+str(path))
def materialize(output,source_only=False):
    output=Path(output).resolve()
    if output.exists():raise FileExistsError('Choose a new workspace: '+str(output))
    manifest=json.loads((ROOT/'reproduce/layout.json').read_text())
    output.mkdir(parents=True,exist_ok=False)
    n=0
    for row in manifest['files']:
        if source_only and not (row['workspace'].startswith(('Implementation/Source Code/','dependency-metadata/','Implementation/Experiment/Models/','Implementation/Experiment/FSE2027/scripts/','campaign/')) or row['workspace']=='fetch_assets.py'):continue
        f=safe(ROOT,row['path']);checked(f,row)
        t=safe(output,row['workspace']);t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,t);n+=1
    if not source_only:
        for archive in manifest['archives']:
            with tempfile.TemporaryFile() as joined:
                for part in archive['parts']:
                    f=safe(ROOT,part['path']);checked(f,part)
                    with f.open('rb') as stream:shutil.copyfileobj(stream,joined)
                joined.seek(0)
                expected={r['workspace']:r for r in archive['files']}
                with tarfile.open(fileobj=joined,mode='r:gz') as tf:
                    seen=set()
                    for member in tf:
                        if member.name not in expected or member.name in seen or not member.isfile():raise ValueError('Unexpected archive member: '+member.name)
                        row=expected[member.name];t=safe(output,member.name)
                        if t.exists():raise ValueError('Duplicate workspace path: '+member.name)
                        t.parent.mkdir(parents=True,exist_ok=True)
                        with tf.extractfile(member) as src,t.open('xb') as dst:shutil.copyfileobj(src,dst)
                        checked(t,row);seen.add(member.name);n+=1
                    if seen!=set(expected):raise ValueError('Missing archive members')
        # The original public package losslessly compressed two very large CSVs.
        for f in output.rglob('*.csv.gz'):
            target=f.with_suffix('')
            if target.exists():raise FileExistsError(target)
            with gzip.open(f,'rb') as src,target.open('xb') as dst:shutil.copyfileobj(src,dst)
    if not source_only:
        compatibility={'parts':[dict(name=r['path'],bytes=r['bytes'],sha256=r['sha256']) for a in manifest['archives'] for r in a['parts']], 'files':[dict(path=r['workspace'],bytes=r['bytes'],sha256=r['sha256']) for a in manifest['archives'] for r in a['files']]}
        (output/'result-assets.json').write_text(json.dumps(compatibility,indent=2)+'\n')
    (output/'PUBLIC_WORKSPACE.json').write_text(json.dumps({'schema':'fgducs-workspace-v1','source_only':source_only,'verified_files':n},indent=2)+'\n')
    print(f'PASS: restored {n} verified files to {output}',flush=True)
    return output
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--source-only',action='store_true');a=p.parse_args();materialize(a.output,a.source_only)
