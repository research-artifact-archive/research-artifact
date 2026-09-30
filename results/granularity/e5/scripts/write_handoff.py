#!/usr/bin/env python3
"""Assemble the final E5 prose from terminal tables; never change inputs or raw."""
from collections import Counter
from datetime import datetime
from pathlib import Path
import csv
import json

E5 = Path(__file__).resolve().parents[1]
SUBMISSION = E5.parents[2]


def read_csv(name):
    with (E5 / 'tables' / name).open() as f:
        return list(csv.DictReader(f))


def main():
    summary = json.loads((E5 / 'tables/summary.json').read_text())
    assert (E5 / 'raw/runner_finished.json').exists()
    assert not summary['provisional'], 'Do not report an ongoing series as final'
    rows, pairs = read_csv('results.csv'), read_csv('pairs.csv')
    models, domains = read_csv('models.csv'), read_csv('source_domains.csv')
    assert len(rows) == 54 and len(pairs) == 18 and len(models) == 9
    assert not any(r['decision'] in ('RUNNING', 'NOT_RUN') for r in rows)
    counts = Counter(p['category'] for p in pairs)
    outcomes = Counter(r['decision'] for r in rows)
    attempted = sum(r['decision'] != 'NOT_RUN_DEADLINE' for r in rows)
    df_attempted = sum(r['method_id'] == 'df_none_initial' and r['decision'] != 'NOT_RUN_DEADLINE' for r in rows)
    decided_pairs = sum(p['none_decision'] in ('WIN', 'LOSS') and p['transfers_decision'] in ('WIN', 'LOSS') for p in pairs)
    model_incidence = {category: sorted({p['model_label'] for p in pairs if p['category'] == category})
                       for category in ('witness', 'bothLOSS', 'null', 'other')}
    issues = {k: summary[k] for k in ('validation_errors', 'baseline_validation_errors', 'df_lazy_mismatches') if summary[k]}
    other_counts = summary.get('other_subcategories', {})
    other_note = ', '.join(f'{n} {kind}' for kind, n in other_counts.items()) or 'none'
    jar = json.loads((E5 / 'jars/e5.json').read_text())
    names = lambda category: ', '.join(summary['category_names'][category]) or 'none'
    by = {(r['model_id'], r['target_id'], r['method_id']): r for r in rows}
    table = ['|入力/要件|元none|initial 細粒度|initial 併合|initial DF|区分|',
             '|---|---|---|---|---|---|']
    def cell(r):
        d = r['decision']
        if d not in ('WIN', 'LOSS'):
            return d
        metric = ('r=' + r['worst_completion_rank']) if d == 'WIN' else ('L=' + r['losing_region_states'])
        return d + ' / ' + r['states_discovered'] + ' / ' + metric
    for p in pairs:
        key = p['model_id'], p['target_id']
        label = p['model_label'] + '/' + ('Base' if p['target_id'] == 'base' else 'R1')
        data = [label, p['original_decision']]
        data += [cell(by[key + (method,)]) for method in ('lazy_none_initial', 'lazy_transfers_initial', 'df_none_initial')]
        data += [p['category'] + (('/' + p['other_detail']) if p.get('other_detail') else '')]
        table.append('|' + '|'.join(data) + '|')
    table = '\n'.join(table)
    model_lines = []
    for m in models:
        model_lines.append(f"{m['model_label']}: Base={m['base_category']}, R1={m['r1_category']}")
    domain_table = ['|入力|元の物理対数|initial後の物理対数|', '|---|---:|---:|']
    for m in models:
        data = [r for r in domains if r['model_id'] == m['model_id']]
        domain_table.append(f"|{m['model_label']}|{sum(int(r['source_original_physical_pairs']) for r in data)}|{sum(int(r['source_retained_physical_pairs']) for r in data)}|")
    domain_table = '\n'.join(domain_table)
    prose = (
        'The nine application models underlying the 27 Base/R1/R2 benchmark instances have 22 transfer relations covering all old physical states of their respective components, and the earlier E1 campaign found no decision changes in 54 merged Base/R1 trials; totality removes the physical transfer-domain obstruction but does not by itself prove preservation of realizability. '
        'We uniformly restricted transfers to each old component\'s physical initial state, retaining observer histories and leaving requirements, endpoints, and Post/goal semantics unchanged. '
        f"Among 18 Base/R1 model/requirement pairs, the recorded results contain {counts['witness']} separate-WIN/merged-LOSS witnesses, {counts['bothLOSS']} both-LOSS pairs, and {counts['null']} both-WIN null results, with {counts['other']} pairs outside these three groups ({other_note}). "
        'These are initial-state contract variants inspired by quiescence, not a validation of DSU quiescence or a DUCS encoding.'
    )
    threats = 'The variants and constructed examples provide evidence of existence where separation is observed, not estimates of its prevalence in applications.'
    loss_rows = read_csv('loss_reasons.csv')
    loss_text = []
    for p in pairs:
        if p['category'] != 'bothLOSS':
            continue
        matching = [r for r in loss_rows if r['model_id'] == p['model_id'] and r['target_id'] == p['target_id'] and r['method_id'] == 'lazy_none_initial']
        if len(matching) == 1:
            loss_text.append('- ' + p['model_label'] + '/' + p['target_id'] + ': ' + matching[0]['reason'])
        else:
            loss_text.append('- ' + p['model_label'] + '/' + p['target_id'] + ': certificate reason unavailable or ambiguous; no causal explanation inferred.')
            issues.setdefault('missing_or_ambiguous_loss_reasons', []).append(p['model_id'] + '/' + p['target_id'])
    missing = [r['model_label'] + '/' + r['target_id'] + '/' + r['method_id'] + '=' + r['decision']
               for r in rows if r['decision'] not in ('WIN', 'LOSS')]
    interpretation = f"""E5一次集計は18入力/要件ペア：証人 {counts['witness']}、両LOSS {counts['bothLOSS']}、両WIN {counts['null']}、その他 {counts['other']}。その他内訳は {json.dumps(summary.get('other_subcategories', {}), ensure_ascii=False)}。54セルの終端内訳は {dict(outcomes)}。

54計画セル中{attempted}を試行し、{outcomes['NOT_RUN_DEADLINE']}セルは期限未実施。両版にWIN/LOSSが得られたのは18ペア中{decided_pairs}ペアであり、未確定ペアまで判定差がないと結論しない。Direct-Fullは18計画セル中{df_attempted}試行。未開始セルは事前登録した固定順で待機中に15:39 JSTの開始締切を迎えたためで、実行中の最後のセルは1,200秒上限を維持した。deadlineの判定と次の未開始jobは `raw/deadline_reached.json`、実終了は `raw/runner_finished.json` に保存。新しい試行を期限後に追加していない。

- 証人: {names('witness')}
- 両LOSS: {names('bothLOSS')}
- 両WIN: {names('null')}
- その他: {names('other')}

9モデルの内訳（Base/R1を混ぜて重複計数しない）: {'; '.join(model_lines)}。

各区分に少なくとも1ペアを持つモデル数: {json.dumps({k: len(v) for k, v in model_incidence.items()}, ensure_ascii=False)}。モデル名: {json.dumps(model_incidence, ensure_ascii=False)}。BaseとR1で区分が異なるモデルは複数区分に現れうるため、これらモデル数を足して18ペアや9モデルの分母を置き換えない。

{table}

各完了セルは判定 / 発見状態数 / r=返却方策rankまたはL=返却敗北証明書状態数。空欄やTO/期限未実施を0としない。元noneはE1表で参照した旧Lazy初回rawで、E5新JARや時間と混同しない。DFとLazyの比較可能数は{summary['df_lazy_comparable']}、判定不一致{len(summary['df_lazy_mismatches'])}。元の非制限契約との比較は別集計: {json.dumps(summary.get('none_initial_vs_original', {}), ensure_ascii=False)}。

両LOSSは、この一様制限の下で細粒度でも完了を保証できず、粒度による判定分離の証拠にはならない。両WINはnull、細粒度WIN/併合LOSSのみ証人に数える。逆転・TO・期限未実施・INVALIDは3区分に押し込まない。未解決の検査事項: {json.dumps(issues, ensure_ascii=False) if issues else 'なし'}。

**物理transfer対数（独立source audit）**

{domain_table}

合計22component、旧物理90状態、全域91対→initial22対。多値関係が1つあるので全て「写像」とは呼ばない。compiled censusとの照合状況: {json.dumps(summary.get('domain_comparisons', {}), ensure_ascii=False)}。未実測censusをsource数で補わない。observer付きのaugmented対数はCSVのoriginal_pairs/retained_pairsで別記録し、上表のphysical対数と混ぜない。

**両LOSSの証明書由来の1文**（none側を以下に示し、merged側もloss_reasons.csvに保存。最大3rootの局所閉包根拠であり、一意な全ゲーム因果説明ではない。）

{chr(10).join(loss_text) if loss_text else '該当なし。'}

未完了・失敗セル: {', '.join(missing) if missing else 'なし。全54セルに完了判定がある。'}
"""
    method = f"""新source commit `{jar['source_commit']}`、base `{jar['source_base_commit']}`（E1 production `{jar['e1_production_commit']}`との差はaudit testのみ）。新JAR SHA `{jar['jar_sha256']}`、build/run JDK17、Maven package成功、76テスト（新9本を含む）PASS。コミット間の実装差分は `build/e5_source_delta.patch`（5ファイル、405行追加/3行削除、SHAと統計は `build/e5_source_delta.json`）。最初のテスト記述ミス1件と修正ログも保存。none GSM CLIは旧E1とWIN/31状態/27query/rank4で一致。Post/独立意味論/solver/component/Linkの6sourceがE1とbyte同一であることをrootが検査した。

CLIは元物理状態の初期値を比較し、内部付加observer座標を初期値へ制限しない。genericAPIでは通常のstate equality。既存full CellのAはinitial=h、g_A={{e→e}}なのでこのliteral規則で空になる。指定の「Cell不変」期待は成立せず、特例を作らずWIN→LOSSと契約差をテストに残した。初期状態が既に唯一の転送域である別の小fixtureでは不変を検査済み。

AI利用のmethods追記対象: AS-8を受けた規則の解釈・前処理/診断/テストの実装、実験スクリプト、実行管理、表と本文案の生成、別担当によるsource/raw/CSV照合をAIが支援した。「独立監査」はcampaign analyzerをimportしない別実装の検査を指し、外部の人間による追試ではない。最終解釈と本文への取込みは主担当/著者が行う。

全域性だけから併合でLOSSが原理的に起こらないとは結論しない。UC優先・要件安全・goal到達は別条件である。初期状態のみという一様proxyは、Kramer–Mageeのtransaction静穏性を直接検証するものではない（[原論文 Sec.III-D, p.1296](https://arwana007.wordpress.com/wp-content/uploads/2013/11/the-evolving-philosophers-problem.pdf), DOI [10.1109/32.60317](https://doi.org/10.1109/32.60317)）。構成や入力を結果に合わせて変更していない。
"""
    columns = """`results.csv` は全54セル、`pairs.csv` は18ペアの分類、`models.csv` は9モデルのBase/R1内訳、`components.csv` は実測component別census、`source_domains.csv` は独立静的原典監査、`loss_reasons.csv` は各LOSSの証明書由来の1文と元JSON。`table_e5_states.tex` / `table_e5_metrics.tex` / `table_e5_domains.tex` がS1/S4用。`original_*`は旧基準だが、`original_pairs`等のtransfer census列は制限前の同じ入力の対数である。`*_physical_*`はobserver座標を除いた物理投影、接尾辞なしのpairs/domain_statesはcompiled augmented状態で数える。`worst_completion_rank`は返却WIN方策の完了上界で最適値とは限らず、`losing_region_states`は返却した発見済敗北領域で全ゲームの最大敗北領域ではない。秒はMacの参考値でXeonや旧JARとの速度比較は行わない。LOSS診断時間は後段の別metric。`validation_errors`と`other_detail`に検査不合格・逆転・未完を残す。rawの絶対local command pathは非公開来歴であり、将来公開する場合は原本を残した別コピーで正規化する。今回pushなし。"""
    ledger = '# E5: proposed EVIDENCE_LEDGER append\n\n'
    ledger += 'Insertion proposal only; no file in paper/ or paper/materials/ is edited. Paths below are within experiments/witness_20260929/e5/.\n\n'
    ledger += interpretation + '\n\n' + method
    ledger += '\n\n## RQ2 paragraph (four sentences)\n\n' + prose
    ledger += '\n\n## Threats sentence\n\n' + threats
    ledger += '\n\n## Provenance and columns\n\n' + columns + '\n'
    target = E5 / 'EVIDENCE_LEDGER_APPEND.md'
    with target.open('x') as f:
        f.write(ledger)
    stamp = datetime.now().strftime('%H:%M')
    daily = '\n\n## E5最終集計・取込み案（' + stamp + ' JST）\n\n'
    daily += interpretation + '\n\n' + method
    daily += '\n\n**RQ2用4文。**\n' + prose
    daily += '\n\n**Threats用1文。** ' + threats
    daily += '\n\n**受渡し。** `experiments/witness_20260929/e5/EVIDENCE_LEDGER_APPEND.md` がledger追記案。同dirのRUNBOOK.mdに1コマンド・版・列定義。\n\n' + columns + '\n'
    with (SUBMISSION / 'DAILY/20260929.md').open('a') as f:
        f.write(daily)
    print(json.dumps({'ledger': str(target), 'pair_counts': dict(counts), 'outcomes': dict(outcomes)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
