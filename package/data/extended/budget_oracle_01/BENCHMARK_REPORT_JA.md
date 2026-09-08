# 六つの指定予算に対する比較結果

BENCHMARK_PLAN.md、benchmark.py/benchmark_worker.py、全48入力、全96単位を
benchmark01/MANIFEST.jsonに結果前固定した。Python3.12.14、同一の逐次cold
process、各5秒・50ms間隔のsampled RSS1GiB、campaign540秒上限で一回実行。
終了まで121.888秒。import、入力、構築、JSON保存、実ファイルからreload、
検証、値取得を含む。無変更の不利単位の再実行はしていない。

|方法|SUCCESS|TIMEOUT|FAILURE/INVALID/NOT_RUN|
|---|---:|---:|---:|
|六つの値のmemoized concave oracle＋union証明書|32|16|0/0/0|
|全予算hybrid＋全曲線検証＋六値取得|45|3|0/0/0|

両者成功32入力×6予算の192値は全一致。指定予算法だけ成功する入力は0。
全予算法の時間切れは32-job fenceの全3価格系列。指定予算法はpremium-only
wide系列12/16がtimeout、SMALLとWIDE_PRICESで各2/16がtimeout。
指定予算の重複、同型の形、zero premiumも固定通り残した。

全単位cold時間の総和は指定予算法86.1296秒、全予算法35.6887秒。
共通成功だけのcold総和は5.6134秒対5.2171秒。指定予算法が速かった共通入力は
10/32だが、多数がprocess起動・50ms pollingの分解能に近く、その数を安定した
勝率とはしない。成功最大artifactは指定値3,674,489bytes、全予算3,139,158bytes
（異なる入力を含む）。本研究で指定値法の性能優位は支持されなかった。

全予算法は全予算の値・方策を返し、oracleは六つの要求値だけを返す。従って
同量の成果物・方策取得費用の比較ではない。oracleの小さい理論的な一点証明書は
探索過程を小さくする保証でもなく、オンラインで方策を選ぶ費用は未評価である。
これら48入力は4形状×4サイズ×3価格系列の著者生成probeであり、実応用分布や
実時間改善を示さない。先行するB1/B2の最適方策比較とも出力の保証範囲が異なる。

RAW.jsonl SHA256: a397f901220c75cb016e66d5b4d62c368f0f483b1efc630f0334b10c598af19a
全stdout/stderr、command、途中まで出たartifact、terminal結果はbenchmark01に保存。
