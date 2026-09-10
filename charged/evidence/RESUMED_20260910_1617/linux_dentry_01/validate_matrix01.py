from pathlib import Path
from collections import defaultdict, Counter
import json, re, hashlib, datetime
D=Path(__file__).resolve().parent
inp=json.loads((D/'INPUTS01.json').read_text())
raw=(D/'KERNEL_MATRIX01.test.log').read_text()
records=defaultdict(list)
errors=[]
for line_number,line in enumerate(raw.splitlines(),1):
    match=re.search(r'\b(DPMETA|DPROW|DPAUX|DPBODY) (\{.*)$',line)
    if not match:continue
    try: value=json.loads(match.group(2))
    except Exception as exc:
        errors.append(dict(kind='invalid_record',line=line_number,error=str(exc)));continue
    records[match.group(1)].append(value)
def check(condition,kind,**detail):
    if not condition:errors.append(dict(kind=kind,**detail))
def unique(items,kind):
    result={}
    for item in items:
        i=item['id'];check(i not in result,'duplicate',record=kind,id=i);result[i]=item
    return result
rows=unique(records['DPROW'],'DPROW');aux=unique(records['DPAUX'],'DPAUX')
bodies=defaultdict(list)
for b in records['DPBODY']:bodies[b['id']].append(b)
check(len(records['DPMETA'])==1,'metadata_count',count=len(records['DPMETA']))
if records['DPMETA']:
    meta=records['DPMETA'][0]
    check(meta['planned']==1540 and meta['valid']==1536 and meta['controls']==4 and meta['cpus']==2,'metadata',value=meta)
check(set(rows)==set(range(1540)),'denominator',missing=sorted(set(range(1540))-set(rows)),extra=sorted(set(rows)-set(range(1540))))
check(set(aux)==set(rows),'auxiliary_denominator',missing=sorted(set(rows)-set(aux)),extra=sorted(set(aux)-set(rows)))
def fnv(data):
    h=0xcbf29ce484222325
    for byte in data:
        h=((h^byte)*0x100000001b3)&0xffffffffffffffff
    return h
joined=[]
for spec in inp['rows']:
    i=spec['id'];r=rows.get(i);a=aux.get(i)
    if not r or not a:continue
    check(r['status']==('CONTROL_DETECTED' if spec['control'] else 'SUCCESS'),'row_status',id=i,status=r['status'])
    if r['status'] in ['NOT_EXECUTED','SETUP_ERROR','ALLOCATION_ERROR']:continue
    f=inp['families'][spec['family']];p=inp['profiles'][spec['profile']];cap=spec['cap'];policy=spec['policy']
    bs=bodies.get(i,[])
    check([b['body'] for b in bs]==list(range(r['bodies'])),'body_denominator',id=i)
    sums=defaultdict(int)
    local=True
    for b in bs:
        cost=1+b['visits']+b['copy']+b['fill']+b['chars']
        byte=b['copy']+b['fill']+b['chars']
        check(cost==b['T'],'body_cost',id=i,body=b['body'])
        local &= b['visits']<=cap and b['copy']+b['chars']<=cap-1 and b['fill']<=cap-1 and cost<=3*(cap-1)+2
        sums['T']+=cost;sums['byte_demand']+=byte;sums['visits']+=b['visits']
        if b['protected']:
            sums['L_T']+=cost;sums['protected_byte_demand']+=byte;sums['protected_visits']+=b['visits']
    for k in ['T','L_T','byte_demand','protected_byte_demand','visits','protected_visits']:
        check(r[k]==sums[k],'resource_sum',id=i,field=k,actual=r[k],calculated=sums[k])
    check(bool(r['per_body_ok'])==bool(local),'local_bound_flag',id=i)
    expected_mid=bool(p['mid'] and f['components'] and policy in [0,1])
    expected_end=p['gates']&1
    if policy in [0,1] and (expected_mid or expected_end):expected_end|=p['gates']&2
    check(r['issued_mid']==expected_mid and r['issued_end']==expected_end,'schedule',id=i)
    expected_B=int(expected_mid)+bin(expected_end).count('1')
    check(r['B']==expected_B,'actual_B',id=i,actual=r['B'],expected=expected_B)
    check(a['pre_writes']==p['pre'] and r['writes_total']==p['pre']+expected_B+p['late'],'write_scope',id=i)
    kind=1 if not f['components'] else p['kind']
    if kind==2 and len(f['components'])<2:kind=0
    names=f['components']
    if (p['pre']+expected_B)%2 and kind!=1:
        names=[f['alternate']]+(names[-1:] if kind==2 else [])
    path=('/'+'/'.join(names)).encode()
    expected_error=-36 if len(path)+1>cap else 0
    eh=0 if expected_error else fnv(path)
    check(r['expected_length']==len(path) and r['expected_error']==expected_error and r['expected_hash']==eh,'fixture_oracle',id=i,path=path.decode(),reported=r['expected_hash'],calculated=eh)
    output=(r['error']==expected_error and (expected_error!=0 or (r['output_hash']==eh and r['offset']==cap-1-len(path))))
    check(bool(r['output_ok'])==output,'output_flag',id=i)
    ceiling=3*(cap-1)+2
    if policy==1:
        limit=1+min(r['B'],2)
        bound=r['Q']<=2 and r['bodies']<=limit and r['T']<=limit*ceiling and r['L_T']<=(ceiling if r['B']>=2 else 0)
    elif policy==0:
        bound=r['Q']<=2 and r['bodies']<=1+min(r['B'],1) and r['L_T']<=(ceiling if r['B'] else 0)
    elif policy==2:bound=r['Q']==1 and r['bodies']==1
    else:bound=r['Q']<=2 and a['snapshot_takes']==a['snapshot_releases'] and a['ref_inc']==a['ref_dec']
    check(bool(r['bounds_ok'])==bound,'global_bound_flag',id=i)
    check(bool(r['control_detected'])==bool(not output or not bound or not local),'detection_flag',id=i)
    check(all(r[k]==1 for k in ['reference_ok','canary_ok','persistent']) and r['internal_error']==0,'health_flags',id=i)
    if not spec['control']:
        check(output and bound and local,'valid_obligation',id=i)
    else:
        check(not output or not bound or not local,'undetected_control',id=i)
    joined.append(dict(input=spec,family=f['name'],profile=p['name'],policy=inp['policies'][policy],row=r,aux=a,bodies=bs))
