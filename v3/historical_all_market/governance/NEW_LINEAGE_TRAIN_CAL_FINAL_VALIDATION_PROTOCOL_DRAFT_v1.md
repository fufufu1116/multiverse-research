# Multiverse Keirin — New Lineage TRAIN / CAL / FINAL Validation Protocol Draft v1

Status: DESIGN CANDIDATE — NOT FROZEN / NOT EXECUTABLE
Date: 2026-08-19 JST

## 0. Purpose and firewall

This protocol is designed before any new untouched validation outcomes are opened.

It does not authorize collection, training, scoring, current DEV2000 C access or ECON_HOLDOUT1000 access.

The goal is to separate:

1. parameter learning;
2. calibration / bounded model-choice decisions;
3. one-shot final validation;
4. economic evaluation after probability architecture is frozen.

## 1. Data lineage requirement

New-lineage data must be distinct from the closed parent validation claim.

Current DEV2000 C is not eligible to become the new untouched FINAL block.
`ECON_HOLDOUT1000` remains SEALED.

The exact new data source/provider, collection semantics, race regime, PRE cutoff and artifact identities must be frozen before outcomes are available to the model-selection process.

## 2. Chronological partition

Required order:

`TRAIN -> CAL -> FINAL`

No random race split for the primary claim.

Calendar/race boundaries must be deterministic and frozen from the eligible universe before FINAL outcome access.

If multiple races share the same meeting/day information environment, the split must avoid casually placing near-identical temporal context on both sides of a boundary. Exact blocking unit will be frozen after source cadence is known.

## 3. TRAIN role

TRAIN may be used for:

- fitting model parameters;
- fitting regularization paths within a prespecified search space;
- internal chronological rolling/expanding CV;
- feature scaling learned without future information;
- architecture implementation debugging using TRAIN only.

TRAIN may not be used to declare final economic edge.

All preprocessing statistics must be fit using only information available within each chronological training fold when producing OOF predictions.

## 4. CAL role

CAL is the last block whose outcomes may affect the frozen final procedure.

Allowed bounded decisions, if preregistered before CAL is opened, may include:

- choosing among the small prespecified regularization grid/family;
- choosing a low-dimensional coherent calibration transform;
- selecting among a prespecified tiny architecture family whose scientific question has already been defined;
- freezing uncertainty-estimation method;
- freezing the first simple BUY/NO-BET rule;
- freezing missingness and quality gates that were already semantically defined.

CAL may NOT be repeatedly reopened after FINAL in order to rescue a failed FINAL result.

Any material rule introduced after seeing CAL consumes CAL for that design decision and must be documented.

## 5. FINAL role

FINAL is opened once after:

- source/provider semantics are frozen;
- eligible universe is frozen;
- feature allowlist and transforms are frozen;
- C0/C1/N1 implementation semantics are frozen;
- regularization/calibration choice is frozen;
- probability metrics and pass logic are frozen;
- economic rule is frozen;
- settlement rules are frozen;
- independent audit is complete.

No parameter, threshold, feature, calibration transform, stake rule or portfolio rule may change after seeing FINAL outcomes and still retain the same FINAL validation claim.

If a change is made, FINAL is burned for the changed lineage.

## 6. Probability-first model selection

Architecture promotion is based first on proper probability scoring, not ROI.

### Required per-race/per-event metrics

For C1/N1 where applicable:

- Winner NLL: `-log P1(actual_first)`;
- Rank-2 conditional NLL: `-log P2(actual_second | actual_first)`;
- Rank-3 conditional NLL: `-log P3(actual_third | actual_first,actual_second)`;
- Joint top-3 NLL = sum of the above;
- Brier-style diagnostics where mathematically appropriate for the probability object;
- calibration / expected-vs-observed reporting.

### Required decomposition

C1 vs N1 must separately report rank2 and rank3 conditional score differences. A joint score alone is insufficient because P1 is intentionally shared in the clean primary ablation.

## 7. Primary structural comparison ladder

### C0 vs C1

Question: does admitted line-aware PRE improve probability quality while PL is retained?

### C1 vs N1 — primary architecture test

Question: after comparable PRE is already available, does explicit relational conditional dependence improve rank-2/rank-3 probability quality beyond PL?

Primary paired score units are races. The comparison must preserve chronology and report the distribution of per-race loss differences, not only aggregate averages.

### N2 / N3

Not part of the first structural promotion unless separately preregistered.

N2 must beat a decision-time market-only baseline on probability metrics before economic optimization.
N3 must add evidence beyond N1 before promotion.

## 8. Statistical uncertainty / dependence

Race observations may be temporally clustered by day/meeting/venue.

The final protocol must use a time-aware uncertainty method that does not treat all tickets as independent observations.

Candidate requirement:

- aggregate primary loss differences at race level;
- use calendar/meeting-aware block resampling or another preregistered dependence-robust interval;
- report both average effect and temporal stability.

Exact block definition, repetition count and confidence rule are NOT frozen in this draft and must be independently audited before FINAL.

## 9. Calibration diagnostics

Diagnostic slices may include:

