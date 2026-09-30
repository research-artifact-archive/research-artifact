#!/usr/bin/env python3
"""Fixed, serial E4-2 schedule. No retries; no measured value feeds input generation."""
import argparse
import csv
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from zoneinfo import ZoneInfo
HERE=Path(__file__).resolve().parent
JAR=HERE.parents[1]/'ablation_20260928'/'jars'/'e1.jar'
JAVA=Path('/opt/homebrew/Cellar/openjdk@17/17.0.19/libexec/openjdk.jdk/Contents/Home/bin/java')
JAR_SHA='ff1e6b176f004ea85f1e99690a90388a6a4d24f44cd8d8e636fcd9337dcf67d5'
JST=ZoneInfo('Asia/Tokyo')
JOBS=[{'n':n,'merge':merge,'solver':solver} for n in range(2,11) for merge,solver in [('none','lazy'),('transfers','lazy'),('boundaries','lazy'),('both','lazy'),('none','direct_full')]]
FIELDS=['n','merge','solver','status','decision','states_discovered','states_expanded','successor_queries','materialized_transitions','enabled_buckets','worst_completion_rank','losing_region_states','certificate_states','linked_states','preparation_seconds','solver_seconds','checking_and_link_seconds','wall_seconds','exit_code','input_sha256','result_file']
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def now():return datetime.now(JST).isoformat()
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def manifest():
    paths=sorted([*HERE.glob('*.java'),*HERE.glob('*.py'),*HERE.glob('*.sh'),*HERE.glob('inputs/*.json'),*HERE.glob('build/classes/**/*.class')])
    return dict(created_at=now(),jar_sha256=digest(JAR),java_version=subprocess.check_output([str(JAVA),'-version'],stderr=subprocess.STDOUT,text=True).strip(),files={str(p.relative_to(HERE)):digest(p) for p in paths},jobs=JOBS,timeout_seconds=1200,heap='32g',trials=1,timeout_scope='entire JVM: preparation, solver, certificate verification and linking',preflight='n2 fixed primitives/full Post/endpoint/decision/returned-rank comparison',solver_properties={'mtsa.otf.guidedStateLimit':'0','mtsa.otf.guidedQueryLimit':'0','mtsa.otf.lazyControllableBuckets':'true','mtsa.otf.controllableActionOrder':'endpoint_guided'})
def verify_frozen():
    m=json.loads((HERE/'build'/'frozen_manifest.json').read_text())
    assert digest(JAR)==m['jar_sha256']==JAR_SHA
    for relative,expected in m['files'].items():assert digest(HERE/relative)==expected,relative
    assert m['jobs']==JOBS
    return m
def execute(directory,args):
    directory.mkdir(parents=True,exist_ok=False)
    command=[str(JAVA),'-Xmx32g','-cp',str(HERE/'build'/'classes')+os.pathsep+str(JAR),'CellRingDriver',*args,'--output',str(directory/'result.json')]
    meta={'started_at':now(),'command':command,'timeout_seconds':1200,'timeout_scope':'whole JVM','jar_sha256':JAR_SHA}
    save(directory/'invocation.json',meta)
    t=time.monotonic();timed_out=False
    with (directory/'stdout.log').open('x') as stdout,(directory/'stderr.log').open('x') as stderr:
        process=subprocess.Popen(command,stdout=stdout,stderr=stderr,start_new_session=True)
        try:code=process.wait(timeout=1200)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            code=process.returncode
    row={'status':'TO' if timed_out else 'ERROR','wall_seconds':time.monotonic()-t,'exit_code':code}
    if not timed_out and (directory/'result.json').exists():
        data=json.loads((directory/'result.json').read_text());row.update(data)
        row['status']=data.get('decision',data.get('status','ERROR')) if code in (0,2) else 'ERROR'
    row['result_file']=str((directory/'result.json').relative_to(HERE)) if (directory/'result.json').exists() else ''
    save(directory/'completion.json',dict(finished_at=now(),**row));return row

def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['freeze','preflight','run']);args=parser.parse_args()
    if args.phase=='freeze':
        m=manifest();assert m['jar_sha256']==JAR_SHA;save(HERE/'build'/'frozen_manifest.json',m);print('FROZEN '+digest(HERE/'build'/'frozen_manifest.json'));return
    verify_frozen()
    if args.phase=='preflight':
        row=execute(HERE/'raw'/'preflight-n2',['--validate-n2',str(HERE/'inputs'/'cell_n02.json')]);print(json.dumps(row),flush=True)
        if row['status']!='PASS':raise SystemExit(1)
        return
    assert json.loads((HERE/'raw'/'preflight-n2'/'result.json').read_text())['status']=='PASS'
    raw=HERE/'raw'/'series';raw.mkdir(parents=True,exist_ok=False)
    with (HERE/'summary.csv').open('x',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=FIELDS,extrasaction='ignore');writer.writeheader();out.flush()
        for job in JOBS:
            verify_frozen();n,merge,solver=job['n'],job['merge'],job['solver'];input_path=HERE/'inputs'/f'cell_n{n:02d}.json'
            if datetime.now(JST)>=datetime(2026,9,29,17,39,tzinfo=JST):
                row=dict(job,status='NOT_RUN_DEADLINE',input_sha256=digest(input_path));writer.writerow(row);out.flush();print(json.dumps(row),flush=True);continue
            print(json.dumps(dict(event='start',at=now(),**job)),flush=True)
            row=execute(raw/f'n{n:02d}_{merge}_{solver}',['--input',str(input_path),'--merge',merge,'--solver',solver]);row.update(job);row['input_sha256']=digest(input_path)
            writer.writerow(row);out.flush();print(json.dumps(row),flush=True)
if __name__=='__main__':main()
