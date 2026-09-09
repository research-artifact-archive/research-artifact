# Roslynコンパイル結果の追加conformance

6種類の背景変更×8方式×cold/warmの全96 processが73.34秒で終了した。96SUCCESS、0FAILURE/TIMEOUT/INVALID/UNSTARTEDで、結果後の入力変更・除外・native再実行はない。結果前に固定したcheckerも96件すべてPASSした。初回のsetup Python構文エラーはnative実行前の失敗として別保存し、その後のC# buildはwarning/errorとも0だった。

保持した444個のSolution snapshotを最後に検査し、warmで先にmaterializeした195個も後続変更後の値と照合した。合計2556project projectionは、宣言した入力から直接構築したCSharpCompilationの診断・emit可否・宣言型/定数・SemanticModelの参照先symbol/定数と一致した。独立なPython規則も、明示source/options/referenceと期待型・定数・CS0029/CS0103を確認する。Workspaceと直接構築oracleは同じRoslyn compilerを使うため、独立言語実装との比較ではない。

| 背景変更 | 再利用guard | 検査した意味上の効果 |
|---|---|---|
| 参照先Aのconst型int→string | eligible | B/Cの参照symbolがstringへ変わり、int返却bodyにCS0029が出る |
| 参照先Aのconst値1→7 | eligible | B/CのSemanticModelが新しい定数7を返す |
| 無関係Dのconst変更 | eligible | Dだけが9となり、B/Cの意味を変えない |
| Bのpreprocessor symbol ALT追加 | ineligible | Bだけ別branch/返却型を選択。背景直後の期待CS0029と前景後の正常化を確認 |
| CからAへのproject reference削除 | ineligible | CだけにCS0103が出て、前景更新後も参照切れを保つ |
| B/Cへの競合linked-text更新 | ineligible | 競合文書を先に更新し、その後の前景新textを両projectへ反映する |

再利用の適格/不適格は各12件（3種類×r0/1×cold/warm）。適格rebaseはQ=1、outside transformation=1、inside full transformation=0、protected merge=1だった。不適格rebaseはthree-modeの宣言された一変更スケジュールの資源値へ戻った。構文解析設定やproject参照の変更も含むため、これらの件数は固定検査scheduleの観測であり、main theoremの固定job-DAGへの自動移転ではない。

八つのraw corruptionは全て拒否された。native出力の両側（actualとdirect-oracle）を同じ誤ったsymbol型・定数に変えても、Pythonの宣言済み期待値規則が検出する。その他は診断削除、保持source破損、背景変更数、rebase counter、final snapshot欠落、snapshot重複である。

これは文書/イベントprojectionに加えてcompiler依存状態の一部を検査するもので、全Roslyn source generator、analyzer、custom loader、任意host、全内部cacheのequivalenceを証明しない。新たな実行時間の比較・production負荷・人対象評価ではない。元の意味検査592件、再入55件、到着5664件と別の96件として扱い、共有compiler/snapshotの複数projectionを独立sample数へ膨らませない。
