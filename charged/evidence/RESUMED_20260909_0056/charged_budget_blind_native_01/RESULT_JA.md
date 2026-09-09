# 書込み上限を受け取らない資源方策

固定128ケース、17,714 native runs（全経路17,200、concurrent512、対照2）は全件が期待結果となった。1,280全経路群の最大Lは理論式に一致し、全件Q<=n+r。意図的live-parent対照は所定のcaptured-parent違反として拒否した。record8、sequence5、parser4対照も全て期待結果。failure/timeout/invalid/unstartedは0で、再実行・除外なし。B=rの256群では、三方式L=0、二方式L=全仕事量が一致した。

SelectorはDAGの複製、方式boolean、残りcheap失敗枠だけを保持する。Bはwriter fixtureと費用上限検査にあるが、方策chooseへ渡さない。javap全命令も点検した。実行は既存callback/kernel/writer意味論を再利用し、有限sourceモデルの実行順証明書を全件再構成して別checkerで確認した。5モデル/checkerファイルは親と同一bytesである。

新しい量化は、一つの方策が全ての有限書込み環境でn+r呼出し以内に完了し、各Bに対する最悪Lを同時に最小化すること。三方式は既知Bの最適値と一致する。二方式は別の有限環境での追加一書込みを除外できず、B=rですでに全仕事量となる。全経路有限テストは普遍定理の証明ではない。定理の詳細は公開resource guideと論文に記載する。fallback機構は既存研究から継承する。

この方策のスカラー価格最適性、W/L/Qの全Pareto最適性、各実行ごとの最適性、料金・時間削減、productionでの普及率は主張しない。価格minimax compilerは引き続きBを用いる。既存価格当てはめ失敗・一般compiler timeout・Deephavenでの不利結果を変更しない。
