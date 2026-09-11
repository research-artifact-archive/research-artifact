# 非一様fee残余ゲーム：未来DAG境界の限定探索報告

**結論：指定した有限探索範囲では、同一のp/h/qベクトル・共通prefix・current targetを保って未来順序だけを変える反例は見つからなかった。** n=2〜5の二つの事前固定population、計130,832ゲームで、共通stateのV差・prefixでのV差・現fresh許否差はいずれも0。これは一般のDAG独立性の証明ではない。依頼どおり一般定理へ昇格せず、著者側の有限結果として保存する。

一方、追加探索前に後退演算の代数候補 `V(D,k)=Top_k(q_D ∪ h_S)` を導出した。恒等式と後退帰納の案を **HYPOTHESIS02.md（未採用・root検査用）** に分けて保存した。有限一致を根拠にこの式や一般定理の成立を認定したものではない。原稿、共通STATUS、公開artifact、旧rawには統合していない。

## 意味論と比較

SCIENTIFIC・著者側探索であり、blind reviewではない。指定された charged_residual_01/{PROOF03.md,check01.py,AUTHOR_THRESHOLD_CHECK03.md} と residual_safety_01/PROOF02.md を読み、固定有限J、p>0、h>=0、q=p+h、fresh増分p、cached match0/bad qを継承した。current preparation直後の各cached gateへ一回のfresh-identity writeでbadを実現する。逐次・各job一回完了・disjoint gateであり、追加prep、retry、部分処理、別資源観測を導入しない。

同じ一つの因果的決定的方策が、budget bを入力せず、全b>=0および全playで無条件にb-write以下の全環境に対して `ell+futureL<=Top_(k+b)(q_J)` を満たす、という量化を保持した。kはmismatch offsetで0<=k<=|D|。一般のactual writesとmismatch数は同一視しない。

主比較はD={0},k=1,ell=q0、current target1。初期cached0の一回badで得る共通prefixである。両worldは同じラベル付きp/h/q、同じ0->1と1->全futureを持ち、future間だけをfree orderまたは各順序のchainへ変える。n4ではfree/2->3/3->2の3種、n5ではfreeと6種類のchain。n2/3はfuture edgeを変える余地のない小さい対照。さらに各graph間で共通idealになっている全physical (D,k) のVを比較した。全ラベル付きDAGを直接列挙したという主張ではない。

## 固定した実施範囲と全分母

PROTOCOL01.mdはrun01前、PROTOCOL02.mdとHYPOTHESIS02.mdはrun02/03前に作成した。各START.jsonがprotocol・checker・具体INPUTSおよび元資料をSHA256結合する。run02はrun01後の明示的な探索拡張、run03はrun01と同じ費用入力を使う別実装であり、独立な新しい入力分母として合算しない。

| run | 固定範囲 | 実施分母・結果 | 実時間 |
|---|---|---|---|
| run01 / check01.py | n2〜4、p∈{1,2},h∈{0,1,2,3}の全ラベル付きベクトル＋共通h対照 | 13,104/13,104ゲーム、209,760 physical state、共通state比較51,680。V差・現fresh許否差0 | 2.603秒 |
| run02 / check02.py | n4: p∈{1,2,3},h∈{0,1,3,8}の全ベクトル。n5:6種類の(p,h)から全ベクトル。共通h対照も別に固定 | 117,728/117,728ゲーム、2,323,360 physical state、共通state比較323,648。V差・現fresh許否差0、代数候補との不一致0 | 34.382秒 |
| run03 / check03.py | run01のn4・4,096費用ベクトル×3graph。現fresh後の全継続方策・全分岐を直接列挙 | 12,288/12,288 cases、98,304完全方策、245,760 leaf paths、737,280 leaf/k検査。36,864閾値照合の不一致0 | 2.738秒 |

run01/02を合わせた記録上のstate数は2,533,120、明示した共通fee controlのstate数は27,808で全て `V=C=Top_k(q_D)`。任意feeでの `V>=C` 違反も0。二populationやcontrolには宣言した重複があり、unique instance数とは呼ばない。

3runすべて正常終了。失敗0、exception0、timeout0、invalid0、未実施0、除外0、再実行0。各run上限120秒と13:18JST絶対期限をコードで設定した。最終実験終了は **13:07:27.507 JST**。新しい実験を追加する必要はないと判断して終了した。

原始rawはrun01/02のSTATES.jsonl.gz（全stateとaction閾値）、COMPARISONS.json（全vector/graph比較）、STATUSES.json、ERRORS.json、WITNESSES.json、run03のALL_POLICY_PATHS.jsonl.gzとALL_INITIAL_PATHS.jsonl.gzに保持した。WITNESSES.jsonの空配列も不利な結果として保存した。予定入力・全policy tree・全leaf skeletonは結果前に保存している。

## 別の全pathcheckとactual write cap

check03.pyは閾値DPや代数候補をimportしない。残り二jobに対するfree orderの12方策、各chainの6方策を明示的な完全treeとして列挙する。cachedのmatch/bad後には別々の子方策を認める。各treeを全budgetで共用し、leafごとのfuture保護費用とbad数cを数え、`min_leaf(G_(k+c)-futurecost)` を評価してから全treeの最大を取る。Gもsortではなく部分集合の全列挙で計算した。この値がk=0,1,2の各DP閾値と一致した。

