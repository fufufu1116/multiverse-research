# Multiverse Keirin — Tri-Model Architecture Review / Lessons Learned v1

Status: LESSONS-LEARNED / DESIGN AUDIT ONLY — NOT A SCIENTIFIC FREEZE / NOT EXECUTABLE
Date: 2026-08-19 JST

## 0. Firewall

This record synthesizes the Owner-provided independent reviews from Claude, Gemini, and a separate ChatGPT conversation, cross-checked against current repository artifacts and official KEIRIN structure documentation.

It does NOT authorize:
- refitting or rescuing the closed DEV2000 lineage;
- rescoring current DEV2000 B/C;
- accessing current DEV2000 C for new-lineage selection;
- opening ECON_HOLDOUT1000;
- unauthorized new data collection;
- adopting any reviewer-suggested numeric threshold without preregistration and independent evidence.

Closed parent remains `NO_B_VALIDATED_CONFIGURATION`.
Current DEV2000 C remains unscored by the Stage-7 evaluator.
`ECON_HOLDOUT1000 = SEALED`.

## 1. Strongly accepted lessons

### L1 — Current PL must be treated as a structural NULL / control, not presumed final top-3 generator

Current Stage-1 converts runner win probabilities to ordered top-3 using repeated Plackett-Luce selection. Under the PL/Luce choice axiom, relative odds between remaining items are context-invariant. Official KEIRIN structure explicitly contains line cooperation, leader/follower roles, bante support, switching, competition for positions, and race-dependent positioning. Therefore there is a scientifically legitimate structural-misspecification hypothesis: runner finish relationships may depend on line relations in ways the frozen PL generator cannot express.

Important restraint: this is NOT accepted as the proven causal explanation of the prior B failure or high-odds overconfidence. It is a priority falsification target.

### L2 — Ensemble agreement does not protect against shared structural misspecification

Candidate A and B1a differ, but both feed the same downstream PL ticket generator and share substantial input structure. `min(pA,pB)` and TV disagreement only measure a form of between-model disagreement. They cannot detect a common architectural error shared by both models.

Future Multiverse rule: model diversity must be audited at the level of assumptions / architecture / data as well as output disagreement.

### L3 — Probability-object coherence must become an explicit invariant

For mutually exclusive exhaustive ticket spaces, a probability object must declare support and required total mass. A lower envelope such as `min(pA,pB)` is generally not a normalized joint distribution. It may remain a conservative diagnostic / ticketwise lower score, but must not be mislabeled as a coherent probability distribution.

Future object contract:
- declare `object_type` (probability distribution, event-probability vector, lower envelope, score, market-shape proxy, etc.);
- declare support;
- declare expected total mass;
- enforce exact/within-tolerance mass invariant;
- enforce marginalization identities across derived markets where applicable.

`consensus_EV = min(EV_A,EV_B)` is algebraically redundant with `min(pA,pB)` for the same ticket/odds (`min(EV)=odds*min(p)-1`). It should not be treated as independent evidence.

### L4 — Wide requires a semantic firewall between event probabilities and normalized shape proxies

Current Stage-1 correctly enforces total Wide event-probability mass = 3. Current Stage-2 deliberately normalizes inverse Wide quotes to a unit-mass `market_shape_q` and compares this to `p/3` as a shape diagnostic.

Therefore the reviewer claim that unit-normalized Wide `q` is automatically a current bug is TOO STRONG: a unit-mass quote-shape proxy is permissible if kept purely diagnostic.

However it MUST NOT be promoted to a literal Wide event-probability baseline or used as though it were the same probability object as Wide event probabilities. Any market-residual Wide model must use explicitly coherent overlapping-event semantics or remain excluded.

### L5 — Race regime must be explicit before line modeling

Current class schema contains L1, but there is no repository evidence of an explicit `race_regime` split. Official KEIRIN documentation identifies Girls KEIRIN as international-style fixed-pacer racing, and current-era KEIRIN ADVANCE also applies international-style rules to some men's races.

Therefore future regime classification must be based on the actual race rule/regime, NOT inferred solely from sex or L1 class.

Minimum candidate regimes:
- `STANDARD_LINE_KEIRIN`
- `INTERNATIONAL_FIXED_PACER`
- other/unknown => FAIL-CLOSED until semantics are frozen.

A standard-line relational model must not automatically pool INTERNATIONAL races.

### L6 — Line provenance needs mutable-feature-specific proof

