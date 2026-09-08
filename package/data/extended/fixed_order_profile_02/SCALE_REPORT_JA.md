# 強制順序の初回cold全工程比較

60新chain×2方式の全120unitを保持。persistent42SUCCESS/18TIMEOUT、current hybrid36SUCCESS/24TIMEOUT、その他0。5秒/1GiB/50ms sample、交互順、全243.126442秒。36の両方保存root curveは全一致し、残る24は既存方式が比較curveを未生成。部分構築をSUCCESSへ昇格しない。

両者の遷移は{"SUCCESS->SUCCESS": 30, "SUCCESS->TIMEOUT": 6, "TIMEOUT->SUCCESS": 12, "TIMEOUT->TIMEOUT": 12}。詳細な構築完了数・時間・最大bytes/RSS/node数はscale01/ANALYSIS.json。特に費用増加chainでは既存packed checkerの方が完了範囲を保ち、新方式の全suffix走査が不利になる。原稿は既存cost-compatible fast pathを持ち続ける。

これは著者作成入力の探索測定で、用途やspeedup一般の根拠ではない。共有treeを使うchecker03は別版・別protocolで検査する。今回18timeoutや既存24timeoutを書き換えず、03にも全60入力を残す。raw SHA256 9c57e9da275fab3dc52d8de94aabfd4cbab9b1a0ee2c54561d8137f0fe978ab6。
