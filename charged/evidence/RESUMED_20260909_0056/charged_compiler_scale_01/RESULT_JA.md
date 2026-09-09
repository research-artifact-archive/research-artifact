# 初回 charged compiler 比較：全分母と限界

固定した24 authored input、224 cold process、1,256 requested rootsを147.59秒で実行した。SUCCESS197、TIMEOUT27、FAILURE/INVALID/NOT_RUN0。完成した共有値の不一致0。RAW SHA-256: c2ac48447a3e4f1e5af14aec503c70f62e85a619d208acc93310f6ae1698e84f。再実行・除外はしていない。

|方式|成功/全実行|完成した要求値|最大成功RSS|
|---|---:|---:|---:|
|ALL（全予算構築・書出し・再読込・証明書検査）|63/72|357|20,905,984 bytes|
|PEAK（共有memo・要求値証明書）|62/72|288|118,538,240 bytes|
|DP（2行Bellman・全状態固定点停止、値のみ）|64/72|312|18,186,240 bytes|
|GENERIC（小予算の明示AND-OR）|8/8|32|285,753,344 bytes|

Q1/Q4は、それぞれALL/PEAK双方完了21組でALLが速い組0。PEAK/ALL時間比中央値は0.405/0.434。ALLの初回全予算サービスは少数の小予算問い合わせでは高い費用を払う。ALLの9timeoutは全て独立12job（3価格条件×3workload）であり、2^n状態の障害が残る。

Q12ではALL/PEAK双方完了14組の全てでALLが速く、PEAK/ALL比2.63–12.94、中央値7.16。他にALL成功/PEAKtimeout7、双方timeout3。DPとの同条件では双方完了14組中ALLが速いのは1組、DP/ALL中央値0.458である。大きいBだけではDPを遅くできず、安い固定点停止が効く場合がある。Q12のALL成功/DPtimeout7、ALLtimeout/DP成功2、双方timeout1も保存する。timeout capを成功時間へ代入しない。

これは一回のcold process費用で、同じAPIを返す全工程policy-service比較ではない。ALLは全予算のrouting/price/basisを、PEAKは要求root値の証明書を、DPは値だけを返す。構造・価格はいずれも著者のstress設計であり、実application分布や実測API価格を代表しない。

読取り報告22で見つかった入力・予算結合不足を測定前に修正し、unchanged/reversed budget/wrong PEAK input/wrong ALL inputの4固定controlは期待どおり通過・拒否した。旧76case conformanceの120秒alarm例外が内側で捕捉され得る手続き上の欠点はmanifestに記録した。当該実行は0.742秒で終了し、今回の測定は別のparent processからhard killで上限を課した。

追加の検討事項：PEAKは巨大Bに対する事前の飽和上界を使用していない。著者側で新しく導いた候補 bound |S|+ceil(sum P_i/min c_i) が証明できれば、より強い比較実装へ適用する必要がある。上記7.16倍を最良の要求値アルゴリズムに対する優位と解釈しない。元のコード・入力・全結果は変更せず、改良比較は別namespaceと固定した差分で扱う。
