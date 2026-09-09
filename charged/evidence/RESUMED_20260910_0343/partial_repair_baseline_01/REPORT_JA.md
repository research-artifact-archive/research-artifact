# 共通publication費用を含む探索結果

1046 footprint/weight入力、q=1..4、μ=0,1/2,1,2,4の全20,920行を4.85秒で計算し、FAIL/TIMEOUT/INVALIDは0。全600件のm≤2ケースで履歴木を直接解く別実装と一致し、二つの指定入力では各4096方策の完全列挙とも一致した。μ=0の4184行は全て前研究のretry-first最適比へ帰着した。五つの追加controlは多くが結果・入力schemaの検査であり、raw破損を投入した五つの独立semantic mutation testとは呼ばない。

正のμでretry-firstより改善したのは6行だけで、残り20,914行は同値。三つの等重みcomponent・singleton footprint、q=3/4、μが重みに比して大きい指定点に限る。代表例はweight=(1,1,1), q=3, μ=2で、比5/3から3/2へ改善した。全厳密値と方策表、同値・不利結果はrun01に保存した。

PROOF.mdは、実際のBを方策へ渡さず、観測dirty集合から算出する最小整合write数eを十分状態とする有限minimax compilerを与える。既知B optimumへμを足すだけでは全B同時最適性の境界は変わらない。今回の改善はmultiplicative competitiveという別の目的に対するものである。

これは共通費用モデルの理論的検討であり、Roslynのmerge時間・source費用をμへ校正したものではない。新規性、実用上の重要性、submission readinessは未確立。artifactには元の20,920行と全列挙結果を含め、元研究の3495入力・160,080行と混ぜず別分母で公開する。
