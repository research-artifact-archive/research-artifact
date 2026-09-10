# Writer-maintained comparison: all16 cells

これは一host・六対応blockの探索。比は同一cell/blockの maintained/comparator の幾何平均で、小さいほど少ない。CIや検定による優位確定は行わない。全288計測・48warmup・12smokeが成功し、全source/全行を保存した。writerは全方式共通の新しいRESP版で、旧JSON版timing03とは別実験。

初期digest構築と各writer hashを全て課金した。初期payloadはdataset作成時にproducerへ与えられる共通入力であり、既存databaseからの移行時の初回payload取得は計測していない。reader command+hash時間は列挙した区間の和で、Python制御・request JSON encoding等の全foreground CPUを測るものではない。mixed traceはそれらとwriter処理、初期構築を含む。最大server commandは全参加者と初期digest metadata HSETを含むが全event-loop停止の上界ではない。

|scale|reads|updates|vs direct mixed time|vs compiled mixed time|vs direct all-server max|vs compiled all-server max|total work: direct/compiled/maintained (scale units)|total wire maintained/compiled|
|---:|---:|---|---:|---:|---:|---:|---|---:|
|4096|1|none|0.4581|0.5025|0.0038|0.1633|6/6/6|0.0003|
|4096|1|small_each|0.5916|0.5786|0.1823|0.7699|6/7/7|0.1429|
|4096|1|all_first|0.9881|0.4923|0.5821|0.6687|6/12/12|0.3330|
|4096|1|all_each|0.9484|0.6243|0.5952|0.9433|6/12/12|0.3330|
|4096|8|none|0.0658|0.0737|0.0042|0.1795|48/48/6|0.0002|
|4096|8|small_each|0.3314|0.3097|0.2599|0.9224|48/56/14|0.1428|
|4096|8|all_first|0.2856|0.2632|0.5713|0.9573|48/54/12|0.1000|
|4096|8|all_each|0.8184|0.5268|0.6191|0.9274|48/96/54|0.3330|
|16384|1|none|0.4367|0.4888|0.0014|0.0562|6/6/6|0.0001|
|16384|1|small_each|0.6312|0.5563|0.1999|0.9491|6/7/7|0.1429|
|16384|1|all_first|0.9613|0.6258|0.6036|0.9612|6/12/12|0.3333|
|16384|1|all_each|0.9851|0.6370|0.6024|0.9436|6/12/12|0.3333|
|16384|8|none|0.0576|0.0633|0.0019|0.0613|48/48/6|0.0000|
|16384|8|small_each|0.3192|0.3035|0.2133|0.9411|48/56/14|0.1428|
|16384|8|all_first|0.2734|0.2530|0.5888|1.0010|48/54/12|0.1000|
|16384|8|all_each|0.8322|0.5595|0.6577|1.0627|48/96/54|0.3332|

全仕事量の恒等式は direct=R*P、maintained=P+sum(update footprint weight)、compiled=sum(reader work)。したがってmaintenanceとdirectの仕事量だけの境界は P+U=R*P。回数比だけでは成分weightが異なる場合を扱えない。これは実時間の損益分岐ではない。

今回のcompiledは初回以後のwriteを受けず、単純dirty-thresholdで同じactionを選べる範囲を保持している。writer協力を禁ずる実在用途の証拠は追加されていない。reader-only action classの定理が、writer変更も許した全システム設計の最適性へ拡張されたとは扱わない。
