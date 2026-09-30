#!/usr/bin/env python3
"""Verify a path-redacted copy without needing its private original paths."""
import argparse,hashlib,json
from pathlib import Path
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);a=ap.parse_args();root=a.directory.resolve()
    manifest=json.loads((root/'PUBLIC_COPY_MANIFEST.json').read_text(encoding='utf-8-sig'));assert manifest['schema']=='e6-anonymous-copy-v1'
    entries={x['path']:x for x in manifest['files']};assert len(entries)==len(manifest['files'])
    actual={str(p.relative_to(root)) for p in (root/'e6').rglob('*') if p.is_file()}
    assert actual==set(entries),'Listed/public file sets differ'
    assert {p.name for p in root.iterdir()}=={'e6','README.md','PUBLIC_COPY_MANIFEST.json'},'Unlisted root artifact'
    relationships=0
    for rel,row in entries.items():
        path=root/rel;assert path.resolve().is_relative_to(root) and not path.is_symlink()
        assert path.stat().st_size==row['bytes'] and digest(path)==row['public_sha256'],rel
        assert row['path_redacted']==(row['original_sha256']!=row['public_sha256']),rel
        if '/inputs/' in rel or path.suffix=='.class' or path.name in ('result.json','certificate.json','certificate_summary.json'):assert not row['path_redacted'],rel
        if path.name=='completion.json':
            data=json.loads(path.read_text(encoding='utf-8-sig'))
            for name,expected in data.get('files',{}).items():
                sibling=str(Path(rel).parent/name)
                assert sibling in entries and entries[sibling]['original_sha256']==expected,(rel,name)
                relationships+=1
        if path.name=='result.json':
            data=json.loads(path.read_text(encoding='utf-8-sig'))
            if 'certificate_sha256' in data:
                sibling=str(Path(rel).parent/'certificate.json')
                assert entries[sibling]['original_sha256']==data['certificate_sha256']
                relationships+=1
    frozen_relationships=0
    canonical=[('e6/'+f+'/build/frozen_manifest.json','e6') for f in ('rolling/v1','canary/v1','policy/v2','db_rolling/v2','rolling_audit/v1','threads/v1','rolling_scale/v1','canary_controls/v1')]
    canonical += [('e6/pc2_rolling/v2/build/frozen_manifest.json','e6/pc2_rolling'),('e6/pc2_rolling/validation_export/frozen_manifest.json','e6/pc2_rolling/validation_export')]
    for rel,base in canonical:
        frozen=json.loads((root/rel).read_text(encoding='utf-8-sig'))
        for name,expected in frozen['files'].items():
            target=str(Path(base)/name)
            assert target in entries and entries[target]['original_sha256']==expected,(rel,name,'frozen original digest differs')
            frozen_relationships+=1
    extension='e6/pc2_rolling/extended_7200/build/frozen_manifest.json'
    if extension in entries:
        frozen=json.loads((root/extension).read_text(encoding='utf-8-sig'))
        assert frozen['jar_sha256']==manifest['solver_jar_sha256']
        for key,base in [('files','e6/pc2_rolling/extended_7200'),('original_pc2_files','e6/pc2_rolling')]:
            for name,expected in frozen[key].items():
                target=str(Path(base)/name)
                assert target in entries and entries[target]['original_sha256']==expected,(extension,key,name,'frozen original digest differs')
                frozen_relationships+=1
    received_rel='e6/pc2_rolling/xeon_20260929_2344/validation/raw_sha256_manifest.json'
    received_relationships=0
    if received_rel in entries:
        received=json.loads((root/received_rel).read_text(encoding='utf-8-sig'))
        for name,expected in received['files'].items():
            target=str(Path('e6/pc2_rolling/xeon_20260929_2344')/name)
            assert target in entries and entries[target]['original_sha256']==expected,(received_rel,name)
            received_relationships+=1
    print(json.dumps(dict(status='PASS',files=len(entries),original_digest_relationships=relationships,
      canonical_frozen_file_relationships=frozen_relationships,
      received_xeon_raw_relationships=received_relationships,
      scope='Exact public file set and byte hashes, preserved original completion/certificate digest references, and canonical family/PC2-export freeze references. Historical superseded freeze records are retained but are not asserted to bind current paths. This is provenance verification, not another solver run.')))
if __name__=='__main__':main()
