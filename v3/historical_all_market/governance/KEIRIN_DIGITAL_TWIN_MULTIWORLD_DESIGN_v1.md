# Multiverse Keirin — Digital Twin / Multiworld Simulation Design v1

Status: DESIGN / ENGINEERING FRAMEWORK — NOT REAL-WORLD VALIDATION
Date: 2026-08-19 JST

## Purpose

Use a source-independent synthetic keirin world to:
- formalize the root race structure before new outcome access;
- test C0/C1/N1 mechanics and failure modes;
- stress-test ticket probability coherence, virtual BUY rules, virtual bankroll/risk, and synthetic market plumbing;
- identify architecture bugs before any untouched real validation is opened.

Synthetic worlds are NEVER evidence of real-market profitability or real-world predictive validity.

## Core anti-circularity rule

Do not create one synthetic world whose data-generating mechanism equals the candidate model under test.

A model must be tested across multiple plausible worlds with different dependence assumptions. If N1 generates the world, N1 cannot claim scientific support merely by recovering its own generating rule.

## Layered world model

### Layer A — race environment
- race_regime
- field size
- venue/bank geometry
- weather/wind context
- class composition consistent with allowed race programs

### Layer B — rider latent state
Each synthetic rider has latent and observable components:
- baseline ability
- style/tactical tendency
- start/position tendency
- B/H/S-like tendencies
- nige/makuri/sashi/mark-like profile
- short-term form noise
- idiosyncratic race-day shock

Observable PRE fields are noisy projections of latent state. The simulator must not reveal latent truth to prediction models unless the experimental protocol explicitly defines an oracle control.

### Layer C — line / formation generator
For standard-line regimes:
- number of lines
- line sizes
- singleton riders
- within-line order
- front/bante/third roles
- line strength composition

For international/fixed-pacer regimes:
- line module disabled or replaced by regime-specific mechanics.

### Layer D — race-dynamics latent state
Candidate latent states may include:
- initiative-winning line
- early position structure
- successful/failed attack
- line survival or fragmentation
- leader fatigue
- bante support/benefit
- singleton attachment opportunity
- late-race stochastic shock

These latent states are simulator internals, not automatically model features.

### Layer E — ordered top-3 outcome generator
The simulator outputs one realized ordered top3 and the underlying world-truth ordered-top3 distribution where computationally feasible.

The output must satisfy the existing Probability Object Contract.

### Layer F — synthetic market
Use the existing synthetic-market engine to create virtual quote shapes/odds from a market-information model that is distinct from the sporting predictor.

The market may observe a different/noisy information set than C0/C1/N1. It must not be mechanically derived from the candidate model being evaluated.

### Layer G — virtual settlement and capital
- official ticket event semantics
- virtual stake only
- virtual payout/return
- FLAT100 primary engineering test
- virtual Kelly/portfolio only after probability/risk plumbing is verified

## Required Multiworld set

At minimum, preregister worlds such as:

### W0 — LUCE / PL-LIKE CONTROL WORLD
Context-free rider utilities; weak/no line conditional interaction.
Purpose: verify that N1 is not automatically superior when the true world is close to PL.

### W1 — STATIC LINE ADVANTAGE WORLD
Line position/size affect utilities, but conditional order interaction remains limited.
Purpose: C1 should capture much of the gain if features, not joint architecture, are the key factor.

### W2 — CONDITIONAL LINE DEPENDENCE WORLD
Explicit P(second | first) and P(third | first,second) relation effects.
Purpose: N1 should have a recoverable structural advantage.

### W3 — LINE BREAK / TRANSITION WORLD
Initiative, attack success, fragmentation, switching/reattachment and line failure create context changes.
Purpose: expose limits of static line covariates and simple conditional models.

### W4 — HEAVY-TAIL / SHOCK WORLD
Large race-day latent shocks and low-probability reorderings.
Purpose: test high-odds overconfidence, calibration robustness and tail concentration.

### W5 — MARKET-STRONG WORLD
Synthetic market observes substantial latent information unavailable to sporting model.
Purpose: test whether market-residual logic correctly defaults toward market rather than inventing alpha.

### W6 — MARKET-WEAK / BIASED WORLD
Synthetic market has systematic low-dimensional biases or stale/noisy information.
Purpose: test whether a residual model can recover genuine incremental information without simply copying market.

## Realism strategy

"Realistic" means matching externally justified structural/statistical constraints, not visual plausibility.

Use a hierarchy of calibration targets:
1. immutable mathematical/official race invariants;
2. distributions of lawfully held PRE variables;
3. general aggregate race statistics when admissible and provenance-tracked;
4. burned-development data only as explicitly outcome-aware simulator calibration, never as untouched validation;
5. sensitivity ranges when exact real calibration is unavailable.

Every calibrated parameter must record source class:
- OFFICIAL_RULE
- PRE_EMPIRICAL
- BURNED_OUTCOME_AWARE
- EXTERNAL_AGGREGATE
- ASSUMPTION_RANGE

## What the Digital Twin may prove

It MAY prove:
- code correctness under known generating mechanisms;
- identifiability/recovery behavior;
- robustness to alternative worlds;
- calibration/pipeline bugs;
- ticket coherence;
- virtual bankroll risk mechanics;
- whether a proposed model fails even under favorable plausible conditions.

It MAY NOT prove:
- real keirin predictive edge;
- real market alpha;
- real ROI/generalization;
- that a world assumption is true merely because the simulator contains it.

## Promotion philosophy

Synthetic testing is a preflight/falsification layer.

A candidate that fails simple synthetic worlds should not consume real untouched evidence.
A candidate that passes synthetic worlds merely earns eligibility for real-data validation after all governance gates pass.

## Initial root features to freeze before sophisticated dynamics

Prefer direct structural fields first:
- race_regime
- field size
- class/rider PRE ability fields
- style
- B/H/S when source semantics are valid
- nige/makuri/sashi/mark-like tactical profile when valid
- line grouping/order/size/singleton
- bank geometry
- weather/wind context

Derived initiative, switching, attachment and transition variables remain latent/experimental until the simpler worlds are understood.

## Initial experiment ladder

1. Build race/rider/line PRE generator.
2. Build W0/W1/W2 first.
3. Verify C0/C1/N1 recover expected ordering across worlds.
4. Add W4 heavy-tail stress.
5. Connect synthetic market engine and virtual FLAT100 attribution.
6. Add W3/W5/W6 only after basic invariants/selftests pass.
7. Independent audit before using simulator outcomes to finalize new-lineage architecture choices.

## Hard blockers

- no synthetic world may be mislabeled as real validation;
- no candidate may tune the world generator to make itself win;
- no synthetic ROI can promote a model to real-world edge status;
- no current DEV2000 C or ECON_HOLDOUT1000 access;
- no external provider contact under current Owner policy;
- no real-money wagering in project scope.

END
