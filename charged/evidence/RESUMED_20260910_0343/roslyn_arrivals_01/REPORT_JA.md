# 独立到着の初回探索

32 foreground更新、64 background要求、要求間隔0/10/100/1000µs、6方式、各方式3独立process、各設定2 warm-up+10 measurementを結果前に固定した。864全件（測定720、warm-up144）はSUCCESS、別checkerも864 PASS。除外・retry・TIMEOUT・INVALIDは0。全96 publication/件の連鎖、リンク文書の原子更新、通知payload、保持snapshot、4,016未変更文書のidentity/version/metadata、および要求の投入・実行・publication・完了時刻を検査した。8 raw破損controlは全て拒否した。全native processは約64.4秒で終了した。

内部の衝突挿入hookはnullである。producerは事前に決めた時刻に要求をFIFOへ投入し、別workerが処理する。通常の公開イベント記録とnative counter計装は残る。各測定cellの分母は3 process×10 batch=30で、原ソースの4,019文書を4,019独立用途へ数えない。

## 資源と性能の得失

すべての通常完了batchでcapped方式はQ≤32+rを満たした。instrumented originalのQ最大は95。r0のtwoとthreeは全120測定batchでQ=32を保ち、保護内変換の合計は3,840→1,641、総変換は3,840→5,481となった。r2ではtwoのQ合計4,046、three4,045、保護変換2,718→1,392、総変換4,046→5,437。異なる方式が異なるinterleavingを作るため、同じ要求列でも実際のwrite数は同一ではない。

100µs間隔/r0では、batchごとの背景要求end-to-end時間のp95（64要求のnearest-rank）を30 batchで中央値にすると、twoは501.98µs、threeは69.00µs。背景queue時間が減少し、foreground中に完了した背景更新の中央値は0→7となった。3つのprocessごとのp95中央値でもthree側が小さい。r2でも同じ集計は232.81→69.19µs、各processで同じ方向だった。

一方、集中到着（0/10µs）ではtwoが前景を速く終え、threeは余分な変換を行う。0µs/r0の前景中央値はtwo677.33µs、three1,045.69µs、10µs/r0は653.81/1,009.33µs。背景p95もthreeが一貫して改善するわけではない。1000µsではr2両方式の保護内変換の中央値は0で、制約のためにfallbackを発動する必要が少ない。全24 cellはanalysis01/CELLS.tsv、process別もanalysis01/SUMMARY.jsonに保持する。

## 解釈上の制約と追加検証の理由

当初の固定擬似乱数shuffleは、偶然instrumented originalの3 processすべてを最初の3位置へ置いた。これは結果前の入力であるが、時間経過による負荷・温度等との交絡が残る。無改変baselineに対してinstrumented originalの前景中央値が12.7–24.4%大きかったことも、計装と実行順序を区別しきれない。小さいtiming差を一般速度改善へ採用しない。観測tailはWCETや保証上限ではない。

この懸念を検査するため、次の版では**同じ4到着条件、同じnative executable・入力内容・counter・イベントcheckerを維持**し、6方式が6ブロックの各process位置に一度ずつ現れるLatin-square順序を結果前に固定する。6新process/方式で全設定を再検証する。既存864結果を置換せず、新しい順序制御のvalidationとして全結果を併記する。有利な到着条件の選別や間隔の再調整は行わず、同じ比較の不利結果が出た場合も保存する。

現在支持されるのは、限定したsource経路・作成した独立到着条件で、bounded callと保護変換削減が実行時にも維持され、ある中間到着域では背景の待ちを改善し得るという交換条件である。production workload、一般的な高速化、Roslyn全体へのlock-safety証明、固定重み付きW/Lの時間への等置を支持しない。
