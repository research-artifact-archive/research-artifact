# 共通の保護仕事重み: 最初の限定grid

27,105 case-weight units / 220,701 budget roots / 130,560 topological ordersを全て検査し、general/compiler/certificate/scalar/fixed-orderの不一致0、全SUCCESS。他status0、strict adaptive-order gapは0件だった。n1..4の全upper-triangular DAG、work {1,2,4}^n、共通lambda {0,1/2,1,2,4}、saturationを含むbudget範囲の結果に限る。33case-weight unitsは以前のfinalの同じcase価格/辺を再利用していることを結果前に記録した。新しい独立finalsampleではない。

このgridは、一様重みなら適応順序の利点が一般に消えるという定理を示さない。非dyadic work、より多いjob、他の共通重みを未観測のまま外挿しない。元のheterogeneous-priceによる4job/2failure gapは変更しない。

MOTIVATION_CORRECTION.json: 親担当が現行nativeを人工的追加仕事と誤読してpre-planへ記した。実際のNativeDagFinalはchargeで全workとcallback内workを数え、dW+sum q_i L_iをすでに採用している。本文252行にも既存記述がある。誤読をユーザーへ訂正し、pre-plan/manifest/runは不変保存した。今回の新しい問いは既存metricを一つの共通lambdaへ制約することだけであり、新metricや新application evidenceではない。コード/入力/算術結果はこの制約を最初から検査しており、動機の訂正による変更はない。

次の科学的判断: common-ratioでfixed orderが常に最適となる構造があるか、限定gridの陰性かを区別する必要がある。新しい分母なしに同じ陰性を再試行しない。新規性と用途の自然さは未確立のまま。
