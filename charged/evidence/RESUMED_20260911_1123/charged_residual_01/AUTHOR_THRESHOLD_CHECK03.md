# 著者側限定証明検査03：threshold adversaryによるcharged residualの必要性

2026-09-11。SCIENTIFIC／著者側の手計算・証明検査であり、独立blind査読ではない。rootが正規稿の唯一writer。本担当の成果物は本ファイルだけである。指定された五資料を読み、新規実験・列挙・Claude呼出し・追加分担・課金・credit・reset・人対象評価は行っていない。

**判定：明示された残余ゲームでは定理Nも任意feeの必要上界も成立する。threshold adversaryと実write数へのcapを組み合わせれば、任意の有限nについて完全な短い証明になる。** ただし、τ非減少、および定理Nのfee仮定下でのσ非増加は指定adversaryに沿った性質であり、任意のcached outcomeに対する不変性ではない。定理N下のfresh guardは最大許容、viable stateでcachedは全ready jobについて安全だが、そのmismatch successorが定理Nの仮定を保つとは限らない。「この敵はfresh/cachedの観測を要しない」という付記は本証明からは支持されない。

## 1. 検査した入力と意味論

読取り時のSHA-256：

| 入力（本ファイルと同じdirからの相対位置） | SHA-256 |
|---|---|
| HYPOTHESIS02_UNIFORM_AND_PAIR.md | `4fa197d14667f568d713cc8640dc73ccdeb6c9c3023a0143f3b7dc0e8424b451` |
| HYPOTHESIS03_SEPARATED_FEES.md | `5c6019add13aa72f92f28a7b8b9e4dc3fb1d305795c7fa07909460f33c8f4707` |
| AUTHOR_PROOF_CHECK02.md | `3ab9331f87c24b98aabb256b55556d1b27b1b9ad7074fd3b17983198314e81ea` |
| CLAUDE_RESPONSE01/RAW.md | `efde8346c68074ba43d9de987d647136f558096b2f2190381b9a3a7c42bc790b` |
| ../residual_safety_01/PROOF02.md | `a9d0dca1eb89a59e17d8e6aebc91dd4c945f634ecdd566e5e3d5ae683069bdc7` |

有限の固定job集合J、DAG、完了ideal D、残集合S=J\Dを扱う。各jobの費用は有限で、p_i>0、h_i>=0、q_i=p_i+h_i。freshは保護費用p_i、cached matchは0、cached mismatchはq_iを払って各jobを一回だけ完了する。cachedはcurrent preparation後の比較gateを持ち、その間の一回のfresh-identity writeでmismatchを強制できる。異なるcompleting callsの該当区間は重ならない。追加prep、cheap retry、retained guard、返金、別の費用・資源観測は追加しない。

初期状態の整数creditは0<=k<=|D|、既払保護費用はell>=0。以後kをcached mismatchごとに一増やす。物理的なcount条件を課しているが、これだけで「ある健全な初期方策から到達した状態」と同義にはしない。

T_t(A)=Top_t(q_A)、G_t=T_t(J)と書く。Topはt>=|A|で全和にclampする。τはDのqのk番目、k=0では+∞。σ=T_k(D)-ell。空futureのfee条件は全称命題として自明に真とする。

viabilityの量化は次のとおりである。

    ∃ 一つの因果的な決定的方策P（予算B/bを入力しない）
    ∀ 整数b>=0  ∀ E∈E_b:
        Pは有限時間に全jobを完了し、ell+L_future(P,E)<=G_(k+b).

E_bのwrite上限bはその環境の全playで無条件に成立する。Pに環境の名前・上限を別入力で通知しない。同じ観測履歴なら同じ次actionを選ぶ。writerは既に選ばれたpublic job/modeまたはcached gateに反応できる。この観測条件より弱いゲームは本検査の定理に含めない。無害なwriteがある一般playではactual writesとmismatch数を同一視しない。

## 2. 正規稿へ使える短い定理と完全証明

**定理（threshold necessity）。** 上記のゲームで0<=k<=|D|とする。任意feeで

    ell <= T_k(D)                                      はviabilityに十分、
    ell <= T_k(D) + Σ_(i∈S) (h_i-τ)^+                  はviabilityに必要。

