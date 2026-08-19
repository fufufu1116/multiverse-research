# Multiverse Keirin — New Lineage C0 / C1 / N1 Probability Architecture Draft v1

Status: DESIGN CANDIDATE — NOT FROZEN / NOT EXECUTABLE
Date: 2026-08-19 JST

## 0. Scientific purpose

The primary structural question is not whether a new model can find a profitable historical ticket. It is:

> With comparable admissible PRE information, does explicitly modeling rank-2 / rank-3 dependence improve out-of-time ordered-top3 probability quality beyond a Plackett-Luce generator?

This draft defines a low-freedom ablation ladder to isolate:

1. the legacy/current PL control;
2. the incremental value of line-aware PRE features while retaining PL;
3. the incremental value of conditional relational dependence after line-aware features are already present.

No current DEV2000 C or ECON_HOLDOUT1000 outcome may be used to choose this architecture.

## 1. Applicability boundary

Initial C1/N1 structural family applies only to races whose `race_regime` is proven to be `STANDARD_ORIGINAL_LINE_KEIRIN` and whose line observation satisfies the separately audited mutable-feature provenance contract.

`INTERNATIONAL_FIXED_PACER` races are not pooled into this first line-conditioned family.

Unknown regime or unproven line state => FAIL-CLOSED for C1/N1 structural evaluation.

## 2. Shared admissible PRE basis

### 2.1 Individual ability/tactical candidates

The common runner basis may include only features admitted in the eventual new-lineage PRE schema, expected to be drawn from:

- current-race class/grade;
- style;
- score;
- win/top2/top3 historical published rates;
- S/B and, if point-in-time proven, H;
- if point-in-time proven, maneuver counts: 逃 / 捲 / 差 / マ;
- stable bank context and timestamped environment only if separately admitted.

Exact feature allowlist and transforms must be frozen before new untouched outcomes.

### 2.2 Structural raw inputs

Candidate CORE raw structure:

- `line_group_id` (grouping key only, never raw identity predictor);
- `line_position`;
- `line_size`;
- `is_singleton`;
- `num_lines`.

### 2.3 Deterministic relation functions

Only functions of already-admitted PRE structure may enter relational stages. Candidate minimal relations:

- `same_line(a,b)`;
- `position_delta(a,b)` within the same line, otherwise a fixed neutral/missing state;
- `directly_ahead(a,b)`;
- `directly_behind(a,b)`;
- `leader_follower_relation(a,b)`;
- candidate's own line position / line size / singleton state.

No result-derived line transition or realized switch may be used as an input.

## 3. C0 — Frozen Current PL Control

### Role

Structural NULL / legacy reference.

C0 uses the already-frozen current sporting probability source(s) and the frozen repeated PL ordered-top3 expansion. It is not refit to make the new architecture look better or worse.

For runner weights `w_i > 0`, the ordered top-3 probability is:

`P_C0(i,j,k) = w_i/S * w_j/(S-w_i) * w_k/(S-w_i-w_j)`

where `S = sum_r w_r` over active runners.

This implies that after a selected runner is removed, relative choice odds among the remaining runners depend only on their fixed weights, not on who occupied the prior finishing position except through removal.

C0 remains a valid benchmark even if later rejected as the primary final generator.

## 4. C1 — Line-Augmented Runner Utility + PL

### Purpose

C1 tests whether adding admissible structural PRE information improves the runner utility / winner layer while **retaining the same PL order-generation assumption**.

### Common utility

For each active runner `i` in race context `X`:

`u_i = beta^T x_i`

and

`P1_C1(i|X) = exp(u_i) / sum_r exp(u_r)`.

`x_i` contains the frozen shared individual PRE basis plus admitted own-line descriptors, but does not include the arbitrary identity of `line_group_id`.

### Ordered top3

C1 uses PL on `exp(u_i)`:

