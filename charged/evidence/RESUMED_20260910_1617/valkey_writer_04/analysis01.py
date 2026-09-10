#!/usr/bin/env python3
from pathlib import Path
from statistics import median
import json,math,hashlib
HERE=Path(__file__).resolve().parent;OUT=HERE/'run01'
rows=[json.loads(x) for x in (OUT/'ROWS.jsonl').read_text().splitlines()];measured=[x for x in rows if not x['warmup']]
assert len(measured)==288 and all(x['status']=='SUCCESS' for x in rows)
manifest=json.loads((OUT/'INPUT_MANIFEST.json').read_text());cells=sorted(manifest['cells'],key=lambda c:c['id']);summary=[];comparisons=[]
def gm(xs):return math.exp(sum(math.log(x) for x in xs)/len(xs))
metrics=['mixed_trace_ns','reader_command_plus_hash_ns','max_any_server_ns','sum_any_server_ns','W_total','total_wire_bytes']
for c in cells:
    by={m:sorted([x for x in measured if x['cell']==c['id'] and x['policy']==m],key=lambda x:x['block']) for m in ['direct','compiled','maintained']}
    for m,rs in by.items():
        assert len(rs)==6 and [x['block'] for x in rs]==list(range(6))
        unit={'cell':c['id'],'scale':c['scale'],'R':c['R'],'scenario':c['scenario'],'policy':m,'blocks':6}
        for k in metrics+['maintenance_build_ns','initial_hash_ns','writer_hash_ns','reader_hash_ns','L_reader','W_reader','W_writer','W_initial','update_weight']:
            unit[k]=median(x[k] for x in rs)
        unit['commands']=rs[0]['commands'];unit['wire']=rs[0]['wire'];summary.append(unit)
    for other in ['direct','compiled']:
        unit={'cell':c['id'],'scale':c['scale'],'R':c['R'],'scenario':c['scenario'],'numerator':'maintained','denominator':other}
        for k in metrics:
            ratios=[a[k]/b[k] for a,b in zip(by['maintained'],by[other])];unit[k]={'paired_geometric_ratio':gm(ratios),'paired_ratios':ratios,'all_six_less':all(x<1 for x in ratios),'all_six_greater':all(x>1 for x in ratios)}
        comparisons.append(unit)
def dump(name,x):(OUT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
dump('ALL_CELL_SUMMARY.json',summary);dump('PAIRED_COMPARISONS.json',comparisons)
counts={}
for other in ['direct','compiled']:
    rs=[x for x in comparisons if x['denominator']==other];counts[other]={k:{'geometric_less':sum(x[k]['paired_geometric_ratio']<1-1e-10 for x in rs),'geometric_greater':sum(x[k]['paired_geometric_ratio']>1+1e-10 for x in rs),'all_six_less':sum(x[k]['all_six_less'] for x in rs),'all_six_greater':sum(x[k]['all_six_greater'] for x in rs)} for k in metrics}
dump('ANALYSIS_RECEIPT.json',{'status':'COMPLETE','cells':16,'paired_comparisons':32,'measured':288,'warmup':48,'raw_sha256':hashlib.sha256((OUT/'ROWS.jsonl').read_bytes()).hexdigest(),'analysis_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'counts':counts,'uncorrected_exploratory_point_estimates':True,'confidence_intervals_not_computed':True})
text=['# Writer-maintained comparison: all16 cells','',
'これは一host・六対応blockの探索。比は同一cell/blockの maintained/comparator の幾何平均で、小さいほど少ない。CIや検定による優位確定は行わない。全288計測・48warmup・12smokeが成功し、全source/全行を保存した。writerは全方式共通の新しいRESP版で、旧JSON版timing03とは別実験。',
'','初期digest構築と各writer hashを全て課金した。初期payloadはdataset作成時にproducerへ与えられる共通入力であり、既存databaseからの移行時の初回payload取得は計測していない。reader command+hash時間は列挙した区間の和で、Python制御・request JSON encoding等の全foreground CPUを測るものではない。mixed traceはそれらとwriter処理、初期構築を含む。最大server commandは全参加者と初期digest metadata HSETを含むが全event-loop停止の上界ではない。',
'','|scale|reads|updates|vs direct mixed time|vs compiled mixed time|vs direct all-server max|vs compiled all-server max|total work: direct/compiled/maintained (scale units)|total wire maintained/compiled|',
'|---:|---:|---|---:|---:|---:|---:|---|---:|']
for c in cells:
    ds=next(x for x in comparisons if x['cell']==c['id'] and x['denominator']=='direct');cs=next(x for x in comparisons if x['cell']==c['id'] and x['denominator']=='compiled');s={m:next(x for x in summary if x['cell']==c['id'] and x['policy']==m) for m in ['direct','compiled','maintained']}
    ratios=[ds['mixed_trace_ns']['paired_geometric_ratio'],cs['mixed_trace_ns']['paired_geometric_ratio'],ds['max_any_server_ns']['paired_geometric_ratio'],cs['max_any_server_ns']['paired_geometric_ratio']]
    work='/'.join(f"{s[m]['W_total']/c['scale']:g}" for m in ['direct','compiled','maintained'])
    text.append(f"|{c['scale']}|{c['R']}|{c['scenario']}|"+'|'.join(f'{v:.4f}' for v in ratios)+f"|{work}|{cs['total_wire_bytes']['paired_geometric_ratio']:.4f}|")
text += ['','全仕事量の恒等式は direct=R*P、maintained=P+sum(update footprint weight)、compiled=sum(reader work)。したがってmaintenanceとdirectの仕事量だけの境界は P+U=R*P。回数比だけでは成分weightが異なる場合を扱えない。これは実時間の損益分岐ではない。',
'','今回のcompiledは初回以後のwriteを受けず、単純dirty-thresholdで同じactionを選べる範囲を保持している。writer協力を禁ずる実在用途の証拠は追加されていない。reader-only action classの定理が、writer変更も許した全システム設計の最適性へ拡張されたとは扱わない。']
(OUT/'REPORT_JA.md').write_text('\n'.join(text)+'\n');print(json.dumps(counts));print('\n'.join(text[7:]))
