# Cost-compatible DAG hybrid01 探索結果

2026-09-08 01:49 JST。全実行終了。入力とソースは MANIFEST.json に結果前固定した。新規性・実アプリ適用・最終評価を確立した記録ではない。

725 small units は全件 SUCCESS: 643 既存入力の回帰、76 新規境界入力、6 不正入力の拒否。正規719入力のうち221が新しい順序固定経路、498が既存 ideal 経路。68,497方策セルで値とreadinessが一致し、643入力の旧root曲線との全予算一致も検査した。所要0.733秒。旧入力は新しい独立分母ではない。

scale は新規48入力＋旧scale中で経路が変わる9入力、各compile/checkの114 units。新規48件はすべて構築成功、全予算checkerは40成功・8 TIMEOUT。旧9件は構築・checkerとも成功。各unit上限10秒、sampled RSS 1 GiB、全体133.416秒。失敗・invalid・unstartedは0。TIMEOUTは全4形状の4096/32768 jobsかつWIDE_Cで、各suffix曲線の再構成が重い。最大32768 jobs、最大30248 positive runs、最大5,356,484 controller bytes（入力DAGを含む）。新規48件のロード・構築・JSON保存時間の最大は0.415秒、sampled worker RSS最大116,621,312 bytes。単発探索測定でありproduction速度を主張しない。

旧scale87件中、構造条件を満たしたのは独立8/12/16 jobs×3価格の9件だけ。残る78件は再実行せず旧receiptへ結ぶ。旧9 compiler TIMEOUTと4 checker TIMEOUTは旧実装の結果のまま保存する。新packed outputはroot曲線＋cursor方策を返し、旧generic outputの全ideal曲線とは出力契約が異なる。混合集計や同一certificate出力の速度比として扱わない。

著者側read-only確認ではcorollary、equal-cost topological tie、packing、全予算のaction optimalityに反例なし。ただし旧checkerはearliest protection-first thresholdの一致までは証明しない。cp=[[1,1]]、threshold2の方策も最適なので受理し得る（生成された値はthreshold1）。これはvalue/policy保証を覆さないが、canonical thresholdの検査と呼ばない。入力IDと元値の対応はmanifest内のexact INPUTS/旧controllers/旧RAWと実行入力に基づく。Pythonは-Oを使っていない。

次は異なるchecker設計を別版で検証する。全root曲線の残りpremiumによるcapをsuffix候補として、各候補のBellman式を少数の境界条件で確認する案である。旧8 TIMEOUTを更新・削除・成功化せず、全57保存済み出力を新checkerの対象とする。単なる同じ実装の引き直しではなく、再構成を除く新しい証明・算法の検証である。
