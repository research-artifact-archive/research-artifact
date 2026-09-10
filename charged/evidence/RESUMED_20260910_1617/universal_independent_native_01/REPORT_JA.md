# 未知予算・独立ジョブの一方策：固定native結果

最初の20,384実行は全件SUCCESS。Java17.0.19+0でcompile/runは3.641秒（実行管理値、性能改善の測定ではない）。比較結果を公開しないcached wrapperを使い、policyは重みを自ら昇順に並べ、r回のcheap失敗後にcachedへ切り替える。B、writer状態、値、診断値、cached比較Booleanを参照しない。

全10,192 replace/validation-only組はpayload・trace・資源が一致。全512群・2,464予算座標で、書込み数d<=Bの全実行を含めたworstW/L/Qがproof10の曲線・Top_(B-r)+・n+min(r,B)と一致した。24,168 cheap失敗と108,576 cached呼出しを保存。衝突tree9の4,092実行は実際のTreeBin一個・容量128・9ノードを開始/終了時に確認。全writerexecutorはfinallyで終了した。独立checkerの12変異は全て拒否された。

全2,548正規化比較pathを八つのlayout/kernel/wrapper条件で実行した。各1ビットでは実際のwriterthreadが当該比較の直前に対象jobへfresh参照を公開した。この実行は複数write下の当該policyの操作対応・資源境界を確認する。任意JMM交錯、resize、一般速度改善、人対象評価、独立再現、新規性確定ではない。無関係key/準備中/返却後writeは以前の一回retry行列の別の証拠であり、この新行列へ混ぜない。全入力・原event・failure分類・群別各座標の証人・全SHAを保持する。
