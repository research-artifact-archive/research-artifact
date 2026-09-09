# Roslynの準備済み差分再利用：強い比較方式と適用境界

2026-09-10 05:40 JST。SCIENTIFIC、著者側探索。既存のpatch03/04、全不利結果、原稿111を保全する。

## 実装と意味

Roslyn既存の `Solution.WithDocumentContentsFrom` を使う保守的な比較方式を実装した。準備元と最新SolutionのIDが一致し、対象が存在し、関連document ID列が一致し、対象・関連documentを含む全project stateが同一参照の場合だけ、準備済みdocument contentを最新Solutionへ組み込む。条件外はpatch04の三方式へ戻る。途中で他projectが更新された場合にも、その最新状態を保持する。

この比較方式は一般的な差分再利用の新算法ではない。現在のwhole-kernel atomic-call interfaceより強いsource-permitted操作を具体化し、旧最適性をシステム全体へ拡大できないことを検討するための比較である。保護内マージも仕事であり、全Transformがゼロ回だからL=0、W最小とは扱わない。

source buildは成功。元174入力に58 rebase入力と4 unmodified controlsを加えた236ケースは全PASS。2,190 events、1,253 publications、2,653 retained snapshotsと、指定したuntouched state、同一・linked target、missing/deletion、no-op等の義務を検査し、12 raw corruption controlsを全検出した。新rebase armだけ、B=5/6のnormal casesで入力write数を実現する配置を実行前に変更した。旧174ケースと全58ケースの入力tupleは保持したが、全armの同一interleaving比較とは呼ばない。

別のerror/reentry 18ケースとsame-text 5ケースも全SUCCESS。patch03での4 TIMEOUTを消していない。これらは有限なpublic-state conformanceであり、任意hostや全Roslyn stateの意味保持・lock安全性の証明ではない。

## 独立到着：全3,072件

`arrivals01/PLAN.md` は実行前固定。以前と同じ4-project/4,019-document projection、32 foreground更新、64 FIFO background更新、0/10/100/1000µs間隔、r=0/2、pre-lock hookなし。unmodified、instrumented original、two0/2、three0/2、rebase0/2の8armを8 cyclic Latin blocksで実行順の位置を均衡化した。全64 processが完了。3,072 units（measurement2,560、warmup512）全SUCCESS・全checker PASS、10破損control全検出、failure/timeout/invalid/除外0。

`analysis01.py` の分母assertionに8072という転記誤りを実行前の静的確認で発見。原scriptを保全して `analyze02.py` で3072へ訂正した。native実行は引き直さず、訂正は別receiptに保存。全32 cellsと全blockの詳細は `arrivals01/analysis02` にある。

| arm | 全call Q | 保護内の全Transform | 全Transform | 保護内rebase |
|---|---:|---:|---:|---:|
| instrumented original | 18,964 | 0 | 18,964 | 0 |
| two r0 | 10,240 | 10,240 | 10,240 | 0 |
| three r0 | 10,240 | 4,274 | 14,514 | 0 |
| two r2 | 10,802 | 7,131 | 10,802 | 0 |
| three r2 | 10,786 | 3,641 | 14,427 | 0 |
| rebase r0 | 10,240 | 0 | 10,240 | 4,219 |
| rebase r2 | 10,240 | 0 | 10,240 | 4,528 |

各armは320測定batch。backgroundは対象と別projectなので、今回のrebase mismatchは全て適格であった。rを消費する失敗も保護内の全再計算も発生せず、r0/r2はこの入力族で同じ動作をする。残るマージ費用は上表の全Transformからは分からない。

100µs/r2で、three/twoのbackground p95中央値は60.00/306.10µs、block方向は7/8でthreeが低い（旧6-block studyでは6/6）。foreground中央値693.98/666.38µs、blockでは5/8でthreeが低く、 pooledとblockの方向も一致しない。0/10µsでのthree/two foreground中央値は993.54/603.88、888.10/653.00µs。一般速度改善とはいえない。

100µs/r0のrebase/three foreground中央値680.96/713.35µs、background p95は63.08/85.17µsだが、blockのforeground改善は4/8。100µs/r2ではrebase/three foreground792.83/693.98µs、background88.02/60.00µsで逆転し、blockでの改善はそれぞれ3/8、2/8だった。同じ動作をするrebase r0/r2間にも時間差があるため、ホスト・過程の変動を無視して小さい順位差を安定した効果と解釈しない。burst条件でもrebaseは全変換数が少ないのにthreeより速いとは限らない。

## 研究上の判断

三方式の全B資源定理への反例ではないが、Roslynでのwhole-system optimalityを否定する具体的な比較範囲を得た。少なくとも別projectの更新について、同じcall capで全再計算を避ける、より強い操作が実装できる。これは比較対象から省くべきではない。一方、partial mergeに要する仕事と時間が残り、全Transform数から保護時間・総仕事量・end-to-end最適性を導けないことも実測で明らかになった。

現時点でRoslynに具体的なn+r上限の数値SLAがあるとは確認できていない。source上の保護・応答性の関心と条件付きblocking効果を、quota要求の実証へ置き換えない。現稿の中心理論は、合法操作を明示した資源契約の結果として保持する。source比較は単純な利益の追加として扱わず、適用範囲と強い代替を原稿・artifactへ統合する。これだけで重要性や投稿readyを確立したとは判断しない。
