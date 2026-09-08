# 共通価格の5仕事反例: complete primitiveとJava検証

探索後のselected witnessはc=(8,2,4,2,6),p=(12,3,6,3,9),E={0→1,1→3}。保護premium p_iは全仕事でnormal work c_iの1.5倍、保護した総kernel costは2.5倍。B=4で通常仕事量を含む最悪値は適応48、全20固定順序の最良値49。5仕事で可能という例であり、最小仕事数・最大gapの定理ではない。

未変更complete primitive checkerでbudgets0..4を実行し、3,625状態・48,630actions・67,711outcomes、全potential/rank/lemma検査、75保存方策choiceに矛盾0。5根はprimitive/scalar/serializedで22,30,38,44,48。全予算の16状態59segment証明書も旧checkerと新policy-aware sweepの両方を通過。1単位SUCCESS、adverse0、0.351秒。Artifact SHAf632d77cb569aeaf28905cdf37d134b0e212fe630384e2fff76b1dded4f961c8。

nativeはbudgets0..4×distinct/colliding×5policyの50cell、事前固定746全terminal pathsがSUCCESS。全ID順序・出力・世代・captured parents・action・work・write・最大値が一致し、欠測/invalid/失敗/timeoutは0。Java実装は旧final評価と同一。d=24、全q_i=36なので24W+36Hを測り、抽象値の192倍となる。B4のtotalはhybrid/fixed/look_fast/look_protected/cached=48/49/49/49/55で両layout一致。準備・compile・実行・検査は別時刻記録に残る。rawSHA16eee38af6d3449340092f9e29974562200f15fd7f490313bce5be67ceba7745。

これは探索後選択例の意味論・実装検査であり、独立population、blind査読、人対象評価、実適用、価格校正、実時間改善の立証ではない。元48DAG/192根native最終評価・その2根だけのfixed-order gain・全過去adverseを変更しない。
