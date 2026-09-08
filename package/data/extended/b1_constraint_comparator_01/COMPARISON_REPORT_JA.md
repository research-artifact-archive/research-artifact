# B1指定予算の強い比較結果

固定した78の新入力で、CP-SATは78 SUCCESS、単純subset DPは56 SUCCESS/22 TIMEOUT、全予算hybrid構築＋独立検証＋B1 queryは53 SUCCESS/25 TIMEOUTだった。234 unit、294.236307秒、FAILURE/INVALID/NOT_RUNは0。共通成功値の不一致は0。全raw SHA-256は0b741079c686c7dde9eaaf7d7328410e22a5aededd7f964ebe990bc6bc1c0f33。5秒cold wall/1GiB上限であり、初回import・構築・serialization・検査を含む。

この後、既存上下界・cheapest-fast dominance・固定順序のfeasible incumbentで探索を省くDPを追加した。観測後に設計した別method extensionで、既存234 unitを引き直していない。8,634既知の開発入力すべてで最適値が一致してから、同じ78入力を一度ずつcold実行した。68 SUCCESS/10 TIMEOUT、57.929821秒、他statusは0、不一致0。raw SHA-256は6ac713f25c541ec8b303cd88e329d92c9940ea799d58370b9739905450c1eb03。成功68のうち62は根で上下界が一致し、状態を展開しない。単純DPを最強比較と扱わないための追加であり、held-out評価ではない。

| 方式 | 成功/78 | timeout | 成功cold中央値 | 返却対象 |
|---|---:|---:|---:|---|
| CP-SAT | 78 | 0 | 0.310秒 | B1の順序・mode証明書 |
| 上下界DP | 68 | 10 | 0.064秒 | B1の順序・mode証明書 |
| 単純subset DP | 56 | 22 | 0.058秒 | B1の順序・mode証明書 |
| 全予算hybrid＋検証 | 53 | 25 | 0.061秒 | 全整数予算の曲線・方策とB1値 |

成功分母が異なるため、この中央値を全入力での速度比較へ使わない。CP-SAT対上下界DPの共通成功68ではCP-SATのcold時間が短いのは4件。CP-SATは大きい範囲を解くが、小入力ではPython/solverのcold import負担を含む。全予算側の成功53はideal39/ordered14であり、CP-SATより速い共通成功は40件。この出力範囲の相違を消して一律の優劣を主張しない。

普通の五shape×四size×三priceの60入力はCP-SAT/上下界DPが全て解く。残る18はhardness還元を意図的に使った入力であり、CP-SATは18/18、他三方式は8/18、各10timeout。CP-SATが解いた最大入力は79jobs。入力生成・全群分母はBENCHMARK_PLAN.mdとbenchmark01/INPUTS.json、全集計はCOMPARISON_ANALYSIS.jsonに保持する。人工shape/価格と還元例であり、実アプリケーションでの頻度・elapsed-time改善・B>=2または全予算のCP性能を示さない。

単一予算だけが必要な場合、全予算compilerを必須または常に優位とする主張は支持されない。B1には上下界判定と制約solverという安い/強い選択肢がある。本文ではこの不利な境界を採用し、全予算の返却物・cost-compatible高速class・primitive対応との役割を区別する。
