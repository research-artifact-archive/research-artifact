# E5: proposed EVIDENCE_LEDGER append

Insertion proposal only; no file in paper/ or paper/materials/ is edited. Paths below are within experiments/witness_20260929/e5/.

E5一次集計は18入力/要件ペア：証人 0、両LOSS 6、両WIN 2、その他 10。その他内訳は {"incomplete": 10}。54セルの終端内訳は {'WIN': 4, 'LOSS': 12, 'TO': 9, 'NOT_RUN_DEADLINE': 29}。

54計画セル中25を試行し、29セルは期限未実施。両版にWIN/LOSSが得られたのは18ペア中8ペアであり、未確定ペアまで判定差がないと結論しない。Direct-Fullは18計画セル中0試行。未開始セルは事前登録した固定順で待機中に15:39 JSTの開始締切を迎えたためで、実行中の最後のセルは1,200秒上限を維持した。deadlineの判定と次の未開始jobは `raw/deadline_reached.json`、実終了は `raw/runner_finished.json` に保存。新しい試行を期限後に追加していない。

- 証人: none
- 両LOSS: Industry/Base, Industry/R1, MetaSocket/Base, MetaSocket/R1, PowerPlant/Base, PowerPlant/R1
- 両WIN: GSM/Base, GSM/R1
- その他: PC1/Base, PC1/R1, PC2/Base, PC2/R1, Railcab/Base, Railcab/R1, Surveillance/Base, Surveillance/R1, Workflow/Base, Workflow/R1

9モデルの内訳（Base/R1を混ぜて重複計数しない）: GSM: Base=null, R1=null; Industry: Base=bothLOSS, R1=bothLOSS; MetaSocket: Base=bothLOSS, R1=bothLOSS; PowerPlant: Base=bothLOSS, R1=bothLOSS; PC1: Base=other, R1=other; PC2: Base=other, R1=other; Railcab: Base=other, R1=other; Surveillance: Base=other, R1=other; Workflow: Base=other, R1=other。

各区分に少なくとも1ペアを持つモデル数: {"witness": 0, "bothLOSS": 3, "null": 1, "other": 5}。モデル名: {"witness": [], "bothLOSS": ["Industry", "MetaSocket", "PowerPlant"], "null": ["GSM"], "other": ["PC1", "PC2", "Railcab", "Surveillance", "Workflow"]}。BaseとR1で区分が異なるモデルは複数区分に現れうるため、これらモデル数を足して18ペアや9モデルの分母を置き換えない。

|入力/要件|元none|initial 細粒度|initial 併合|initial DF|区分|
|---|---|---|---|---|---|
|GSM/Base|WIN|WIN / 18 / r=10|WIN / 18 / r=10|NOT_RUN_DEADLINE|null|
|GSM/R1|WIN|WIN / 33 / r=10|WIN / 33 / r=10|NOT_RUN_DEADLINE|null|
|Industry/Base|WIN|LOSS / 13804 / L=13804|LOSS / 13804 / L=13804|NOT_RUN_DEADLINE|bothLOSS|
|Industry/R1|LOSS|LOSS / 11865 / L=11865|LOSS / 11865 / L=11865|NOT_RUN_DEADLINE|bothLOSS|
|MetaSocket/Base|WIN|LOSS / 37 / L=37|LOSS / 13 / L=13|NOT_RUN_DEADLINE|bothLOSS|
|MetaSocket/R1|WIN|LOSS / 47 / L=47|LOSS / 17 / L=17|NOT_RUN_DEADLINE|bothLOSS|
|PowerPlant/Base|WIN|LOSS / 2724 / L=2724|LOSS / 1412 / L=1412|NOT_RUN_DEADLINE|bothLOSS|
|PowerPlant/R1|WIN|LOSS / 10809 / L=10809|LOSS / 5859 / L=5859|NOT_RUN_DEADLINE|bothLOSS|
|PC1/Base|WIN|TO|TO|NOT_RUN_DEADLINE|other/incomplete|
|PC1/R1|WIN|TO|TO|NOT_RUN_DEADLINE|other/incomplete|
|PC2/Base|WIN|TO|TO|NOT_RUN_DEADLINE|other/incomplete|
|PC2/R1|WIN|TO|TO|NOT_RUN_DEADLINE|other/incomplete|
|Railcab/Base|WIN|TO|NOT_RUN_DEADLINE|NOT_RUN_DEADLINE|other/incomplete|
|Railcab/R1|WIN|NOT_RUN_DEADLINE|NOT_RUN_DEADLINE|NOT_RUN_DEADLINE|other/incomplete|
|Surveillance/Base|WIN|NOT_RUN_DEADLINE|NOT_RUN_DEADLINE|NOT_RUN_DEADLINE|other/incomplete|
|Surveillance/R1|WIN|NOT_RUN_DEADLINE|NOT_RUN_DEADLINE|NOT_RUN_DEADLINE|other/incomplete|
|Workflow/Base|WIN|NOT_RUN_DEADLINE|NOT_RUN_DEADLINE|NOT_RUN_DEADLINE|other/incomplete|
|Workflow/R1|WIN|NOT_RUN_DEADLINE|NOT_RUN_DEADLINE|NOT_RUN_DEADLINE|other/incomplete|

