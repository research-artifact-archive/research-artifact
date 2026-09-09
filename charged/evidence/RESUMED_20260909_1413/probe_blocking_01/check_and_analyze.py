from pathlib import Path
from collections import Counter,defaultdict
import copy,datetime,hashlib,json,time
import numpy as np

D=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,data):(D/name).write_text(json.dumps(data,indent=2)+'\n')
def key(x):return tuple(x[k] for k in ('fork','phase','rep','scale','r','layout','policy'))
def validate(x):
    if x['status']!='SUCCESS':return []
    s,r,c=x['scale'],x['r'],x['policy']=='three';errors=[]
    expected={'Q':4+r,'W':(11+r)*s,'L':0 if c else 11*s,'writes':r,'failures':r}
    for k,v in expected.items():
        if type(x.get(k)) is not int or x[k]!=v:errors.append('counter:'+k)
    if x['versions']!=[r,0,0,0]:errors.append('versions')
    if x['trace']!=['0:F']*r+[f'{i}:C' if c else f'{i}:P' for i in range(4)]:errors.append('trace')
    if len(x['probes'])!=4:errors.append('probe_count')
    for i,p in enumerate(x['probes']):
        if p['job']!=i:errors.append('probe_job')
        if not (0<=p['issue_ns']<=p['entry_ns']<=p['end_ns']<=x['foreground_ns']):errors.append('probe_time')
        if not (0<=p['callback_entry_ns']<=p['issue_ns']<=p['body_start_ns']<=p['body_end_ns']<=x['foreground_ns']):errors.append('callback_time')
        if x['layout']=='same_bin' and p['entry_ns']<p['body_end_ns']:errors.append('same_bin_order')
        for k,a,b in [('wait_ns','entry_ns','issue_ns'),('operation_ns','end_ns','issue_ns'),('callback_body_ns','body_end_ns','body_start_ns'),('callback_hooked_ns','body_end_ns','callback_entry_ns')]:
            if p[k]!=p[a]-p[b]:errors.append('interval:'+k)
    if x['wait_sum_ns']!=sum(p['wait_ns'] for p in x['probes']):errors.append('wait_sum')
    if x['probes'] and x['wait_max_ns']!=max(p['wait_ns'] for p in x['probes']):errors.append('wait_max')
    if c and x['kernel_in_ns']!=0:errors.append('cached_kernel_inside')
    return sorted(set(errors))

def reference(scale,r):
    # Sequential mathematical interpretation using Python integers, independent of JVM policy/counters.
    mask=(1<<64)-1;parent=0;seeds=[]
    for i,w in enumerate([1,2,3,5]):
        seed=17+31*i+(104729*r if i==0 else 0)
        x=(seed^(0 if i==0 else seeds[i-1]))&mask
        for _ in range(w*scale):
            x=((((x<<13)&mask)|(x>>51))*6364136223846793005+1442695040888963407)&mask
        seeds.append(x)
    return [x-(1<<64) if x>>63 else x for x in seeds]

