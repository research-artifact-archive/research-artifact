# 最近接研究から何がそのまま得られ、何に追加の論証が必要か

著者側の限定一次資料比較である。広い先行研究の不在証明や独立blind査読ではない。今回の重要な結論は、retry/cache/guard、保護量とlock回数、頑健DP、有限予算の最適化という発想自体を新規性へ数えないことである。追加の貢献は、正確な操作範囲における価値の正規形、同じ方策の全B同時保証、閉形式と表現・計算量の論証に置く必要がある。

| 一次資料と読んだ箇所 | すでに与えるもの | 本稿の保証までに追加で必要なこと |
|---|---|---|
| Kung–Robinson1981 §3.3/p220 | validation失敗が繰り返されたtransactionを、同じcritical-section semaphoreを保持して再実行し完了させる機構 | cached fallbackの再発明ではない。複数のpersistent job、全因果call program、Q≤n+rを満たす集合の各Bの最悪L、Bを受け取らない同一方策の同時達成を示す |
| Černýほか2011 §2.1–2.3, §4.2/Theorem6 | 有限変数・partial concurrent program、guard/CAS等の選択、schedulerとweighted automatonを合成したlimit-average安全性最適化。定理6は確率分布と重みを一致させるbisimulation商の値を保存する | 有限実行のworst total costとL/Qを使う状態/目的のencoding、実write予算の条件、全Bの同一方策、およびretained preparationを含む初期価値のlower boundが必要。本稿のpotentialはaction-wise不等式であり、中間状態のbisimulation/最適値等号ではない |
| Černýほか2015 §6.1–6.2/Thm6.1–6.2 | lock配置の静的statement数/保護statement数をMaxSMTで最適化。さらにblock費用・contention・acquisition頻度のprofilingに基づく統計的性能モデルを最適化 | 単にLとQを測ることは追加ではない。本稿のL/Qは有限実行中の動的課金で、上限Bごとの最悪値とuniversal call capを同時に課す。平均時間の校正が成立するとは限らず、独立到着測定も定理の時間版ではない |
| 同著者2017 FM-SD §4.3.5, §9, §10（公開本文） | 2015 CAVの拡張。preemption-safe、既存にないdeadlockを導入しないlock配置、静的目的の最適化。性能profiling版は別の継続研究として引用 | sourceの意味保持とdeadlock条件は既存合成が重視する中心事項。本稿はその一般的なsource変換保証を持たず、Roslynの限定経路と著者側検査に留まることを明示する |

**導出可能性についての判断。** 有限のn,B,rと有限価格を固定し、操作を明示したstate graphへ展開すれば、一般的なweighted-game/constraint手法で個別の値や候補方策を調べる余地はある。既存frameworkには本問題を表現できない、という主張はしない。一方、そのencodingを列挙することだけでは、本稿の全B同時の閉形式、全因果programに対する初期lower bound、budgetの数値に依存しないfinite slope-basis構築、価格条件付きのO(|E|+n log n) compilerは得られない。これらを支える各証明が追加の仕事である。追加がFSE上十分大きいかは別の評価問題として残る。

**誤解を防ぐ二点。** 2011の終端実行は初期状態へ戻すことでlimit-averageを定義し、元有限実行の平均を測る。これは本稿の累積費用と同じ量ではないが、一般手法を別目的へ拡張できないことの証明でもない。2015のprofilingは実行環境・入力/oblivious schedulerを前提とし、費用モデルは統計的で常に正しい予測を保証しない。未知Bと未校正価格を一つの情報不足へ混ぜない。

今回再読した固定PDFは、2011 `primitive_reduction_source_01/CERNY2011_PRIMARY.pdf` SHA256 e0c5a9b76cce9e9465d33c9d4c1bc69fab364dc3fcaaba1e9001b84542e4f8de、2015 `synchronization_quality_source_01/cerny2015v1.pdf` SHA256 f76080fd02eb6b17f7000a82006937ac994ef6c4e3e82c6a66dacb553186898d（双方RESUMED_20260907_1942配下）。2011の著者ページはNEXP主張をPSPACEへ訂正しており、旧abstractをそのまま引用しない。

一次リンク：[Kung–Robinson著者版](https://www.eecs.harvard.edu/~htk/publication/1981-tods-kung-robinson.pdf)、[2011著者ページ・erratum](https://www.microsoft.com/en-us/research/publication/quantitative-synthesis-for-concurrent-programs/)、[2015 arXiv](https://arxiv.org/abs/1511.07163)、[2017公開論文](https://link.springer.com/article/10.1007/s10703-016-0256-5)。2017は2015 arXivの置換と断定せず、本文自身の系譜記載に従う。Neiderほかの最適resilience研究は既存引用として保持し、今回のweb abstract検索だけから追加の非包含claimを作らない。
