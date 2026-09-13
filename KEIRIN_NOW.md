# Multiverse 競輪ver — いまここ

最終更新: 2026-09-14 JST

この1枚は **主向けの現在地表示**。NOW / CURRENT / LATEST は必ず canonical GitHub を Fresh Read して確認する。

## 現在の結論

**Synthetic（合成）工学検証の広域耐性マイルストーンは完了し、次の限定Gateとして「既存の実データPRE-only適合性監査」だけが許可されています。**

主の明示Gateは issue #377 comment `5657106213` に固定済みです。

この許可は「現実で勝てるか」を試す許可ではありません。既存保存済みのPRE（レース前情報）だけを使い、データ構造・項目欠損・型・範囲・分布支持・入力インターフェース適合性を確認するための限定監査です。

---

## 今回許可された範囲

対象は最初に **`DEV2000_PRE_TABLE_v1.csv` だけ**。

canonical expected SHA256:
`25303ed3a7bce2bbc1c681823cbe9d009e3d3c5f07ef669a43fd6cf1ea86af73`

既知identity:
- 14,255 rows
- 2,000 races

許可された作業:
1. 既存保存物から対象PRE tableを回収する
2. 科学利用前にSHA256を完全一致確認する
3. header/schemaを確認し、結果・払戻・オッズ・価格・精算・経済項目があればfail-closedする
4. PRE必須項目の有無、型、missingness、cardinality、range、supportを監査する
5. race shape / PRE interface / frozen N2入力との構造適合性を監査する
6. PRE-only分布の支持範囲をSynthetic工学側と比較する
7. outcome labelを使わないparser/transform/interface dry-runを行う

証拠区分は
**REAL_PRE_ONLY_SUITABILITY_COMPATIBILITY_EVIDENCE_NOT_PREDICTIVE_PERFORMANCE**
です。

---

## 引き続き禁止・未許可

- RESULT/PAYOUT
- 着順、勝者、精算など outcome label
- odds / price / market price
- economics / bankroll / ROI / profit
- `ECON_HOLDOUT1000` の開封・採点・方針変更
- DEV2000 C の結果・払戻アクセスや救済
- untouched outcome validation
- 実PREを使った学習・fit・パラメータ選択
- result-aware feature / threshold / exclusion / ticket decision
- model promotion / freeze acceptance / production
- 新規自動大量収集
- 外部providerへの連絡、課金、credential利用
- access-control / rate-limit / CAPTCHA / WAF bypass
- Runtime起動
- 自動投票
- 現実のお金を使う賭け

scientific segment C scoring count は **0のまま**。
`ECON_HOLDOUT1000` は **SEALEDのまま**。

---

## Synthetic側の最後の科学チェックポイント

Frozen candidate:
`N2_SPEC_ALIGNED_POSTERIOR_CONDITIONAL`

Synthetic classification:
`N2_BROADLY_ROBUST_W0_W4_SYNTHETIC`

workflow run: `34789364394`
artifact: `10327508665`
artifact digest:
`sha256:81376746cd1ad75836f1603ec44d8827cfa1bc73380885b5c67504b6ce2f8293`

これは引き続きSynthetic工学証拠であり、Real edge / ROI / 実世界性能の証拠ではありません。

---

## 実行前Fresh Read

最初の実PRE byte access直前に必ず確認する:

- canonical main HEAD
- issue #394
- issue #377
- `governance/KEIRIN_OWNER_GATE_REAL_PRE_ONLY_SUITABILITY_AUDIT_20260914_v1.json`
- `v3/historical_all_market/governance/CURRENT_STATE_KEIRIN.json`
- `multiverse_vnext/VNEXT_CURRENT_STATE_v0.json` generation 13
- この `KEIRIN_NOW.md`

一致しなければ fail-closed。

対象byteはcanonical SHA256一致前に科学監査へ使わない。

---

## 主がやること

**今はなし。**

このGateはPRE-only適合性監査専用です。結果検証、オッズ、経済評価、Holdout、実データ学習、モデル昇格、Runtime、自動投票には流用しません。

詳細ルール: `AI_COUNCIL.md`
科学Current State: `v3/historical_all_market/governance/CURRENT_STATE_KEIRIN.json`
Foundation / vNext Current State: `multiverse_vnext/VNEXT_CURRENT_STATE_v0.json`