def main():
    started=time.monotonic();raw=[];ledger=[];errors=[];seen=set();raw_hashes={}
    receipt=json.loads((D/'INPUT_RECEIPT.json').read_text())
    for name,value in receipt['files'].items():
        if sha(D/name)!=value:errors.append(['input_changed',name])
    for fork in range(1,4):
        path=D/f'fork{fork}/stdout.jsonl';raw_hashes[str(path.relative_to(D))]=sha(path)
        rows=[json.loads(line) for line in path.read_text().splitlines()];plan=json.loads((D/f'FORK{fork}_UNITS.json').read_text());planned={key(x):x for x in plan}
        actual={}
        for x in rows:
            k=key(x)
            if k in actual:errors.append(['duplicate',k])
            if k not in planned:errors.append(['unplanned',k])
            actual[k]=x;raw.append(x)
            if k in seen:errors.append(['cross_duplicate',k])
            seen.add(k)
        if [x['sequence'] for x in rows]!=list(range(len(rows))):errors.append(['sequence',fork])
        process=json.loads((D/f'fork{fork}/RESULT.json').read_text())
        for k,unit in planned.items():
            x=actual.get(k)
            if x is None:ledger.append(unit|{'status':'TIMEOUT' if process['status']=='TIMEOUT' else 'INVALID','reason':'planned unit missing after process termination'});continue
            issues=validate(x)
            if issues:errors.append([k,issues])
            ledger.append(unit|{'status':'FAILURE' if issues else x['status'],'reason':issues or x['error']})
    pair_index=defaultdict(dict)
    for x in raw:pair_index[key(x)[:-1]][x['policy']]=x
    for k,pair in pair_index.items():
        if set(pair)!={'two','three'}:errors.append(['incomplete_pair',k]);continue
        if pair['two']['seeds']!=pair['three']['seeds']:errors.append(['pair_output',k])
    references={}
    for scale in [64,2048,65536,2097152]:
        for r in range(3):references[f'{scale}:{r}']=reference(scale,r)
    for x in raw:
        if x['status']=='SUCCESS' and x['seeds']!=references[f"{x['scale']}:{x['r']}"]:errors.append(['sequential_reference',key(x)])
    controls=[];sample=next(x for x in raw if x['layout']=='same_bin' and x['policy']=='three')
    mutations=[('wrong_L',lambda x:x.update(L=1)),('wrong_Q',lambda x:x.update(Q=100)),('wrong_versions',lambda x:x.update(versions=[-1]*4)),('missing_probe',lambda x:x['probes'].pop()),('early_entry',lambda x:x['probes'][0].update(entry_ns=x['probes'][0]['body_end_ns']-1)),('wrong_interval',lambda x:x.update(wait_sum_ns=-1)),('hidden_inside_kernel',lambda x:x.update(kernel_in_ns=1))]
    for name,mutate in mutations:
        bad=copy.deepcopy(sample);mutate(bad);found=validate(bad);controls.append({'name':name,'rejected':bool(found),'errors':found})
    write('OUTCOME_LEDGER.json',ledger);write('SEQUENTIAL_REFERENCE.json',references)
    counts={p:dict(Counter(x['status'] for x in ledger if x['phase']==p)) for p in ['warmup','measure']}
    checked={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if not errors and all(x['rejected'] for x in controls) and counts=={'warmup':{'SUCCESS':1440},'measure':{'SUCCESS':4320}} else 'FAIL','counts':counts,'probes':sum(len(x['probes']) for x in raw if x['phase']=='measure'),'pairs':sum(k[1]=='measure' for k in pair_index),'raw_hashes':raw_hashes,'errors':errors,'controls':controls,'sequential_reference_units':12,'sequential_reference_compared_invocations':len(raw),'seconds':time.monotonic()-started}
    write('CHECK_RECEIPT.json',checked)
    if checked['status']!='PASS':print(json.dumps(checked));return
    cells=[];rng=np.random.default_rng(20260909)
    for scale in [64,2048,65536,2097152]:
        for r in range(3):
            for layout in ['same_bin','disjoint_bin']:
                pairs=[p for k,p in sorted(pair_index.items()) if k[1]=='measure' and k[3]==scale and k[4]==r and k[5]==layout]
                a=np.array([p['two']['wait_sum_ns'] for p in pairs],dtype=np.float64);b=np.array([p['three']['wait_sum_ns'] for p in pairs],dtype=np.float64);diff=a-b
                bootstrap=np.median(diff[rng.integers(0,len(diff),size=(20000,len(diff)))],axis=1)
                byfork=[]
                for fork in range(1,4):
                    sub=[p for p in pairs if p['two']['fork']==fork];aa=np.array([p['two']['wait_sum_ns'] for p in sub]);bb=np.array([p['three']['wait_sum_ns'] for p in sub]);byfork.append({'fork':fork,'pairs':len(sub),'two_median_ns':float(np.median(aa)),'three_median_ns':float(np.median(bb)),'paired_difference_median_ns':float(np.median(aa-bb))})
                cells.append({'scale':scale,'r':r,'layout':layout,'pairs':len(pairs),'two_median_ns':float(np.median(a)),'three_median_ns':float(np.median(b)),'two_over_three_ratio_of_medians':float(np.median(a)/np.median(b)),'paired_difference_median_ns':float(np.median(diff)),'paired_difference_95_percentile_bootstrap_ns':np.percentile(bootstrap,[2.5,97.5]).tolist(),'forks':byfork,'secondary':{p:{k:float(np.median([x[p][k] for x in pairs])) for k in ['wait_max_ns','foreground_ns','setup_ns','kernel_in_ns','kernel_out_ns']} for p in ['two','three']}})
    write('SUMMARY.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kind':'DESCRIPTIVE_PAIRED_TIMING_CONSTRUCTED_B_EQUALS_R','measurement_units':4320,'pairs':2160,'cells':cells,'limits':'Instrumented authored mechanism experiment; bootstrap repeats within 3 JVMs on one host, not independent machines; not WCET, throughput, population prevalence or a universal runtime guarantee. All24 cells retained.'})
    lines=['# Complete paired blocking results','','Semantic check: 4320 measurement and 1440 warmup invocations SUCCESS; 17280 measured probes; 2160 measured pairs. All 5760 outputs match 12 independent Python sequential references. Seven checker controls rejected. No exclusions or retries.','','All times below are microseconds. Difference = two minus three; CI is the descriptive paired bootstrap of the median (20000 resamples), not a tail bound. Each row pools 90 pairs from three JVMs. The per-fork range is the range of three paired median differences.','','| scale | r | layout | two median | three median | paired difference | 95% interval | fork difference range |','|---:|---:|---|---:|---:|---:|---|---|']
    for c in cells:
        ci=c['paired_difference_95_percentile_bootstrap_ns'];fd=[x['paired_difference_median_ns']/1000 for x in c['forks']]
        lines.append(f"| {c['scale']} | {c['r']} | {c['layout']} | {c['two_median_ns']/1000:.3f} | {c['three_median_ns']/1000:.3f} | {c['paired_difference_median_ns']/1000:.3f} | [{ci[0]/1000:.3f}, {ci[1]/1000:.3f}] | [{min(fd):.3f}, {max(fd):.3f}] |")
    (D/'RESULTS.md').write_text('\n'.join(lines)+'\n');print(json.dumps({'check':checked['status'],'counts':counts,'seconds':time.monotonic()-started}));print((D/'RESULTS.md').read_text())

if __name__=='__main__':main()
