# Call-slack frontierのnative検査

8形状、κ=0/2、threshold0..3×二/三モードの128入力を固定し、全8,800policy-path replays、512 concurrent runs、2 native controlsを保存した。ordinary9,312件は全てSUCCESS、全1,024 replay groupsでモデルの各最大W/L/Q/costと一致した。Lの最大値はcall slack r=max(B-threshold,0)で、三モードtop min(B-r,n)の合計、二モードB>rなら全合計・B<=rなら0に一致する。

Record8/8、sequence5/5、parser4/4 controlsは期待結果で、live-parentはfixed_policy_and_static/captured parentの拒否へ結ぶ。失敗・timeout・invalid・unstartedなし。ソース・生ログ・入力・計数の全hashと時刻はattempt01。table domainはb0..3のみで、定数tailやscalar-cost最適性を主張しない。

Java callback/kernel/writer/outputはValue以降の原source bytesを保持。W/L/Qは選択した演算/保護内演算/foreground atomic-call入口の計数で、nativeの実時間・通常application利用頻度・全Java意味論の独立証明ではない。全W/L/Q Pareto frontierの導出でもない。
