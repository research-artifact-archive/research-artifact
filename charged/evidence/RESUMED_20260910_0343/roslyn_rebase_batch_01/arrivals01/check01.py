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
  require(c['Rebases']>=0 and (row['mode'] in ('rebase','batch') or c['Rebases']==0),'rebase mode binding')
  require(0<=inside<=32 and outside>=0,'transformation accounting')
  if row['mode']=='original':require(inside==0 and outside==q and c['Mismatches']==fail,'original accounting')
  else:
   require(fail<=row['r'],'universal call budget')
   if row['mode']=='two':require(outside+inside==q and c['Mismatches']==fail,'two accounting')
   else:require(row['mode'] in ('three','rebase','batch') and outside==q and c['Mismatches']==fail+inside+c['Rebases'] and inside<=min(max(during-row['r'],0),32),'three guarantee/accounting')
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

def phase_check(row):
 require(row['timing_hook_enabled'] is True and row['hook_enabled'] is False,'nonblocking timing hook/no injection declaration')
 phases=row['observed_phases'];allowed={'kernel_outside_begin','kernel_outside_end','before_lock','lock_enter','kernel_inside_begin','kernel_inside_end','rebase_completed','cheap_failure','return_changed'}
 require(phases and all(p['name'] in allowed for p in phases),'phase alphabet')
 require(all(a['at_ns']<=b['at_ns'] for a,b in zip(phases,phases[1:])),'phase chronology')
 opened=None;intervals=[];inside=None;outside=None
 for p in phases:
  name=p['name'];at=p['at_ns']
  require(row['foreground_start_ns']<=at<=row['foreground_end_ns'],'phase foreground interval')
  if name=='lock_enter':require(opened is None and outside is None,'nested lock observation');opened=at
  elif name in ('cheap_failure','return_changed'):
   require(opened is not None and inside is None,'missing lock entry or open kernel');intervals.append((opened,at));opened=None
  elif name=='kernel_inside_begin':require(opened is not None and inside is None,'inside begin');inside=at
  elif name=='kernel_inside_end':require(opened is not None and inside is not None,'inside end');inside=None
  elif name=='kernel_outside_begin':require(opened is None and outside is None,'outside begin');outside=at
  elif name=='kernel_outside_end':require(opened is None and outside is not None,'outside end');outside=None
  elif name=='rebase_completed':require(opened is not None and inside is None,'rebase phase')
  elif name=='before_lock':require(opened is None and outside is None,'pre-lock phase')
 require(opened is inside is outside is None,'unfinished phase span')
 counts=collections.Counter(p['name'] for p in phases);c=row['counters']
 require(len(intervals)==counts['before_lock']==c['Calls'],'observed call count')
 require(counts['cheap_failure']==c['CheapFailures'] and counts['return_changed']==32,'terminal phase counts')
 require(counts['kernel_inside_begin']==counts['kernel_inside_end']==c['PreparedInside'],'inside phase count')
 require(counts['kernel_outside_begin']==counts['kernel_outside_end']==c['PreparedOutside'],'outside phase count')
 require(counts['rebase_completed']==c['Rebases'],'rebase phase count')
 require(sum(b-a for a,b in intervals)<=row['foreground_ns'],'observed protected span bound')
 return intervals

def main():
 O=D/'run01';dest=O/'check01';dest.mkdir();order=json.loads((D/'harness01/PROCESS_ORDER.json').read_text());details=[];allrows=[];processes=[]
 for p in order['processes']:
  label=Path(p['input']).stem;folder=O/label
  planned=[x.split('\t') for x in (D/'harness01'/p['input']).read_text().splitlines()]
  raw=folder/'stdout.jsonl';rows=[json.loads(x) for x in raw.read_text().splitlines()] if raw.exists() else []
  byid={x.get('id'):x for x in rows};require(len(byid)==len(rows),'duplicate raw identity')
  require(all(x.get('id') in {y[0] for y in planned} for x in rows),'unplanned unit')
  process=read_result=json.loads((folder/'RESULT.json').read_text());processes.append(process['status'])
  if raw.exists():require(sha(raw)==process['stdout_sha256'],'process/raw binding')
  for expected in planned:
   row=byid.get(expected[0]);status='INVALID';error='missing raw unit'
   if row:
    try:
     require([str(row[k]) for k in ['id','phase','fork','rep','period_us','mode','r']]==expected,'input identity');check(row);phase_check(row);status='PASS';error=''
    except Exception as e:status='FAIL';error=f'{type(e).__name__}: {e}'
    allrows.append(row)
   details.append({'id':expected[0],'status':status,'native_status':row['status'] if row else 'MISSING','error':error})
 candidate=next((x for x in allrows if x['status']=='SUCCESS' and x['mode']=='three'),None);ctrl=controls(candidate) if candidate else []
 for name,mode in [('batch_mismatch_partition','batch'),('three_rebase_ineligible','three')]:
  sample=next((x for x in allrows if x['status']=='SUCCESS' and x['mode']==mode),None)
  if sample:
   corrupt=copy.deepcopy(sample);corrupt['counters']['Rebases']+=1
   try:check(corrupt);detected=False
   except Exception:detected=True
   ctrl.append({'name':name,'detected':detected})
 if candidate:
  variants=[]
  for name,mut in [('missing_lock_entry',lambda x:x['observed_phases'].remove(next(p for p in x['observed_phases'] if p['name']=='lock_enter'))),('phase_outside_foreground',lambda x:x['observed_phases'][0].update(at_ns=-999)),('missing_observer_declaration',lambda x:x.update(timing_hook_enabled=False))]:
   corrupt=copy.deepcopy(candidate);mut(corrupt)
   try:phase_check(corrupt);detected=False
   except Exception:detected=True
   ctrl.append({'name':name,'detected':detected})
 good=len(details)==1728 and all(x['status']=='PASS' for x in details) and len(ctrl)==13 and all(x['detected'] for x in ctrl) and len(processes)==36 and all(x=='SUCCESS' for x in processes)
 receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if good else 'FAIL','planned_units':1728,'raw_units':len(allrows),'phase_counts':dict(collections.Counter(x['phase'] for x in allrows)),'native_statuses':dict(collections.Counter(x['status'] for x in allrows)),'process_statuses':dict(collections.Counter(processes)),'checker_statuses':dict(collections.Counter(x['status'] for x in details)),'controls':ctrl,'checker_sha256':sha(Path(__file__)),'raw_sha256':{str(x.relative_to(O)):sha(x) for x in O.glob('p*/stdout.jsonl')}}
 (dest/'DETAILS.json').write_text(json.dumps(details,indent=2)+'\n');(dest/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
 for x in details:
  if x['status']!='PASS':print(json.dumps(x))
if __name__=='__main__':main()
