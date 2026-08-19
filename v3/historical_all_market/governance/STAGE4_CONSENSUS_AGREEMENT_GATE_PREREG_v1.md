# Multiverse Hybrid v3.0 — Stage 4 Consensus / Agreement Gate Prereg v1

Status: PREREGISTERED BEFORE RESULT / PAYOUT / SETTLEMENT ACCESS
Track: All-Market Historical Economic Track
Date: 2026-08-19 JST

## 1. Purpose

Stage 4 converts the two already-frozen probability sources (`candidate_a`, `b1a_reconstituted_v1`) into a conservative consensus candidate layer and a finite race-level model-agreement gate family.

No realized outcome information is admissible.

## 2. Authorized inputs

Only frozen pre-result artifacts are admissible:

- Stage 2 catalog SHA-256 `34ad32bed6e8b4d700864c46f4533bef1da254c7d87dc7ffe6ec266fd74530dc`
- Stage 3 preregistered profiles `P00,P05,P10,P20,P35,P50,P100`
- frozen Candidate A / B1a probabilities
- race/ticket identities and market availability already present in Stage 2

No RESULT, PAYOUT, refund, Settlement, realized hit, realized return, realized ROI, or post-race feature may be used.

## 3. Ticket-level conservative consensus

For the same race / market / ticket, define:

- `consensus_probability = min(p_candidate_a, p_b1a)`
- `consensus_raw_ev = min(raw_ev_candidate_a, raw_ev_b1a)`
- `consensus_shape_edge_ratio = min(shape_edge_ratio_candidate_a, shape_edge_ratio_b1a)`

A ticket is Stage-4 consensus-eligible for Stage-3 profile `Pxx` only if **both models independently satisfy the same frozen Stage-3 thresholds**. Equivalently:

`consensus_raw_ev >= EV_MIN(Pxx)` AND `consensus_shape_edge_ratio >= EDGE_MIN(Pxx)`.

No model-specific union is allowed.

## 4. Canonical race-level model disagreement metric

The canonical race-level disagreement metric is Total Variation distance on the normalized `3rentan` ticket probability distribution.

For a race with normalized Candidate-A vector `a` and B1a vector `b` over identical 3rentan ticket keys:

`TV3 = 0.5 * sum_t |a_t - b_t|`.

3rentan is used because it is sold in all 2000 Stage-0 recovered development races and contains the full ordered top-3 probability surface used by the other car-based markets.

Ticket-key mismatch or missing 3rentan is FAIL-CLOSED.

## 5. Frozen agreement-gate family

The following finite gate family is preregistered:

| Gate | Rule |
|---|---|
| `G0` | no TV3 cap; ticket-level two-model consensus still required |
| `G20` | `TV3 <= 0.20` |
| `G25` | `TV3 <= 0.25` |
| `G30` | `TV3 <= 0.30` |

If a race fails the selected gate, the entire race is `NO_BET` for that configuration.

No different threshold may be used for a particular venue, market, class, field size, date, or model.

## 6. Deterministic ticket ranking for Stage 5

Within an eligible set, ticket order is frozen as:

1. higher `consensus_raw_ev`
2. higher `consensus_shape_edge_ratio`
3. higher `consensus_probability`
4. lexicographically smaller ticket key

When comparing tickets across markets for a race-level single-ticket template, use the same first three numeric fields, then lexicographically smaller market code, then ticket key.

This ranking is a deterministic ordering rule, not a learned score.

## 7. Stage-4 diagnostics

Stage 4 may report only pre-result diagnostics such as:

- TV3 distribution
- race pass count per agreement gate
- consensus-candidate counts by Stage-3 profile / market / gate
- NO-BET rate

These diagnostics cannot be used to claim profitability.

## 8. Scientific state

- RESULT access = false
- PAYOUT access = false
- Settlement access = false
- realized ROI = not computed
- scientific trial count = 0
- `ECON_HOLDOUT1000 = SEALED`

Stage 4 does not authorize Settlement.

END OF STAGE 4 PREREG v1
