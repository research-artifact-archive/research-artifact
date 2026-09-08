# 値と保存方策を直接検査するsweep v2

v1の全値検査は健全だが、stored fast actionの達成性には既存cheapest-fast lemmaが別途必要だった。新namespaceでは全actionの非負性を維持し、zero集合のcoverageを全protected actionとstored fast actionだけへ制限した。実行器は値に一致するprotected actionを選び、存在しなければstored fastを選ぶため、この追加条件は保存方策の達成性も直接検査する。数学的model/abstraction theoremの機械証明ではない。

結果前に固定した83,125算術unitはfull-valueとselected-policyの二条件（166,250判定）とも整数全列挙と一致。full成立7,238/不成立75,887、selected成立6608/不成立76517。既存ideal証明書1,296件、既存control25件、大規模保存証明書36件も全SUCCESS。v1の原結果・原codeは不変。入力の形・gameのゼロbudget・定数tailを信頼境界として明示する。

新コードの同条件比較は36既知成功証明書×2方式=72 cold units、両方式36 SUCCESS/他0/不一致0。旧/新check合計14.585864918/5.932542245秒、cold16.587626129/8.089727336秒。新方式はpolicy達成性も追加検査するため、その保証範囲の差を隠さない。各method5秒/1GiB、交互順序、full分母固定。元の失敗/timeout再試行0、constructor0。これは既知成功証明書の検査費用probeであり、新populationやend-to-end完走率を示さない。

per-state M=自身を二回数えた構成profile entries、I=merge区間数、a=ready job数として、scanはO(M log(a+2)+I a log(a+1))算術操作、shape費用別。実装はboundary配列をmaterializeするので補助memory O(M+a)、bit費用別。constant-memory streamingとは呼ばない。旧curve/scientific bytes、paper build36、artifactv3.1は未変更。
