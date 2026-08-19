# Multiverse Hybrid v3.0 — Next-Lineage Long-Horizon Stability Charter CANDIDATE v1

Status: DIAGNOSTIC DESIGN CANDIDATE — NOT A VALIDATION FREEZE
Date: 2026-08-19 JST
Parent closed lineage: `CLOSED_NO_B_VALIDATED_CONFIGURATION`

## 1. Objective

The next economic lineage targets **generalizable profitability over meaningful time horizons**, not a requirement to win every day.

A losing day is acceptable. The intended operational question is whether the system can produce a positive and survivable bankroll path across weeks and months without depending on one or a few exceptional payouts.

This document is result-aware hypothesis generation after the DEV2000 A/B failure. It MUST NOT be used to rescore current Segment C or to open `ECON_HOLDOUT1000`.

## 2. Evidence motivating the redesign

The closed DEV2000 lineage reached `NO_B_VALIDATED_CONFIGURATION`.

The leading Segment-A path had:

- 148 bet races
- 18,900 JPY stake
- 45,790 JPY return
- +142.275% realized ROI
- only 1 hit ticket

Thus the apparent Segment-A edge was maximally concentrated in one realized hit and did not survive the preregistered Segment-B gate.

DEV2000 also spans too few distinct dates for robust long-horizon stability inference:

- Segment A: 15 unique race dates
- Segment B: 8 unique race dates

## 3. Diagnostic-only metrics to add

For every investigated historical configuration/path, report all of the following without using them as a validation claim on the current lineage:

### Overall economics
- total stake
- total return
- realized ROI
- ending bankroll
- maximum drawdown
- bet-race count
- hit-ticket count

### Daily stability
- active bet days
- positive / zero / negative active days
- positive-active-day share
- worst active-day ROI
- best active-day ROI
- maximum consecutive losing active days

### Weekly stability
Use ISO calendar week, aggregating all races by race date.

- active bet weeks
- positive / zero / negative active weeks
- positive-active-week share
- median active-week ROI
- worst active-week ROI
- best active-week ROI
- maximum consecutive losing active weeks

### Monthly stability
Aggregate by calendar month.

- active bet months
- positive / zero / negative active months
- positive-active-month share
- median active-month ROI
- worst active-month ROI
- best active-month ROI

### Return concentration / fragility
- largest single-ticket return / total realized return
- top-3 ticket returns / total realized return
- largest winning race return / total realized return
- top-3 winning race returns / total realized return
- share of total profit attributable to the single best race when defined

A high aggregate ROI accompanied by extreme concentration is treated as fragile evidence, not stable proof.

## 4. Long-horizon data requirement candidate

Before any new lineage is promoted to untouched validation, collect a fresh historical economic development/validation universe spanning substantially more calendar time than DEV2000.

Candidate minimum coverage target:

- at least 12 calendar weeks of race dates, and
- at least 3 calendar months with active bets available for evaluation,
- chronological splits only.

Race count alone is not sufficient; calendar-time coverage is mandatory because weekly/monthly stability is an explicit objective.

These minimums are a design candidate and require governance review before being treated as a final validation protocol.

## 5. Current DEV2000 usage after closure

Allowed:
- analyze Segment A and Segment B to understand failure modes
- generate diagnostic hypotheses
- measure return concentration and time-bucket stability
- inspect which market/template/risk mechanisms created unstable paths

Prohibited:
- modify Stage 3–6 rules and rescore current Segment C
- use current Segment C to select a new rule
- claim a new profitable system from A/B postmortem analysis
- open `ECON_HOLDOUT1000`

## 6. Candidate scientific redesign questions

The next diagnostic work should distinguish at least:

1. **Probability transformation risk** — whether winner-probability-to-ticket PL expansion creates economically miscalibrated tail probabilities.
2. **Market-selection risk** — whether a small number of high-odds markets dominate apparent EV and realized return.
3. **Portfolio concentration risk** — whether `SINGLE` systematically turns the path into rare-hit/high-variance exposure.
4. **Agreement-gate stability** — whether A performance depends on a narrow TV3 regime that does not persist through time.
5. **Stake-policy sensitivity** — whether fractional Kelly magnifies calibration error even when nominal bankroll caps are conservative.
6. **Calendar stability** — whether any candidate edge repeats across independent weeks/months instead of only in aggregate.

## 7. Governance boundary

This candidate charter does not authorize:

- a new frozen threshold family
- new model fitting
- current Segment-C access
- HOLDOUT access
- live or real-money wagering

Once A/B diagnostics produce a bounded candidate redesign, the final new-lineage rules and untouched validation protocol require material governance review before any new untouched outcome set is opened.

`ECON_HOLDOUT1000 = SEALED`

END OF CHARTER CANDIDATE v1
