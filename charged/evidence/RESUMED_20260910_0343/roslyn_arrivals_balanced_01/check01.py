from pathlib import Path
import collections,copy,datetime,hashlib,json,math,statistics
D=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(c,m):
 if not c:raise AssertionError(m)
def check(row):
 require(row['status']=='SUCCESS','native status')
 require(row['jobs']==32 and row['requested_writes']==64 and row['actual_writes_total']==64 and row['foreground_publications']==32,'denominators')
 require(row['events']==128 and row['untouched_documents']==4016 and row['source_documents']==4019 and row['linked_documents']==2,'source/event denominators')
 require(row['hook_enabled']==False,'hook must be disabled')
 fg=row['foreground_requests'];bg=row['writer_requests'];pubs=row['publications'];snap={x['snapshot']:x for x in row['retained_snapshots']}
 require(len(fg)==32 and len(bg)==64 and len(pubs)==96 and len(snap)==97,'raw denominators')
 require([x['index'] for x in fg]==list(range(1,33)) and [x['index'] for x in bg]==list(range(1,65)),'request identities')
 require(row['foreground_start_ns']<=fg[0]['invoked_ns'] and row['foreground_end_ns']>=fg[-1]['returned_ns'],'foreground interval')
 require(row['foreground_end_ns']-row['foreground_start_ns']==row['foreground_ns'],'foreground duration')
 for i,x in enumerate(bg):
  require(abs(x['intended_ns']-i*row['period_us']*1000)<=1,'intended arrival')
  require(x['intended_ns']<=x['enqueued_ns']<=x['invoked_ns']<=x['published_ns']<=x['returned_ns'],'background timeline')
  if i:require(bg[i-1]['returned_ns']<=x['invoked_ns'],'FIFO worker')
 for i,x in enumerate(fg):
  require(x['invoked_ns']<=x['published_ns']<=x['returned_ns'],'foreground timeline')
  if i:require(fg[i-1]['returned_ns']<=x['invoked_ns'],'foreground seriality')
 previous=row['initial_snapshot'];f=b=0;last=-10**30;event_total=0;during=0
 require(snap[previous]['foreground']==snap[previous]['background']==0,'initial snapshot')
 for pub in pubs:
  require(pub['old']==previous and pub['new']!=previous,'publication chain')
  require(pub['old_foreground']==f and pub['old_background']==b,'predecessor content')
  require(pub['published_ns']>=last,'publication order');last=pub['published_ns']
  if pub['kind']=='foreground':
   require(pub['documents']==[0,1] and pub['new_foreground']==f+1 and pub['new_background']==b,'foreground transition')
   require(pub['published_ns']==fg[f]['published_ns'],'foreground publication binding');f+=1
  else:
   require(pub['kind']=='background' and pub['documents']==[-1] and pub['new_foreground']==f and pub['new_background']==b+1,'background transition')
   require(pub['published_ns']==bg[b]['published_ns'],'background publication binding');b+=1
   during+=row['foreground_start_ns']<=pub['published_ns']<=row['foreground_end_ns']
  require(snap[pub['old']]['foreground']==pub['old_foreground'] and snap[pub['old']]['background']==pub['old_background'],'old retained snapshot')
  require(snap[pub['new']]['foreground']==f and snap[pub['new']]['background']==b,'new retained snapshot')
  event_total+=len(pub['documents']);previous=pub['new']
 require(previous==row['final_snapshot'] and f==32 and b==64 and event_total==128 and during==row['actual_writes_during_foreground'],'final binding')
 if row['mode']!='baseline':
  c=row['counters'];fail=c['CheapFailures'];inside=c['PreparedInside'];outside=c['PreparedOutside'];q=c['Calls']
  require(q==32+fail and 0<=fail<=during,'call accounting')
  require(0<=inside<=32 and outside>=0,'transformation accounting')
  if row['mode']=='original':require(inside==0 and outside==q and c['Mismatches']==fail,'original accounting')
  else:
   require(fail<=row['r'],'universal call budget')
   if row['mode']=='two':require(outside+inside==q and c['Mismatches']==fail,'two accounting')
   else:require(row['mode']=='three' and outside==q and c['Mismatches']==fail+inside and inside<=min(max(during-row['r'],0),32),'three guarantee/accounting')
 return {'publications':96,'events':128}
def controls(row):
 variants=[]
 def add(name,fn):x=copy.deepcopy(row);fn(x);variants.append((name,x))
 add('publication_predecessor',lambda x:x['publications'][0].__setitem__('old',-1))
 add('linked_atomicity',lambda x:next(p for p in x['publications'] if p['kind']=='foreground').__setitem__('documents',[0]))
 add('writer_publication_binding',lambda x:x['writer_requests'][0].__setitem__('published_ns',-999))
 add('arrival_schedule',lambda x:x['writer_requests'][1].__setitem__('intended_ns',-999))
 add('retained_snapshot',lambda x:x['retained_snapshots'][0].__setitem__('foreground',1))
 add('foreground_interval',lambda x:x.__setitem__('foreground_end_ns',-999))
 add('actual_interference',lambda x:x.__setitem__('actual_writes_during_foreground',999))
 add('call_counter',lambda x:x['counters'].__setitem__('Calls',999))
 out=[]
 for name,x in variants:
  try:check(x);detected=False
  except Exception:detected=True
  out.append({'name':name,'detected':detected})
 return out
def main():
 O=D/'run01';dest=O/'check01';dest.mkdir();order=json.loads((D/'harness01/PROCESS_ORDER.json').read_text());details=[];allrows=[]
 for p in order['processes']:
  label=Path(p['input']).stem;folder=O/label
  planned=[x.split('\t') for x in (D/'harness01'/p['input']).read_text().splitlines()]
  raw=folder/'stdout.jsonl';rows=[json.loads(x) for x in raw.read_text().splitlines()] if raw.exists() else []
  byid={x.get('id'):x for x in rows};require(len(byid)==len(rows),'duplicate raw identity')
  require(all(x.get('id') in {y[0] for y in planned} for x in rows),'unplanned unit')
  for expected in planned:
   row=byid.get(expected[0]);status='INVALID';error='missing raw unit'
   if row:
    try:
     require([str(row[k]) for k in ['id','phase','fork','rep','period_us','mode','r']]==expected,'input identity');check(row);status='PASS';error=''
    except Exception as e:status='FAIL';error=f'{type(e).__name__}: {e}'
    allrows.append(row)
   details.append({'id':expected[0],'status':status,'native_status':row['status'] if row else 'MISSING','error':error})
 candidate=next((x for x in allrows if x['status']=='SUCCESS' and x['mode']=='original'),None);ctrl=controls(candidate) if candidate else []
 receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if len(details)==1728 and all(x['status']=='PASS' for x in details) and ctrl and all(x['detected'] for x in ctrl) else 'FAIL','planned_units':1728,'raw_units':len(allrows),'phase_counts':dict(collections.Counter(x['phase'] for x in allrows)),'native_statuses':dict(collections.Counter(x['status'] for x in allrows)),'checker_statuses':dict(collections.Counter(x['status'] for x in details)),'controls':ctrl,'checker_sha256':sha(Path(__file__)),'raw_sha256':{str(x.relative_to(O)):sha(x) for x in O.glob('p*/stdout.jsonl')}}
 (dest/'DETAILS.json').write_text(json.dumps(details,indent=2)+'\n');(dest/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
 for x in details:
  if x['status']!='PASS':print(json.dumps(x))
if __name__=='__main__':main()
