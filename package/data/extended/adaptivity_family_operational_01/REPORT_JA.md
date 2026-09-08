# 選択した4処理例の完全primitive / native照合

2026-09-08 03:57 JST。探索後に選択したk=1数理例の検算であり、固定最終評価の分母を増やさない。

## Complete primitive

485状態、4,040操作、5,364outcomes、5root予算0..4、30policy cells。全primitive値・独立scalar値・serialized hybrid値は16,21,24,27,28で一致。全potential/goal-rank/readiness/certificateと405subset / 205one-pass / 64budget monotonicity / 48concavity / 80cheapest-fast / 80cached-fallback checksが整合。1unit SUCCESS、FAILURE/TIMEOUT/INVALID/NOT_RUNなし。約0.02635秒。

元のimport済み科学コード全件とcaseは実行前SEMANTIC_MANIFESTへhash固定した。ただしshellへinlineで渡した約40行の呼出しwrapper自体はmanifestへ含めていなかった。これはwrapperの事前hash記録の不足として保持し、後から事前封印済みと扱わず、検査の再実行もしない。科学算法は不変のevaluate_final / evaluate / primitive / curve / certificate / lemma実装である。raw tool commandは当時の実行記録に残る。

## Native

1case、4priced roots、8layout cells、40policy cells、全110terminal paths。内訳hybrid28/fixed22/look_fast26/look_protected22/cached12。全SUCCESS、欠落/重複/parse error/unexpected ID/最大値不一致なし。全IDの元順序も一致。原Javaコードは変更せずcopyし、全case/profile/expected paths/sourceをNATIVE_MANIFESTへnative実行前に固定した。

native費用は840倍されており、下はその係数を除いた同一の仕事量指標。両bin配置の最大値は一致。

|B|hybrid|best fixed|look fast|look protected|cached|
|---:|---:|---:|---:|---:|---:|
|0|16|16|16|16|16|
|1|21|21|21|21|24|
|2|24|26|26|26|28|
|4|28|28|28|28|28|

compile0.412637秒、execute0.148902秒、checking0.013347秒。いずれもreturn0、stderrなし。方策の実時間比較ではない。NATIVE_RAW SHA256 c67bee9969958c6fa0f4e4610a8ca44c233ea14609b8c585349fc521aa5a8994。

4処理がpositive adaptive-order gapの最小規模という著者証明と、1/13 homogeneous familyの明示導出は隣のadaptivity_gap_search_01へ保存した。これはreal application、任意Javaプログラム、practical prevalence、採択、新規性認定を追加しない。旧固定192rootの2/192・最大2.0833%と旧全不利結果を保持する。
