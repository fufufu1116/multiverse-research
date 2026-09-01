# KEIRIN Parallel Research — Mechanism Affinity Audit v1

Status: `RESEARCH_CANDIDATE_NOT_CANONICAL_NOT_ACCEPTED_NOT_PROMOTED`
Evidence class: `SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY`
Created: 2026-09-01 JST
Canonical fresh-read base: `5c1403c1f5aabb80d29e8c868440aede8888ce61`
Lane: `KEIRIN_PARALLEL_RESEARCH_CANDIDATE`

## 0. Safety / authority

This artifact is a Research/Candidate note only. It does not change Canonical Keirin state, accepted architecture, model status, Core Phase C, main, ruleset, Runtime, production authority, scientific trial accounting, or any protected-data boundary.

Fresh-read authorization permits only:
- source-independent synthetic regression / invariants;
- Digital Twin W0-W4 synthetic stress and failure diagnostics;
- C0/C1/N1 comparison inside those synthetic worlds.

Not used or opened for this audit:
- PR #15 quarantined metrics;
- RESULT/PAYOUT;
- ECON_HOLDOUT1000;
- DEV2000 C for new-lineage rescue;
- same-lineage B/C rescue tuning;
- real/live or untouched validation;
- economics / bankroll / real-money wagering.

Synthetic results are not real-world edge, ROI, or deployment evidence.

## 1. Fresh reconstruction

### 1.1 Current scientific position

`KEIRIN_NOW.md` and canonical `CURRENT_STATE_KEIRIN.json` show that Keirin scientific execution is authorized only for the limited Synthetic scope above. The last explicitly named pre-authorization scientific checkpoint is PR #14 exact scientific head `e70bda39a5d3ce585af4e028b35106b859871bd9`. PR #15 remains `QUARANTINED_NOT_ADMITTED`.

Canonical main also contains later nonauthorizing limited-Synthetic evidence from Batch 3/4, evidence synthesis, structure-scramble negative control, line-shape localization, and campaign boundary closure. Those records remain Synthetic engineering/falsification evidence and do not promote any model.

### 1.2 Already completed / do not repeat

1. Source-independent Digital Twin mechanical invariants, including PRE exclusion of latent skill and probability-object checks.
2. PR #14 broad assumption-range / topology stress. Recorded Actions evidence executed 388,800 scenario-race evaluations across 16,200 scenario-world cells. In the reported Tier-A cells, winner counts were C0=5,025, N1=1,090, C1=365 out of 6,480. This already answers the generic “run a wider parameter/topology sweep” question.
3. Batch 3 fixed C0/C1/N1 W0-W4 diagnostic comparison.
4. Batch 4 same-family post-hoc replication. Canonical synthesis says the W0-vs-W1-W4 N1/C1 sign pattern replicated across four added seed blocks, while explicitly not constituting untouched validation.
5. Same-family additional seed replication: canonical evidence synthesis says marginal value is saturated; do not add runs merely to increase count.
6. Structure-scramble negative control: C0 was exactly unchanged; N1 degraded under structure scramble in 19/20 world-by-seed-block cells. Mean scrambled-minus-intact N1 log-loss was approximately W0 +0.00055, W1 +0.00312, W2 +0.01269, W3 +0.00937, W4 +0.00718. This establishes sensitivity to the intended structure mapping inside the Synthetic system.
7. Line-shape localization: observed engineered seven-rider shapes `2-2-2-1`, `3-2-2`, `3-3-1`; the recorded synthetic relational-world advantage was not concentrated in only one of those motifs.
8. Boundary closure: routine same-scope seed replication and additional post-hoc slicing are stop-by-default unless a qualitatively new prespecified falsification question exists.

### 1.3 Rejected / isolated / non-admissible

- PR #15 metrics: quarantined and not admissible for resume/model selection.
- Protected outcome / holdout / Segment C routes: prohibited.
- Real/live collection, real-world validation, economics, promotion: outside this authorization.
- More ordinary same-family seed-only replication: not scientifically “rejected,” but explicitly low-value / stop-by-default under canonical boundary-closure guidance.

