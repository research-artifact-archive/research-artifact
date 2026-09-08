# 05:34 JST: 先行理論の具体的対応

親担当が一次資料の該当箇所を再確認した。Burdzy–Kang–Ramanan (2009) の出版版 Theorem 2.6 と Eq.2.8 は印刷p.433/PDF6、射影と跳躍則 Eq.2.12–2.13/Prop.2.9 は印刷p.435/PDF8。preprintの式番号とは異なる。出版PDFとpreprintのbytes/hashはSOURCE_RECEIPTに保存。

自分たちの代入は psi(t)=c floor(t), ell(t)=g_floor(t), r(t)=h_floor(t)。g0=0, h0>=0, g<=h により初期値0、各整数時刻の射影が現在のcapped recurrenceに一致する。上障壁を除くとD_b=cb+max_{0<=k<=b}(g_k-ck)。一般再帰のexplicit solutionは継承である。今回の追加代数は、gの離散凹性でDをslope-floor和へ書換え、さらにhの凹性でv=min(h,D)とする点、ならびに各DAG child curveがその仮定を満たす証明である。

hの凹性は除けない。g=(0,0,0,...), h=(0,1,100,100,...), c=2なら、b=0,1,2でv=(0,1,3)、D=(0,2,4)、min(h,D)=(0,1,4)。これは新しい実験ではなく式への直接代入による反例である。独自貢献の重要性/短い既知導出の有無は未確立。

Lawler (1973) はpublisher abstractだけを親担当がweb表示で確認した。ローカルHTML取得403とfull PDF未読を保持する。B1の各modeを(processing,tail)=(p_i,0)または(0,c_i)へ写す。precedenceはmachine completionを拘束する。mode固定後のsequencingを継承し、mode選択に関する今回のrestricted hardnessは自己完結証明を保持する。full theoremを読んだとは記さず、先行研究不在やfirstを宣言しない。

原稿25/26に帰属を統合。正規000088/旧raw/旧不利結果は変更しない。CP/DP結果はall-budgetが指定B1/B2でも必要という主張を否定し、policy/curve outputの差も明示する。