k=0で右の和は0と定義する。従って、全i∈Sについてh_i<=τなら

    viable(D,k,ell,S)  iff  ell<=T_k(D).                 (N)

**証明。** 十分性はall-cachedで得られる。matchではT_k(D+i)>=T_k(D)、mismatchでは

    T_(k+1)(D+i) >= T_k(D)+q_i

なのでσ>=0を保つ。有限DAGをready順に完了でき、future mismatch数cはfuture writes以下である。終端でell_final<=G_(k+c)<=G_(k+b)となる。

必要性では、契約を満たす一つのPを固定する。k=0ならb=0のno-write環境で総費用>=ellかつG_0=0だからell=0が必要である。以後k>=1とする。

環境E_*は各cached iのgateで、**その時点の**q_i>=τのときだけfresh identityを一回書き、それ以外はwriteしない。各初期残jobに一個のwrite slotを割り当て、使用済みslotは再使用しない。従って全playで高々N=|S| writesであり、Pの契約をb=Nに適用できる。得られるplay ρは有限に完了する。

このplayで、cached iがq_i>=τならmismatchによりσは不変、τも不変である。q_i<τならmatchにより上位k個が不変なのでσもτも不変である。freshではkは不変、Dに一要素が加わるためτは非減少であり、

    Δσ = (q_i-τ)^+ - p_i
        = -p_i          if q_i<=τ,
        = h_i-τ        if q_i>τ.

ここでτ_0を初期値とすると、τ>=τ_0より全fresh stepで

    Δσ <= (h_i-τ_0)^+.

特に定理Nのfee仮定下ではh_i<=τ_0<=τなので、各freshのΔσ<=0、cachedのΔσ=0であり、σは非増加である。任意feeの場合にはσの非増加を仮定せず、上の増分上界だけを使う。

各jobは一回だけ完了するため、終端のslackは

    σ_final <= σ_0 + Σ_(i∈S) (h_i-τ_0)^+.               (1)

ρで実際に行ったwrite数をcとする。**このcを定数として**、E_*を模倣するが累計c回を超えるwriteを必ず抑止する環境E_cを新たに定義する。E_cはρ以外も含む全playで高々c writesである。同じPと初期状態を用いるとρを終端まで再現する。実際、同一履歴の次actionは同一であり、ρにはc回を超えるwrite要求がないのでcapはρのどのwriteも削らない。観測値・identity・mode・結果・費用を含む全履歴についてこの帰納法が成立する。

従って**同じP**の契約をE_c、b=cに適用できる。このplayでは各writeがちょうど一つのcached mismatchを生じ、他のwriteはないのでk_final=k+c。よって

    ell_final <= G_(k+c) = T_(k_final)(J),
    0 <= σ_final.

(1)と合わせて必要上界を得る。全future feeがτ_0以下なら右の補正和は0であり、十分性と合わせて(N)が成立する。□

この証明は有限の任意n、正の実数p、非負の実数h、同率q、h_i=τ、k=|D|、S=空を含む。h_i=τではfreshのΔσ=0も許すため、厳密減少を主張する必要はない。k=0は別に処理しており、∞-∞を計算していない。実験件数は証明に使っていない。

### capの量化で省略してはいけないこと

論理順序は「Pを固定→合法なN-bounded環境で有限ρを得る→整数cを固定→合法なc-bounded環境を構成→同じPにb=cを適用」である。反証環境が固定Pに依存することは全称契約への反証として合法である。実行中のwriterに未来のcを予知させず、E_*自身が全playでc-boundedだったとも主張しない。

PをP_cへ取り替える、予算cを新たにPへ教える、cap後の別playがたまたま同じ費用だと仮定する、という議論ではない。追加の乱数モデルや期待値保証への拡張も行っていない。

Claude冒頭の「全b契約は終端Cと同値」は、この証明の入口として不要である。一般playのharmless writesを無視してk_finalを全write数へ読み替えることはできない。本証明で必要な終端Cは、無害writeのないρをc-bounded環境に再現して得た**そのplayについての帰結**である。全観測モデルについての一律な終端同値を別途主張する必要はない。

## 3. fresh最大許容とcached successor

以下の「safe」は、そのactionから同じ全b契約を守るcontinuationが存在することを指す。総仕事量Wの最適性ではない。

### fresh：定理Nの仮定を保つので必要十分

