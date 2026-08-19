# Multiverse — Keirin Structure Feature Candidate Audit v1

Status: OUTCOME-AGNOSTIC DESIGN AUDIT — NOT A SCIENTIFIC FREEZE / NOT EXECUTABLE
Date: 2026-08-19 JST
Scope: audit whether general keirin structural features are explicitly present in the current PRE model/rules, and classify missing concepts without using any individual race result as design evidence.

## Hard firewall

This audit does NOT use the result of any individual race as feature-selection evidence.
It does NOT authorize refitting Candidate A/B1a, rescoring DEV2000 B/C, opening DEV2000 C, opening ECON_HOLDOUT1000, or adding a rule to the closed lineage.
Current DEV2000 C remains unscored. ECON_HOLDOUT1000 remains SEALED.

## Evidence hierarchy

Tier 1 preferred: KEIRIN.JP / JKA / official rules / official guide / official racecard semantics / official race-flow and line explanations.
Tier 2: specialist media and expert commentary for structural interpretation not fully stated in primary sources.
Tier 3: forum/SNS/commentary only for hypothesis discovery; never sufficient alone for CORE promotion.

Primary public evidence used in this audit:
- KEIRIN.JP `ラインを読む` — line composition, self-powered rider at front,追込 behind, 2/3/4-line patterns, second-position role, switching and competition for positions.
- KEIRIN.JP `出走表を見る` — style categories 逃/両/追, 決まり手, B/H/S semantics.
- KEIRIN.JP `レースの流れ` — pre-race player introduction exposes the intended line formation; race position is tactically chosen using style, wind and bank characteristics.
- KEIRIN.JP glossary — 単騎 = no line and runs alone; 並び = order within a line; 番手/2番手/3番手 definitions; B as an indicator of prior leading behavior.
- KEIRIN.JP competition rules — race movement is constrained by safety/positioning rules, but declared line order is not a deterministic state trajectory.

Secondary evidence used only where marked:
- netkeirin expert explanation (former GP winner 加藤慎平) — single riders have greater freedom to choose position but also higher risk of being forced far back; front/second/third line roles differ materially.

## Current active DEV2000 model evidence

Exact verified PRE schema used by the frozen DEV2000 Prediction Lock:
`race_id, car_no, rider_id, class, style, score, S, B, win_rate, quinella_rate, trio_rate, withdrawn`.

Candidate A uses only within-race standardized:
- score
- win_rate
- quinella_rate
- trio_rate
- B
- S

B1a_RECONSTITUTED_v1 adds only:
- style one-hot (`逃`,`追`,`両`)
- class one-hot (`SS`,`S1`,`S2`,`A1`,`A2`,`A3`,`L1`)

Stage 1 then expands winner probabilities into ticket probabilities using a Plackett-Luce independence/order baseline. Stage 1 does not consume line structure, line position, line length, single-rider state, or tactical transition state.

Stage 5 current portfolio templates use consensus probability ranking and finite templates (`SINGLE`, `TOP1_PER_MARKET`, `TOP3_PER_MARKET`, `TOP5_PER_MARKET`, `BOX3`, `WHEEL1x3`, `FORMATION_2x3x4`). They do not contain a single-rider/low-popularity second-or-third-place scenario rule.

## Important registry distinction

The repository's NEXTGEN `feature_registry_v1.csv` already contains structural fields:
- `line_id`
- `line_position` (`0=head`)
- `line_size`
- `line_score_sum`
- `self_power_count`
- `nige`
- `makuri`
- `sashi`
- `mark`

These entries show the concepts exist in a design registry, but registry presence is NOT equivalent to active model implementation, parser provenance, or scientific admission. The frozen DEV2000 Prediction Lock does not consume the line fields.

## Classification definitions

`CORE_REUSABLE` = stable, general PRE structural fact with direct or near-direct official support and low researcher degrees of freedom. May enter a NEW lineage only after exact timestamp/source/provenance semantics are frozen.

`FEATURE_CANDIDATE` = PRE-only derivation or probability that is scientifically plausible but requires a predeclared formula/model and chronological validation. Not automatically admitted.

`EXPERIMENTAL` = latent tactical/dynamic construct that cannot be observed as a fixed PRE fact. Requires a separate transition/state model and stronger data support.

## Nine requested concepts

### 1. Line composition
Current active model: NOT EXPLICITLY IMPLEMENTED.
Registry: `line_id` already exists.
Classification: `CORE_REUSABLE`.
Reason: line formation is a fundamental official-described race structure and is observable before the race when properly timestamped. Must fail closed if the announced/observed formation cannot be proven before the prediction cutoff.

### 2. Line head / second / third position
Current active model: NOT EXPLICITLY IMPLEMENTED.
Registry: `line_position` already exists.
Classification: `CORE_REUSABLE`.
Reason: official guide/glossary explicitly distinguishes line front, second (`番手`) and third; these roles have different tactical functions.

Recommended canonical encoding for a new lineage:
- `line_position_index`: 0=head, 1=second, 2=third, 3+=rear
- explicit booleans: `is_line_head`, `is_bante`, `is_third`
- `is_singleton` kept separate rather than overloading head position