## 2. New finding from this audit: simulator–model mechanism affinity

### Finding MA-1 — `CONSTRUCT_ALIGNMENT_RISK`, not protected-data leakage

The current Digital Twin and N1 comparison use overlapping relational predicates.

In `digital_twin_v1.py`, W2 truth is generated with explicit conditional relational terms after earlier finishers are known:
- rank-2 truth uses `same line` and `follower` predicates;
- rank-3 truth uses `same line to first`, `same line to second`, and an ordered `chain` predicate.

In `keirin_synthetic_c0_c1_n1_comparison_v1.py`, N1 uses the same predicate family:
- P2 adds `same line` and `follower` terms;
- P3 adds same-line-to-first, same-line-to-second, and ordered-chain terms.

The coefficients are not identical, and N1 does not see latent skill. The Batch 3 harness also asserts that `latent_skill` is absent from PRE. Therefore this is **not evidence of RESULT/PAYOUT leakage or hidden latent-truth leakage into PRE**.

However, the simulator’s relational truth mechanism and N1’s hypothesis class are intentionally close in functional form. Therefore part of N1’s W2/W3/W4 Synthetic advantage can be expected by construction. The current evidence strongly demonstrates “N1 can exploit a relation family deliberately embedded in these synthetic worlds,” but it does not yet distinguish that from “N1 remains robust when relational dependence is present but misspecified relative to N1’s exact same-line/follower/chain basis.”

### Finding MA-2 — existing falsification strengthens mechanism use but does not close MA-1

The structure-scramble negative control is valuable: N1 worsens when the intended rider-to-structure assignment is broken, while C0 is invariant. This makes a pure numerical-noise explanation less plausible inside the simulator.

But that test still asks whether N1 uses the same structural mapping that the simulator embeds. It does not test **out-of-basis relational misspecification**.

### Finding MA-3 — topology localization also does not close MA-1

Line-shape localization shows the effect is not confined to one engineered topology motif. That is a meaningful robustness result, but all observed motifs are still evaluated under the same relation family. Topology breadth and relation-kernel breadth are different axes.

## 3. Most valuable next research question

### `Q-MISMATCH-1`

> Does N1 retain any Synthetic advantage when the world contains PRE-only relational dependence, but the truth relation kernel is deliberately not isomorphic to N1’s same-line/follower/ordered-chain kernel?

This is higher value than another seed batch because it attacks the strongest remaining construct-validity explanation for the observed N1 advantage.

### Falsification target

The desired evidence should separate three explanations:

A. `GENERIC_RELATIONAL_VALUE` — N1 is robust to relation-kernel misspecification.

B. `MATCHED_SIMULATOR_AFFINITY` — N1 helps mainly when truth uses the relation family N1 already encodes.

C. `NO_STABLE_RELATIONAL_ADVANTAGE` — apparent gains disappear or reverse under modest relational misspecification.

Any of B or C is scientifically useful and should not be “rescued” by coefficient retuning.

## 4. Prespecified experiment design candidate

Classification: `DESIGN_ONLY_RESEARCH_CANDIDATE`.

No execution is authorized by this artifact. Before execution, Fresh Read and classify whether the proposed truth-kernel variants remain inside the already-approved “ordinary W0-W4 stress/failure diagnostic” envelope. If not clearly inside, fail closed and route a separate governed scope request; do not stretch the existing authorization.

### Fixed controls

- Keep C0/C1/N1 implementation and frozen coefficients unchanged.
- No result-adaptive retuning.
- No new seed selection based on observed outcomes.
- Prefer paired evaluation on already-declared synthetic seed blocks to isolate mechanism effect; explicitly label this as diagnostic, not independent validation.
- Keep the same PRE interface and forbid latent-skill exposure.
- Keep ordered-top3 proper scoring as the primary diagnostic; no economics.
- Preserve support and unit-mass invariants.

### Candidate mismatch families

Only use a family if governance confirms it remains inside the approved W0-W4 stress envelope.