(N)の仮定を満たすstateでready iをfreshにすると、後続は(D+i,k,ell+p_i,S\{i})。τ' >= τなので残る全h_j<=τ'であり、physical count条件も保つ。後続に(N)を適用して

    fresh i がsafe  iff  ell+p_i <= T_k(D+i).            (F)

従ってviableな(N) stateでは(F)が最大許容fresh guardである。qi=τの境界も含む。k>=1では同じ条件を

    q_i>=τ:  ell <= T_(k-1)(D)+h_i,
    q_i< τ:  ell+p_i <= T_k(D)

と書ける。k=0ではT_0=0、p_i>0、ell>=0のためfreshは許可されない。

### cached：Cを保つが、任意mismatch後のN仮定までは保たない

viableな(N) stateではC、すなわちell<=T_k(D)が成立する。ready iの二後続は

    match:     (D+i,k,ell,S\{i}),
    mismatch:  (D+i,k+1,ell+q_i,S\{i}).

両方がCを満たすことは十分性証明の二不等式から直接従う。任意feeでCは十分なので、**全ready cached actionが安全**である。mismatch後に(N)を再適用してこの結論を出す必要はない。

任意outcomeに対する差分を明示する。k>=1、d_(k+1)をDのk+1番目のq（存在しなければ0）とすると、

    cached match:     Δσ=(q_i-τ)^+ >=0、τ'>=τ,
    cached mismatch:  Δσ=(d_(k+1)-q_i)^+ >=0、
                      τ'=min(τ,max(q_i,d_(k+1))).

従って、q_i>=τのmismatchはτ'=τだが、q_i<τのmismatchではτ'<τも起きる。k=0からのmismatchではτ'はD+iの最大qとなり、+∞から有限値へ変わる。この場合もCの保存は成立する。

**確定反例：N仮定は通常のcached mismatchで不変ではない。** chain A→i→jを、(p,h,q)がA=(1,9,10)、i=(1,1,2)、j=(1,5,6)とする。all-cachedでAが一回mismatchした状態はD={A},k=1,ell=10,τ=10。futureの最大h=5<=10で(N)とCを満たす。ここでcached iがmismatchするとD'={A,i},k'=2,ell'=12,τ'=2。残るh_j=5>2となり(N)の仮定は外れるが、Cは12<=12で保たれる。このprefixは健全な初期all-cached方策から物理的に到達する。

よって正確な結論は「(N)が成立するviable stateの全safe actionは、全cachedと(F)を満たすfresh」である。初期の点ごとの(N)だけから、全将来stateでもこのfilterが最大許容だとは言えない。上例のように仮定外へ移った後もfilterは安全だが、その先の最大許容性には新しい(N)確認または別の十分な構造契約が必要である。

この区別は証明形式だけの問題ではない。chain A→B→C→Zで(p,h,q)をA=(1,9,10)、B=C=(1,1,2)、Z=(990,10,1000)とする。A mismatch後のD={A},k=1,ell=10,τ=10はfuture最大h=10で(N)を満たす。cached BがさらにmismatchするとD={A,B},k=2,ell=12,τ=2となる。ここからfresh Cは13>Top_2(10,2,2)=12で(F)に拒否されるが、続けてfresh Zを行えば総費用1003<=G_2=1010なので、全future budgetに安全である。このprefixの全初期方策も、AとBがともにmismatchしたときだけfresh C,Z、それ以外はall-cached、として構成できる。前者は二write以上で1003<=G_2、後者は通常のall-cached boundを満たす。従って初期(N)からの健全な到達経路上でも、仮定を失った後の(F)は厳密に保守的になり得る。

## 4. 成立範囲と追加の手計算反例

### 同一B非入力方策は実質的な条件

量化を「各bに別々の方策P_bが存在」へ弱めると、(N)は偽になり得る。全jobが共通h=1のchain A→B→Zを、p=(1,1,9)、q=(2,2,10)とする。cached A mismatch→fresh Bの物理prefixでD={A,B},k=1,ell=3,τ=2である。h_Z=1<=2だがCは3<=2で偽。

予算を入力する方策なら、b=0でcached Zを選び費用3<=G_1=10、b>=1でfresh Zを選び費用12<=G_(1+b)（G_2=12）を満たす。一方、予算を入力しない一つの方策は、freshならb=0で12>10、cachedなら一writeで13>12なので不可能である。これがcap再現で「同じP・同じ観測履歴」を保つ理由である。このprefixが未知予算に対して健全な初期方策から到達するとは主張していない。

