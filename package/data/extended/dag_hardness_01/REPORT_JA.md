# B=1でも残るDAG費用最適化の計算難しさ

2026-09-08 04:12 JST。著者側理論・反証検査であり、採択または独立blind認証ではない。

**失敗予算B=1の閾値判定は、保護premiumが全て1、二層DAG、最大入次数2、失敗費用が2種類に限られてもNP完全である。** 二つの費用値はinstance-dependentであり、全入力で固定した二定数ではない。CLIQUEからの還元はPROOF_DRAFT.mdに実行前保存した。n<=3 / 4処理の正のadaptivity gapとは異なる計算複雑性の境界である。

B1では、任意方策のno-failure経路に沿うtopological orderとmode bitsを固定し、失敗後は同じ残り順序を全FASTで終えることができる。費用はmax(全protected premium,各FAST job直前のprotected premium+c_i)。これがNP membershipの短いcertificateになる。同時に、B1では任意DAGでF=Vであることも示す。

読み取り担当は還元を確認したが、無条件にk1までisolatedvertex追加を適用すれば誤る境界を指摘した。元draft/plan/codeは既にk>=2に限定し、m<binom(k,2)を負の固定instanceへ処理しているため、今回の実行入力にこの欠陥はない。一般CLIQUE全domainへ記述を拡張する際はk<=1/k>nのtrivialcasesを先にYES/NOへ処理する。rawはAUTHOR_CHECK_RAW.jsonへ不変保存し、担当は終了した。

## 固定した有限反証

元グラフの頂点数2..5、全ラベル付き単純無向グラフ、k2..nの全4,306units。1,813は結果前定義のtrivialnegative、2,493は通常還元。全4,306 SUCCESS、FAILURE/TIMEOUT/INVALID/NOT_RUN0。CLIQUE YES1,822 / NO2,484、scalarが訪れたresidualstates合計923,314。全no-failure certificateの独立走査値がscalar値と一致し、全YESのclique-first証明方策も閾値を満たした。

事前のstructural ruleで選んだ274inputsについて、既存hybrid compilerと全budget checkerも一致。残りはNOT_SELECTED_BY_PREDECLARED_RULEであり、失敗・未実行隠蔽ではない。総3.340255秒、RAW SHA256 d6d439284e7260336fcf68d7d038e59215678e32398ca0e0b6def71f276bf18f。全case/plan/codeはMANIFESTへ実行前固定した。小規模検査は一般定理の証明を代替しない。

## 主張の範囲

数字はjob数Nに対してc_i<=N+1、全仕事量閾値も多項式に抑えられ、巨大なbinarybudgetを原因としない。この定理は一般多項式時間解法に対する障害を説明するが、全ideal列挙の最適性、指数space、curve数の下界を証明しない。cost-compatibleDAGの高速部分クラスと同条件で対置する。primitiveへの値等価性を通じた帰結と、一般言語のprogram synthesisの複雑性を混同しない。
