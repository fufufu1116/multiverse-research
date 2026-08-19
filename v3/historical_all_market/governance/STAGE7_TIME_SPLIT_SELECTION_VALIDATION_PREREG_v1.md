# Multiverse Hybrid v3.0 — Stage 7 Chronological Selection / Validation Prereg v1

Status: PREREGISTERED BEFORE RESULT / PAYOUT / SETTLEMENT ACCESS
Track: All-Market Historical Economic Track
Date: 2026-08-19 JST

## 1. Purpose

Stage 7 defines, before any economic Settlement is opened, how the 784 frozen Stage-3–6 configurations will be selected and evaluated chronologically.

The goal is out-of-sample generalization, not retrospective maximization over all 2000 races.

## 2. Immutable ordering

Use `DEV2000_UNIVERSE_v1.csv` immutable `dev_index` ordering.

No race may be reordered using outcome, payout, odds attractiveness, venue performance, or model performance.

## 3. Frozen chronological segments

- `A_DEVELOPMENT`: `dev_index 1..1000`
- `B_VALIDATION`: `dev_index 1001..1500`
- `C_UNTOUCHED_TEST`: `dev_index 1501..2000`

Segment C must not influence configuration selection.

`ECON_HOLDOUT1000` remains a separate sealed asset and is not part of these segments.

## 4. Configuration selection on Segment A

Evaluate all 784 frozen configurations on Segment A only.

A configuration is eligible for the A shortlist only if:

- at least 100 races contain one or more executed tickets after stake rounding
- total realized stake is positive
- bankroll never becomes negative
- maximum peak-to-trough drawdown is no greater than 35%

Rank eligible configurations lexicographically by:

1. higher realized ROI = `(total_return / total_stake) - 1`
2. higher ending bankroll
3. lower maximum drawdown
4. higher number of bet races
5. lexicographically smaller immutable configuration ID

Freeze the top 10 as the `A_TOP10` shortlist.

If fewer than 10 satisfy the eligibility gate, keep all eligible. If none qualify, the track halts with `NO_A_ELIGIBLE_CONFIGURATION` and Segment C remains untouched.

## 5. Selection on Segment B

Evaluate only `A_TOP10` on Segment B.

A B-pass configuration must satisfy:

- realized ROI > 0
- at least 50 bet races
- maximum drawdown <= 35%
- no negative bankroll

Among B-pass configurations, select exactly one by:

1. higher B realized ROI
2. higher B ending bankroll
3. lower B maximum drawdown
4. higher B bet-race count
5. lexicographically smaller configuration ID

That one configuration becomes `FINAL_DEV2000_CONFIGURATION`.

If no A_TOP10 configuration passes B, halt with `NO_B_VALIDATED_CONFIGURATION`; Segment C remains untouched.

## 6. One-time Segment C scoring

Once `FINAL_DEV2000_CONFIGURATION` is frozen, score it exactly once on Segment C.

Primary C metrics:

- realized ROI
- total stake
- total return
- bet-race count
- hit-ticket count
- ending bankroll
- maximum drawdown

C verdict categories:

- `OOS_STRONG_PASS`: ROI > 0, bet races >= 50, max drawdown <= 25%, and race-block bootstrap 95% ROI lower bound > 0
- `OOS_POSITIVE_BUT_UNCERTAIN`: ROI > 0, bet races >= 50, max drawdown <= 35%, but bootstrap lower bound <= 0
- `OOS_FAIL`: otherwise

## 7. Bootstrap rule

For Segment C uncertainty, resample whole races with replacement, not individual tickets.

- 10000 bootstrap replicates
- deterministic PRNG seed `20260819`
- each sampled race contributes its entire realized stake and return under the frozen final configuration
- bootstrap ROI = total sampled return / total sampled stake - 1
- report percentile 2.5% and 97.5% bounds

If a replicate has zero total stake, omit that replicate and report the number omitted. If fewer than 9500 valid replicates remain, FAIL-CLOSED.

## 8. No post-C rescue tuning

After Segment C is scored, no threshold, gate, template, stake rule, split, or model may be changed and then rescored on C in the same lineage.

A failed C result closes this frozen decision lineage for DEV2000. Any new rule requires a new lineage and a new untouched dataset.

## 9. HOLDOUT boundary

`ECON_HOLDOUT1000` stays `SEALED` regardless of the DEV2000 C verdict. Opening it requires separate explicit governance authorization.

## 10. Scientific state at preregistration

- economic Settlement access = false
- realized ROI = not computed
- Stage-7 realized trial has not started
- `ECON_HOLDOUT1000 = SEALED`

END OF STAGE 7 PREREG v1
