# 依存DAGを含む操作モデル：固定最終評価01

4,232/4,232入力がSUCCESS。FAILURE、TIMEOUT、INVALID、NOT_RUNはすべて0。
初期予算0〜4の21,160値が、完全な操作ゲーム、別実装の数値Bellman再帰、
保存・再読込したhybrid制御器の間で一致した。約53.434秒で完了し、
プロセスの観測peak RSSは46,186,496 bytesだった。性能比較を目的とした計測ではない。

固定範囲は1〜3仕事、全forward-edge DAG、各(c,p)∈{1,2}×{0,1,2,3}。
1,220,680状態、9,239,600操作、12,551,856環境outcomeを全件扱った。
全状態のBellman最小値、選択方策の終了rank、potential下界、全操作のpotential不等式を検査した。
さらに保存方策68,520選択の実行可能性と最適値を検査した。
ordered routeは2,936入力、general ideal routeは1,296入力。
general routeには独立した完全性・schema検査を追加してから旧Bellman恒等式検査を適用した。
ordered routeは既存の共有root certificate検査を用いた。

補題の有限検査はsubset単調性558,840、one-pass409,720、予算単調性133,184、
離散凹性99,888、最小費用fast支配191,776、cached fallback153,376件で違反0。
これらは証明を置き換えない。全予算を扱う証明書検査と、予算0〜4に限定した
完全操作状態列挙を区別する。

584入力は以前の独立ケース最終評価の回帰。依存関係がある3,648入力中4件は
今回の開発preflightで観測済み。以前の643 DAG入力および719入力hybrid集合との
exact入力一致は0だが、著者が定義した体系的集合であり、独立な実応用集団ではない。
推移辺が冗長なgraphも事前定義どおり分母に残した。非topological番号の全列挙はしていない。

開発preflight10件、検査器control25件（正常1・不正24）、補題preflight10件は別記録。
著者側検査が発見した旧preflight例外分類の欠陥も保持した。実際の10件はすべて成功し、
誤分類された不利結果はない。最終runnerはvalidator assertionをFAILUREとして扱う。
助手の著者側検査は独立blind reviewではない。

MANIFEST SHA-256:
`fe9ffb7f6312d9f2f0f4b7172fc680f16e06239ae3863343ce30e46bfb007782`。
RAW SHA-256:
`2f7cc40c5c79be36e402b9baccb5a0015562d1104111457089179b12bead5634`。
36固定fileと全4,232保存artifactのhash・bytes・入力順序を事後に照合した。
モデル正当性、新規性、実用的重要性、採択可能性、投稿準備完了を本結果から認定しない。
