# 任意固定順序のpersistent構築：初回意味論検査

結果前固定24,029入力すべてSUCCESS、FAILURE/TIMEOUT/INVALID/NOT_RUNは各0。内訳はc=1..3,p=0..3の長さ0..4全列22,621、wide binary256、長さ5..20のseed固定1,024、明示順序を付けた分岐DAG128。最後の128はその順序に限定したserial macro族を検査し、一般DAGの自由順序最適値との一致を主張しない。

全入力をJSON保存形式へ変換・reloadし、独立な構造/full Bellman checkerが全suffixの全非負整数予算と最初の保護閾値を検査した。既存一般curve構築器を同じ強制順序chainへ適用し、全329,275 suffix profile entryと無限tailが一致した。別のscalar recurrenceの1,659,762 cellsでもvalueと保存policy actionが一致。事前選択80artifactを保存し、残りはexact hash/bytesをrawへ保存した。12 malformed inputと3正例×17 corrupted certificateの63 rejection controlもすべて想定通りだった。

6.130137秒。raw SHA256 285fbc5c9e98bf54ae7a2dbc546a5c3faed9c739c7736fcddb7ae9ef9d282888。これらは探索的な反証検査であり、帰納的な定理やAVL計算量を有限標本から証明しない。共有treeの構築はO(n log n) arithmeticを意図するが、現在の独立full checkerはsuffix走査の最悪O(n²)。60新入力/120cold unitの別測定で初回構築・serialization・reload・full check・queryの全費用を検査する。旧結果・raw・コードを変更しない。