- predicted-probability band;
- actionable odds band when a lawful decision-time market snapshot exists;
- model-market disagreement band for N2;
- line-position/line-size/singleton structural slices;
- race regime (only within separately applicable families);
- field size / bank context as prespecified diagnostics.

For each eligible slice report at minimum:

- count;
- expected event count `sum p`;
- observed event count;
- observed/expected ratio where defined;
- NLL / Brier where defined;
- confidence/uncertainty summary.

These slices are diagnostics by default. They do not authorize separate bucket calibrators or BUY thresholds unless those calibrators were separately preregistered.

Sparse slices must be labeled sparse, not interpreted aggressively.

## 10. Probability-object quality gates

Before scoring economics, every produced probability artifact must pass its Probability Object Contract:

- finite/nonnegative values;
- expected total mass;
- no duplicate/impossible outcomes;
- exact cross-market marginalization identities within tolerance;
- Wide overlapping-event mass semantics preserved;
- frame aggregation consistent with official mapping;
- no lower-envelope/score object mislabeled as a distribution.

Failure => no economic scoring for that artifact.

## 11. Economic evaluation order

Only probability families that pass their preregistered scientific probability gate proceed to economic evaluation.

### E0 — probability only

No realized ROI used for model selection.

### E1 — first clean economic edge test

Candidate primary rule:

- elementary tickets only;
- at most one selected ticket per race;
- FLAT100;
- deterministic BUY/NO-BET rule frozen before FINAL;
- actionable decision-time price only;
- no Kelly;
- no portfolio optimizer.

Purpose: measure selection alpha with minimal capital-policy confounding.

### E2 — simple exposure sensitivity

Only after E1 evidence:

- simple race-level caps / equal-budget variants may be evaluated under a separately preregistered policy.

### E3 — bankroll optimization

Fractional Kelly / portfolio optimization only after coherent calibrated probabilities and simple economics pass untouched validation.

## 12. Required economic robustness report

A final positive ROI alone is insufficient.

Required:

### Time stability
- weekly P&L;
- monthly P&L;
- positive active-week fraction;
- positive active-month fraction;
- median weekly/monthly return;
- worst prespecified rolling windows.

### Drawdown / persistence
- maximum drawdown;
- longest underwater duration in days;
- longest underwater duration in races;
- recovery duration.

### Profit concentration
- largest winning ticket / total profit;
- top-3 winning tickets / total profit;
- top-5 winning tickets / total profit;
- profit HHI or another frozen concentration statistic;
- ROI excluding largest winner;
- ROI excluding top-3 winners.

### Forecast consistency
- expected vs observed hits in relevant probability/odds/disagreement/structure slices.

A tail-event-dominated positive ROI may be reported as positive realized ROI but may not automatically be labeled reproducible economic edge.

## 13. Market data boundary

For any market-aware BUY rule or N2:

- BUY input price must be observed at or before the frozen decision timestamp;
- final closing odds unavailable at action time are prohibited as decision inputs;
- settlement/payout is outcome-side and accessed only after decision artifacts are locked;
- the same snapshot semantics must be transportable in development, CAL, FINAL and live operation.

## 14. Outcome-sensitive trial accounting

Every distinct configuration scored on CAL/FINAL must be enumerated before scoring.

Behaviorally identical configurations must be deduplicated.

A result-aware rerun with changed semantics is a new trial/lineage decision and cannot be hidden as an implementation retry.

Implementation bug fixes that preserve preregistered semantics must be documented and proven to preserve the semantic decision rule before rerunning.

## 15. Falsification candidates

Before FINAL, define kill conditions that do not depend on a lucky payout.

At minimum candidates include:

- N1 fails to improve rank2/rank3 conditional probability quality over C1;
- N2 fails to improve probability quality over market-only baseline;
- high-odds/high-disagreement regions remain materially overconfident;
- expected event counts continue to substantially exceed observed counts in the target selection region;
- economic selections disappear or change regime materially out of time;
- positive ROI is not robust to removal of the dominant winner(s);
- a proposed architecture only appears superior after ROI-driven threshold changes.

Exact numeric thresholds require independent audit before freeze.

## 16. Independent audit gate

Before scientific Freeze / FINAL:

An independent reviewer must inspect at least:

- source rights and timestamp semantics;
- eligible race regimes;
- feature/provenance contracts;
- C0/C1/N1 fairness of ablation;
- probability-object invariants;
- hyperparameter/search budget;
- chronology/split policy;
- uncertainty/statistical test;
- calibration policy;
- economic E1 rule;
- settlement/dead-heat/cancel handling;
- holdout/C boundary protection;
- trial accounting and researcher degrees of freedom.

Verdict must be APPROVE / CONDITIONAL APPROVE / REJECT with concrete required changes.

## 17. Current protected state

- parent = `NO_B_VALIDATED_CONFIGURATION`;
- current DEV2000 C = not eligible for new-lineage untouched validation;
- `ECON_HOLDOUT1000 = SEALED`;
- prospective collection = not authorized until source/provider/collector audit passes.

END OF DRAFT
