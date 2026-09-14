# Multiverse 競輪ver — いまここ

最終更新: 2026-09-14 JST

この1枚は主向けの現在地表示。NOW / CURRENT / LATEST は canonical GitHub を Fresh Read して確認する。

## 現在の結論

Frozen `N2_SPEC_ALIGNED_POSTERIOR_CONDITIONAL` は引き続き変更せず、合成環境での比較基準として維持します。

既存DEV2000 PRE-only補完監査では、Frozen N2が直接要求する次の5項目をDEV2000期間へ安全に補完できる既存保存ソースは見つかりませんでした。

- `line_group_id`
- `line_position`
- `line_size`
- `bank_length_m`
- `wind_speed_mps`

既存安全ソースの監査結論は `SAFE_EXISTING_STORED_PRE_ONLY_ENRICHMENT_SOURCES_EXHAUSTED_WITHOUT_FIVE_FIELD_DEV2000_COMPATIBILITY_CLOSURE`。

そのため主は issue #377 comment `5658034266` で、新しい別系統研究を明示許可しました。

## 新たに許可された研究

既存DEV2000 PREで実際に利用可能であることが既に確認されたfield familyだけを前提に、Frozen N2とは別の sibling model / interface を設計し、**合成環境だけ**でアブレーションを行います。

目的:
- 上記5欠損項目への依存度を合成環境で測る
- 5項目を使わない別系統が技術的に成立し得るかを判定する
- Frozen N2との比較は合成robustness / calibration / sensitivityに限定する

これは実世界の的中率・収益性・ROIの検証ではありません。

## Frozen N2

- name: `N2_SPEC_ALIGNED_POSTERIOR_CONDITIONAL`
- status: `UNCHANGED`
- role: `SYNTHETIC_COMPARISON_BASELINE_ONLY`

## 引き続き禁止

- RESULT / PAYOUT
- outcome / 着順 / winner / settlement
- odds / price / market data
- economics / bankroll / ROI / profit
- `ECON_HOLDOUT1000`
- DEV2000 C outcome access
- untouched real-outcome validation
- 実PRE row値を使ったtraining / fit / tuning / parameter selection / model selection
- model promotion / freeze acceptance / production
- 新規自動大量収集
- 外部providerへの連絡・課金・credential利用
- Runtime起動
- 自動投票
- real-money wagering

scientific segment C scoring count は0のまま。
`ECON_HOLDOUT1000` はSEALEDのまま。

## 実行前Fresh Read

合成sibling実験の実行前に必ず確認する:
- canonical main HEAD
- issue #394 最新
- issue #377 最新
- `governance/KEIRIN_OWNER_GATE_DEV2000_AVAILABLE_FIELD_SYNTHETIC_SIBLING_20260914_v1.json`
- `v3/historical_all_market/governance/CURRENT_STATE_KEIRIN.json`
- `multiverse_vnext/VNEXT_CURRENT_STATE_v0.json` generation 15
- この `KEIRIN_NOW.md`
- exact synthetic experiment preregistration

一致しなければ fail-closed。

## 次にやること

1. issue側に残っている最新PRE監査証拠を研究branchのcontinuityへ正式固定する。
2. DEV2000-available field sibling interface/modelのexact preregistrationを作る。
3. 5欠損項目を除いたsynthetic ablationを実行する。
4. 結果をsynthetic engineering evidenceとしてのみ保存する。

## 主がやること

現在の合成sibling設計・アブレーションについては、今はなし。

詳細ルール: `AI_COUNCIL.md`
科学Current State: `v3/historical_all_market/governance/CURRENT_STATE_KEIRIN.json`
Foundation / vNext Current State: `multiverse_vnext/VNEXT_CURRENT_STATE_v0.json`
