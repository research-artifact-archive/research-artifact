from pathlib import Path
import collections,copy,datetime,hashlib,json
import semantic_base_check as base
D=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
require=base.require
def check(row):
 base.check(row,resources=False)
 mode=row['mode'];r=row['r'];require(r>=0,'nonnegative retry cap')
 scope='per-job' if mode.startswith('per-job-') else 'shared' if mode in ['two','three'] else 'unbounded'
 require(row['retry_scope']==scope,'declared retry scope')
 jobs=row['job_counters']
 if mode=='baseline':require(jobs==[] and row['counters']=={},'uninstrumented counts');return
 require(len(jobs)==32 and [x['index'] for x in jobs]==list(range(1,33)),'job identities')
 c=row['counters'];q=c['Calls'];f=c['CheapFailures'];inside=c['PreparedInside'];outside=c['PreparedOutside'];B=row['actual_writes_during_foreground']
 for k in ['Calls','CheapFailures','PreparedInside','PreparedOutside','Mismatches']:require(sum(j[k] for j in jobs)==c[k],'job sum '+k)
 require(q==32+f and 0<=f<=B and 0<=inside<=32,'total count bound')
 two=mode.endswith('two');three=mode.endswith('three');last=r
 for j,request in zip(jobs,row['foreground_requests']):
  bi=sum(request['invoked_ns']<=w['published_ns']<=request['returned_ns'] for w in row['writer_requests'])
  fi=j['CheapFailures'];qi=j['Calls'];li=j['PreparedInside'];oi=j['PreparedOutside']
  require(qi==1+fi and 0<=fi<=bi and 0<=li<=1 and oi>=0,'job counts within actual writes')
  if scope=='per-job':
   require(j['remaining_before']==r and j['remaining_after']==r-fi and fi<=r,'per-job allowance')
   require(li<=int(bi>=(r if two else r+1)),'per-job protection bound')
  elif scope=='shared':
   require(j['remaining_before']==last and j['remaining_after']==last-fi and j['remaining_after']>=0,'shared allowance');last=j['remaining_after']
  if two:require(oi+li==qi and j['Mismatches']==fi,'two counts')
  elif three:require(oi==qi and j['Mismatches']==fi+li,'three counts')
  else:require(mode=='original' and li==0 and oi==qi and j['Mismatches']==fi,'original counts')
 if scope=='shared':
  require(f<=r,'shared call cap')
  if three:require(inside<=min(max(B-r,0),32),'shared protected bound')
 elif scope=='per-job':
  require(f<=32*r,'sum local call caps')
  if two and r:require(inside<=min(B//r,32),'local-two aggregate protection')
  if three:require(inside<=min(B//(r+1),32),'local-three aggregate protection')
def controls(original,local):
 results=base.controls(original)
 for kind in ['job_call','job_identity','retry_remaining','scope']:
  row=copy.deepcopy(local)
  if kind=='job_call':row['job_counters'][0]['Calls']+=1
  elif kind=='job_identity':row['job_counters'][0]['index']=2
  elif kind=='retry_remaining':row['job_counters'][0]['remaining_after']=-1
  else:row['retry_scope']='shared'
  try:check(row);detected=False
  except Exception:detected=True
  results.append(dict(name=kind,detected=detected))
 return results
def main():
 O=D/'run01';dest=O/'check01';dest.mkdir();order=json.loads((D/'harness01/PROCESS_ORDER.json').read_text());details=[];allrows=[];raw_hash={}
 for p in order['processes']:
  label=Path(p['input']).stem;folder=O/label;planned=[x.split('\t') for x in (D/'harness01'/p['input']).read_text().splitlines()]
  raw=folder/'stdout.jsonl'
  try:rows=[json.loads(x) for x in raw.read_text().splitlines()] if raw.exists() else []
  except Exception:rows=[]
  byid={x.get('id'):x for x in rows};require(len(byid)==len(rows),'duplicate raw identity');require(all(x.get('id') in {y[0] for y in planned} for x in rows),'unplanned unit')
  if raw.exists():raw_hash[str(raw.relative_to(O))]=sha(raw)
  for expected in planned:
   row=byid.get(expected[0]);status='INVALID';error='missing raw unit'
   if row:
    try:require([str(row[k]) for k in ['id','phase','fork','rep','period_us','mode','r']]==expected,'input identity');check(row);status='PASS';error=''
    except Exception as e:status='FAIL';error=f'{type(e).__name__}: {e}'
    allrows.append(row)
   details.append(dict(id=expected[0],status=status,native_status=row['status'] if row else 'MISSING',error=error))
 original=next((x for x in allrows if x['status']=='SUCCESS' and x['mode']=='original'),None);local=next((x for x in allrows if x['status']=='SUCCESS' and x['mode']=='per-job-three'),None)
 ctrl=controls(original,local) if original and local else []
 receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS' if len(details)==3072 and all(x['status']=='PASS' for x in details) and len(ctrl)==12 and all(x['detected'] for x in ctrl) else 'FAIL',planned_units=3072,raw_units=len(allrows),phase_counts=dict(collections.Counter(x['phase'] for x in allrows)),native_statuses=dict(collections.Counter(x['status'] for x in allrows)),checker_statuses=dict(collections.Counter(x['status'] for x in details)),controls=ctrl,checker_sha256=sha(Path(__file__)),semantic_base_sha256=sha(D/'semantic_base_check.py'),raw_sha256=raw_hash)
 (dest/'DETAILS.json').write_text(json.dumps(details,indent=2)+'\n');(dest/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
 for x in details:
  if x['status']!='PASS':print(json.dumps(x))
if __name__=='__main__':main()
