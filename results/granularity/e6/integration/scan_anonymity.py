#!/usr/bin/env python3
"""Local scan: report locations/categories, never echo personal matched strings."""
import argparse,getpass,hashlib,json,re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
E6=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--forbidden-name',action='append',default=[]);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
 names=[getpass.getuser()]+args.forbidden_name
 patterns=[('workstation_home',re.compile(r'<USER_HOME>/\s"\']+')),('email',re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'))]
 for i,name in enumerate(names):patterns.append(('local_identity_'+str(i),re.compile(r'(?<![A-Za-z0-9])'+re.escape(name)+r'(?![A-Za-z0-9])',re.I)))
 findings=[];scanned=0;skipped=[]
 for path in sorted(E6.rglob('*')):
  if not path.is_file() or path.resolve()==args.output.resolve():continue
  relative=str(path.relative_to(E6))
  if path.suffix.lower() in ('.png','.pdf','.class','.pyc','.jar','.zip','.gz'):continue
  if path.stat().st_size>64*1024*1024:skipped.append(dict(path=relative,reason='larger than 64 MiB; not silently declared clean'));continue
  try:data=path.read_text()
  except UnicodeDecodeError:continue
  scanned+=1
  for line_no,line in enumerate(data.splitlines(),1):
   kinds=[kind for kind,pattern in patterns if pattern.search(line)]
   if not kinds:continue
   metadata=(any(part in ('raw','build','validation','validation_export','remaining_queue','design','design_archive') for part in path.relative_to(E6).parts)
     or path.suffix in ('.log','.json','.aux','.fls','.fdb_latexmk') or path.name=='run_family.py')
   # Input contracts are public candidates even though they are JSON.
   if 'inputs' in path.relative_to(E6).parts:metadata=False
   findings.append(dict(path=relative,line=line_no,categories=kinds,scope='private_execution_metadata_review' if metadata else 'handoff_source_review'))
 report=dict(status='REVIEW_REQUIRED' if findings or skipped else 'PASS',scanned_at=datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),files_scanned=scanned,
  pattern_hashes=[hashlib.sha256(n.encode()).hexdigest() for n in names],findings=findings,skipped=skipped,
  interpretation='Original raw/freeze records are preserved. Path-containing local execution metadata must be redacted in a separate publication copy; no push is authorized. Source URLs to unrelated cited authors require manual citation review, not blanket removal.')
 with args.output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps(dict(status=report['status'],files_scanned=scanned,findings=len(findings),handoff_source_hits=sum(x['scope']=='handoff_source_review' for x in findings),skipped=len(skipped))))
if __name__=='__main__':main()
