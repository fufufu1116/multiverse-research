# Multiverse Hybrid v3.0 — Next-Lineage v1 Design Candidate

Status: MATERIAL SCIENTIFIC DESIGN CANDIDATE — NOT FROZEN / NOT EXECUTABLE
Date: 2026-08-19 JST
Parent closed lineage: `NO_B_VALIDATED_CONFIGURATION`

## 0. Purpose

Build an economic decision system whose profitability is **repeatable across weeks/months**, not dependent on winning every day and not dependent on one jackpot ticket.

A negative day is acceptable. Promotion requires evidence that the bankroll path is economically positive and robust over longer calendar horizons.

This candidate is result-aware because it incorporates lessons from the closed DEV2000 A/B lineage. Therefore it MUST receive independent material governance review before Freeze or scientific execution.

Current Segment C is prohibited for redesign/selection. `ECON_HOLDOUT1000` remains `SEALED`.

---

## 1. Closed-lineage evidence that motivates the redesign

Exact A/B postmortem reproduced all frozen A_TOP10 metrics.

Leading A path:
- 148 bet races
- 18,900 JPY stake
- 45,790 JPY return
- net ROI +142.275%
- exactly 1 hit ticket
- 100% of realized return from that one ticket
- positive active days: 1/15
- positive active ISO weeks: 1/4

B for the seven G20/SINGLE/FK10 paths:
- 44 bet races
- 5,100 JPY stake
- 0 JPY return
- net ROI -100%
- 0 hits
- positive days 0/8
- positive weeks 0/2

B for the three G25/SINGLE/FK10 paths:
- 54 bet races
- 6,200 JPY stake
- 0 JPY return
- net ROI -100%
- 0 hits
- positive days 0/8
- positive weeks 0/2

Dominant exposure was high-odds 3rentan SINGLE tickets.

These facts establish a strong tail/concentration failure, but do NOT by themselves prove that PL or the underlying winner models are the unique cause.

---

## 2. Scientific architecture — sequential and bounded

The old 784 full-policy Cartesian comparison is not reused.

New lineage uses ordered stages. A candidate eliminated at an earlier stage cannot be revived later.

### Hard experiment budget candidate

- maximum scientifically distinct executions across Stages 1–5: **64**
- maximum unique full economic policies reaching final development comparison: **12**
- maximum survivors passed from any stage: **3**
- unlogged execution: invalidates the selection run
- outcome-changing rerun: prohibited
- technical identical retry: maximum 2 and does not alter scientific trial count

These numbers reuse a previously developed Multiverse governance design rather than being derived from the latest B outcomes.

---

## 3. Stage 0 — failure diagnostics only

No policy selection.

Required falsification targets:

D1 winner-probability calibration
D2 PL joint-order misspecification
D3 market-specific probability mismatch
D4 raw-EV overstatement
D5 rare-jackpot concentration
D6 race-quality selection weakness
D7 odds-regime instability
D8 field-size / grade / venue heterogeneity
D9 Candidate A vs B1a disagreement
D10 closing-price vs executable-price gap
D11 same-race ticket dependence
D12 payout-tail dependence
D13 transform/provenance leakage

Current evidence:
- D5 = strongly supported
- temporal instability = observed
- portfolio concentration = supported
- D4 concern = supported, causal conclusion not established
- D2 = inconclusive and a priority falsification target

---

## 4. Data constitution candidate

### 4.1 Development / validation universe

A fresh result-independent historical membership rule must be frozen before new scientific execution.

Minimum calendar coverage candidate:
- **>= 16 calendar weeks** total coverage
- **>= 4 distinct calendar months**
- enough active opportunities for each market-specific evidence floor

Race count alone cannot satisfy the calendar requirement.

The universe must undergo a collision audit against:
- DEV2000 A/B/C
- all previously scored economic datasets
- SIM100 dates
- Shadow universes
- any prior holdout membership

A collision may be admitted only as explicitly exposed development data; it can never be represented as untouched validation.

### 4.2 Final untouched evidence

`ECON_HOLDOUT1000` remains sealed and may be considered only if a separate pre-open audit proves:
- membership identity
- no Price/PAYOUT/RESULT access
- no collision that invalidates untouched status
- sufficient market-specific evidence scale

If not, designate a new future/untouched holdout before final policy Freeze.

---

## 5. Temporal development design candidate

Use chronological expanding-window validation; no shuffle.

Candidate structure:
- 5 validation folds
- TRAIN always strictly earlier than VALID
- learned calibration/transform state fit on TRAIN only
- no manual favorable date/venue deletion

Promotion stability across folds:
- activity in >=4/5 folds
- net ROI >0 in >=3/5 folds
- median validation-fold net ROI >0
- no single validation fold contributes >60% of total development net profit

---

## 6. Week / month operating-stability gate candidate

This is added because the operational objective is not daily perfection but repeatable weekly/monthly profitability.

Daily results are descriptive; **a negative day is not an automatic fail**.

For any final development candidate:

### Weekly
- >= 12 active ISO weeks in the development/validation evidence used for stability reporting
- positive active-week share >= 50%
- median active-week net ROI > 0
- maximum consecutive losing active weeks <= 4

### Monthly
- >= 4 active calendar months
- at least 3 positive active months out of 4, or if >4 months are present, positive-month share >= 60%
- median active-month net ROI > 0
- no single month contributes >60% of total development net profit

These are **candidate thresholds** and must be independently challenged before Freeze. Their purpose is to reject jackpot-like paths that are aggregate-positive but operationally unstable.