各完了セルは判定 / 発見状態数 / r=返却方策rankまたはL=返却敗北証明書状態数。空欄やTO/期限未実施を0としない。元noneはE1表で参照した旧Lazy初回rawで、E5新JARや時間と混同しない。DFとLazyの比較可能数は0、判定不一致0。元の非制限契約との比較は別集計: {"comparable_pairs": 8, "changed_pairs": ["Industry/Base", "MetaSocket/Base", "MetaSocket/R1", "PowerPlant/Base", "PowerPlant/R1"], "scope": "New initial-domain restriction versus existing unrestricted original contract; distinct from separate-versus-merged E5 classification."}。

両LOSSは、この一様制限の下で細粒度でも完了を保証できず、粒度による判定分離の証拠にはならない。両WINはnull、細粒度WIN/併合LOSSのみ証人に数える。逆転・TO・期限未実施・INVALIDは3区分に押し込まない。未解決の検査事項: なし。

**物理transfer対数（独立source audit）**

|入力|元の物理対数|initial後の物理対数|
|---|---:|---:|
|GSM|8|1|
|Industry|16|3|
|MetaSocket|3|2|
|PowerPlant|4|2|
|PC1|7|1|
|PC2|14|2|
|Railcab|11|4|
|Surveillance|16|2|
|Workflow|12|5|

合計22component、旧物理90状態、全域91対→initial22対。多値関係が1つあるので全て「写像」とは呼ばない。compiled censusとの照合状況: {"component_comparisons": 32, "passed": 32, "failed": 0, "census_shape_errors": [], "models_observed": ["gsm", "industry", "metasocket", "powerplant"], "scope": "Independent source inventory/parsed relation counts versus actual compiled raw-projection counts; observer-augmented counts are not predicted by source counts."}。未実測censusをsource数で補わない。observer付きのaugmented対数はCSVのoriginal_pairs/retained_pairsで別記録し、上表のphysical対数と混ぜない。

**両LOSSの証明書由来の1文**（none側を以下に示し、merged側もloss_reasons.csvに保存。最大3rootの局所閉包根拠であり、一意な全ゲーム因果説明ではない。）

- Industry/base: The checked certificate contains 13804 discovered states (3250 unsafe), including 131/131 initial states; among its 3 reported root examples (at most 3), 3 have an enabled uncontrollable action with an outcome in the certificate and 0 have a nonempty set of enabled controllable actions all with such an outcome, while locally disabled pending-transfer components observed in these samples are 1:DSD1_OLD, 2:GATEFORM1_OLD (local closure evidence, not a complete causal explanation).
- Industry/r1: The checked certificate contains 11865 discovered states (8292 unsafe), including 131/131 initial states; among its 3 reported root examples (at most 3), 3 have an enabled uncontrollable action with an outcome in the certificate and 0 have a nonempty set of enabled controllable actions all with such an outcome, while locally disabled pending-transfer components observed in these samples are 1:DSD1_OLD, 2:GATEFORM1_OLD (local closure evidence, not a complete causal explanation).
- MetaSocket/base: The checked certificate contains 37 discovered states (10 unsafe), including 4/4 initial states; among its 3 reported root examples (at most 3), 1 have an enabled uncontrollable action with an outcome in the certificate and 2 have a nonempty set of enabled controllable actions all with such an outcome, while locally disabled pending-transfer components observed in these samples are 0:IO_OLD (local closure evidence, not a complete causal explanation).
- MetaSocket/r1: The checked certificate contains 47 discovered states (20 unsafe), including 4/4 initial states; among its 3 reported root examples (at most 3), 1 have an enabled uncontrollable action with an outcome in the certificate and 2 have a nonempty set of enabled controllable actions all with such an outcome, while locally disabled pending-transfer components observed in these samples are 0:IO_OLD (local closure evidence, not a complete causal explanation).
- PowerPlant/base: The checked certificate contains 2724 discovered states (928 unsafe), including 10/10 initial states; among its 3 reported root examples (at most 3), 2 have an enabled uncontrollable action with an outcome in the certificate and 1 have a nonempty set of enabled controllable actions all with such an outcome, while locally disabled pending-transfer components observed in these samples are 0:MAINTENANCE_OLD, 1:ENV_OLD (local closure evidence, not a complete causal explanation).
- PowerPlant/r1: The checked certificate contains 10809 discovered states (7529 unsafe), including 10/10 initial states; among its 3 reported root examples (at most 3), 2 have an enabled uncontrollable action with an outcome in the certificate and 1 have a nonempty set of enabled controllable actions all with such an outcome, while locally disabled pending-transfer components observed in these samples are 0:MAINTENANCE_OLD, 1:ENV_OLD (local closure evidence, not a complete causal explanation).

