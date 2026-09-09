# Atomic呼出し数と保護内計算量のnative検査

8形状×2価格×6selector=96件。全2,056policy-path replay、384 concurrent writer実行、2 native controlsを保存した。2,440 ordinary recordsは全てSUCCESS、576比較セルの成分別最大値と総費用上限が予測に一致した。record controls8/8、sequence controls5/5、parser controls4/4は期待結果。scalar三モードとscalar二モードの96比較セルはlower/equal/higher=2/94/0。

Wは選択したparent-fold/cell-update演算、Lは同演算のうちatomic callback内、Qは対象foregroundのcompletion/validation API入口を計数し、失敗conditionalも含む。read-only get、initialization、external writer callsはQに入れない。各実行のcost=W+L+8κQを生ログから照合した。pは追加実時間の測定値ではなくLの重み。各成分のsupとcostのsupは別に計算し、supの加算を等式にしない。

二job chain w=(1,2), κ=2, B=1では、三モードのworst(W,L,Q)=(32,16,2), worst cost72。二モードのprotect-first tieは(24,24,2), cost80、cheap-first tieは(32,16,3), cost80。各policyの全分岐集合の最大値比較であり、同じ実現writer活動・pointwise優越・latency効果ではない。cached-allのworstは(40,16,2), cost88で、全資源を同時に最小化するpolicyではない。

Value以後のkernel/callback/writer/outputソースは原版と同一。新Inputとselector、元ソース由来の有限因果checker、独立sequence checker、追加resource checkerを区別する。native live-parent controlは実行自体は返るがcheckerは期待通り拒否する。有限source-model feasibilityをJava全意味論の機械証明と呼ばない。
