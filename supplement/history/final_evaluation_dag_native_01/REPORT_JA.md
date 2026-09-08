# 固定したJava DAG評価01

19,644/19,644 native経路がSUCCESS。FAILURE、TIMEOUT、INVALID、NOT_RUN、
parse error、unexpected ID、最大値不一致はいずれも0。Java compile/executeはともにexit0。
125固定file、全rawの一意IDと入力順、両layoutの方策最大値一致を照合した。

事前に種202609080250と生成規則を固定し、3/4/5仕事×2構造条件×8例の48 DAGを生成。
24例はcost-compatible、24例は不適合辺を持つ一般route。番号をpermutationした。
重複・過去に選んだnative例とのexact一致は0。予算0/1/2/4により192 priced roots、
両bin layoutで384 root/layout cells、5方策で1,920 policy cells。
固定順序基準は全397 topological orderを対象とし、各初期予算で最良順序を選ぶ。
native実行前に数値モデル・全終端経路・期待値を計算して保存した。この準備値は観測済みである。
4件のcompleted-parent postwrite controlは比較分母の192 rootsと分離した。

hybrid制御器はordered routeで保存order/thresholdとcursorを使用し、一般routeで保存curveを使用。
Javaの実際のreplace/compute、別background executor、immutable parent milestonesを実行。
whole-kernelのparent foldと配列entryを数え、宣言した重みd*W+Σq_i*L_iを比較した。
全出力digest、親seed、世代、trace、work、guarded work、実write数、方策最大値が
別のPython再構成と一致した。全4controlでlive parentとcaptured milestoneが異なり、
childは保存milestoneを消費した。これは自然な利用頻度・production・latencyの証拠ではない。

layoutを重複計上しない192 rootsでの結果:

| 比較相手 | hybridが厳密に小さい | 同値 | hybridが大きい | 最大相対総仕事量差 |
|---|---:|---:|---:|---:|
| 最良固定topological順序＋最適adaptive mode | 2 | 190 | 0 | 2.0833% |
| 固定mode boundのlookahead、fast優先tie | 18 | 174 | 0 | 12.5% |
| 同、protected優先tie | 30 | 162 | 0 | 13.6364% |
| exact adaptive cached-fallback family | 138 | 54 | 0 | 76.7442% |

全4比較相手を同時に上回るのは2/192 rootsで、同じ一般DAG native-final-47のB=2,4。
c=(4,10,3,8,7), p=(23,4,10,7,17), edges={1→2,4→1,4→2}。
基礎仕事量32を含む非scale値はB2で47対48、B4で61対62（固定順序基準）。
したがって最強基準に対する改善は、この固定sampleでは少数かつ小さい。
大きなcached-family差だけを一般的な必要性や最良既存手法への大幅改善へ読み替えない。

モデル・経路準備5.033秒、Java compile＋execute合算1.542秒。これらは別段階の一回計測。
計画はcompile/executeの個別費用報告を求めたがrunnerは合算時間だけを記録しており、
両者の個別時間とchecker専用時間は不明。この計測不足を保持し、合算値をfresh end-to-end
時間やpolicyの速度差へ使わない。測定不足を埋めるため同じnative経路を再実行していない。

MANIFEST SHA-256:
`89458cedad93020acf88e998a997cc326276b35cd2f30652d63411f8d6ea32d7`。
RAW SHA-256:
`1c31b59de0f23dca1d2a1573ec74388243d148812a7d27167ec23b640a9b2ec7`。
旧選択例11,334経路・全開発と不利結果を保持する。著者側code検査は別receiptに保存し、
blind review、科学proof closure、重要性や投稿準備の認定として扱わない。
