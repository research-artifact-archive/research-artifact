from pathlib import Path
import collections,copy,datetime,hashlib,json,re,sys
D=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(condition,message):
 if not condition:raise AssertionError(message)
def check(row):
 require(row['status']=='SUCCESS','native non-success')
 normal=row['scenario'] in ('normal','spread','target_writer','linked_writer')
 target_writer=row['scenario'] in ('target_writer','linked_writer')
 missing=row['scenario']=='missing_required';removed=row['scenario']=='removed_between'
 require(row['source_documents']==4019 and row['linked_documents']==2,'source universe')
 require(row['unchanged_source_documents']==4016,'untouched denominator')
 require(row['actual_writes']==(row['B'] if normal else int(removed)),'actual write denominator')
 sp={p['snapshot']:p for p in row['snapshot_projections']}
 require(len(sp)==len(row['snapshot_projections']),'duplicate snapshot')
 require(row['initial_snapshot'] in sp and row['final_snapshot'] in sp,'missing endpoint snapshot')
 digest=row['initial_untouched_projection_sha256']
 require(re.fullmatch('[0-9a-f]{64}',digest) is not None,'invalid projection digest')
 for snap in sp.values():
  require(snap['untouched_documents']==4016 and snap['untouched_projection_sha256']==digest,'untouched projection')
  require(snap['documents']==4019-(snap['targets'][0]==-1),'membership')
  require(len(snap['targets'])==2,'linked denominator')
 initial=sp[row['initial_snapshot']]
 require(initial['targets']==([-1,0] if missing else [0,0]) and initial['background']==0,'initial state')
 queued=row['queued_events'];immediate=row['immediate_events']
 require(queued==[x['payload'] for x in immediate],'immediate/queued payload equality')
 require(all(x['current']==x['payload']['new'] for x in immediate),'immediate current binding')
 pubs=row['publications'];expected_events=[]
 previous=row['initial_snapshot'];targets=initial['targets'];bg=0;fg=0;writers=0
 for pub in pubs:
  require(pub['old']==previous and pub['new']!=previous,'publication chain')
  before=sp[pub['old']];after=sp[pub['new']]
  require(pub['old_targets']==before['targets'] and pub['new_targets']==after['targets'],'payload target projection')
  require(pub['old_background']==before['background'] and pub['new_background']==after['background'],'payload background projection')
  require(before['targets']==targets and before['background']==bg,'linearized predecessor')
  docs=pub['documents']
  if pub['kind']=='DocumentRemoved':
   require(removed and docs==[0] and targets==[0,0] and after['targets']==[-1,0] and after['background']==bg,'remove transition')
   writers+=1
  elif docs==[-1]:
   require(normal and not target_writer and after['targets']==targets and after['background']==bg+1,'background transition')
   writers+=1
  else:
   require(pub['kind']=='DocumentChanged','publication kind')
   value=after['targets'][0]
   require(after['targets']==[value,value] and after['background']==bg,'linked atomic content')
   if value<=-101:
    writers+=1
    require(target_writer and value==-100-writers,'interfering target request')
    require(docs==([1,0] if row['scenario']=='linked_writer' else [0,1]),'writer linked notification order')
   else:
    fg+=1
    require(docs==[0,1] and value==(fg if normal else 0),'foreground request/order')
  for doc in docs:expected_events.append((pub['kind'],doc,pub['old'],pub['new']))
  previous=pub['new'];targets=after['targets'];bg=after['background']
 require([(e['kind'],e['document'],e['old'],e['new']) for e in queued]==expected_events,'publication/event sequence')
 require(previous==row['final_snapshot'] and writers==row['actual_writes'],'final chain/writer binding')
 require(fg==(4 if normal else 1 if row['scenario']=='equal_identity' else 0),'foreground publications')
 require(targets==row['final_target_versions'] and bg==row['final_background_version'],'final projection')
 expected_not=[]
 for e in queued:
  if e['kind']=='DocumentChanged':
   snap=sp[e['new']];doc=e['document']
   expected_not.append({'document':doc,'version':snap['background'] if doc==-1 else snap['targets'][doc],'snapshot':e['new']})
 require(row['notifications']==expected_not,'document notification payload binding')
 require(row['workspace_event_document_sequence']==[e['document'] for e in queued if e['kind']=='DocumentChanged'],'event document projection')
 for writer in row['writer_events']:
  pair=[p for p in pubs if p['old']==writer['before_snapshot'] and p['new']==writer['after_snapshot']]
  require(len(pair)==1,'writer publication binding')
 if row['scenario']=='spread':
  require([w['job'] for w in row['writer_events']]==list(range(1,row['B']+1)),'spread schedule')
 for capture in row['captures']:
  snap=sp[capture['snapshot']]
  require(capture['target_versions']==snap['targets'] and capture['background_version']==snap['background'],'captured snapshot projection')
  require(capture['target_versions']==([capture['job']]*2 if normal else [0,0]),'capture requested contents')
  require(capture['background_version']==(0 if target_writer else capture['writes_at_return']),'capture interfering writes')
 require(len(row['captures'])==(4 if normal else 0 if missing or removed else 1),'capture denominator')
 if row['mode']!='baseline':
  kinds=collections.Counter(t['Kind'] for t in row['trace'])
  counters=row['counters']
  for field,kind in [('Calls','lock_enter'),('PreparedOutside','kernel_outside_begin'),('PreparedInside','kernel_inside_begin'),('CheapFailures','cheap_failure'),('Rebases','rebase_completed')]:
   require(counters[field]==kinds[kind],f'counter {field}')
  require(row['remaining']==(row['r'] if row['mode']=='original' else row['r']-counters['CheapFailures']),'remaining budget')
  require(counters['Rebases']==0 if row['mode']!='rebase' or target_writer else counters['Rebases']>=0,'rebase eligibility')
  if normal:
   if row['mode'] in ('three','rebase'):
    require(counters['Mismatches']==counters['CheapFailures']+counters['PreparedInside']+counters['Rebases'],'mismatch partition')
   require(counters['Calls']==4+counters['CheapFailures'],'calls from publications/failures')
   require(counters['Calls']<=4+(row['B'] if row['mode']=='original' else min(row['B'],row['r'])),'call guarantee')
   require(counters['PreparedInside']<=(0 if row['mode']=='original' else 4 if row['mode']=='two' else min(max(row['B']-row['r'],0),4)),'protected transformation guarantee')
 return {'events':len(queued),'publications':len(pubs),'snapshots':len(sp)}
