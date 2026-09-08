# 共通比witnessの簡略化探索

元のstrict7条件をすべてseedにし、4,305照会を記録。3,251unique casesは全SUCCESS、1,054は既存結果のcached referenceで再実行ではない。84selected successorを保存。5.297秒、adverse/unstarted0。仕事削除、辺削除、work値低減による局所最小7件はすべて5仕事。一般最小性は未確立。

説明用にseed66512から得たwork=(4,1,2,1,3),q=3,E={0→1,1→3}を選択した。c=2work,p=3work,B4でV26/F27、normal22、total48/49。別namespace critical_exposure_operational_01で元の細粒度モデルとnative実装を検査する。この選択後検証を事前固定の新無作為評価とは呼ばない。
