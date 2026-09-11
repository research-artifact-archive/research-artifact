# Java残余filter・最小native integrationの担当報告

2026-09-11、著者側の限定実装担当。blind reviewerではない。依頼の純filter、Java17 wrapperへの最小統合、固定入力からの全trace比較を完了した。**採用実装は v2/ResidualFilter.java**、実行記録は attempt02。指定領域以外の正規稿・公開package・共通status・他担当・旧rawには書き込んでいない。追加agent/Claude/課金/credit/reset/人対象評価は0。

## 実装したもの

completed positive long weights、k、ellとその二heap索引だけを保持する。permitsFresh(currentWeight)はO(1)。currentWeightは現在呼ぶ未完成jobの固定重みで、queryでは保存せず、完成報告で一回だけheapへ挿入する。recordCompletionのMATCH/MISMATCH/FRESHはO(log(|D|+1))のリンク操作・比較。残り重み、全DAG、total n、B、実write数、診断workはfilter APIにない。初期状態、非正重み、null outcome、unsafe fresh、long加算overflowを検出し、通常の拒否では数学的状態を変更しない。詳細と呼出側の義務は IMPLEMENTATION_NOTES.md。

初回のJava PriorityQueue版も意味論検査に一致したが、動的配列拡張時の線形コピーにより単発更新の厳密O(log n)をそのまま主張できなかった。この点をREVISION02.mdに残し、リンク付き完全二分heap二つに修正した。初版とattempt01を保存し、修正版で同一入力を再実行した。計算量は抽象操作数であり、allocation/GCやnative latencyの上限ではない。

NativeIntegration.javaは既存UniversalCallbacks.javaのper-key compute wrapper形式を利用した最小例。immutableなown-inputとコピー済みimmutable saved parentsだけでpure wholekernelを計算する。freshは準備せずcallback内で一回、cachedはcurrent captureから準備後、比較不一致だけcallback内で一回追加、cheapはvalidation-only compute。返された出力を保存し、live mapを再読して親出力にしない。失敗cheapはfilterへcompletionを登録せず、成功cheapの重みはswitch前からDに残す。

## 固定分母と照合結果

実行前にPROTOCOL.md、全入力とコード・元証明・JDKのhashを固定した。初回はattempt01/FREEZE.json、修正後はREVISION02.mdとattempt02/FREEZE.json。Python参照は旧online_filter.pyをimportせず直接sortし、native側は入力からcapture、kernel、外部publication、比較結果、保存出力と全診断を独立に再構成する。同じ著者側の検査であり、独立査読/独立研究者による再現ではない。

| 対象 | 固定分母 | 最終結果 |
|---|---:|---|
| 残余filterの小分岐全探索 | 18根×27操作列＝486列 | 全一致 |
| 無効入力・long境界 | 12追加根 | 想定した拒否/成功に全一致 |
| 修正版heapの構造回帰 | 2追加根、195 query/195 update | 全一致 |
| Native統合 | 48根、996全経路 | 全31,892 eventと最終値が一致 |

filterの498列では7,294 query・1,467 update。unsafe freshの想定拒否231件を保存。overflow・無効入力の拒否も除外していない。nativeは全996経路がSUCCESS、FAILURE/TIMEOUT/INVALID/NOT_EXECUTEDは各0、全writerがterminated。compile警告0。初版/修正版の反復を足し合わせて分母を増やしていない。全root/path台帳はattempt02/ROOT_LEDGER.json・PATH_LEDGER.json、差異0はDISCREPANCIES.json。診断の抽出別traceはDIAGNOSTICS_FROM_NATIVE.jsonl、制御の抽出別traceはCONTROL_FROM_NATIVE.jsonl。両者は同じnative rawからの派生物。

## 判断を変える境界と不利結果

指定chain(100,1,2,80,80,80),r=1で、cheap100 match、cheap1 failure、cached1 mismatchの後、D=[100,1],k=1,ell=1に到達した。次のweight2で **ell+w=3<=Top1(D+2)=100なのでfreshを選択**する。旧whole-suffix条件は **ell+remaining=243>Top2(J)=180**で拒否する。具体Java記録はSTRICT_NATIVE_EXAMPLE.json（path01100）。この経路の実測したbodyW=345、bodyL=83、Q=7、actualExternalWrites=2で、saved outputsも参照に一致する。これは厳密な許容差のwitnessであり、性能改善の証拠ではない。

共通cheap phase+allcachedとfilterを比較した主fixturesの62個のat-most-B座標では、**最悪body-Wは全て等しい**。指定chainのB=0..7も両方[343,443,543,623,703,783,785,786]。strictなmode許容差をworst-W改善とは書けない。allfreshも全fixtureで実行し、chainではW=L=343,Q=6,write0。これはWの一回計算baselineだがB=0の最適保護曲線L=0を満たさず、同保証の代替とは扱わない。

postpublication境界118経路では、job0のcomputeから戻った後かつcompletion保存前に外部writeを入れた。保存出力とlive値が異なり、その後のbodyはsaved parentを使って参照と一致した。doublewrite境界118経路では一つのbad comparisonに二つの実assignmentを対応させた。実write数は2×bad comparisonsで、filterのkはcached mismatchごとに一回だけ増える。いずれも48根/996経路の内数で、別の追加分母ではない。

## 未証明・未実装の範囲

純filterと要求された最小native統合は実装済み。実clientへの導入、latency/throughput、wall-time改善、待ち時間込みの費用、ソフトウェア上の重要性は確立していない。body workにはmap内部処理・filter維持・allocation・parent capture/fold・writer・待ち時間を含めない。課金付きp/h/q版は実装せず、PROOF03の共通feeの式を実測native chargeに読み替えない。body-only版はk>|D|も扱うが、charged theoremのk<=|D|条件を外していない。

Java source/APIとの対応は条件付き。今回の有限テストからJMM、任意の並行interleaving、並行resize、tree bin、任意環境でのprogressは証明しない。constant-hashでも最大6keysでtree binは未検査。postwriteはJDK内部のpublication前後の窓を直接制御したものではない。callerは正しいreadiness・fixed weight・exactly-once completionとpublic outcomeを保証する必要がある。long表現域を超える状態は例外で止め、数学的に可能な全入力でJava処理が完了するとは主張しない。native入力はn<=6,w<=100,r<=2に固定し、その表現域内。

## 引渡しと終了

採用ソース：v2/ResidualFilter.java、NativeIntegration.java、Json.java。参照/driver：reference.py、FilterDriver.java、compare.py、heap_structure.py。再現手順はREPRODUCE.md。初回raw、修正理由、全入力・hash・stdout/stderr・終了codeを保持する。正規稿への採用と公開packageの編集はroot担当。ローカルfreeze/source receiptsは絶対パスを含む著者記録なので、公開はrootが別の匿名copyで管理する。

研究実行は12:44:05 JSTに全終了した。その後はこの担当の報告・hash・終了確認だけを行い、追加研究は実行していない。最終STOP_RECEIPT.jsonに確認時刻と所有process0を記録する。12:55 JSTまでの担当停止を満たし、新しい明示依頼なしに再開しない。