warning_patterns=[r'WARNING:',r'BUG:',r'possible circular locking',r'inconsistent lock state',r'sleeping function called',r'suspicious RCU',r'INFO: task .*blocked',r'KASAN:',r'Kernel panic']
warnings=[line for line in raw.splitlines() if any(re.search(p,line,re.I) for p in warning_patterns)]
check(not warnings,'kernel_diagnostics',lines=warnings)
check('ok 1 dpath-retry' in raw,'kunit_completion')
controls=[j for j in joined if j['input']['control']]
check(len(controls)==4,'control_denominator')
for j in controls:
    r=j['row'];mut=j['input']['mutation']
    check((not r['bounds_ok'] and r['output_ok']) if mut==2 else (not r['output_ok']),'control_reason',id=r['id'],mutation=mut)
valid=[j for j in joined if not j['input']['control']]
report=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS' if not errors else 'FAIL',scope='independent record/fixture/resource recomputation of exploratory matrix; not source proof or native performance',planned=1540,recorded=len(rows),valid_rows=len(valid),valid_statuses=dict(Counter(j['row']['status'] for j in valid)),controls=len(controls),control_statuses=dict(Counter(j['row']['status'] for j in controls)),successful_paths=sum(j['row']['error']==0 for j in valid),expected_overflow=sum(j['row']['error']==-36 for j in valid),body_records=len(records['DPBODY']),copy_fault_fill_rows=sum(any(b['fill'] for b in j['bodies']) for j in valid),snapshot_fallback_rows=sum(j['aux']['snapshot_fallback']>0 for j in valid),unrelated_writer_rows=sum(j['row']['B']>0 and j['profile']=='unrelated' for j in valid),kernel_diagnostics=warnings,errors=errors,max_record_length=max(len(x) for x in raw.splitlines() if re.search(r'\bDP(ROW|AUX|BODY|META) ',x)),source_files=[dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in [D/'INPUTS01.json',D/'KERNEL_MATRIX01.test.log',Path(__file__).resolve()]])
with(D/'MATRIX_VALIDATION01.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
with(D/'MATRIX_JOINED01.json').open('x') as f:json.dump(joined,f,indent=2);f.write('\n')
print(json.dumps(report,indent=2))
raise SystemExit(bool(errors))
