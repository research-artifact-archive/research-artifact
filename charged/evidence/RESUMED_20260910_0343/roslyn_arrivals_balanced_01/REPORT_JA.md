# 実行位置を均等化した独立到着validation

初回探索で残ったprocess順序の交絡を検査するため、同じ実行harness・patch04 DLL・全到着条件を使い、6方式×6 cyclic Latin-square blockを結果前に固定した。1,728件（measurement1,440、warm-up288）がすべてSUCCESS、同一check関数に基づくcheckerも1,728 PASS。8 raw破損controlをすべて拒否した。除外、引き直し、FAILURE、TIMEOUT、INVALIDは0。36 source processは約132秒で終了した。各cellは6 process×10 measurement=60 batchである。

## 維持された資源保証

r0のtwo/threeは各240測定batchの全件でQ=32。保護内変換の合計はtwo7,680、three2,729で、総変換は7,680/10,409。r2ではQ合計8,102/8,097、保護内変換5,361/2,840、総変換8,102/10,937。各batchでQ≤32+rを検査した。実際の背景writeのinterleavingは方式により変わるので、r2の総Qまで同じとはしない。

## 改善域と不利な条件

100µs間隔/r2で、各batch64背景要求の予定到着から完了までのp95（nearest rank）を60 batchで中央値にすると、two265.35µs、three73.33µs。6 blockの各process中央値でもthree/two比は0.354,0.178,0.401,0.295,0.559,0.229であり、6/6でthreeが小さい。foreground中の背景publication中央値は2→5、保護変換中央値30→3、Q中央値は両34だった。前景batch中央値は709.46→645.79µsだが、blockごとの前景比は同じ方向に揃わない。

100µs/r0でも背景p95のpooled中央値は408.69→62.31µsとなった。ただしblock別では5/6で改善し、block3はthreeが1.889倍大きかった。全block一致の結果へ書き換えない。

集中到着（0/10µs）ではr2のthreeの前景が6/6 blockでtwoより遅い。0µsのpooled前景中央値は722.40→1,030.27µs、10µsは738.42→902.92µs。cached completionは少ない保護変換と引換えに再計算を増やす。背景時間のblockごとの方向は混在する。1000µs/r2では両方式の保護変換中央値は0で、主に楽観的更新が完了する。

24全cellと6 blockの詳細はanalysis01/SUMMARY.jsonおよびCELLS.tsv。初回探索の全864結果は隣接directoryに保持する。初回ではthreeの前景が無改変baselineより遅いcellがあったが、順序制御後のpooled中央値では全8 cellで小さくなった。方向が変わる小さい時間差を安定した一般効果としない。instrumented originalは今回も無改変baselineより前景中央値が6.9–13.8%大きく、計装等の影響がある。

本validationは、強制衝突hookなしでも呼出し数の保証が成立し、100µs/r2の背景待ち削減と集中到着の前景悪化が複数blockで再現されたことを支持する。一方、作成した周期/集中到着、一台の計算機、公開callback計装、共有source projectionという範囲を持つ。production trace、数値SLAの充足、tailの保証上限、一般的な速度改善、weighted minimaxの実時間最適性を意味しない。