1. `RELATION_BASIS_ROTATION`: preserve relational dependence magnitude but replace the exact same/follower/chain basis with a different PRE-only relation basis not directly encoded by N1.
2. `DIRECTIONALITY_MISMATCH`: preserve line membership dependence but alter which ordered position relation carries conditional signal.
3. `SPARSITY_MISMATCH`: relational effects exist only for a prespecified subset of transitions rather than all same-line/follower/chain transitions.
4. `SIGN_ORIENTATION_COUNTEREXAMPLE`: prespecified relational dependence conflicts with N1’s hard-coded directional preference; no coefficient tuning is allowed after seeing results.

### Pass/fail interpretation

There is deliberately no “N1 must win” pass criterion.

- If N1 remains better across prespecified mismatch families without retuning: stronger Synthetic robustness evidence.
- If advantage sharply shrinks: evidence favors matched-simulator affinity.
- If N1 becomes worse: record a clean failure boundary; do not rescue-tune.
- If results vary by world: localize the boundary and stop before post-hoc slicing proliferates.

## 5. Leakage / mechanical checks to add before any broader experiment

These are source-independent and suitable for the currently authorized regression class:

1. **Car-ID permutation equivariance** — renumber riders while preserving every semantic PRE field; ordered-top3 predictions must relabel exactly, not change numerically.
2. **Line-group-ID permutation invariance** — rename line group IDs while preserving partition/membership/position; predictions and truth should be unchanged up to key relabeling.
3. **Container/order invariance** — reorder rider dictionaries/lists without changing semantic values; predictions must remain identical.
4. **PRE/latent barrier regression** — retain explicit assertion that `latent_skill` never enters PRE or model-facing objects.
5. **Truth/prediction code-path separation audit** — model prediction functions must not import/call the truth distribution except in the evaluator.
6. **No adaptive seed/condition selection** — test metadata must prove conditions were fixed before result inspection.

Failure of 1–5 is a mechanical block for interpreting later Synthetic model comparisons.

## 6. What can progress now vs what must wait

### Can progress now

- static construct-validity / mechanism-affinity audit;
- source-independent leakage/invariance test design;
- prespecified mismatch protocol design;
- portable evidence schema;
- de-dup registry for completed Synthetic questions;
- future Core integration interface design that carries only Candidate evidence and provenance.

### Must wait for separate governed scope / future gate

- real/live PRE acquisition/use;
- untouched or real-world validation;
- any protected holdout or RESULT/PAYOUT access;
- economics/bankroll/profit evaluation;
- model selection/freeze/promotion;
- external provider contact;
- any truth-kernel experiment that governance cannot clearly classify inside the already-approved W0-W4 Synthetic stress envelope.

Core Phase C is independent and must not be touched by this lane.

## 7. Portable candidate-evidence interface for future Core integration

Future Candidate evidence should minimally carry:

- `classification = Research/Candidate`;
- canonical GitHub base SHA;
- exact code/artifact blob SHAs;
- authorization receipt identity;
- experiment/question ID and prespecification hash;
- synthetic world/condition IDs;
- fixed seeds and explicit statement whether seeds are post-hoc or untouched;
- proper-scoring metrics and baseline deltas;
- invariants/mechanical checks;
- leakage checks;
- falsification outcome and known failure regions;
- no-real-world-claim marker;
- protected-boundary attestations;
- reviewer/auditor status;
- integration status default `NOT_AUTHORIZED`.

This allows future Core compatibility review without promoting Candidate evidence by accident.

## 8. Current candidate conclusion

`CANDIDATE_CONCLUSION = MECHANISM_AFFINITY_IS_A_REAL_SYNTHETIC_CONSTRUCT_VALIDITY_GAP_WORTH_FALSIFYING`

The existing evidence is stronger than a simple “N1 wins in W2” story: it includes broad stress, repeated fixed-family diagnostics, structure-scramble sensitivity, and topology localization. At the same time, the Digital Twin truth and N1 share the same relational predicate family, so further same-family positive results have diminishing informational value.

The next high-value research is therefore not a new model and not more seed count. It is a prespecified mechanism-mismatch falsification plus low-level invariance/leakage regression, with no retuning and no promotion.

END
