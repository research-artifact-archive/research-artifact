from pathlib import Path
from collections import Counter,defaultdict
import argparse,hashlib,json,statistics
p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[];sources={};derived={}
for f in range(1,4):
 d=a.directory/f'fork{f}';receipt=json.loads((d/'check/CHECK_RECEIPT.json').read_text());assert receipt['status']=='PASS'
 raw=d/'stdout.jsonl';sources[str(raw)]=hashlib.sha256(raw.read_bytes()).hexdigest()
 rows.extend(json.loads(x) for x in raw.read_text().splitlines())
 for x in json.loads((d/'check/DERIVED.json').read_text()):derived[(f,x['id'])]=x['kernel_intervals_ns']
measure=[x for x in rows if x['phase']=='measure'];assert all(x['status']=='SUCCESS' for x in rows)
cells=defaultdict(list);paired=defaultdict(dict)
for x in measure:
 cells[(x['projects'],x['r'],x['B'],x['mode'])].append(x);paired[(x['fork'],x['rep'],x['projects'],x['r'],x['B'])][x['mode']]=x
fields=['foreground_ns','writer_join_ns','setup_ns','whole_unit_ns'];summary=[];comparisons=[]
for key,xs in sorted(cells.items()):
 n,r,b,mode=key;counts={k:sorted({x['counters'][k] for x in xs}) for k in xs[0]['counters']};entry={'projects':n,'r':r,'B':b,'mode':mode,'units':len(xs),'counts':counts}
 for field in fields:
  vals=[x[field] for x in xs];medians=[statistics.median(x[field] for x in xs if x['fork']==f) for f in range(1,4)]
  entry[field]={'median':statistics.median(vals),'min':min(vals),'max':max(vals),'fork_medians':medians}
 for place in ['inside','outside']:entry['transformation_'+place+'_ns']={'median':statistics.median(derived[(x['fork'],x['id'])][place] for x in xs)}
 summary.append(entry)
for n,r,b in sorted({k[:3] for k in cells}):
 batches=[(k,v) for k,v in paired.items() if k[2:]==(n,r,b)]
 for baseline in ['original','two']:
  item={'projects':n,'r':r,'B':b,'comparison':'three minus '+baseline,'pairs':len(batches)}
  for field in fields:
   vals=[v['three'][field]-v[baseline][field] for _,v in batches]
   ratios=[v['three'][field]/v[baseline][field] for _,v in batches if v[baseline][field]>0]
   item[field]={'paired_median_difference':statistics.median(vals),'paired_median_ratio':statistics.median(ratios) if ratios else None,'fork_median_differences':[statistics.median(v['three'][field]-v[baseline][field] for k,v in batches if k[0]==f) for f in range(1,4)]}
  comparisons.append(item)
aggregate={}
for mode in ['original','two','three']:
 xs=[x for x in measure if x['mode']==mode];aggregate[mode]={'units':len(xs),'calls':sum(x['counters']['Calls'] for x in xs),'inside_transformations':sum(x['counters']['PreparedInside'] for x in xs),'outside_transformations':sum(x['counters']['PreparedOutside'] for x in xs),'foreground_ns_sum':sum(x['foreground_ns'] for x in xs)}
signs={}
for baseline in ['original','two']:
 signs[baseline]=dict(Counter('lower' if x['foreground_ns']['paired_median_difference']<0 else 'higher' if x['foreground_ns']['paired_median_difference']>0 else 'tie' for x in comparisons if x['comparison']=='three minus '+baseline))
result={'scope':'Post-outcome descriptive summary of all fixed repetitions; no source reruns, no exclusion, no significance or whole-application claim. Negative paired difference favors three.','raw_sha256':sources,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'all_units':len(rows),'measured_units':len(measure),'warmup_units':len(rows)-len(measure),'counts':dict(Counter(x['status'] for x in rows)),'aggregate':aggregate,'foreground_paired_median_signs':signs,'cells':summary,'comparisons':comparisons}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['all_units','measured_units','counts','aggregate','foreground_paired_median_signs']},indent=2))
for x in comparisons:print(x['r'],x['B'],x['comparison'],round(x['foreground_ns']['paired_median_difference']/1000,3),round(x['foreground_ns']['paired_median_ratio'],3))
