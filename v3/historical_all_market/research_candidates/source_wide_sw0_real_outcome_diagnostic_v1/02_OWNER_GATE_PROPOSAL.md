# SW0 A+B Real-Outcome Diagnostic Owner Gate Proposal v1

Status: PROPOSAL ONLY — NOT AUTHORITY
Date: 2026-09-14 JST

## Purpose
Evaluate the already hash-locked `SW0_SCORE_ONLY_PL` predictions against real race outcomes without opening economics, changing the model, or touching protected DEV2000-C / ECON_HOLDOUT1000.

## Exact universe
- Predictions: the already frozen artifact SHA256 `779f9fca7eedf2c668ef22c45319543c9f3c999ebb2bdd390f7d2cd11f9d9127`.
- Races: exactly DEV2000 A+B, `dev_index 1..1500`, exactly 1500 race IDs.
- DEV2000-C (`1501..2000`) remains excluded and must not be read/scored/repurposed.
- `ECON_HOLDOUT1000` remains sealed.

## Allowed outcome access if Owner approves
Only the minimum outcome fields required to identify the observed ordered top 3 for those exact 1500 race IDs:
- `race_id`
- 1st-place `car_no`
- 2nd-place `car_no`
- 3rd-place `car_no`
- `dev_index` only when needed for exact partition verification.

If the stored source cannot be safely isolated to those fields/races without reading prohibited protected material, fail closed and stop without evaluation.

## Prohibited even after this proposed Gate
- payout / settlement amount
- odds / price / market data
- ROI / profit / bankroll / economics
- DEV2000-C outcome access
- ECON_HOLDOUT1000 access
- any real-data fit, tuning, calibration, threshold selection or model selection
- model promotion
- Runtime activation
- automatic betting or real-money wagering

## Frozen evaluation protocol
Use only:
- `00_EVALUATION_PREREG.json`
- `evaluate_sw0_ab_predictions_v1.py`

Primary reporting is Segment B (`dev_index 1001..1500`) with A and A+B shown as diagnostics. Metrics and verdict thresholds are frozen before outcome access. Any verdict is diagnostic predictive evidence only, not untouched confirmatory evidence and not profitability evidence.

## Exact Owner approval text
`SW0 A+B REAL-OUTCOME DIAGNOSTIC v1 を承認。既にhash-lock済みのSW0予測について、DEV2000 A+B（dev_index 1..1500）の正確な1500 race_idだけを対象に、race_idと1着/2着/3着car_no（必要ならpartition確認用dev_index）の最小限の実結果を読み、事前登録済み評価器で一度だけ予測性能を評価してよい。DEV2000-C、ECON_HOLDOUT1000、payout/settlement amount、odds/price、ROI/profit/economicsは開かない。real-data fit/tuning/calibration/model selection/model promotionは禁止。安全に結果だけ分離できない場合はfail closed。Runtimeと自動投票はOFFのまま。`

This file itself grants no authority.