### 3. Line length
Current active model: NOT EXPLICITLY IMPLEMENTED.
Registry: `line_size` already exists.
Classification: `CORE_REUSABLE`.
Reason: official guide explicitly describes 2/3/4-line race patterns and examples such as 5-4, 4-3-2, 3-2-2-2. Line length is deterministic given a verified PRE formation.

### 4. Self-powered / chasing type
Current active model: PARTIALLY AND EXPLICITLY IMPLEMENTED.
Evidence: B1a uses `style` one-hot with `逃/追/両`; Candidate A uses B/S but not style.
Registry: `nige`, `makuri`, `sashi`, `mark`, `self_power_count` are present as richer candidates.
Classification: existing `style` = `CORE_REUSABLE`; richer maneuver counts = `CORE_REUSABLE` only after exact PRE source semantics are proven.

### 5. Probability of taking initiative / controlling the race
Current active model: NOT EXPLICITLY IMPLEMENTED.
Partial proxies only: Candidate A uses B and S; B1a uses style. Official racecard semantics support B/H/S and decision-method counts as tactical indicators, but no current model variable is an explicit `initiative_probability`.
Classification: `FEATURE_CANDIDATE`.

Candidate new-lineage inputs may include only PRE-proven variables such as:
- is_line_head
- style
- B/H/S
- nige/makuri counts
- line_size / line_score_sum
- count/strength of opposing self-powered line heads
- bank/weather PRE context

The mapping to an initiative probability must be trained/preregistered independently of the current individual race result.

### 6. Positioning freedom of a single rider
Current active model: NOT EXPLICITLY IMPLEMENTED.
Classification: `FEATURE_CANDIDATE`.

`is_singleton` itself can be CORE once PRE formation is verified. A numerical `position_freedom_score` is not a direct official fact and should remain a candidate. Secondary expert evidence supports the general tradeoff: a single rider can choose position more freely, but lacks line protection and can be forced to the rear.

### 7. Probability that a single rider switches/follows onto the rear of a strong line
Current active model: NOT IMPLEMENTED.
Classification: `EXPERIMENTAL`.

Reason: this is a dynamic transition event, not a fixed pre-race state. Official sources establish that switching/following another line is a real tactic and that race positioning changes, but a single-specific probability of attaching to a strong line is not directly published. It may only be represented as a probabilistic latent transition under a separately validated state model; it must not be hard-coded as a deterministic rule.

### 8. Favorite fixed first with low-popularity / single rider entering second or third
Current active model/rules: NOT EXPLICITLY IMPLEMENTED.
Current Stage 5 `WHEEL1x3` fixes the top consensus car as axis and uses the next three consensus-ranked cars as partners; it does not privilege low-popularity or single riders.
Classification: `FEATURE_CANDIDATE` at the probability/portfolio interface, NOT a CORE rider feature.

Safe generic representation for a NEW lineage is not 'always include a single longshot'. Instead compute predeclared conditional probability mass, e.g.:
- P(favorite first AND any singleton second)
- P(favorite first AND any singleton third)
- P(favorite first AND any low-market-rank runner in top3)
- market residual for those ticket subsets

Any threshold or ticket-construction rule must be frozen from independent development data before untouched validation. The current individual race result may not choose the threshold, partner count, popularity cutoff, or market.

### 9. How much in-race positioning transition can be represented using PRE only
Current active model: NOT IMPLEMENTED.
Classification: `EXPERIMENTAL`.

PRE can represent a DISTRIBUTION over plausible race states, not the realized path. A bounded phase model could use states such as:
- announced line/initial formation
- start/front-position preference
- early line ordering
- initiative/lead acquisition around bell/final-lap phase
- line survival/break
- switch/reattach
- final-back position class

But those are latent probabilities at prediction time. They must never be stored as if the actual future transition were known. Without timestamped historical state labels or a defensible proxy-label protocol, this remains experimental.

## Final audit matrix

1. line composition -> active NO / registry YES -> CORE_REUSABLE
2. line positions -> active NO / registry YES -> CORE_REUSABLE
3. line length -> active NO / registry YES -> CORE_REUSABLE
4. self-powered/chasing -> active PARTIAL YES (`style`) -> CORE_REUSABLE
5. initiative probability -> active NO, proxy-only -> FEATURE_CANDIDATE
6. single-rider positioning freedom -> active NO -> FEATURE_CANDIDATE
7. single-rider switch to strong-line rear -> active NO -> EXPERIMENTAL
8. favorite-first + low-pop/single top3 scenario -> active NO -> FEATURE_CANDIDATE / portfolio-layer hypothesis
9. PRE-only position transition model -> active NO -> EXPERIMENTAL

## Scientific conclusion

The main structural gap in the current frozen DEV2000 model is real: it models rider ability/style but is largely line-agnostic, then uses a Plackett-Luce ordering baseline that does not condition finishing-order dependence on line relationships.

That conclusion is based on code/schema inspection plus general official keirin structure, not on the outcome of an individual race.

The safest next-lineage order is:
1. admit only direct PRE structural facts first (`line_id`, `line_position`, `line_size`, `is_singleton`, existing style),
2. test whether those improve chronological probability metrics over the market baseline,
3. only then test derived initiative/solo-freedom candidates,
4. keep tactical transition models separate and experimental until adequate PRE-compatible training labels exist.

No current B/C rescue tuning is authorized.
`ECON_HOLDOUT1000 = SEALED`.
