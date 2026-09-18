# FG-DUCS Xeon campaign bundle

Completed first return: `raw/rq3`, `raw/rq4_controlled`, `raw/rq4_independent`. Travel/hub remain pending. Added follow-up instructions: `RQ3_SUPPLEMENT_README_JA.md`; only a human starts those jobs after the ongoing campaigns finish. Original results are retained.

M2/M3 改訂後の既存 shaded JAR と既存27例をそのままコピーした、Windows Xeon W-2265 / 256 GB 用の実験パッケージです。Java・モデル意味論は変更していません。既定の起動は **RQ3 の初回135 jobだけ**です。別コマンドで追加反復・RQ4を実行します。すべて fresh JVM、`-Xmx64g`、1200秒、同時1 job です。

## Windows での準備と起動

1. ZIP を短いローカルパス（例 `C:\fgducs`）に展開し、`run-windows.ps1` があるフォルダを開きます。ネットワークドライブ・同期フォルダは使いません。
2. 64-bit **JDK 17** と **Python 3.10以上**を導入します。JDK は [Adoptium の JDK 17 配布](https://adoptium.net/temurin/releases/?version=17&os=windows&arch=x64)、Python は [公式 Windows installer](https://www.python.org/downloads/windows/)から取得し、PATH を設定します。JREだけでは起動時の小さなJava infrastructure probeをコンパイルできません。Maven、pip package、Git、ネットワーク接続は実験実行には不要です。
3. PowerShell を開き、以下を実行します。Javaのpatch versionとvendorは全反復で同一にします。実際の版、CPU、RAM、電源設定、RSS方式は各 campaign の raw に保存します。実験中は他のビルド・大きな計算を避け、スリープを無効にします。

```powershell
Set-Location C:\fgducs\fg-ducs-xeon-campaign
java -version
python --version
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-windows.ps1 -Stage plan
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-windows.ps1
```

既定実行は `-Campaign rq3 -Stage stage1` です。PATH にない場合は `-Python 'C:\path\python.exe' -Java 'C:\path\java.exe'` を指定します。wrapper は自分のフォルダを cwd とし、実行ファイル以外のパスはすべてbundle内の相対パスです。

初回完了後、`raw\rq3\stage1.csv` と `stage2_plan.json` を確認してから、次で完走条件だけ追加4回を行います。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-windows.ps1 -Campaign rq3 -Stage stage2
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-windows.ps1 -Campaign rq3 -Stage collect
```

同じコマンドを再開しても、記録済みの成功・TO・OOM・crashを再試行しません。中断中のjobは `INTERRUPTED_NOT_RETRIED` として残します。未着手jobから続けます。runtimeのOS lockは、別campaignを同時に起動しても複数JVMを並列実行しないためのものです。`Ctrl+C` 時は親Pythonが子JVMのプロセス木終了を試みます。OSの強制終了・電源断は通常の中断処理外なので、再開前に残存した当該実験JVMがないことを確認します。

## 保存・反復・集計の規則

- 最初の全135条件は `stage1.csv` に常に残ります。OOM/TOを能力差や証明LOSSとして数えません。
- 初回 `SUCCESS` / `UNREALIZABLE` かつ必要なcheckerが通った条件のみ追加4回を生成します。初回は反復1であり、追加後の合計は5回です。
- 反復2以降でTO/OOMが出ると、同じ条件の未着手反復は `SKIPPED_AFTER_RESOURCE_FAILURE` です。crash・invalid・判定不一致でも残りを明示的にskipします。都合のよい再測定、キャップ延長、別seedへの置換はしません。
- **5回すべて完走・check合格・判定一致した条件だけ**中央値とmin–maxを出します。途中censored群の成功回だけの中央値は出しません。`summary.csv` に invalid / inconsistent / expected_mismatch と各反復statusがあります。異なる同意味論の手法の判定不一致も明示します。
- 構造量は初回のみを報告します。`raw_runs.csv` は全計画行、`metrics_long.csv` はLTSの全生指標、`runs/<job>/` はstdout/stderr/output/metadataを保持します。missing指標を0に置換しません。
- FG lazy / eager-controllable / update-first / Direct-Full は同一の新意味論です。Legacy DUCS solver は同じ `fine_grained` 入力を先行ツール・legacy意味論に与える参照値であり、atomic bulk比較ではありません。Legacyとの判定差は同一問題の不整合判定から分離します。Legacyの内部発見状態数・successor query数が未計装なら空欄とし、別の既存peak state-space指標を同一視しません。
- LTSのsolver timeは `revised_solve_and_internal_check_time`（Legacyは既存solve-control-problem時間）です。hubのsolver timeは合成driverのsolver単体時間で、checker時間は別のraw列です。両backendを同じ時間定義として混在集計しません。全JVMのelapsed時間とRSSも保存します。
- n4 hubの旧generator期待値との不一致は `expected_mismatch` として残します。`unexpected_decision` でも actual decision がWIN/LOSSで内部certificateが通れば、その判定を保持します。旧期待値だけを理由に新意味論の正当なLOSSをinvalidにしません。

## RQ4 と最大件数

RQ4は以下の別コマンドで起動します。`stage1`後にtiming族のみ`stage2`を実行します。controlledは構造132件のみで、追加反復はありません。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-windows.ps1 -Campaign rq4_independent -Stage stage1
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-windows.ps1 -Campaign rq4_independent -Stage stage2
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-windows.ps1 -Campaign rq4_travel -Stage stage1
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-windows.ps1 -Campaign rq4_travel -Stage stage2
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-windows.ps1 -Campaign rq4_hub -Stage stage1
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-windows.ps1 -Campaign rq4_hub -Stage stage2
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-windows.ps1 -Campaign rq4_controlled -Stage stage1
```

| Config | 入力数×手法 | 初回job | 最大追加job | 最大総job | 初回cap総和 | 追加cap総和 | 総cap総和 |
|---|---:|---:|---:|---:|---:|---:|---:|
| rq3 | 27×5 | 135 | 540 | 675 | 45 h | 180 h | 225 h |
| rq4_independent | K=2..20の19×4 | 76 | 304 | 380 | 25 h 20 m | 101 h 20 m | 126 h 40 m |
| rq4_travel | 48×4 | 192 | 768 | 960 | 64 h | 256 h | 320 h |
| rq4_hub | 30 seeds×3 UC profiles×4 | 360 | 1440 | 1800 | 120 h | 480 h | 600 h |
| rq4_controlled | 33×4 | 132 | 0 | 132 | 44 h | 0 h | 44 h |

これは全jobが上限近くまでかかった場合の実行cap総和で、起動・集計・終了処理の時間はさらに加わります。RQ3だけでも最大225時間なので、**一晩完了は保証できません**。実際には早い完走と初回TO/OOMの除外で短縮しますが、Xeon上の所要時間は未測定です。全RQ3/RQ4を上限まで逐次実行すると895初回＋最大3052追加＝3947 job、cap総和1315時間40分です。既定はRQ3初回のみとし、残りはdeadlineに合わせてこの件数を見ながら投入します。

独立K族は既存の決定的generatorで指定どおり全整数2..20を生成しました。Travelは旧Windows launcherの固定48格子 N={1,2,4,6,8,12}, K={1,2,4,6,8,12,16,20}を同じgeneratorで展開しています。元Travel Agencyのadmissionをcontrollableにする等の既存FG適応であり、元モデルの等価変換や実運用の効果を主張しません。n4 hubは既存30 seedsをそのまま使用し、u0/u_local/u_crossの各profileを独立JVMで実行します。controlled33例は既存LTSをbyte一致コピーし、元の小10例×4手法のindependent checker指定を維持します。

## Mac pilot と移送

固定3例（GSM/base・MetaSocket/base・ProductionCell Arms=1/base）×5手法を4g/60秒で各1回実行しました。**13 SUCCESS、1 OOM（PC1 Legacy）、1 TIMEOUT（PC1 Direct-Full）、invalid/inconsistent 0**。JVM実時間合計112.18秒。完走13条件から追加52 jobが生成され、資源失敗2条件は除外されました。追加反復は実行していません。これはパッケージ動作確認で、Windows本計測とは混ぜません。親エージェントのheavy buildはpilot中停止しました。

Macでは親Python→子JVMのRSS取得とプロセス木終了を確認済みです。**Windows PowerShell・Win32 RSS・taskkillはMacで実実行していません**。Windows起動時に同じ親子probeを走らせ、RSS取得と子JVM終了の両方が通らなければ本実験を開始しません。結果はtimestamp付き `process_tree_smoke-*.csv` に残ります。RSSは約100 ms間隔で採取した子JVM resident/working-setの観測最大値であり、短いpeakの取りこぼしはあり得ます。

bundle生成元では `raw/pilot/` に15件、`raw/hub-adapter-smoke/` と `raw/hub-adapter-smoke-cli-fix/` にhub adapter確認を保存します。最初のhub確認はCLIが0のguided limitを受けない起動前失敗で、rawを保持したままCLI既定値に修正しました。同じ固定seed=698/u_cross/FG1件は修正後にWIN・内部certificate passedで完走しました。今回の4手法ではJava内のguided探索上限は0固定なので、その変更は手法を変えません。人工fixtureの集計検査は `raw/orchestration-checks.log` に保存し、実験観測とは分けています。配布ZIPにはMac rawを含めません。

完了後、展開先の **`raw/` 全体**（途中失敗・除外行・環境・logsを含む）を、作業repoの **`FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/raw/`** へコピーします。`rq3/`, `rq4_independent/`, `rq4_travel/`, `rq4_hub/`, `rq4_controlled/` のディレクトリ名を維持し、過去結果へ上書きしません。

生成元で再bundle化する場合は `python3 prepare_bundle.py --zip`。既存JARの再ビルドは行わず、copy直後に元byteとの一致を検査します。ZIPは `fg-ducs-xeon-campaign.zip` です。
