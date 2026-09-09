# 強い要求値比較法：残る利点と消えた利点

144改良実行/816要求値を74.03秒で測定し、SUCCESS128/TIMEOUT16、その他0。PEAKとDPは各64/72成功、各312要求値を完成した。全ての旧・新で完成した共有値の不一致0。RAW SHA-256:93589ae8fbee655dfcba3454e0ea4b676657a3484b326c68308077ab9baa0b2c。

旧ALL72実行は再実行せず、原63成功/9timeoutを参照する。新旧測定は別のserial campaignであり、以下の時間比は記述的な参照比較である。統計的な優位や同時のpaired trialを主張しない。

|入力・問い合わせ|units/方式|旧ALL成功|新PEAK成功|新DP成功|
|---|---:|---:|---:|---:|
|MIXED/WIDE_ALL、Q1/Q4|32|28|32|32|
|MIXED/WIDE_ALL、Q12|16|14|16|16|
|LONG_PREMIUM、Q1/Q4|16|14|16|16|
|LONG_PREMIUM、Q12|8|7|0|0|

主な改善は、大きなBがすでに飽和しているMIXED/WIDE_ALLである。Q12の双方成功14組では、新PEAK/旧ALL時間比中央値0.576（旧PEAKでは7.16）、新DP/旧ALL中央値0.457。ALLが小さな時間差で速かった組はPEAK相手2/14、DP相手0/14に縮んだ。旧9独立12jobのALLtimeoutはそのまま残し、新方式は同型MIXED/WIDE_ALLの全問い合わせを完成した。

一方、premiumだけを2^32倍したLONG_PREMIUMのQ12では両要求値方式とも全8件timeout、ALLは7/8を完成した。この結果は、単なる巨大Bと、飽和前の数値的に長い曲線を区別する。全価格を2^96倍するWIDE_ALLでは予算方向の幾何は変わらず、改善された比較法が速い。著者stress入力の一回4秒上限であり、実application頻度や最良の任意アルゴリズムに対する下界ではない。

Q1/Q4の双方成功は各21組。新PEAK/旧ALL中央値0.382/0.431、新DP/旧ALL中央値0.370/0.286。プロセスstartup近傍の小時間差は解釈を抑える。最大成功RSSはPEAK116,310,016 bytes、DP24,330,240 bytes。タイムアウト実行のpartial artifactとstdout/stderr/PROCESSも全て保持した。

前段の76観測済み入力に対する532要求値と304generic rootsの意味論照合、および11証明書対照は全て期待どおりだった。追加boundはprivate failure budget下界Lとfixed-mode上界Uの一致を使う。PEAK証明書checkerは別コードでL/Uを再計算するが、DPとPEAKの探索側はbound helperを共有する。全予算ALL、要求値証明書PEAK、値だけDPというサービス差は維持する。
