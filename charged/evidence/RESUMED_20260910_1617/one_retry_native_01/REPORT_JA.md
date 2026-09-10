# 一回の再試行と出力のみのcallback：固定native実行結果

最初の実行12,224件は全件SUCCESS。OpenJDK17.0.19+0で実際にcompile/runし、準備・保護下kernel・外部writer・完了を独立checkerで再構成した。compile/runを含む2.214秒は実行管理値であり、方策間の性能測定ではない。全writerはfinallyで終了し、各終了を確認した。

全176群でW最大=Omega+M、L最大=sum_(wi>M)wiを達成し、全実行でQ<=n+1。M0群の最大Qはn、それ以外はn+1。条件付きreplaceと検証用computeの6,112対応組は資源・成功履歴・保存出力payload・最終live payloadが一致した。方策はcheap成功/失敗だけを受け取り、cachedの比較Boolean・kernel値・計測値・writer状態を参照しない。

304件にcheap失敗、合計1,056 cached呼出しがある。失敗時は公開せず、以後は予算内でcachedが一致した。9キー衝突layoutの4,336実行では開始/終了時に実際のConcurrentHashMap$TreeBin一個を検査した。他のlayout/fixtureはTreeBinなし。全件でtable容量128・ノード数nが不変。process-local reflectionは診断用でありcontrollerの入力ではない。resize、新規キー追加/削除、任意のJMM実行は試験していない。

終端まで呼出し位置nへ進まなかった1,848件では予定した後方writeが未発行となるが、Bは上限なので分母に保持し、checkerがその条件を検証した。保存完了出力が最終live entryと異なるジョブ観測は4,792件で、後続kernelは保存した正確な親出力を用いた。全入力・原event・全成功/失敗区分・群最大と証人・全SHAを保存した。

意味は、既知B1で一回の失敗を許す方策の操作対応と資源境界のnative裏付けである。一般の任意program下界はONE_WRITE_RETRY03.mdの別の証明に依存し、この実行数で成立させない。一般速度改善、採択、新規性の独立確定、実サービスSLAの証拠にはしない。