### 一般必要上界は十分条件ではない

chain A→B→u→vで、(p,h,q)をA=(1,1,2)、B=(2,0,2)、u=v=(1,3,4)とする。cached A mismatch→fresh Bの物理prefixではD={A,B},k=1,ell=4,τ=2。

    T_1(D)+Σ_future(h_i-τ)^+ = 2+(3-2)+(3-2)=4

なので必要上界は等号で通る。しかし敵が各cached futureをmismatchさせると、u,vのmode列(FF,FC,CF,CC)の終端費用はそれぞれ(6,9,9,12)、actual write数に対応するbenchmarkは(G_1,G_2,G_2,G_3)=(4,8,8,10)。全て違反する。同じcap論法で各方策に合法な環境を与えられるためviableではない。この反例は解析的な四つの計算であり、新規実験・網羅結果ではない。

上界の緩さは、各future feeの超過を初期τに対して合算する一方、freshによってτが上がる場合をその合算で差し引いていないことに由来する。必要上界を正確なviability式へ昇格させない。

### 一様fee・分離条件・領域境界

一様hならk>=1でτ=p_d+h>h、k=0ならτ=+∞なので(N)が全physical-count stateで成立する。全Jに共通する契約max_i h_i<=min_i q_iも同じ結論を与え、等号も許す。これらは任意のcached successorにも適用できるため、前節の点ごとの(N)と違って全経路の最大許容filterを正当化する。completed jobsのhまで制限する必要があるのはこのglobalな設計時条件の書き方であり、点ごとの(N)自体はfutureのhだけを制限する。

futureの正確な費用を読まない実行guardと、そのguardの最大許容性を保証する入力契約は区別する。例えば全jobについて共通の定数Hを契約しh_i<=H<=q_iを保証すれば、futureの個別値を読まずに分離条件を満たせる。(N)の仮定が保証されていない未知futureに対し、guardの形がcompleted/current情報だけを使うことから無条件の最大許容性を導いてはいけない。

0<=k<=|D|というdomainを外すと、D=空,k=1,ell=1,S={i},(p_i,h_i,q_i)=(1,2,3)でも、fresh完了の総費用2<=G_(1+b)=3が全bで成り立つ一方Cは偽になる。これは今回の定理への反例ではない。以前のuniform/separated証明が物理count条件を課した理由とも整合する。

## 5. 観測条件・原稿で残すべき区別

**「no-mode-observation」は未支持。** 本構成は「選ばれたcached iでq_i>=τなら、current preparation後に書く」というpublic action/gateへの反応を使う。hidden program stateや未来のwrite数は観測しないが、これだけではfresh/cachedを区別できない観測モデルでも同じ環境を実装できるとは言えない。cachedだけに現れるgateを観測できるなら明示的mode labelを読む必要がない可能性はあるが、それは観測インターフェースについての追加説明である。真にmode/gateを区別できないwriterへの定理拡張は別証明を要する。今回「no-mode theoremへの確定反例」を示したのではなく、付記を削るか条件付きにするのが正しい。

**初等構造と研究上の差は別である。** top-k差分、cardinality-budgetのtop-weight構造、winning regionからsafe actionを選ぶ構造は既知の基礎として扱う。本担当の成果は、この局所費用モデル・全budget量化に対して短い必要性証明を成立させ、feeの適用条件とcached後続の扱いを明確化したことに限る。これだけで新規性・FSE上の重要性・native資源契約・Gのminimax最適性・W最適性は確立しない。Claudeの報告した実験数は未追試であり、証拠として採用していない。

## 6. 担当終了

2026-09-11 12:28 JSTに結論・完全証明・解析的反例を確定し、本担当を終了停止した。本文の読戻しと、指定五入力のSHA-256が読取り時から一致することを確認した。本担当の変更は本ファイルの新規作成のみであり、正規稿、status、既存証明、旧記録は変更していない。研究用子processは起動0・残0。新規実験・Claude・追加分担・課金・credit・reset・人対象評価は0。終了文の読戻し以外の作業は行わず、12:50 JST以後の継続や通知による再開はしない。