未完了・失敗セル: PC1/base/lazy_none_initial=TO, PC1/base/lazy_transfers_initial=TO, PC1/r1/lazy_none_initial=TO, PC1/r1/lazy_transfers_initial=TO, PC2/base/lazy_none_initial=TO, PC2/base/lazy_transfers_initial=TO, PC2/r1/lazy_none_initial=TO, PC2/r1/lazy_transfers_initial=TO, Railcab/base/lazy_none_initial=TO, Railcab/base/lazy_transfers_initial=NOT_RUN_DEADLINE, Railcab/r1/lazy_none_initial=NOT_RUN_DEADLINE, Railcab/r1/lazy_transfers_initial=NOT_RUN_DEADLINE, Surveillance/base/lazy_none_initial=NOT_RUN_DEADLINE, Surveillance/base/lazy_transfers_initial=NOT_RUN_DEADLINE, Surveillance/r1/lazy_none_initial=NOT_RUN_DEADLINE, Surveillance/r1/lazy_transfers_initial=NOT_RUN_DEADLINE, Workflow/base/lazy_none_initial=NOT_RUN_DEADLINE, Workflow/base/lazy_transfers_initial=NOT_RUN_DEADLINE, Workflow/r1/lazy_none_initial=NOT_RUN_DEADLINE, Workflow/r1/lazy_transfers_initial=NOT_RUN_DEADLINE, GSM/base/df_none_initial=NOT_RUN_DEADLINE, GSM/r1/df_none_initial=NOT_RUN_DEADLINE, Industry/base/df_none_initial=NOT_RUN_DEADLINE, Industry/r1/df_none_initial=NOT_RUN_DEADLINE, MetaSocket/base/df_none_initial=NOT_RUN_DEADLINE, MetaSocket/r1/df_none_initial=NOT_RUN_DEADLINE, PowerPlant/base/df_none_initial=NOT_RUN_DEADLINE, PowerPlant/r1/df_none_initial=NOT_RUN_DEADLINE, PC1/base/df_none_initial=NOT_RUN_DEADLINE, PC1/r1/df_none_initial=NOT_RUN_DEADLINE, PC2/base/df_none_initial=NOT_RUN_DEADLINE, PC2/r1/df_none_initial=NOT_RUN_DEADLINE, Railcab/base/df_none_initial=NOT_RUN_DEADLINE, Railcab/r1/df_none_initial=NOT_RUN_DEADLINE, Surveillance/base/df_none_initial=NOT_RUN_DEADLINE, Surveillance/r1/df_none_initial=NOT_RUN_DEADLINE, Workflow/base/df_none_initial=NOT_RUN_DEADLINE, Workflow/r1/df_none_initial=NOT_RUN_DEADLINE


新source commit `5603a4366f3fe5237d2a7ef34cb9cc40f184bbf3`、base `c7294d6e0c834b03430fc66e4055eb5b2d0342fb`（E1 production `50563fc45bd4d3870a48318944a83ccf2bcf4676`との差はaudit testのみ）。新JAR SHA `00221f6a91f382179186286a70ea99474ae50d07f0ad241212324b0430ad08da`、build/run JDK17、Maven package成功、76テスト（新9本を含む）PASS。コミット間の実装差分は `build/e5_source_delta.patch`（5ファイル、405行追加/3行削除、SHAと統計は `build/e5_source_delta.json`）。最初のテスト記述ミス1件と修正ログも保存。none GSM CLIは旧E1とWIN/31状態/27query/rank4で一致。Post/独立意味論/solver/component/Linkの6sourceがE1とbyte同一であることをrootが検査した。

