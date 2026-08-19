# Multiverse Hybrid v3.0 — Stage 3 Ticket Candidate Filter Family Prereg v1

Status: PREREGISTERED BEFORE RESULT / PAYOUT / SETTLEMENT ACCESS
Track: All-Market Historical Economic Track
Stage: 3 — elementary-ticket candidate filtering
Date: 2026-08-19 JST

## 1. Purpose

Stage 3 freezes a finite family of elementary-ticket candidate filters using only Stage 2 pre-result price/probability diagnostics.

This stage does **not** determine which family is profitable and does **not** select a final wagering policy.

The goal is to define, before any Settlement access, which elementary tickets are eligible to be considered by later quality gates and portfolio construction.

## 2. Authorized inputs

Only the following Stage 2 fields are admissible:

- `race_id`
- `probability_source`
- `sold_markets`
- ticket identity
- `model_event_probability`
- primary closing odds
- `raw_ev_primary`
- `market_shape_probability_primary`
- `model_shape_probability`
- `shape_edge_delta_primary`
- `shape_edge_ratio_primary`

Wide uses the already frozen Stage 2 rule:

- `closing_odds_low` is primary
- `closing_odds_high` remains diagnostic only

No RESULT, PAYOUT, refund, Settlement, realized return, realized ROI, hit/miss, or post-race feature is admissible.

## 3. Common market treatment

The same filter family is applied to all seven official markets:

- `3rentan`
- `3renhuku`
- `2shatan`
- `2shahuku`
- `wide`
- `2wakutan` when sold
- `2wakuhuku` when sold

No market-specific threshold tuning is permitted in Stage 3 v1.

Each probability source is evaluated independently:

- `candidate_a`
- `b1a_reconstituted_v1`

Model-agreement gating is explicitly deferred to Stage 4.

## 4. Candidate filter family

A ticket passes profile `Pxx` only when **all** conditions in that profile are satisfied.

| Profile | minimum raw EV | minimum shape-edge ratio | meaning |
|---|---:|---:|---|
| `P00` | 0.00 | 1.00 | weakest positive-value diagnostic baseline |
| `P05` | 0.05 | 1.05 | light edge requirement |
| `P10` | 0.10 | 1.10 | modest edge requirement |
| `P20` | 0.20 | 1.20 | medium edge requirement |
| `P35` | 0.35 | 1.35 | strong edge requirement |
| `P50` | 0.50 | 1.50 | very strong edge requirement |
| `P100` | 1.00 | 2.00 | extreme-edge stress profile |

Formal rule for ticket `t` under profile `p`:

`eligible(t,p) = [raw_ev_primary(t) >= EV_MIN(p)] AND [shape_edge_ratio_primary(t) >= EDGE_RATIO_MIN(p)]`

Because `shape_edge_ratio_primary >= 1` implies non-negative market-shape edge, no additional `shape_edge_delta_primary` threshold is used.

## 5. What is intentionally NOT filtered in Stage 3

Stage 3 v1 does not impose:

- odds caps
- absolute model-probability floors
- active-car-count restrictions
- venue restrictions
- class / rider / line restrictions
- race-level model-disagreement restrictions
- ticket-count caps per race
- top-K ranking limits
- BOX / wheel / formation structure
- bankroll limits

These are deferred to Stage 4–6 so that elementary-ticket edge filtering and portfolio/risk construction remain separated.

## 6. Stage 3 outputs

Stage 3 produces diagnostics only:

- candidate count per race / model / market / profile
- candidate share of sold tickets
- NO-BET race count under each profile
- distribution of candidate counts per race
- total candidate counts by model / market / profile

Stage 3 v1 does **not** need to persist a full ticket-level candidate catalog because eligibility is deterministic from this preregistration and the Stage 2 catalog.

## 7. No selection from Stage 3 diagnostics

The candidate-count distribution may be inspected to detect implementation errors or obviously unusable density, but it must not be interpreted as realized economic performance.

No profile may be promoted because it 'looks profitable' before Settlement exists.

If a Stage 3 implementation bug is discovered, a bug-fixed implementation may replace code while preserving this preregistered semantic family. Semantic changes require a new preregistration version before Settlement access.

## 8. Scientific state

At this preregistration point:

- All-Market Historical Track scientific trial count = 0
- RESULT access for this economic track = false
- PAYOUT / Settlement bulk = prohibited
- realized ROI = not computed
- Stage 4 = not started
- Stage 5 = not started
- Stage 6 = not started
- `ECON_HOLDOUT1000 = SEALED`

## 9. Stage boundary

Stage 3 completion does not authorize Settlement.

After Stage 3 diagnostics pass, proceed to Stage 4 race-quality / model-agreement gates using pre-result information only.

Settlement remains prohibited until Stage 1–6 decision and risk rules are frozen.

END OF STAGE 3 PREREG v1
