# 共有subtreeを利用するcap証明書検査

全44,838 unit SUCCESS、FAILURE/TIMEOUT/INVALID/NOT_RUNは各0。既存24,029入力を再構築したartifact hashは全て02の保存hashと同一。changed checkerで51旧corruptionを全拒否した。入力生成器・閾値・c/p・source closure・runtimeは結果前manifestへ固定した。

新しい20,758 adversarial artifactは、freshで正しいtree metadataを持つ。単一jobのp=1..12,c=1..6について、pの全非増加整数partitionと全提案threshold0..p+2を含む。加えて2つの正例/改変例対は、非共有treeの面積・support・先頭/末尾slopeを保って中間二slopeだけを変更する。計74正例をaccept、20,684不正例をrejectし、独立な直接Bellman checkerと一致した。単にmetadataエラーを検出した検査へ縮約しない。

全3.145654秒。raw SHA256 6614f3da5bcfeacac221f46034979d93aa65264e3e865053b8de9f964424c7e4。これはcheckerの反証検査であり、抽象化・cap定理や漸近計算量の機械証明ではない。checkerはconcave cap定理、検査済みimmutable node structure、exact integer/run比較に依拠し、hash衝突仮定は使わない。共有identityで飛ばせない部分は展開して照合する。現時点で保証するのは実際の走査量に応じた費用で、O(n log n)検査を計測だけから宣言しない。

旧02の直接Bellman checkerと18 timeout、既存hybridの24 timeoutを保持し、別の03全60input測定を実施中。新構築器の再実行と検査法変更による再評価を混同せず、全工程時間と未完了出力を保存する。