`P_C1(i,j,k|X) = P1_C1(i|X) * exp(u_j)/sum_{r != i} exp(u_r) * exp(u_k)/sum_{r notin {i,j}} exp(u_r)`.

### Interpretation

C1 can learn that, for example, being a bante rider in a longer line changes a runner's baseline strength. It still cannot make candidate `j`'s relative rank-2 probability change specifically because the actual first-place rider was `i`, beyond removing `i` from the choice set.

## 5. N1 — Line-Conditional Top-3 Chain Model

### Purpose

N1 keeps the same P1 runner utility basis as C1 but allows low-dimensional, preregistered relational terms at rank 2 and rank 3.

### Rank 1

`P1_N1(i|X) = P1_C1(i|X)`

under the primary architecture comparison. This shared P1 is intentional: the structural hypothesis is tested primarily at conditional rank 2/3 rather than by changing the winner layer simultaneously.

### Rank 2 conditional

For candidate `j != i`:

`v2(j; i, X) = u_j + gamma2^T R2(j,i,X)`

`P2_N1(j | i,X) = exp(v2(j;i,X)) / sum_{r != i} exp(v2(r;i,X))`.

Minimal R2 candidate family:

- same-line relation between candidate and first-place context rider;
- signed/role-based within-line positional relation where applicable;
- direct-ahead/direct-behind indicator where applicable;
- candidate own singleton/line-size context if not already captured by `u_j` only through a prespecified interaction.

Exact R2 encoding must be frozen before fitting.

### Rank 3 conditional

For candidate `k notin {i,j}`:

`v3(k; i,j,X) = u_k + gamma3^T R3(k,i,j,X)`

`P3_N1(k | i,j,X) = exp(v3(k;i,j,X)) / sum_{r notin {i,j}} exp(v3(r;i,j,X))`.

Minimal R3 candidate family should be restricted to deterministic relations between `k` and each of `i,j`, plus whether `i` and `j` themselves share a line. It must not include realized in-race state.

### Joint probability

`P_N1(i,j,k|X) = P1_N1(i|X) * P2_N1(j|i,X) * P3_N1(k|i,j,X)`.

Exact enumeration is primary. With at most nine active runners there are at most `9P3 = 504` ordered top-3 outcomes, so Monte Carlo is unnecessary for N1 and would only add simulation noise.

## 6. Core ablation invariants

To interpret C1 vs N1 scientifically:

1. C1 and N1 must use the same eligible race universe.
2. C1 and N1 must use the same admitted raw PRE information.
3. The primary N1 comparison shares the same P1 utility layer as C1.
4. Only the rank-2 / rank-3 relation terms differ.
5. Hyperparameter/search budgets must be prespecified and comparable.
6. Architecture selection occurs on proper probability scores, not realized ROI.
7. Economic policies are not tuned until probability architecture is frozen.

If a later N1 variant changes P1 as well, it is a distinct execution/family and cannot be presented as the clean C1-vs-N1 structural ablation.

## 7. Probability Object Contract

Every probability-like artifact must declare:

- `object_type`;
- support;
- expected total mass;
- normalization/marginalization rules;
- whether events are mutually exclusive or overlapping;
- whether the object may be used in a proper scoring rule;
- whether the object may be used for EV/Kelly sizing.

### 7.1 Ordered top3 joint

Object type: `COHERENT_MUTUALLY_EXCLUSIVE_DISTRIBUTION`

Support: all distinct ordered triples `(i,j,k)` of active runners.

Invariant:

`sum_{i != j != k} P(i,j,k) = 1` within numerical tolerance.

All probabilities finite, non-negative, no duplicate runner within a triple.

This ordered-top3 joint is the single source of truth for all car-based ticket-event probabilities in C1/N1.

### 7.2 3rentan

`P_3rentan(i-j-k) = P(i,j,k)`.

Mass over complete sold 3rentan ticket space = 1.

### 7.3 3renhuku

For unordered set `{a,b,c}`:

