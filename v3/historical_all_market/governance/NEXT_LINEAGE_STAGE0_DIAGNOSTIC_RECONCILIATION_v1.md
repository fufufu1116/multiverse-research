# Multiverse Hybrid v3.0 — Next-Lineage Stage-0 Diagnostic Reconciliation v1

Status: DIAGNOSTIC / RESULT-AWARE / NOT EXECUTABLE AS A NEW POLICY
Date: 2026-08-19 JST
Closed parent lineage: `NO_B_VALIDATED_CONFIGURATION`

## 1. Exact evidence incorporated

The closed DEV2000 Stage-7 A/B path was replayed using exact frozen Stage-2, prediction, universe, and A/B settlement hashes. The replay reproduced every frozen Segment-A Top10 metric exactly.

Segment-C content was not read by the diagnostic replay and `ECON_HOLDOUT1000` remains `SEALED`.

Exact diagnostics receipt:
`STAGE7_AB_POSTMORTEM_EXACT_DIAGNOSTICS_RECEIPT_v1.json`

## 2. Findings

### D5 — rare-jackpot / tail concentration
**SUPPORTED STRONGLY.**

The leading Segment-A path:
- 148 bet races
- 18,900 JPY total stake
- 45,790 JPY total return
- +142.275% ROI
- exactly 1 hit ticket
- the sole hit contributes 100% of realized return

Removing the largest winning ticket/race leaves zero return and a negative net result. This would fail the previously developed Multiverse tail/jackpot robustness principle that a policy must not be promoted because of a single extreme payout.

### Temporal stability
**FAILED on the observed A/B path.**

For the G20/SINGLE/FK10 group:
- Segment A active days = 15; positive active days = 1/15
- Segment A active ISO weeks = 4; positive active weeks = 1/4
- Segment B active days = 8; positive active days = 0/8
- Segment B active ISO weeks = 2; positive active weeks = 0/2
- Segment B ROI = -100%, 44 bet races, 0 hits

For the G25/SINGLE/FK10 group:
- Segment B ROI = -100%, 54 bet races, 0 hits
- active B days = 8; positive = 0
- active B weeks = 2; positive = 0

This is not a complaint that individual losing days are unacceptable. The operational objective is weekly/monthly positive performance over long horizons; the observed path does not show that property.

### Portfolio concentration
**SUPPORTED.**

A_TOP10 collapsed to `SINGLE + FK10_R2` for all ten configurations.

The dominant market was 3rentan:
- G20 A: 140/148 executed tickets were 3rentan
- G20 B: 41/44 executed tickets were 3rentan
- G25 A: 184/195 executed tickets were 3rentan
- G25 B: 50/54 executed tickets were 3rentan

This indicates that aggregate-ROI ranking over the 784-policy Cartesian set selected a sparse-hit, high-tail exposure path.

### D4 — raw EV overstatement
**CONCERN SUPPORTED; CAUSAL CLAIM INCONCLUSIVE.**

In Segment B, selected 3rentan tickets had approximately:
- median closing odds 592.6 (G20) / 488.95 (G25)
- mean conservative ticket probability 1.78% / 1.75%
- median conservative raw EV +785.5% / +748.6%

Yet realized B return was zero. The sample is too sparse to conclude from this alone that the probabilities or prices are mathematically wrong; however, such extreme model-implied edges require explicit calibration, tail, odds-regime, and market-specific falsification before promotion.

### D2 — PL joint-order misspecification
**INCONCLUSIVE, PRIORITY FALSIFICATION TARGET.**

The failure is compatible with PL/tail miscalibration but does not uniquely identify PL as the cause. PL remains a baseline hypothesis, not established truth.

### Multiple-testing / winner's-curse risk
**SUPPORTED AS A MATERIAL DESIGN RISK.**

The old line searched 784 full configurations and ranked Segment-A survivors by realized ROI. A single 45,790-JPY ticket was sufficient to make multiple upstream profiles share exceptional A rank. The next lineage should restore sequential bounded search and heavy-tail robustness gates rather than another large full Cartesian comparison.

## 3. Reuse of prior governance work

The following previously developed principles are consistent with the new evidence and should be treated as candidate inputs rather than rediscovered from scratch:

- sequential Stage 1–6 search; no unrestricted Cartesian product
- total trial / full-policy caps
- market-specific promotion units
- minimum positive-return race-event floor
- largest-win / top-3-win removal robustness
- expanding-window temporal folds
- fold-level stability requirements
- dependence-preserving bootstrap / FWER control
- PL as baseline rather than truth

These principles do not become newly frozen merely because this reconciliation references them.

## 4. Data-horizon requirement

DEV2000 is too short in calendar time for a meaningful monthly-stability claim:
- Segment A: 15 unique race dates
- Segment B: 8 unique race dates

The next development/validation universe must be selected by a result-independent membership rule and span materially more calendar time, with a candidate floor of at least 12 calendar weeks and at least 3 calendar months of active betting opportunity.

The existing frozen NEXTGEN5000 begins 2026-03-01 and its R4501–R5000 batch begins on 2026-04-29; it is therefore not assumed sufficient for the new long-horizon objective without an exact end-date/coverage and collision audit.

## 5. Boundaries

Allowed next:
- finish a bounded next-lineage design candidate
- audit data-collision and calendar coverage
- independently audit final new-lineage thresholds/search caps before execution

Forbidden:
- current Segment-C rescue tuning
- current Segment-C use for new-policy selection
- `ECON_HOLDOUT1000` access
- live wagering

`ECON_HOLDOUT1000 = SEALED`
