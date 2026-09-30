#!/usr/bin/env python3
"""Create a separately hashed path-redacted copy; never mutate original evidence."""
import argparse,csv,getpass,hashlib,io,json,os,re,socket,sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

E6=Path(__file__).resolve().parents[1]
PROJECT=E6.parents[3]
TEXT_SUFFIXES={'.md','.json','.csv','.tex','.bib','.py','.java','.sh','.ps1','.log','.txt','.svg','.xml','.properties','.yml','.yaml','.toml','.aux','.fls','.fdb_latexmk','.out'}
SKIP_PARTS={'public_exports','__pycache__'}
JAR_SHA='ff1e6b176f004ea85f1e99690a90388a6a4d24f44cd8d8e636fcd9337dcf67d5'
def sha(data):return hashlib.sha256(data).hexdigest()
def transform(value,replacements):
    if isinstance(value,str):
        for old,new in replacements:value=value.replace(old,new)
        return value
    if isinstance(value,list):return [transform(x,replacements) for x in value]
    if isinstance(value,dict):
        result={}
        for k,v in value.items():
            key=transform(k,replacements)
            assert key not in result,'Redaction would collapse distinct JSON keys'
            result[key]=transform(v,replacements)
        return result
    return value
def unique_object(pairs):
    result={}
    for key,value in pairs:
        assert key not in result,'Duplicate JSON keys in source or redacted copy'
        result[key]=value
    return result
def redact(data,replacements):
    for old,new in replacements:data=data.replace(old.encode(),new.encode())
    return data
