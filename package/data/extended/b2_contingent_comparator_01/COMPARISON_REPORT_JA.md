# B2指定予算と全予算の比較

開発ではCP-SATと独立scalar/contingent-policy checkerが4,336/4,336一致（10.556302秒）。上下界DPと独立emitted-policy checkerも同じ4,336入力で一致（0.288717秒）。三つの明示的empty/zero-premium/repeated-failure入力、5選択scale、既知semantic4,232とlabel96を保持する。各checkerの不正4構造は全て拒否。これは既知/選択入力による開発であり、held-outまたは一般定理の機械証明ではない。

入力・code・全分母固定後の新48入力×3方式=144cold unitでは、CP-SAT48 SUCCESS、上下界DP48 SUCCESS、全予算hybrid構築＋独立検証46 SUCCESS/2 TIMEOUT。その他statusと共通成功値の不一致は0。5秒/1GiB、one worker、初回構築/出力/検査込みで、全体57.277070秒。raw SHA-256 70a47ca77fbf6ad14bd163804b6d4c42edb4b611727335ed93291c3a0e76094d。

| 方式 | 成功/48 | timeout | 成功cold中央値 | 成功worker中央値 |
|---|---:|---:|---:|---:|
| CP-SAT | 48 | 0 | 0.529秒 | 0.462秒 |
| 上下界DP | 48 | 0 | 0.058秒 | 0.000803秒 |
| 全予算hybrid＋検証 | 46 | 2 | 0.058秒 | 0.0140秒 |

CP-SATは全48共通成功で上下界DPより遅い。上下界DPは21入力を根だけで閉じ、最大探索701状態、出力方策最大17node。CPモデルは最大13,252変数/25,727制約。48中27でV>L、18でV<U、15でL=U。全予算側はideal42/ordered4成功；time out2件はいずれも五つの独立な四-job block（BASEとPREMIUM_WIDE）である。全予算側46共通成功中、上下界DPがcoldで速いのは31件だが中央値比は1.003であり、50ms polling/起動費用近傍の差を精密な速度差としない。

24入力は既知の四-job familyをdisjoint/serial/sparseに2–5個組み合わせたもの、24入力は新たなfence/layered/forward graphと価格。外部用途の標本ではない。PREMIUM_WIDEの保護premiumは2^40倍で、同じ費用改善を持つfamily scalingとは区別する。全予算出力と指定B2方策の返却範囲は異なり、一律の優劣を主張しない。

指定予算が小さい場合、一般DAGでも全予算ideal compilerより上下界DPが有用なことを示す。CP-SATを含めたspecified-budgetの選択肢を明記し、全予算の利点を大きい/複数予算の返却物に限定する。CP scenario-tree定式化自体の新規性、一般all-budget optimized-solver superiority、実アプリケーションの工数/latency効果は主張しない。
