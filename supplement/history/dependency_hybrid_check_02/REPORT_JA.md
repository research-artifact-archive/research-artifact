# Root-cap checker02 探索結果

2026-09-08 02:00 JST。MANIFEST.jsonを結果前固定し、全実行終了。compiler再実行0、既存出力bytesを検査した別checkerである。旧checker01の49成功・8 TIMEOUTは不変。

5484 semantic units は全SUCCESS。既存のordered221出力を受理し、748個の価格ベクトルから結果前に列挙した5247候補曲線のうち、scalar全action Bellmanと一致する748個を受理、4499個を拒否した。16種の不正payloadも全て拒否。canonical thresholdを超える最適tie方策も、このcheckerではearliest protection-first規約との不一致として拒否する。所要0.134秒。この有限検査は定理証明の代わりではない。

全57保存済みscale出力（新規48＋旧データのchanged-path9）で全予算checker SUCCESS。failure/timeout/invalid/not-run0。新規コンパイルは実施していない。全57cold checker unitsの実行管理込み所要6.032秒。最大ロード・検査時間0.365秒、最大cold process時間0.412秒、sampled RSS最大116,719,616bytes。32768 jobs/30248 runs/約5.36MBの保存出力も完了した。

保全済み初回構築・JSON保存時間と新ロード・検査時間を各入力で足すと最大0.779秒、57件合計5.514秒。ただし別時点の保存済みstageの和であり、fresh end-to-end測定でもproduction latencyでもない。過去の初回実装・検査失敗を含む開発費用を消さない。

根拠はPROOF_DRAFT.mdのsuffix候補f_k=min(F,P_k)に対する全予算Bellman検査である。一般曲線構築・packingのimportなし。O(n log(r+1)+n+|E|+r)の整数算術で検査でき、bit costは別途残る。sorted-topological最適性・原ゲーム・Python/実行環境は依然TCBに属する。実アプリ、source-derived価格、native追加実行、最終評価または採択可能性の認定ではない。