def check_structure(relative,original,copy,replacements):
    if relative.suffix=='.json':
        assert transform(json.loads(original,object_pairs_hook=unique_object),replacements)==json.loads(copy,object_pairs_hook=unique_object),relative
    elif relative.suffix=='.csv':
        before=list(csv.reader(io.StringIO(original.decode())))
        after=list(csv.reader(io.StringIO(copy.decode())))
        assert transform(before,replacements)==after,relative

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--name',required=True)
    ap.add_argument('--forbidden-name',action='append',default=[])
    a=ap.parse_args();assert re.fullmatch(r'[a-z0-9][a-z0-9_-]*',a.name)
    required=[E6/x/'raw/runner_finished.json' for x in ('rolling/v1','canary/v1','policy/v2','db_rolling/v2','rolling_audit/v1','threads/v1','rolling_scale/v1','canary_controls/v1')]
    assert all(p.exists() for p in required),'Export only after the registered series are terminal'
    assert (E6/'pc2_rolling/v2/build/export_and_tables_ready.json').exists()
    extended=E6/'pc2_rolling/extended_7200'
    if extended.exists():
        assert (extended/'raw/runner_finished.json').exists(),'The authorized PC2 extended series is not terminal'
        assert (extended/'build/final_tables_ready.json').exists(),'Extended PC2 final tables/checks are not ready'
        for job in ('lazy_transfers','direct_full_none'):
            assert any((extended/'raw'/job/name).exists() for name in ('completion.json','not_run.json')),job
        with (extended/'tables/results.csv').open() as f:
            assert all(row['status'] not in ('RUNNING','NOT_STARTED') for row in csv.DictReader(f))
    canonical=[(E6/f/'build/frozen_manifest.json',E6) for f in ('rolling/v1','canary/v1','policy/v2','db_rolling/v2','rolling_audit/v1','threads/v1','rolling_scale/v1','canary_controls/v1')]
    canonical += [(E6/'pc2_rolling/v2/build/frozen_manifest.json',E6/'pc2_rolling'),(E6/'pc2_rolling/validation_export/frozen_manifest.json',E6/'pc2_rolling/validation_export')]
    for manifest_path,base in canonical:
        for name,expected in json.loads(manifest_path.read_text())['files'].items():
            assert sha((base/name).read_bytes())==expected,('Original freeze differs before copy',str(manifest_path.relative_to(E6)),name)
    if extended.exists():
        frozen=json.loads((extended/'build/frozen_manifest.json').read_text())
        assert frozen['jar_sha256']==JAR_SHA
        for key,base in [('files',extended),('original_pc2_files',E6/'pc2_rolling')]:
            for name,expected in frozen[key].items():
                assert sha((base/name).read_bytes())==expected,('Extended PC2 freeze differs before copy',key,name)
    xeon=E6/'pc2_rolling/xeon_20260929_2344'
    if xeon.exists():
        arrival=json.loads((xeon/'validation/arrival_audit.json').read_text())
        assert arrival['status'] in ('PASS','PASS_WITH_PROVENANCE_LIMITATIONS')
        received=json.loads((xeon/'validation/raw_sha256_manifest.json').read_text())
        for name,expected in received['files'].items():
            assert sha((xeon/name).read_bytes())==expected,('Received Xeon raw changed',name)
    target=E6/'public_exports'/a.name
    assert not target.exists(),'Create-only export; choose another snapshot name'
    replacements=[(str(E6),'${E6_ROOT}'),(str(PROJECT),'${PROJECT_ROOT}'),(str(Path.home()),'${HOME}')]
    # Replace an actual local hostname only if it occurs; never alter cited author names.
    hostname=socket.gethostname()
    if hostname and hostname.lower() not in ('localhost','unknown','mac'):
        replacements.append((hostname,'${HOSTNAME}'))
    names=[getpass.getuser()]+a.forbidden_name
    patterns=[re.compile(rb'(?<![A-Za-z0-9])'+re.escape(n.encode())+rb'(?![A-Za-z0-9])',re.I) for n in names if n]
    candidates=[];excluded=[]
    for path in sorted(E6.rglob('*')):
        if not path.is_file():continue
        rel=path.relative_to(E6)
        if set(rel.parts).intersection(SKIP_PARTS) or path.name in ('.DS_Store','jvm.lock') or path.suffix=='.pyc' or (path.suffix=='.tmp' and 'raw' not in rel.parts):
            excluded.append(str(rel));continue
        # Local identity-pattern hashes can themselves link an anonymous copy to a person.
        # These are privacy diagnostics, not experiment outcomes or failed model versions.
        if rel.parent==Path('integration') and path.name.startswith(('anonymity_scan_','anonymity_review_')):
            excluded.append(str(rel));continue
        assert path.suffix!='.jar','The existing solver JAR is referenced by digest, not redistributed here'
        assert not path.is_symlink(),('Unreviewed symlink',rel)
        candidates.append((path,rel))
    initial_file_set={str(x.relative_to(E6)) for x in E6.rglob('*') if x.is_file() and 'public_exports' not in x.relative_to(E6).parts}
    pdf_review=json.loads((E6/'integration/pdf_anonymity_review.json').read_text())
    assert pdf_review['status']=='PASS' and pdf_review['identity_pattern_count']==len(names)
    reviewed_pdfs={x['path']:x for x in pdf_review['files']}
    prepared=[];findings=[]
    for path,rel in candidates:
        before_stat=path.stat();raw=path.read_bytes();after_stat=path.stat()
        assert (before_stat.st_size,before_stat.st_mtime_ns)==(after_stat.st_size,after_stat.st_mtime_ns),('Concurrent write',rel)
        copied=redact(raw,replacements) if path.suffix in TEXT_SUFFIXES else raw
        if copied!=raw:check_structure(rel,raw,copied,replacements)
        hits=[(i,m.start(),m.end()) for i,patt in enumerate(patterns) for m in patt.finditer(copied)]
        if path.suffix=='.pdf':
            review=reviewed_pdfs[str(rel)]
            assert review['sha256']==sha(raw) and copied==raw and not review['decoded_identity_hits']
            approved={(x['pattern_index'],x['start'],x['end']) for x in review['raw_stream_coincidences']}
            if set(hits)!=approved:findings.append(str(rel)+' [PDF review differs]')
        elif hits:findings.append(str(rel))
        if str(Path.home()).encode() in copied:findings.append(str(rel)+' [home path]')
        prepared.append((path,rel,raw,copied))
    assert not findings,('Unredacted identity requires review; no export created',findings)
    assert initial_file_set=={str(x.relative_to(E6)) for x in E6.rglob('*') if x.is_file() and 'public_exports' not in x.relative_to(E6).parts},'Concurrent source inventory change before export'
    target.mkdir(parents=True)
    entries=[]
    for path,rel,raw,copied in prepared:
        assert path.read_bytes()==raw,('Source changed before copy',rel)
        dest=target/'e6'/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(copied)
        entries.append(dict(path='e6/'+str(rel),original_sha256=sha(raw),public_sha256=sha(copied),bytes=len(copied),path_redacted=copied!=raw))
    assert initial_file_set=={str(x.relative_to(E6)) for x in E6.rglob('*') if x.is_file() and 'public_exports' not in x.relative_to(E6).parts},'Concurrent source inventory change during export'
    assert all(path.read_bytes()==raw for path,rel,raw,copied in prepared),'Concurrent source content change during export'
    # All critical model/results/certificates must be byte-identical, not merely numerically equal.
    changed_critical=[e['path'] for e in entries if e['path_redacted'] and ('/inputs/' in e['path'] or Path(e['path']).suffix=='.class' or Path(e['path']).name in ('result.json','certificate.json','certificate_summary.json'))]
    assert not changed_critical,('Critical evidence unexpectedly needed redaction; copy is not publishable',changed_critical)
    manifest=dict(schema='e6-anonymous-copy-v1',created_at=datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),status='PATH_REDACTED_COPY',
      solver_jar_sha256=JAR_SHA,solver_jar_included=False,
      transformation='Literal local E6/project<UPSTREAM_HOME> replacement in text only; JSON/CSV structure checked. All input contracts, result.json and certificate.json files are byte-identical to the originals.',
      provenance_scope='Original completion/freeze digests refer to original bytes. Use original_sha256 to check those references, and public_sha256 to check this copy. This is not a newly measured or newly frozen series.',
      identity_patterns_checked=len(names),pdf_identity_review='e6/integration/pdf_anonymity_review.json',generic_default_hostname_preserved=True,files=entries,
      omitted='Prior public exports, runtime locks, Python bytecode caches, temporary files outside raw, desktop metadata, and local anonymity-scan/review reports containing private identity-pattern hashes. No timeout, failed model version, raw result, or negative/null condition is omitted.',
      excluded_paths=[x for x in excluded if not x.startswith('public_exports/')])
    (target/'PUBLIC_COPY_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (target/'README.md').write_text('''# Anonymous local copy of E6 evidence

This copy redacts local workstation paths and hostname only. Original evidence remains unchanged in the private workspace. No upload or push was performed.

All input contracts, result JSON files, and certificate JSON files are byte-identical to the originals. Full schedules, failed versions, timeout records, and null/negative results are retained. The manifest records both original and public-copy digests for every included file. Old freeze/completion records deliberately retain their original digest references; a redacted invocation or manifest has a different public-copy digest. Do not present the original raw-hash checker as having checked the redacted bytes directly.

Run `python3 e6/integration/verify_anonymous_copy.py .` to validate the copy and its retained raw-hash references. The fixed E1 JAR is not duplicated here; obtain the existing artifact JAR with the manifest's exact SHA-256. Original launchers record the Mac Java path and historical schedule; reproducing new trials requires a fresh campaign rather than reusing raw directories. `${E6_ROOT}`, `${PROJECT_ROOT}`, `${HOME}`, and `${HOSTNAME}` are provenance placeholders, not executable shell commands.

Start with `e6/README.md`, `e6/ME_PACKAGE.md`, `e6/EVIDENCE_LEDGER_APPEND.md`, and `e6/results_index.csv`. The source paths inside preserved reports refer to the original campaign layout. This snapshot does not authorize publication or claim to reproduce a deployed system.

The nine Cell_n rows in the index are labelled `reference_e4`. Their immutable earlier E4 source material is an external dependency at `../e4_2_corrected`, not a newly measured E6 series and not duplicated in this E6-only snapshot. Index source digests identify the referenced E4 summary. PC2's original and extended Mac budgets and the separately received Xeon trials are all retained; terminal status does not turn a timeout into LOSS. The Xeon records omit runtime class hashes and exit codes; distribution-class provenance and native WIN diagnostics are documented separately, without filling missing raw fields.
''')
    print(json.dumps(dict(status=manifest['status'],directory=str(target.relative_to(E6)),files=len(entries),redacted=sum(x['path_redacted'] for x in entries),critical_files_unchanged=True)))
if __name__=='__main__':main()
