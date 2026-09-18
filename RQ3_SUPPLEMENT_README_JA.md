# RQ3 supplement（2026-09-17 判断 L）

これは既存 RQ3 の未決結果を残した追加 campaign です。**Xeon の Travel/hub 全 stage 完了後に人間が起動します。準備時には実験を実行していません。** 既存 JAR・モデル・手法の JVM properties・1200 s の元結果は変更しません。元の `raw/rq3` へ結果を書き戻しません。

| Config | 対象 | Heap / timeout | 最大実行数 | 目的 |
|---|---|---|---:|---|
| `rq3_supplement_workflow_r2_direct_full` | Workflow/R2, Direct-Full | 64g / 1200 s | 5 | 元の運用中断 1 セルを別 campaign で補完 |
| `rq3_supplement_pc_arms2_r2_fg_3600` | ProductionCell Arms=2/R2, FG lazy | 64g / 3600 s | 1 | 別キャップの単発 stretch。元の 1200 s TO を維持 |

Workflow は stage1 を第1反復とし、成功または証明 LOSS の場合だけ stage2 で追加4回を実行します。TO/OOM/異常終了/不整合は再試行せず、未着手反復を既存 runner の SKIPPED status として残します。5回すべて正常完走したセルだけ中央値と min–max を使用します。PC の単発値を5反復値に混ぜません。タイムアウト上限の合計は Workflow 最大100分＋PC最大60分＝最大160分で、前処理・起動・収集の時間は別です。

## 既存 Windows bundle への配置

現在使用中の bundle へ、このフォルダの `configs/*.json` 2個を `configs/` に、`run-supplement.ps1` を bundle 直下に、本文書を `RQ3_SUPPLEMENT_README_JA.md` として追加します。Mac の `rq3_xeon/bundle/` には同じ追加ファイルを配置済みです。既存 ZIP・runtime・`run-all.ps1`・`run-windows.ps1` は更新しません。

元と同じ Xeon W-2265、JDK 17、Python 3.10以上を使用します。新 wrapper は既存 wrapper と同じ host check、native stderr 処理、実行ファイル PATH 設定を用います。起動時に既存 runner が RAM 240 GiB以上、空き disk 50 GiB以上、RSS/process-tree probe を確認し、OS lock により1 JVMだけを実行します。実験中の自動 sleep を無効にしておきます。追加 wrapper 自体の PowerShell 実行は Mac では未検証です。

bundle 直下（例 `C:\fgducs\fg-ducs-xeon-campaign`）で以下を順に実行します。PATH が必要な場合は各呼出しに `-Python 'C:\path\python.exe' -Java 'C:\path\java.exe'` を追加します。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-supplement.ps1 -Campaign rq3_supplement_workflow_r2_direct_full -Stage plan
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-supplement.ps1 -Campaign rq3_supplement_workflow_r2_direct_full -Stage stage1
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-supplement.ps1 -Campaign rq3_supplement_workflow_r2_direct_full -Stage stage2
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-supplement.ps1 -Campaign rq3_supplement_workflow_r2_direct_full -Stage collect
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-supplement.ps1 -Campaign rq3_supplement_pc_arms2_r2_fg_3600 -Stage plan
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-supplement.ps1 -Campaign rq3_supplement_pc_arms2_r2_fg_3600 -Stage stage1
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-supplement.ps1 -Campaign rq3_supplement_pc_arms2_r2_fg_3600 -Stage collect
```

各コマンドの終了を確認してから次を実行します。異常終了を検出したら raw を保存し、記録済みセルを削除してやり直しません。Workflow の stage2 は stage1 の結果を読み、資源失敗なら追加実行せず除外を記録します。PC は追加反復がないため stage2 を使いません。

既存 runner は比較用 config に2手法以上の定義を要求するため、元の5手法定義をそのまま保持し、各 model の `method_ids` で上表の1手法だけを選択しています。plan の実ジョブ数がそれぞれ **5 / 1**、初回が **1 / 1** であることを Mac の準備検査で確認しました。config単位の timeout 仕様に合わせ2個に分けています。

## 帰還先と解釈

次の各フォルダ全体（config、plan、environment、runs、launcher log、CSV、Workflow の stage2_plan を含む）を Mac の同名 `experiments/rq3_xeon/raw/` 配下へ新規回収します。

- `raw/rq3_supplement_workflow_r2_direct_full/`
- `raw/rq3_supplement_pc_arms2_r2_fg_3600/`

元の Workflow/R2 は運用中断という来歴を残し、別 campaign の結果を採用する場合は印と脚注を付けます。PC の結果は 3600 s 単発の補足として扱い、1200 s 表の TO は置換しません。既存 renderer の固定27×5入力へ自動的には混ぜず、別 campaign として取り込み時に確認します。