---

## 7. Market-specific promotion — no pooled masking

Each market is a separate promotion unit.

Primary initial economic markets:
- 2shatan
- 2shahuku
- 3rentan
- 3renhuku

Wide and frame markets may be diagnosed, but cannot enter a promoted live-candidate portfolio until their own evidence/price semantics meet the same standard.

Minimum necessary evidence candidate:

### 2-car market
- >=300 unique bet races
- >=300 evaluable decisions

### 3-car market
- >=500 unique bet races
- >=500 evaluable decisions

### Every promoted market
- >=10 distinct positive-return race events
- positive net profit
- net ROI >0
- lower dependence-aware 95% net-ROI bound >0
- primary family-wise error rate <=0.05 under a predeclared dependence-aware method

Below the evidence floor = `INSUFFICIENT_EVIDENCE`, not PASS.

A winning market cannot rescue a failing market.

---

## 8. Tail / jackpot robustness — hard candidate gate

A candidate cannot be promoted solely because of rare extreme payouts.

Mandatory outputs:
- largest winning race contribution
- top-1 winning race removed
- top-3 winning races removed
- top-5% positive-return races removed or winsorized sensitivity
- market-level and fold-level profit concentration

Candidate hard conditions:
- no single race contributes >=50% of total development net profit
- removing the largest winning race must leave net profit >0
- removing the top-3 winning races must leave net profit >0

This would have rejected the closed +142% A path before promotion.

---

## 9. Stage 1 — probability / joint-order family screening

Maximum 2 major families in v1:

F1. frozen Candidate A / B1a winner probabilities expanded with Plackett-Luce baseline

F2. one predeclared dependence-aware joint-order family, only if PRE provenance and deterministic implementation are accepted before execution

PL is a baseline hypothesis, not truth.

The exact F2 model must be frozen before any development comparison. If no scientifically defensible F2 is ready, Stage 1 executes F1 only rather than inventing one post hoc.

Market-specific calibration diagnostics are required.

---

## 10. Stage 2 — calibration / shrinkage

Maximum 3 methods per surviving Stage-1 family:

C1 identity baseline
C2 fold-local logistic calibration
C3 fold-local isotonic calibration, only when a predeclared minimum-support gate passes

No PAYOUT may fit probability calibration.

All learned state is TRAIN-fold local and serialized.

---

## 11. Stage 3 — economic edge transformation

Maximum 2 transforms per survivor:

E1 calibrated EV baseline: `p_calibrated * price - 1`

E2 uncertainty/tail-shrunk edge: deterministic formula frozen before execution; may use TRAIN-only calibration uncertainty and/or a TRAIN-only market odds-tail statistic, but no favorable VALID threshold selection.

Raw extreme EV is never trusted automatically.

Wide retains LOW price semantics until separately re-audited.

---

## 12. Stage 4 — race/price quality filters

Maximum 2 filter families, maximum 2 points each.

Candidate families:

Q1 model-agreement / uncertainty gate
- uses Candidate A vs B1a disagreement only

Q2 odds-tail / price-fragility gate
- threshold must be objective and TRAIN-derived or otherwise predeclared before execution
- no numeric cutoff may be chosen because the closed A winner had odds 457.9

No venue/grade/date filter may be added merely because it improves observed ROI.

---

## 13. Stage 5 — ticket / portfolio construction

Market edges must already be validated before portfolio comparison.

Maximum 3 rules:

P1 market-specific TOP1 with equal 100-JPY unit
P2 market-specific TOP3 with equal stake and same-race exposure cap
P3 cross-market diversified portfolio using only markets that independently passed, with a frozen inclusion rule

No global `SINGLE` across all markets may select one sparse jackpot market merely because it has the largest modeled EV.

Within-race ticket dependence must be accounted for in any multi-ticket portfolio.

---

## 14. Stage 6 — bankroll / risk

Risk policy is not allowed to create an edge.

Primary validation:
- Equal Stake

Sensitivity after edge validation only:
- fractional Kelly 0.10 maximum

No Full Kelly, Martingale, loss-chasing, borrowing, or bankroll-dependent rescue selection.

Candidate maximum drawdown promotion floor:
- <=25% of normalized starting bankroll

---

## 15. Uncertainty / multiplicity candidate

Headline inference preserves race/time dependence.

Candidate primary method:
- 10,000 deterministic resamples
- calendar-week block as the resampling unit, or an independently approved time-aware block method
- fixed seed before execution
- 95% confidence interval

Primary promotion claims require FWER <=0.05.

The exact multiplicity method (e.g. dependence-preserving maxT / Romano-Wolf style stepdown where mathematically valid) must be frozen after independent audit and before execution.

Ticket-level iid bootstrap is prohibited for headline inference.

---

## 16. Final untouched verdict

Per market exactly one:
- PASS
- FAIL
- INSUFFICIENT_EVIDENCE

A portfolio verdict is supplemental and cannot overwrite market failures.

Final untouched scoring is one-shot.

If final untouched validation fails:
- report FAIL
- no rescue tuning on the same holdout
- close lineage
- any later attempt requires a new untouched OOS set

---

## 17. Explicit non-authorizations

This candidate does NOT authorize:
- execution of the new scientific search
- current DEV2000 Segment-C use for redesign
- `ECON_HOLDOUT1000` access
- Candidate A/B1a refit
- live order generation
- real-money wagering

Next required material boundary:
**Independent hostile audit of this candidate and the data/collision plan.**

`ECON_HOLDOUT1000 = SEALED`
