# Roslyn の契約と研究への帰結

対象は公開pin `6c4a46a31302167b425d5e0a31ea83c9a9aa1d09`のWorkspace.SourceText更新経路である。実ソースの変換をwhole・純粋・一定費用の抽象kernelと自動的に同一視しない。今回のソース調査、再入反例、修正、イベント検査、独立到着測定は、その移転条件を分けて評価する。

## 上流がすでに区別している問題

[PR42228](https://github.com/dotnet/roslyn/pull/42228)の議論は、外部/virtual呼出し中にserialization lockを保持する問題と、更新通知の順序を保つ必要を同時に扱う。特に[変換とlockの議論](https://github.com/dotnet/roslyn/pull/42228#discussion_r390022557)は、source変換を外で行う意図と既存virtual APIによる移行の難しさを説明する。[イベント順序の指摘](https://github.com/dotnet/roslyn/pull/42228#discussion_r392485165)を受け、通知はlock内へ戻された。現在のpinも、transform、publication、同期callback、queued eventを一律に同じ段階とはしていない。従って「lock内fallbackなら元の意味をそのまま保つ」とは言えない。

[PR74189](https://github.com/dotnet/roslyn/pull/74189)は、solution更新の再試行とmutableなproject更新状態に関係するmetadata referenceの欠落を修正する。source generator起因の更新が別のproject-system gateに従わないことが動機にある。ここから、変換の再実行に対する状態管理と、保護内へ移せるかどうかは別の義務と読む。これは当該PR全体の再現実験ではなく、保存したbody/filesと対象sourceの著者側照合である。

## 対象実装に課す具体的な義務

| 段階 | 要求 | 今回の扱い |
|---|---|---|
| 準備・再実行 | input Solutionを基準にやり直し、前attemptの変更通知scratchを混入させない | OnAnyDocumentTextChangedのupdatedDocumentIds.Clearを各transformの先頭に保つ |
| 保護内の再計算 | lockを再取得するhost/virtual呼出しを新たに導入しない | 同一text no-opをロック外で識別。missing-documentのGetDocumentNameは捕捉Solutionを保持してロック外へ延期する |
| publication | 最新の旧Solutionから一つの新Solutionを公開し、背景の既完了更新を失わない | 旧/新payload連鎖、リンク文書content、背景version、callbackのDocument.Project.Solutionを照合 |
| 通知 | linked target-first順序、旧/新payloadの同一性、即時/queued通知の一致 | forced semantic178件とindependent-arrival各件のnative/checkerで検査 |
| 完了後の保持 | 過去のcaptured/published Solutionを後続writerが変えない | 保持snapshotと4,016未変更文書のtext identity/version/metadataを検査。全内部cache・compiler状態の完全証明ではない |
| 資源対応 | admission、outside/inside transform、総変換、時間を区別 | 正常終了経路のQとtransform数を移転。lazy解析、VersionStamp、管理処理のため固定weighted work/価格最適値は移転しない |

missing-document再入ではpatch03の14件中4件がTIMEOUTし、patch04で同じ14件が完了した。これは今回作成したhostでの反例で、上流で発見されたbugや原ソースのbugとは呼ばない。抽象定理の純粋・終了するkernel条件への反例でもない。

## 実用上の価値について現時点で言えること

上流には短い保護区間、再試行の意味、イベント順序に具体的な理由がある。一方、対象経路のserialization callに数値的なSLA/課金上限が採用されている証拠は得ていない。r=0/2は今回の比較入力であり、Roslynが要求する値ではない。過去の別経路の1.2%CPUやUI時間の報告をこの経路の費用校正へ代用しない。

独立到着測定は、bounded callと保護変換削減が、ある到着域で背景待ちを減らす交換条件を示した。しかし集中到着では前景の総再計算が不利になり、時間差はblockによっても変わる。対象sourceで資源間の交換が無意味だったとは言えなくなったが、一般的な高速化や投稿に十分な重要性が確立したわけではない。

より強いsource操作（文書/projectごとのvalidation、差分merge、複数jobを一つの保護区間で処理する等）に対する最適性は含めない。現在の理論はopaque whole-kernel/一job一call interfaceの境界を扱う。Roslyn内部のWithDocumentContentsFromのような差分操作を追加できるなら、同じresource metricで測り直す必要があり、再実行回数という名称だけで保護下の実作業をゼロに数えてはならない。

raw source調査はQUERIES_RECEIPT.json、details01/RECEIPT.json、各API JSONに保存。新しいsource patchとnative検証は隣接roslyn_patch04_01、到着探索/順序制御validationはroslyn_arrivals_01/roslyn_arrivals_balanced_01を参照。