def mutation_controls(row):
 variants=[]
 def add(name,fn):
  x=copy.deepcopy(row);fn(x);variants.append((name,x))
 add('queued_old_payload',lambda x:x['queued_events'][0].__setitem__('old',-1))
 add('queued_new_payload',lambda x:x['queued_events'][0].__setitem__('new',x['initial_snapshot']))
 add('immediate_current_binding',lambda x:x['immediate_events'][0].__setitem__('current',-1))
 add('missing_event',lambda x:x['queued_events'].pop())
 add('duplicate_event',lambda x:x['queued_events'].append(copy.deepcopy(x['queued_events'][-1])))
 add('publication_chain',lambda x:x['publications'][0].__setitem__('old',-1))
 add('untouched_projection',lambda x:x['snapshot_projections'][0].__setitem__('untouched_projection_sha256','0'*64))
 add('linked_callback_snapshot',lambda x:x['notifications'][1].__setitem__('snapshot',x['initial_snapshot']))
 add('linked_text_payload',lambda x:x['publications'][0]['new_targets'].__setitem__(1,999))
 add('resource_counter',lambda x:x['counters'].__setitem__('Calls',999))
 out=[]
 for name,x in variants:
  try:check(x);out.append({'control':name,'detected':False})
  except (AssertionError,KeyError,IndexError,TypeError):out.append({'control':name,'detected':True})
 require(all(x['detected'] for x in out),'undetected corruption')
 return out
def main():
 O=D/'run01';dest=O/'check01';dest.mkdir()
 details=[];allrows=[]
 for label,unitfile in [('baseline','BASELINE.tsv'),('patched','UNITS.tsv')]:
  planned=[x.split('\t') for x in (D/'harness01'/unitfile).read_text().splitlines()]
  rows=[json.loads(x) for x in (O/label/'stdout.jsonl').read_text().splitlines()]
  require([r['id'] for r in rows]==[x[0] for x in planned],label+' exact denominator')
  for raw,plan in zip(rows,planned):
   require([str(raw[k]) for k in ['id','phase','fork','rep','projects','r','B','mode','scenario']]==plan,'input identity')
   try:counts=check(raw);status='PASS';error=''
   except Exception as e:counts={};status='FAIL';error=f'{type(e).__name__}: {e}'
   details.append({'label':label,'id':raw['id'],'status':status,'native_status':raw['status'],'error':error,**counts})
   allrows.append(raw)
 (dest/'DETAILS.json').write_text(json.dumps(details,indent=2)+'\n')
 candidate=next((r for r in allrows if r['mode']=='original' and r['scenario']=='normal' and r['B']==1 and r['status']=='SUCCESS'),None)
 controls=mutation_controls(candidate) if candidate else []
 rebase_candidate=next((r for r in allrows if r['mode']=='rebase' and r['scenario']=='normal' and r['B']==1 and r['status']=='SUCCESS'),None)
 if rebase_candidate:
  corrupt=copy.deepcopy(rebase_candidate);corrupt['counters']['Rebases']+=1
  try:check(corrupt);detected=False
  except (AssertionError,KeyError,IndexError,TypeError):detected=True
  controls.append({'control':'rebase_trace_count','detected':detected})
 target_candidate=next((r for r in allrows if r['mode']=='rebase' and r['scenario']=='target_writer' and r['B']==1 and r['r']==0 and r['status']=='SUCCESS'),None)
 if target_candidate:
  corrupt=copy.deepcopy(target_candidate);corrupt['counters']['Rebases']=1;corrupt['counters']['PreparedInside']-=1
  victim=next(t for t in corrupt['trace'] if t['Kind']=='kernel_inside_begin');victim['Kind']='rebase_completed'
  try:check(corrupt);detected=False
  except (AssertionError,KeyError,IndexError,TypeError):detected=True
  controls.append({'control':'same_target_rebase_ineligible','detected':detected})
 require(len(controls)==12 and all(x['detected'] for x in controls),'complete corruption controls')
 receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if all(r['status']=='PASS' for r in details) and controls else 'FAIL','units':len(details),'native_statuses':dict(collections.Counter(r['status'] for r in allrows)),'checker_statuses':dict(collections.Counter(r['status'] for r in details)),'counts':{key:sum(r.get(key,0) for r in details) for key in ['events','publications','snapshots']},'corruption_controls':controls,'checker_sha256':sha(Path(__file__)),'raw_sha256':{label:sha(O/label/'stdout.jsonl') for label in ['baseline','patched']},'scope':'bounded source-projection author-side conformance; unmodified controls have no writers or source hooks; not independent review'}
 (dest/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
 for r in details:
  if r['status']!='PASS':print(json.dumps(r))
if __name__=='__main__':main()