`P_3renhuku({a,b,c}) = sum over all 6 permutations pi of P(pi(a,b,c))`.

Mass over complete sold 3renhuku ticket space = 1.

### 7.4 2shatan

`P_2shatan(i-j) = sum_{k notin {i,j}} P(i,j,k)`.

Mass over complete sold 2shatan space = 1.

### 7.5 2shahuku

`P_2shahuku({i,j}) = P_2shatan(i-j) + P_2shatan(j-i)`.

Mass over complete sold 2shahuku space = 1.

### 7.6 Wide

For unordered pair `{i,j}`:

`P_wide({i,j}) = sum of all ordered top3 outcomes containing both i and j`.

Object type: `OVERLAPPING_EVENT_PROBABILITY_VECTOR`, not a mutually exclusive probability distribution.

Invariant for every race with at least 3 active runners:

`sum_{i<j} P_wide({i,j}) = C(3,2) = 3`.

A unit-mass market-shape proxy, if separately constructed, must carry a different object type and may not be substituted for Wide event probabilities.

### 7.7 Frame markets

When 2wakutan / 2wakuhuku are officially sold, probabilities must be deterministically aggregated from the coherent car top-2 joint using the official race-specific car-to-frame mapping.

Expected mass over each complete sold frame-market ticket space = 1.

Missing/ambiguous frame mapping => FAIL-CLOSED.

## 8. Cross-market coherence tests

For every race/model artifact before any economic evaluation:

- all ordered-top3 mass = 1;
- all 3rentan mass = 1;
- all 3renhuku mass = 1;
- all 2shatan mass = 1;
- all 2shahuku mass = 1;
- Wide event mass = 3;
- sold frame-market mass = 1;
- every 3renhuku equals exact six-permutation marginalization;
- every 2shatan equals exact rank-3 marginalization;
- every 2shahuku equals the two ordered top-2 directions;
- every Wide pair equals exact top-3 co-occurrence marginalization;
- frame markets exactly match deterministic car-to-frame aggregation.

Any mismatch above tolerance => artifact invalid / FAIL-CLOSED.

## 9. Lower-envelope / consensus objects

`min(p_A, p_B)` may only be represented as something such as:

`object_type = TICKETWISE_LOWER_ENVELOPE`

It is not automatically a coherent distribution and must not be named as one.

For the same ticket odds `O`:

`min(O*p_A - 1, O*p_B - 1) = O*min(p_A,p_B) - 1`.

Therefore ticketwise min-probability and min-EV are not independent evidence signals.

Any future ensemble must define a coherent combination rule if a distribution is required.

## 10. Model complexity guardrails

Initial C1/N1 implementation candidate:

- regularized linear/softmax conditional-choice models;
- no deep neural network in primary N1;
- exact enumeration, no Monte Carlo;
- no latent initiative/switch state in N1;
- no market odds as sporting-model inputs in C1/N1;
- no independent calibrator per sparse odds/structure bucket;
- no ROI-driven feature deletion/addition.

N2 market-residual and N3 initiative models remain separate later families.

## 11. Primary falsification logic candidate

The strongest test of the N1 structural hypothesis is conditional:

- compare C1 vs N1 rank-2 conditional log loss on untouched chronological data;
- compare C1 vs N1 rank-3 conditional log loss on the same data;
- report joint-top3 log loss and calibration as confirmation.

If explicit relation terms fail to provide reproducible out-of-time improvement beyond C1, line-conditioned rank dependence should not be retained merely because an economic tail event happens to be profitable.

Exact statistical thresholds / uncertainty rules are deferred to the validation-protocol preregistration and independent audit.

## 12. Current status

This document does not admit any feature source and does not authorize training. Mutable line/race-regime/H transport and source rights remain P0 prerequisites.

Current DEV2000 C remains unavailable for new-lineage rescue.
`ECON_HOLDOUT1000 = SEALED`.

END OF DRAFT
