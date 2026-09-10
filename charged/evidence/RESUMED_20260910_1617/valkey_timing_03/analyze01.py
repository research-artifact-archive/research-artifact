#!/usr/bin/env python3
from pathlib import Path
import json,math,random,statistics,time
HERE=Path(__file__).resolve().parent;P=HERE/'run01';START=time.monotonic()
receipt=json.loads((P/'COMPLETION.json').read_text());assert receipt['status']=='SUCCESS'
manifest=json.loads((P/'INPUT_MANIFEST.json').read_text());cells={c['id']:c for c in manifest['cells']}
rows=[json.loads(l) for l in (P/'ROWS.jsonl').read_text().splitlines()];measured=[r for r in rows if not r['warmup']];assert len(measured)==1536 and all(r['status']=='SUCCESS' for r in rows)
index={(r['cell'],r['policy'],r['block']):r for r in measured};rng=random.Random(20260910);resamples=[tuple(rng.randrange(8) for j in range(8)) for i in range(10000)]
def interval(vals):
 logs=[math.log(v) for v in vals];point=math.exp(sum(logs)/8);boot=sorted(math.exp(sum(logs[j] for j in ix)/8) for ix in resamples);return {'geometric_mean_paired_ratio':point,'ci95':[boot[249],boot[9749]],'eight_paired_ratios':vals}
metrics=['foreground_ns','max_foreground_server_command_ns','sum_foreground_server_command_ns','ping_max_ns'];comparisons=[];summary=[]
for cell in sorted(cells):
 c=cells[cell];one={'cell':cell,'scale':c['scale'],'coefficient_template':c['coefficient_template'],'scenario':c['scenario'],'policies':{}}
 for policy in ['direct','accept','retry','compiled']:
  a=[index[(cell,policy,b)] for b in range(8)];one['policies'][policy]={'root_action':a[0]['root_action'],'resource_vectors':sorted(set(tuple(x[k] for k in ['L','W','Q_wire','C']) for x in a)),'ping_counts':[x['ping_count'] for x in a],'median_wire_bytes':statistics.median(x['wire_sent_bytes']+x['wire_received_bytes'] for x in a),**{'median_'+m:statistics.median(x[m] for x in a if x[m] is not None) if any(x[m] is not None for x in a) else None for m in metrics}}
 summary.append(one)
 for baseline in ['direct','accept','retry']:
  r={'cell':cell,'scale':c['scale'],'coefficient_template':c['coefficient_template'],'scenario':c['scenario'],'policy':'compiled','baseline':baseline,'root_action':one['policies']['compiled']['root_action'],'metrics':{}}
  for m in metrics:
   pairs=[(index[(cell,'compiled',b)][m],index[(cell,baseline,b)][m]) for b in range(8)]
   r['metrics'][m]=interval([x/y for x,y in pairs]) if all(x is not None and y is not None and x>0 and y>0 for x,y in pairs) else {'status':'UNAVAILABLE','pairs':pairs}
  comparisons.append(r)
counts={}
for baseline in ['direct','accept','retry']:
 counts[baseline]={}
 for metric in metrics:
  selected=[r['metrics'][metric] for r in comparisons if r['baseline']==baseline];counts[baseline][metric]={'ci_below1':sum('ci95'in x and x['ci95'][1]<1 for x in selected),'ci_above1':sum('ci95'in x and x['ci95'][0]>1 for x in selected),'ci_includes1':sum('ci95'in x and x['ci95'][0]<=1<=x['ci95'][1] for x in selected),'unavailable':sum('ci95'not in x for x in selected)}
for name,data in [('PAIRED_COMPARISONS.json',comparisons),('ALL_CELL_SUMMARY.json',summary),('ANALYSIS_RECEIPT.json',{'status':'SUCCESS','measured':1536,'warmups':192,'cells':48,'paired_comparisons':len(comparisons),'bootstrap_resamples':10000,'bootstrap_seed':20260910,'counts':counts,'seconds':time.monotonic()-START,'interpretation':'exploratory descriptive per-cell paired geometric ratios;8 blocks;not corrected for multiple comparisons;no SLA or independent application count'})]:(P/name).write_text(json.dumps(data,indent=2)+'\n')
lines=['# 全48条件の性能探索03','', '各比はcompiled方策 / 指定baselineの8対応blockの幾何平均とbootstrap95%区間。全条件を表示し、改善だけを選別していない。探索であり多重比較補正は行っていない。異なる入力・係数を独立アプリ数とは数えない。','', '|cell|scale|係数template|更新|compiled開始|対direct:前景|対direct:最大server command|対direct:最大PING|','|---|---:|---|---|---|---|---|---|']
def fmt(x):return 'NA' if 'ci95'not in x else f"{x['geometric_mean_paired_ratio']:.3f} [{x['ci95'][0]:.3f},{x['ci95'][1]:.3f}]"
for r in comparisons:
 if r['baseline']=='direct':lines.append('|'+ '|'.join([str(r['cell']),str(r['scale']),str(r['coefficient_template']),r['scenario'],r['root_action'],fmt(r['metrics']['foreground_ns']),fmt(r['metrics']['max_foreground_server_command_ns']),fmt(r['metrics']['ping_max_ns'])])+'|')
(P/'REPORT_JA.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'counts':counts,'examples':[r for r in comparisons if r['baseline']=='direct' and r['scale']==65536 and r['coefficient_template']==[4,1,1]],'seconds':time.monotonic()-START}))
