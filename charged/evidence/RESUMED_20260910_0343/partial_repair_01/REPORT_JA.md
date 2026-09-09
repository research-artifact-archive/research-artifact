# 部分修復で全予算同時最適性が成立する条件

2026-09-10 06時台。手導出と有限照合による著者側の新結果。旧whole-kernel定理への反例ではない。詳細な操作・情報条件、証明は `PROOF.md` に固定した。

単一jobが独立な成分を持ち、writeが所定のfootprintを無効にする。callはdirty setを観測して、dirty成分だけ保護内で修復し全体を完了するか、保護を解放して再準備する。最大q=r+1 callを許す。G(b)をb writeで無効にできる最大の成分仕事量とすると、以下を導いた。

| 返却する保証 | 値・条件 |
|---|---|
| B既知の最小worst repair | G(floor(B/q)) |
| B≤rで保護仕事0を守るunaware方策の最小envelope | G(max(B−r,0))、通常のretry-firstが達成 |
| 一つのunaware方策が全Bでknown optimumを達成（r≥1） | Gが1writeで飽和する場合に限る |
| 最良の有限multiplicative competitive factor | 二envelopeの比の有限最大。q以下、q成分のunit/singleton族でqを達成 |

最小の分離例は2成分・2call。B=3既知なら「1成分dirtyは今修復、2成分dirtyなら再試行」でworst repair1にできる。B=1で最適な0を守る同じ未知B方策は、最初の1成分dirtyを受け入れられない。再試行後に2成分を無効にする2writeを置くと、合計B=3でrepair2が必要になる。

全非空footprint族（m≤3、到達不能成分がある族も除外しない）、各成分weight1/2/3、r0..3、B0..q*m+3の3,495入力・160,080セルで、観測したdirty setごとに一つの応答を選ぶDP、damage-spectrum DP、known-B式は全一致。失敗0。hiddenな重複write数ごとに別応答を選ぶ実装にはしていない。五つの誤りcontrolを検出した。

分類13,980件は導出した二式の比較であり、全方策列挙ではない。m2/q2だけでは、初回非空dirty setへの8応答mappingとalways-freshを全記録した。rawの `all_undominated_policies` というfield名は不正確で、支配された方策も含むcanonical candidate集合である。元rawを変更せずこの訂正を残す。oracle profile B0..7=(0,0,1,1,2,2,2,2)へ一致する同一方策は無い。retry-firstは(0,0,1,2,2,2,2,2)である。

部分再利用の導入だけから同時最適性の失敗は導けない。1writeで到達可能な全仕事を無効にできるなら、上記の単一jobモデルでは性質が残る。Roslynの保守的rebaseも、関係projectが変わったときはall-or-nothingに元の変換へ戻るため、この2成分分離の実装実証とは扱わない。

研究上は、全B同時最適性を部分再利用へ一般化するために必要な条件を具体化できた。元論文の適用境界を補強する候補である。一方、bounded-loss stoppingやcoverageからの導出に対する外部新規性と、重要なソフトウェア契約への価値は、この小結果と有限照合だけでは未確立。新しい多数のアプリケーションやnative latency効果として数えない。
