# Multiverse 競輪ver — いまここ

最終更新: 2026-09-14 JST

この1枚は **主向けの現在地表示**。NOW / CURRENT / LATEST は必ず canonical GitHub を Fresh Read して確認する。

## 現在の結論

Synthetic（合成）工学のFrozen N2はW0-W4広域耐性マイルストーンまで完了しています。最初の実データPRE-only監査では、canonical `DEV2000_PRE_TABLE_v1.csv` がFrozen N2に必要な5項目を欠くことを、データ行を読まずheader段階で確認しました。

不足項目:
- `line_group_id`
- `line_position`
- `line_size`
- `bank_length_m`
- `wind_speed_mps`

主の追加明示Gateは issue #377 comment `5657234204` に固定済みです。

このGateで新たに許可されたのは、**既存保存済みのDEV2000 PRE collection / PRE-only line structure / PRE-only race context 補完ソースを使って、上記5項目の取得可否・schema・missingness・support・Frozen N2入力互換性だけを監査すること**です。

これは現実の的中性能・利益・ROIを調べる許可ではありません。

---

## 必須アクセス順序

追加ソースごとに必ず次の順序を守る:
1. exact sourceを事前登録
2. identity/hash確認
3. RESULT/PAYOUT/outcome/settlement/odds/price/economics等の禁制項目scan
4. PRE-onlyであることを確認
5. その後だけ値レベルのavailability / schema / missingness / cardinality / range / support監査

事前登録前に許可されるのは、既存保存物を特定するためのmetadata-only列挙だけ。追加sourceのfile bytesは読まない。

証拠区分:
`REAL_PRE_ONLY_ENRICHMENT_SUITABILITY_COMPATIBILITY_EVIDENCE_NOT_PREDICTIVE_PERFORMANCE`

---

## 引き続き禁止・未許可

- RESULT / PAYOUT
- 着順・勝者・settlement等のoutcome label
- odds / price / market price
- economics / bankroll / ROI / profit
- `ECON_HOLDOUT1000`
- DEV2000 C の結果・払戻アクセス
- untouched outcome validation
- 実PREを使ったtraining / fit / parameter selection / model selection
- result-aware feature / threshold / exclusion / ticket decision
- model promotion / freeze acceptance / production
- 新規自動大量収集
- 外部providerへの連絡・課金・credential利用
- access-control / rate-limit / CAPTCHA / WAF bypass
- Runtime起動
- 自動投票
- 現実のお金を使う賭け

scientific segment C scoring count は **0のまま**。
`ECON_HOLDOUT1000` は **SEALEDのまま**。
Frozen N2は変更しない。

---

## 現在の科学チェックポイント

Frozen candidate:
`N2_SPEC_ALIGNED_POSTERIOR_CONDITIONAL`

Synthetic classification:
`N2_BROADLY_ROBUST_W0_W4_SYNTHETIC`

Real PRE v1 classification:
`EXACT_PRE_TABLE_NOT_DIRECTLY_COMPATIBLE_WITH_FROZEN_N2_INPUT_CONTRACT`

最新continuity:
- `v3/historical_all_market/continuity/KEIRIN_CURRENT_STATE_v9.json`
- `v3/historical_all_market/continuity/KEIRIN_EXPERIMENT_LEDGER_v14.jsonl`

Real PRE v1は適合性/schema証拠であり、Real edge / ROI / 実世界予測性能の証拠ではありません。

---

## 実行前Fresh Read

追加PRE sourceの最初のbyte access直前に必ず確認する:
- canonical main HEAD
- issue #394 最新
- issue #377 最新
- `governance/KEIRIN_OWNER_GATE_REAL_PRE_ONLY_ENRICHMENT_AUDIT_20260914_v2.json`
- `v3/historical_all_market/governance/CURRENT_STATE_KEIRIN.json`
- `multiverse_vnext/VNEXT_CURRENT_STATE_v0.json` generation 14
- この `KEIRIN_NOW.md`
- exact source preregistration

一致しなければ fail-closed。

---

## 主がやること

**現在のPRE-only補完監査については、今はなし。**

追加のRESULT/PAYOUT、outcome validation、odds/price、economics、Holdout、実データ学習、モデル昇格、Runtime、自動投票にはこのGateを流用しません。

詳細ルール: `AI_COUNCIL.md`
科学Current State: `v3/historical_all_market/governance/CURRENT_STATE_KEIRIN.json`
Foundation / vNext Current State: `multiverse_vnext/VNEXT_CURRENT_STATE_v0.json`