CLIは元物理状態の初期値を比較し、内部付加observer座標を初期値へ制限しない。genericAPIでは通常のstate equality。既存full CellのAはinitial=h、g_A={e→e}なのでこのliteral規則で空になる。指定の「Cell不変」期待は成立せず、特例を作らずWIN→LOSSと契約差をテストに残した。初期状態が既に唯一の転送域である別の小fixtureでは不変を検査済み。

AI利用のmethods追記対象: AS-8を受けた規則の解釈・前処理/診断/テストの実装、実験スクリプト、実行管理、表と本文案の生成、別担当によるsource/raw/CSV照合をAIが支援した。「独立監査」はcampaign analyzerをimportしない別実装の検査を指し、外部の人間による追試ではない。最終解釈と本文への取込みは主担当/著者が行う。

全域性だけから併合でLOSSが原理的に起こらないとは結論しない。UC優先・要件安全・goal到達は別条件である。初期状態のみという一様proxyは、Kramer–Mageeのtransaction静穏性を直接検証するものではない（[原論文 Sec.III-D, p.1296](https://arwana007.wordpress.com/wp-content/uploads/2013/11/the-evolving-philosophers-problem.pdf), DOI [10.1109/32.60317](https://doi.org/10.1109/32.60317)）。構成や入力を結果に合わせて変更していない。


## RQ2 paragraph (four sentences)

The nine application models underlying the 27 Base/R1/R2 benchmark instances have 22 transfer relations covering all old physical states of their respective components, and the earlier E1 campaign found no decision changes in 54 merged Base/R1 trials; totality removes the physical transfer-domain obstruction but does not by itself prove preservation of realizability. We uniformly restricted transfers to each old component's physical initial state, retaining observer histories and leaving requirements, endpoints, and Post/goal semantics unchanged. Among 18 Base/R1 model/requirement pairs, the recorded results contain 0 separate-WIN/merged-LOSS witnesses, 6 both-LOSS pairs, and 2 both-WIN null results, with 10 pairs outside these three groups (10 incomplete). These are initial-state contract variants inspired by quiescence, not a validation of DSU quiescence or a DUCS encoding.

## Threats sentence

The variants and constructed examples provide evidence of existence where separation is observed, not estimates of its prevalence in applications.

## Provenance and columns

`results.csv` は全54セル、`pairs.csv` は18ペアの分類、`models.csv` は9モデルのBase/R1内訳、`components.csv` は実測component別census、`source_domains.csv` は独立静的原典監査、`loss_reasons.csv` は各LOSSの証明書由来の1文と元JSON。`table_e5_states.tex` / `table_e5_metrics.tex` / `table_e5_domains.tex` がS1/S4用。`original_*`は旧基準だが、`original_pairs`等のtransfer census列は制限前の同じ入力の対数である。`*_physical_*`はobserver座標を除いた物理投影、接尾辞なしのpairs/domain_statesはcompiled augmented状態で数える。`worst_completion_rank`は返却WIN方策の完了上界で最適値とは限らず、`losing_region_states`は返却した発見済敗北領域で全ゲームの最大敗北領域ではない。秒はMacの参考値でXeonや旧JARとの速度比較は行わない。LOSS診断時間は後段の別metric。`validation_errors`と`other_detail`に検査不合格・逆転・未完を残す。rawの絶対local command pathは非公開来歴であり、将来公開する場合は原本を残した別コピーで正規化する。今回pushなし。


## Final verification

Derived-table checks and the separate raw/table audit passed after the last trial; all 54 scheduled rows are retained, including 9 timeouts and 29 deadline-limited non-runs. The three LaTeX fragments compile to three pages without warnings. Receipts: `build/final_tables_ready.json`, `build/final_independent_review.json`, and `build/handoff_anonymity_check.json`. The earlier stale-table audit failure is retained separately. The run ended at 15:51:03 JST, reporting was generated at 15:52:15 JST, and the continuation heartbeat was paused after finalization.