Existing feature registry contains `line_id`, `line_position`, and `line_size` with generic `available_at_required=1`, but no explicit `line_source` or `line_snapshot_timestamp` fields were found.

Official KEIRIN guidance states that rider introduction / leg-show is an information point where lines are displayed. Line formation can therefore be mutable near the decision cutoff.

Future rule: a generic prediction timestamp is insufficient for mutable tactical structure. Required provenance candidate fields:
- `line_source`
- `line_snapshot_timestamp`
- `line_observation_type` (announced/expected lineup vs observed leg-show lineup)
- raw payload SHA / source URI or equivalent provenance
- explicit cutoff comparison

A historical line reconstructed from post-race narrative/video is NOT PRE evidence.

### L7 — H is a real missing PRE candidate; bank/weather are not newly discovered concepts

Official KEIRIN race-card documentation describes H, B, S and finishing-technique counts (`逃/捲/差/マ`) as information useful for race-development inference.

Current NEXTGEN registry already contains B, S, `nige/makuri/sashi/mark`, line features, bank length/home straight/cant, and weather/wind. Therefore bank/weather/wind are not newly discovered by this review; they were already designed but are not active in frozen DEV2000.

`H` was not found in `feature_registry_v1.csv` and is a genuine candidate gap to audit.

### L8 — Actionable market time is a separate boundary from PRE/result leakage

The current closed historical Stage-2 uses closing odds. The already-created next-lineage market-baseline draft had independently recognized that final/post-decision closing prices must not be live BUY inputs unless proven available at the frozen decision time.

This review independently reinforces that rule.

Future general Multiverse distinction:
- `PRE_AVAILABLE`: known before outcome;
- `DECISION_AVAILABLE`: known before action commitment;
- a feature must satisfy BOTH if used for a live decision.

### L9 — Conditional top-3 is the cleanest first structural alternative

A low-freedom chain-rule family is accepted as the strongest first alternative to test:

`P(i,j,k|X) = P1(i|X) * P2(j|i,X) * P3(k|i,j,X)`.

The conditional models may use deterministic relational PRE features such as:
- same_line;
- line_position;
- position gap;
- leader/follower relation;
- line_size;
- singleton;
- race regime;
- line-relative strength.

This directly tests the missing dependency at rank 2 and rank 3 while preserving exact normalization over ordered top-3 outcomes.

### L10 — Required ablation ladder separates feature value from architecture value

Provisional scientific comparison order:

- `C0`: frozen current PL control;
- `C1`: line-augmented runner/winner utilities while retaining PL order generation;
- `N1`: line-conditioned top-3 chain model allowing rank-2/rank-3 dependence;
- `N2`: market-residual top-3, only with decision-time transportable market snapshot;
- `N3`: initiative mixture only after N1 evidence supports added complexity.

This ablation is important because it distinguishes:
1. line features help runner ability;
2. explicit conditional dependence helps beyond line features;
3. market anchoring adds incremental value.

### L11 — Decompose proper probability scoring by rank before economics

For N1, primary scientific diagnostics should include:
- Winner NLL: `-log P1(i)`;
- Rank2 conditional NLL: `-log P2(j|i)`;
- Rank3 conditional NLL: `-log P3(k|i,j)`;
- joint top-3 NLL = sum of the three.

A key falsification test is whether N1 improves rank2/rank3 conditional likelihood over C1, not whether it happens to hit a large payout.

Economic policy must not select the probability architecture before proper-scoring evidence.

### L12 — Calibration slices should diagnose; independent bucket calibrators are not automatically safe

Odds-band and model-vs-market disagreement-band reporting is strongly accepted.

However fitting independent isotonic calibrators in many odds/disagreement buckets can:
- increase researcher degrees of freedom;
- destroy cross-ticket/joint probability coherence;
- overfit sparse heavy-tail regions.

Initial calibration family should remain low dimensional and coherent (e.g. global temperature / limited rank-specific transforms / one residual shrink parameter), while bands are primarily diagnostics unless a coherent constrained calibration method is preregistered.

### L13 — Uncertainty-aware BUY is accepted in principle, but first economic test must be simple

Point-estimate raw EV alone is fragile under probability error. Lower-confidence/shrunk probability EV is a valid candidate.

But the first economic experiment should minimize policy freedom:
- FLAT100 primary;
- preferably <=1 elementary ticket per race in the first clean edge test;
- no Kelly-driven model selection;
- no portfolio optimizer until probability evidence passes.

