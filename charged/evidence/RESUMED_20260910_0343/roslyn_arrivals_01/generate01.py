from pathlib import Path
import hashlib,json,random
D=Path(__file__).resolve().parent;old=(D.parent/'roslyn_semantics_01/harness01/Program.cs').read_text()
prefix=old[:old.index('sealed class StudyWorkspace')]
helpers=old[old.index('    static readonly BindingFlags'):old.index('    static Dictionary<string,object?> Run(Unit u)')]
helpers=helpers.replace('    static bool Normal(Unit u)=>u.Scenario is "normal" or "spread" or "target_writer" or "linked_writer";\n','').replace('    static bool TargetWriter(Unit u)=>u.Scenario is "target_writer" or "linked_writer";\n','')
helpers=helpers.replace('Enumerable.Range(0,5)','Enumerable.Range(0,33)')
setup=old[old.index('            ws=new StudyWorkspace();'):old.index('            if(u.Scenario=="missing_required")')]
setup=setup.replace('ws=new StudyWorkspace();','ws=new ArrivalWorkspace();').replace('u.Projects!=projectRows.Length','4!=projectRows.Length')
body=(D/'Program.body.cs.txt').read_text().replace('/*HELPERS*/',helpers).replace('/*SETUP*/',setup)
(D/'harness01').mkdir();(D/'harness01/Program.cs').write_text(prefix+body)
arms=[('baseline',0),('original',0),('two',0),('two',2),('three',0),('three',2)]
rng=random.Random(9100438);processes=[(f,m,r) for f in range(1,4) for m,r in arms];rng.shuffle(processes)
table=[]
for sequence,(fork,mode,r) in enumerate(processes,1):
 rows=[]
 for phase,reps in [('warmup',2),('measurement',10)]:
  for rep in range(1,reps+1):
   periods=[0,10,100,1000];rng.shuffle(periods)
   for period in periods:rows.append([f'f{fork}_{mode}_r{r}_{phase}_{rep}_d{period}',phase,fork,rep,period,mode,r])
 name=f'p{sequence:02d}_f{fork}_{mode}_r{r}.tsv';(D/'harness01'/name).write_text(''.join('\t'.join(map(str,row))+'\n' for row in rows))
 table.append({'sequence':sequence,'fork':fork,'mode':mode,'r':r,'units':len(rows),'input':name,'sha256':hashlib.sha256((D/'harness01'/name).read_bytes()).hexdigest()})
(D/'harness01/PROCESS_ORDER.json').write_text(json.dumps({'seed':9100438,'processes':table,'units':864,'measurement':720,'warmup':144},indent=2)+'\n')
print(json.dumps({'program_sha256':hashlib.sha256((D/'harness01/Program.cs').read_bytes()).hexdigest(),'processes':len(table),'units':sum(x['units'] for x in table)}))
