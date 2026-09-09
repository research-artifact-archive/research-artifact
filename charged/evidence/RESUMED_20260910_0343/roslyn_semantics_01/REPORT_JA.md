# Roslyn意味検査拡張01：174ケース＋4対照

2026-09-10 03:59 JST。patch03そのものは変更していない。前回のrepository計測330バッチ/方式とは別の、著者側の限定意味検査である。

## 結果
174/174のinstrumented original/two/three実行と、未改変ライブラリのゼロwriter対照4/4がSUCCESS。別のraw検査プログラムも178/178をPASSと判定した。1,645イベント、941公開遷移、1,975個の観測snapshotについて検査したが、これらは独立なシステムや実験入力の数ではない。明示的に壊した10種類のrawを検査器が全て拒否した。実行失敗・timeout・invalidは0、除外0、各入力の実行回数1である。

対象は前回と同じ4 upstream projectのsource-membership投影、4,019文書occurrenceである。174件にはr=0,1,2、旧first-B-pre-lock配置、各foreground jobへの分散配置、同一target/linked targetへのwriter、同一SourceText no-op、内容同一・別identity、最初からmissing、途中削除を含む。Bは各実行で実際にcommitされたwriter数。mode間の途中historyが一致するとは主張しない。

## 今回加えた確認
- immediateイベントのNewSolutionがcallback時のCurrentSolutionと同じ参照である。
- queuedイベントのkind/document/project/OldSolution/NewSolutionがimmediateと一対一に一致する。
- document callbackが指すSolutionと対応するイベントのNewSolutionが同じ参照である。
- distinct公開遷移が初期Solutionから最終Solutionまで鎖をなし、linked二文書のイベントが同じold/new pairを共有する。
- 明示requestに従うtarget/background内容、linked整合、writer commitと公開遷移、削除、各captured returnを検査する。
- 全観測Solutionについて、4,016 untouched文書のSourceText参照、同一実行の初期text version、文書metadataを比較する。projectのmembership、公開metadata/references、parse/compilation optionの参照、全document membershipも確認する。比較対象を超える全Roslyn内部stateの同値とは呼ばない。
- traceからforeground call/transform/failure countersを再計算し、normal系のQと保護内変換数の上界をチェックする。

raw payload破壊controlはqueued old/new、immediate/current、event欠落/重複、公開chain、untouched digest、linked callback snapshot、linked content、counterの10種類。native実装mutantや独立な実システム故障の検出率ではない。

## 適用範囲
標準SourceText/PreserveIdentity、読み込み済み文書、pinned source/library、指定host・schedulerでの著者側conformanceである。一般的なextension再入、changed-text再入、lazy/custom loader、source-generator/コンパイル処理全体、実editor workload、自然負荷下の時間改善は検査していない。旧patch02同一identity再入TIMEOUTおよび旧測定4条件高速/7条件低速は保存される。未改変4件はwriter0であり、未改変sourceの競合下同値検査と呼ばない。

この結果は公開event payloadのcoverage不足を補う。実用的重要性、新規性、投稿readyを単独で確立する結果ではない。次は、sourceにある競合/ロックの問題と資源保証の対応、保護内変換を許せる条件を調べる。