Note: `RACE2PCT_EQUAL` is NOT the same as pure Equal/Flat Stake; its stake varies with bankroll and ticket count. `FLAT100` is the cleaner alpha diagnostic.

### L14 — Kelly is secondary until coherent calibrated probabilities are demonstrated

Current closed Stage-6 used ticketwise conservative `min(pA,pB)` for Kelly-like sizing. Given the detected calibration failure and the non-coherent lower-envelope semantics, Kelly should be secondary sensitivity only in a new lineage.

This does not imply ticketwise Kelly is algebraically impossible with a conservative event estimate; the problem is scientific reliability and multi-ticket coherence, not merely normalization.

### L15 — Profit concentration / underwater metrics are core evaluation, not cosmetic reporting

Accepted metrics include:
- largest winner / total profit;
- top-3/top-5 contribution;
- HHI or other concentration index;
- ROI excluding largest/top-3 wins;
- weekly/monthly P&L and positive fractions;
- median weekly/monthly return;
- max drawdown;
- longest underwater duration by days and races;
- recovery duration;
- expected-vs-observed hits by probability/odds/disagreement slice.

No positive ROI dominated by one tail event should be called reproducible economic edge without separate robustness evidence.

## 2. Reviewer suggestions NOT accepted as established facts

### R1 — `PL caused the B failure` / `direct mathematical cause`
NOT ESTABLISHED.
PL structural misspecification is a strong hypothesis, but the burned diagnostics do not causally isolate it from winner-model calibration, selection conditioning, market timing, price semantics, or other omitted structure.

### R2 — `70%+ of KEIRIN outcomes are determined by line physical position`
NOT ADMITTED. No verified evidence supporting this exact numerical statement was supplied/confirmed in this audit.

### R3 — `same-line one-two should be ~40-50%`
NOT ADMITTED as a preregistered expected value or threshold. Requires an exact dataset/source/regime definition before use.

### R4 — Nested/Hierarchical PL is automatically sufficient
NOT ESTABLISHED. It is a legitimate candidate family, but nesting still imposes structural assumptions. It should not displace the simpler C0/C1/N1 ablation without evidence.

### R5 — Monte Carlo is required to derive 3rentan probabilities
REJECTED AS NECESSARY for the minimal 5-9 runner case. Ordered top-3 state space is small (maximum 9P3=504), so exact enumeration/marginalization is preferable initially and avoids simulation noise. Sampling remains optional for later, more complex latent-state models.

### R6 — Independent bucket-wise isotonic calibration should be default
NOT ACCEPTED as default due coherence/sparsity/multiple-fitting risk. Use buckets first for diagnostics.

### R7 — Ticket covariance example `1-2-3` and `1-2-4` as positively correlated wins
MISLEADING. Two distinct 3rentan elementary tickets are mutually exclusive as winning events in one race. Portfolio optimization may still be useful for payoff/exposure structure across markets, but exact outcome-level payoff covariance must be computed from the coherent joint distribution rather than inferred from visual ticket similarity.

### R8 — Immediate portfolio optimizer
DEFERRED. Adding CVaR/knapsack/covariance optimization before proving the probability model would confound forecasting with portfolio tuning and enlarge researcher degrees of freedom.

## 3. What Mr.3 / current research process had actually missed

### M1 — We diagnosed calibration failure before auditing the generative assumption that creates rank 2/3

Why it happened:
- the project evolved from winner prediction;
- PL was introduced as a mathematically coherent way to expand winner probabilities to all markets;
- implementation correctness and sum-to-one invariants were audited more strongly than domain-structural suitability.

Prevention:
Every derived probability architecture must receive an `ASSUMPTION AUDIT` before economic tuning:
- independence/context assumptions;
- conditional dependence omitted;
- regime invariance;
- physical/relational structure omitted;
- falsification test.

### M2 — We used a ticketwise conservative lower envelope without a probability-measure type system

Why it happened:
- focus was on conservative decision safety (`min` feels safe ticket by ticket);
- no explicit object-level distinction between coherent distribution vs conservative score/lower envelope.

Prevention:
Introduce the Probability Object Contract in L3 and prohibit any object from being named/used as `probability_distribution` unless mass and marginalization invariants pass.

### M3 — Ensemble diversity was treated mainly as output disagreement, not shared-assumption diversity

Why it happened:
- Candidate A and B1a were different enough in coefficients/features to be operationally treated as two sources;
- downstream shared PL architecture was not included in the diversity audit.

Prevention:
For every ensemble, record:
- feature overlap;
- training-data overlap;
- model-family overlap;
- downstream-transform overlap;
- known shared failure modes.

