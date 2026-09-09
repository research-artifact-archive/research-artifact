# 共通料金・共通倍率の固定順仮説：有限入力では全曲線一致

17,424固定authored inputsを51.569秒で実行し、全てSUCCESS。独立ジョブの全予算曲線と、仕事量wの昇順へ固定したchainの全予算曲線は17,424/17,424で一致した。双方の証明書をserialize/reload後に独立affine checkerで検査し、b=0..8の各156,816要求値を別scalar recurrenceでも照合した。反例input0、failure/timeout/invalid/not-run0。3解析対照は期待どおり：昇順excess8、降順12、cachedなし12（全体倍率4、baseline28）。

対象はn2..5、w multiset{1,2,4,7}、lambda9値、共通v/k各4値の積である。価格とworkを全て4倍し整数化し、vertex identityを回転した。これは既存格子と重なる可能性のある著者探索であり、独立application populationではない。全予算一致は各固定inputに限り、任意n・任意共通価格に対する順序定理を証明しない。

一般の異種料金でc順が不利だった16既存input、その他の旧不利結果、JMHで全pfit0だった結果は変更しない。今回の仮説はpaper67に採用していない。正しい交換証明または反例を別に調べる。

RAW SHA-256:b74abaf1256c3ac7f765321b4dc5856e5f9c2d7503f09b7037d58059c44f48fc。
