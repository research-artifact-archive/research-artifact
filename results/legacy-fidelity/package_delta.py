#!/usr/bin/env python3
"""Create only the private legacy-fidelity overlay ZIP; never replace old ZIPs."""
from pathlib import Path
import hashlib,json,zipfile
HERE=Path(__file__).resolve().parent
DELTA=HERE/'bundle_delta'
OUT=HERE.parent/'rq3_xeon/fg-ducs-xeon-campaign-legacy-fidelity.zip'
def main():
    if OUT.exists():raise RuntimeError('New delta ZIP already exists; refusing silent replacement')
    paths=[]
    for p in sorted(DELTA.rglob('*')):
        if not p.is_file():continue
        relative=p.relative_to(DELTA)
        if '__pycache__' in relative.parts or p.suffix=='.pyc' or relative.parts[0] in {'raw','Implementation'}:continue
        # These unmodified files are present in the already installed bundle.
        if relative.as_posix() in {'scripts/process_probe.py','scripts/PortableProcessProbe.java'}:continue
        paths.append(p)
    assert sum(p.suffix=='.lts' for p in paths)==28
    assert {p.name for p in paths if p.suffix=='.json'}=={'legacy_fidelity_published.json','legacy_fidelity_fork.json'}
    with zipfile.ZipFile(OUT,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for p in paths:z.write(p,p.relative_to(DELTA).as_posix())
    with zipfile.ZipFile(OUT) as z:
        assert z.testzip() is None
        for p in paths:
            # Compare every embedded byte to the generated source, not just names.
            assert hashlib.sha256(z.read(p.relative_to(DELTA).as_posix())).digest()==hashlib.sha256(p.read_bytes()).digest(),str(p)
    print(json.dumps(dict(path=str(OUT),bytes=OUT.stat().st_size,files=len(paths),model_files=28,stage1_jobs=42,maximum_jobs=210,zip_verified=True)))
if __name__=='__main__':main()