### M4 — Generic `available_at` was too coarse for mutable line information

Why it happened:
- provenance controls were built generically around `prediction_timestamp`;
- lineup is a tactical/mutable object whose semantic state can change near start.

Prevention:
Mutable-feature contract requires source-specific snapshot timestamp, observation type, raw provenance and cutoff test.

### M5 — Race-regime heterogeneity was not explicit in line-feature design

Why it happened:
- current DEV model did not use line structure, so L1/regime differences were partially hidden inside class;
- adding line features changes this from a minor class distinction into an architecture-defining boundary.

Prevention:
Every new structural feature family must first declare `applicable_regimes` and fail closed for unknown regimes.

### M6 — H was overlooked while B/S and maneuver counts were already considered

Why it happened:
- legacy/current PRE schema centered on fields already recovered reliably;
- NEXTGEN registry expanded style features but omitted H despite official availability/interpretability.

Prevention:
Use an official-racecard field completeness checklist before freezing a new PRE registry; omission must be explicit, not accidental.

## 4. General Multiverse-main lessons to transfer later

When KEIRIN research is complete, candidates for Multiverse-main governance:

1. **Structural Null Rule** — a simple independence model remains a control even if replaced as the primary model.
2. **Probability Object Contract** — support, total mass, marginalization/coherence, object type.
3. **Shared Misspecification Audit** for ensembles.
4. **Decision-Availability Boundary** separate from merely PRE/result-free data.
5. **Mutable Feature Provenance Contract**.
6. **Regime Applicability Contract** before structural feature use.
7. **Ablation Ladder**: same features/simple architecture before adding architectural complexity.
8. **Proper-Scoring-First Rule**: probability model selected by out-of-time probability quality before economic tuning.
9. **Conditional Score Decomposition** where a joint model has natural stages.
10. **Coherent Calibration Rule**: diagnostic slicing must not silently become many independent calibrators.
11. **Simple-Economics-First Rule**: flat/path-independent stake before Kelly/portfolio optimization.
12. **Tail-Concentration Gate** before calling ROI reproducible.
13. **Causal Claim Gate**: a diagnostic association may be a hypothesis; do not label it the root cause until an ablation/falsification isolates it.
14. **Numeric Claim Provenance**: no memorable percentage/threshold from reviewer commentary enters governance without exact evidence.

## 5. Provisional next-lineage PRE/schema candidates

CORE candidate additions / clarifications (must still pass provenance audit):
- `race_regime`
- `line_group_id` (grouping key, not raw categorical identity)
- `line_position`
- `line_size`
- `is_singleton`
- `num_lines`
- `line_source`
- `line_snapshot_timestamp`
- `line_observation_type`
- `H`

Already present in NEXTGEN registry but not active in frozen DEV2000:
- `nige`, `makuri`, `sashi`, `mark`
- `line_id`, `line_position`, `line_size`, `line_score_sum`, `self_power_count`
- `bank_length_m`, `home_straight_m`, `bank_cant_deg`
- weather / temperature / wind speed / wind direction
- timestamp-proven market snapshots (`tminus3`, `tminus1`) and movement.

Feature candidate (not direct fact):
- race-relative initiative probability;
- line support strength;
- single-rider conditional positioning effect.

Experimental:
- switch / reattach latent transition;
- full in-race state transition model;
- initiative mixture N3;
- portfolio optimizer.

## 6. Provisional next-lineage architecture order

`C0 Frozen Current PL control`
→ `C1 Line-augmented PL ablation`
→ `N1 LINE-COND-TOP3`
→ `N2 MARKET-RESIDUAL-TOP3` (only if decision-time market transport is proven)
→ `N3 INITIATIVE-MIXTURE` only after N1 evidence.

The main primary experiment should ask:

**Does explicit line-conditioned dependence improve Rank2|Rank1 and Rank3|Rank1,Rank2 out-of-time likelihood beyond a line-feature PL control?**

This question is deliberately independent of the prior 457.9x outcome and cannot be answered by patching current DEV2000 C.

## 7. Current hard state

- closed parent: `NO_B_VALIDATED_CONFIGURATION`
- same-lineage rescue: PROHIBITED
- current DEV2000 C new-lineage use: PROHIBITED
- current Stage-7 C scoring count: 0
- `ECON_HOLDOUT1000 = SEALED`
- no reviewer numeric threshold is frozen by this document
- no network acquisition is authorized by this document