現fresh許可は4,020 case、拒否は8,268 caseであり、全て拒否されるだけの空疎な一致ではない。各拒否caseで **全継続方策のそれぞれに** 違反leafが存在することを検査し、全leafと各方策の最小slack leafを保存した。閾値を先に最適化してから別budgetの方策を組み合わせる検査ではない。

ある固定treeの違反leafを一つ選び、そのbad数cを固定する。そのleafのcached gateだけに一回ずつfresh identityを書き、履歴が逸れたら以後writeせず、c回を超えるwriteは必ず抑止する環境を作れる。これは全playで無条件にc-write以下であり、固定した決定的tree上で同じleafを再現する。future契約にはb=cを、初期契約には後述のprefix一回を加えB=1+cを適用できる。この構成はpolicyにcを知らせず、writerの未来予知も要求しない。

逆に全leafがG_(k+c)を満たす同じtreeなら、無害writeを含む任意playでもc<=bで、Gの単調性によりG_(k+b)を満たす。これが有限leaf検査から全actual-write-cap量化へ接続する理由であり、単にbを有限個だけ試したという論拠ではない。

## 初期all-cachedからの到達性と許可側の全初期方策

各graph/vectorに対して初期all-cachedの全16leaf、計196,608 pathsを検査した。全て元の初期boundを満たし、job0だけbad・以後matchの一write環境で共通prefixD={0},k1,ell=q0へ到達できる。拒否側でもこのprefix自体は健全な初期all-cached方策から到達可能である。

現freshが許可された4,020 caseそれぞれについて、`cached0; matchなら残りall-cached; badならfresh1と最初のsafe suffix tree` という一つの初期方策を作成した。全42,738 leafをactual targeted writesに対応するGで照合し、違反0。全initial treeとtraceをrawに保存した。これは許可/拒否を初期からの新しい最悪仕事量改善へ読み替える主張ではない。

読みやすい正例（DAG差の反例ではない）は、p=(1,1,1,1),h=(0,0,0,2),q=(1,1,1,3)。G=(0,3,4,5,6)。cached0 badでell1、その後fresh1でell2。future job2はcached、job3はfreshにすると、**2->3でも3->2でも** 終端費用は3+c、実write数は1+c、c∈{0,1}。G1=3,G2=4で両方安全である。completedだけのCはfresh直後に1なので、この例は保守的Cを越える許可が実在する一方、未来順序差はないことを示す。EXAMPLES03.jsonに該当する保存済み入力・両checker結果を抽出した。

## 代数候補と残課題

HYPOTHESIS02.mdの候補は、futureのqをhへ置き換えたmultisetでVを表すもの。核となる式は、Xを非負multiset、q=p+hとして

    max(Top_k(X∪{q})-p,
        min(Top_k(X∪{q}),Top_(k+1)(X∪{q})-q))
      = Top_k(X∪{h}).

k=0、1<=k<=|X|のq対kth(X)の二場合、k>|X|を分けた導出と、各ready iについて同じ式を得る後退帰納の案を同ファイルへ保存した。rootが一般結果を検討する場合は、有限0件という結果より先に、この恒等式と全budgetゲームへの帰納の接続を別途確認するのが有用である。**本担当では一般DAG独立性の定理として採用・公開しない。**

既知の「点ごとのh_future<=tauは任意bad successorで不変ではない」という反例はそのまま継承する。candidateが正しくてもこの非不変性は消えず、Cからのcached安全性と、C外の任意viable stateで全cachedが安全という別主張を混同しない。未来feeの情報が許否に影響する既存A/B結果も反証していない。

実client効果、native費用、初期からの新最悪仕事量曲線、一般最適性、FSE上の重要性、採択可能性、投稿readyは今回確立していない。

## 所有範囲・終了

成果物は本dir内のPROTOCOL01.md、PROTOCOL02.md、HYPOTHESIS02.md、check01.py〜check03.py、run01〜run03の入力・原始raw・summary、EXAMPLES03.json、VERIFICATION01.json、本報告、MANIFEST.json、STOP_RECEIPT.json。最終の全変更pathとhashはMANIFEST.json/STOP_RECEIPT.jsonに列挙する。正規稿、共通STATUS、public、旧rawを編集していない。

範囲逸脱を一件開示する：一回のpatchで `../PROTOCOL02.tmp`（内容はtemporary placeholderのみ）を誤作成し、次のpatchで即削除した。結果やrunには使用していない。指定外への一時書込み0とは報告せず、SCOPE_INCIDENT01.mdに保存した。最終時点で同ファイルが存在しないことを確認した。

全STARTに結合した入力・protocol・code・rawのhashはcloseout時にも一致。起動した実験processは3個で全て正常終了し、記録PID87901/88949/89270は不在、**所有実験process残0**。追加agent・Claude・API・課金・credit・reset・人評価は0。停止後は新たな明示指示なしに研究を再開しない。
