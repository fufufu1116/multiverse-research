# KEIRIN DOMAIN COVERAGE MATRIX v1

Status: WORKING DOMAIN AUDIT — MATERIAL BLOCK CLOSED; FINAL MICRO-RECHECK PENDING  
Date: 2026-08-20 JST

## Purpose

Prevent a failure mode where Multiverse/ChatGPT conceptually knows keirin terms but the repository schema, current prediction model, Digital Twin generation, synthetic-truth mechanism, and tests do not actually support them.

Audit ladder:

`KNOWN_DOMAIN_CONCEPT -> SCHEMA_REPRESENTED -> MODEL_CONSUMES -> DIGITAL_TWIN_REPRESENTS_OR_GENERATES -> DIGITAL_TWIN_TRUTH_USES -> TEST_COVERED -> REAL_WORLD_EVIDENCE_VERIFIED`

These layers are not interchangeable.

## Evidence classes

- `FORMAL_RULE_OR_PROGRAM`: official competition/program/operating rule.
- `OFFICIAL_GUIDE`: KEIRIN.JP official guide, glossary, venue guide, or official explanatory material.
- `OFFICIAL_PRE_FIELD`: official pre-race/racecard field semantics.
- `SCOPED_REALITY_ANCHOR`: narrowly scoped real-world observation with explicit selection and claim limits.
- `ENGINEERING_DERIVATION`: Multiverse abstraction for representation/testing, not an official keirin fact.
- `HYPOTHESIS_ONLY`: empirical/tactical proposition not verified as a general real-world effect.
- `UNVERIFIED_TERM`: semantics/source not yet pinned sufficiently.

## Layer semantics

- `Model consumes = YES` only when current C0/C1/N1 prediction code actually reads the concept into prediction calculations.
- `DT represents/generates = YES` means the current Digital Twin can represent or generate the concept/field.
- `DT truth uses = YES` only when the synthetic truth mechanism actually changes utility/probability using the concept. A generated field alone does not count.
- Synthetic truth is engineering evidence only and never real causal truth.

## Primary official sources pinned

1. Lines: https://keirin.jp/pc/static/beginner/basics/lines.html
2. Racecard/PRE semantics: https://www.keirin.jp/pc/static/beginner/basics/racecard.html
3. Race flow/phases: https://keirin.jp/pc/static/beginner/basics/phases.html
4. Rules: https://www.keirin.jp/pc/static/beginner/basics/rules.html
5. 2026 program materials: https://www.keirin.jp/pc/dfw/portal/guest/data/prize/2026/2026.html
6. Glossary / fixed-pacer / KEIRIN ADVANCE official material.
7. Venue/bank geometry source: https://www.keirin.jp/pc/jyoguide (official venue guide / bank basic data, including straight distance and bank cant fields).
8. Official KEIRIN.JP analysis material treats weather/wind as race-context variables, but an exact public decision-time PRE weather/temperature source is not yet pinned; therefore weather/temperature are **not** classified as verified official PRE fields here.

## Current repository anchors audited

- `v3/historical_all_market/new_lineage/PRE_INTERFACE_SCHEMA_DRAFT_v1.json`
- `v3/historical_all_market/new_lineage/validate_pre_structure_v1.py`
- `v3/historical_all_market/new_lineage/digital_twin_v1.py`
- `v3/historical_all_market/new_lineage/digital_twin_stress_grid_v1.py`
- `v3/historical_all_market/new_lineage/balanced_synthetic_sampler_v1.py`
- `v3/historical_all_market/new_lineage/balanced_synthetic_fit_cal_v1.py`
- `v3/historical_all_market/new_lineage/synthetic_selftest_v1.py`

## Current prediction-code reality

- C0 consumes rider `score`.
- C1 consumes `score` plus line grouping/line mean, `line_position`, and `line_size` terms.
- N1 consumes the C1 base plus same-line / follower / ordered-chain relations.
- Current C0/C1/N1 do **not** consume style, H/B/S, nige/makuri/sashi/mark historical counts, rider class/race-band, bank length, wind, weather, temperature, or wind direction as prediction features.

## Coverage matrix

| Domain concept | Evidence class | Known | Schema | Model consumes | DT represents / generates | DT truth uses | Test | Real evidence | Gap / action |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Standard original-line keirin | FORMAL_RULE_OR_PROGRAM + OFFICIAL_GUIDE | YES | YES | PARTIAL via line context | YES | YES line worlds | PARTIAL | YES semantics | Keep explicit scope. |
| International fixed-pacer / KEIRIN ADVANCE | FORMAL_RULE_OR_PROGRAM | YES | YES enum | NO | NO first-class family | NO | NO mechanical routing proof | YES | Schema separation only; fixed-pacer -> line-model fail-closed routing not demonstrated. Scope-conditional. |
| Girls/L-class international-style regime | FORMAL_RULE_OR_PROGRAM | YES | PARTIAL | NO | NO | NO | NO | YES | Explicit applicability boundary before whole-keirin claims. |
| Standard 7-rider FI/FII | FORMAL_RULE_OR_PROGRAM | YES | PARTIAL active list | PARTIAL candidate-set effect only | YES | YES generically | YES format invariant | YES | Structurally supported. |
| Designated 9-rider formats | FORMAL_RULE_OR_PROGRAM | YES | PARTIAL | PARTIAL | YES `SPECIAL_9` | YES generically | YES basic | YES | Long-line support still incomplete. |
| Other/special program structures | FORMAL_RULE_OR_PROGRAM | YES | PARTIAL fallback | NO program-specific feature | PARTIAL/NO | PARTIAL/NO | NO | YES existence | Audit before scope expansion. |
| 2/3/4-line structures | OFFICIAL_GUIDE | YES | YES | PARTIAL line groups consumed | PARTIAL | YES only when generated | PARTIAL | YES examples | Generator support narrower than domain. |
| 2-rider / 3-rider lines | OFFICIAL_GUIDE | YES | YES | YES line relations | YES | YES | YES current motifs | YES | Real frequency/effect unmeasured. |
| 4-rider lines | OFFICIAL_GUIDE | YES | YES structurally | PARTIAL, unvalidated position 3+ | NO supported generator | NO supported path | NO | YES | **MATERIAL** before long-line robustness claims. Issue #5. |
| 5-rider / longer lines | OFFICIAL_GUIDE | YES | YES structurally | PARTIAL in principle | NO | NO | NO | YES | Add only as sign-neutral support/stress. |
| Singleton / solo | OFFICIAL_GUIDE | YES | YES | PARTIAL indirectly via line structure | YES | YES line structure | YES motifs | YES | Effect unmeasured. |
| Line head / position 0 | OFFICIAL_GUIDE | YES | YES | YES | YES | YES synthetic positional assumption | PARTIAL | YES role semantics | Real effect unverified. |
| 番手 / position 1 | OFFICIAL_GUIDE | YES | YES | YES | YES | YES synthetic positional assumption | PARTIAL | YES | Block/contest states absent. |
| Third wheel / position 2 | OFFICIAL_GUIDE | YES | YES | YES | YES | YES synthetic positional assumption | PARTIAL | YES | Real effect unverified. |
| Fourth wheel+ / position 3+ | OFFICIAL_GUIDE | YES | YES structurally | PARTIAL; C1 position basis defaults after 2 | NO | NO supported truth coverage | NO | YES | **MATERIAL LONG-LINE GAP.** |
| 番手ブロック | OFFICIAL_GUIDE | YES | NO explicit state | NO | NO | NO | NO | YES concept | Conditional on mechanistic scope. |
| 車間をあける | OFFICIAL_GUIDE | YES | NO | NO | NO | NO | NO | YES concept | Conditional on mechanistic scope. |
| 切替 | OFFICIAL_GUIDE | YES | NO transition | NO | NO explicit transition | NO | NO | YES | Conditional-material for dynamic/mechanistic claims; not static PRE baseline blocker. |
| 番手競り | OFFICIAL_GUIDE | YES | NO | NO | NO | NO | NO | YES | Same conditional severity. |
| 追走 / mark behavior | OFFICIAL_PRE_FIELD + OFFICIAL_GUIDE | YES | PARTIAL historical `mark` + static line | **NO** | YES synthetic field | **NO** | PARTIAL field/invariant | YES semantics | Historical mark count != explicit in-race pursuit state. |
| 付け直し | UNVERIFIED_TERM | PARTIAL | NO | NO | NO | NO | NO | UNKNOWN | Do not promote until exact admissible semantics are pinned. |
| Line collapse / split topology | ENGINEERING_DERIVATION | YES as engineering abstraction | NO transition | NO | PARTIAL W3 generic disruption | PARTIAL generic shock only | PARTIAL generic | N/A literal term | Conditional-material only for dynamic claims. |
| 逃 / 両 / 追 style | OFFICIAL_PRE_FIELD | YES | YES | **NO** | YES | YES synthetic base/style truth | PARTIAL | YES semantics | Distribution/predictive increment unverified. |
| 逃・捲・差・マ historical PRE counts | OFFICIAL_PRE_FIELD | YES | YES | **NO** | YES generated fields | **NO** | PARTIAL | YES semantics | Historical PRE statistics, not upcoming action states. |
| H / B / S PRE counts | OFFICIAL_PRE_FIELD | YES | YES | **NO** | YES generated | **NO** | PARTIAL | YES semantics | Real distributions/predictive increment unverified. |
| Competition score / 競走得点 | OFFICIAL_PRE_FIELD | YES | YES | **YES core** | YES observed field | **NO** | YES model use | YES semantics | Synthetic truth uses latent skill/class/style/etc.; observed score is not a truth-mechanism input. Preserve point-in-time semantics. |
| S / A1-A2 / A3 structure | FORMAL_RULE_OR_PROGRAM + OFFICIAL_PRE_FIELD | YES | YES | **NO current prediction use** | YES | YES synthetic class/base utility | YES engineering strata | YES | Band-specific tactical claims remain hypotheses. |
| Race-band x line-shape | HYPOTHESIS_ONLY | YES hypothesis | PARTIAL | NO explicit interaction | PARTIAL | PARTIAL | YES only current 3 shapes | NO general effect | Extend only after support coverage. |
| Bank circumference 333/335/400/500 | FORMAL_RULE_OR_PROGRAM + SCOPED_REALITY_ANCHOR | YES | YES | **NO current prediction use** | PARTIAL 333/400/500 only | YES generated banks | PARTIAL | YES domain + scoped schedule anchor | 335 omission is **AMBER**; never silently equate 335 with 333. |
| Home straight / bank cant | **OFFICIAL_GUIDE** | YES context | YES candidate fields | NO | NO | NO | NO | **YES official venue/bank geometry fields; no scoped calibration anchor claimed** | Candidate context only until calibrated. |
| Wind speed | OFFICIAL_GUIDE | YES | YES | **NO** | YES | YES synthetic truth/stress | YES engineering stress | YES qualitative relevance | Real effect size/sign unverified. |
| Wind direction | OFFICIAL_GUIDE | YES | YES | NO | NO explicit geometry interaction | NO | NO | PARTIAL | Missing direction x bank mechanics. |
| Weather / temperature | **OFFICIAL_GUIDE** | YES context | YES candidate fields | NO | NO | NO | NO | **YES as official context/analysis concept; exact decision-time PRE availability not pinned** | Do not call it an OFFICIAL_PRE_FIELD until exact PRE source is pinned. |
| Registration geography / local affiliation | OFFICIAL_GUIDE | YES | NO explicit relationship feature | NO | NO | NO | NO | YES qualitative | Requires PRE provenance/leakage audit before feature work. |
| PRE line observation / lineup forecast | OFFICIAL_GUIDE + OFFICIAL_PRE_FIELD | YES | YES | YES C1/N1 grouping if supplied | PARTIAL synthetic | YES synthetic line mechanisms | PARTIAL validator | YES concept; real path under PR #4 | Forecast/observed PRE line != executed-line truth. |
| Race phase: 周回 / 赤板 / 打鐘 / 最終周回 | OFFICIAL_GUIDE | YES | NO phase state | NO | NO | NO | NO | YES semantics | Missing; required for mechanistic transition timing, not static PRE baseline. |
| Explicit tactics: 抑え先行 / つっぱり先行 / かまし先行 / 捲り / 差し・追込み | OFFICIAL_GUIDE | YES | NO action state | NO | NO taxonomy | NO | NO | YES taxonomy | Distinguish from historical counts/style. |
| Race distance / lap count | FORMAL_RULE_OR_PROGRAM + OFFICIAL_GUIDE | YES | NO dedicated field | NO | NO mechanics | NO | NO | YES variation | Add only if regime/phase scope requires it. |
| Bank/regime-specific pacer withdrawal timing | FORMAL_RULE_OR_PROGRAM | YES | PARTIAL regime only | NO | NO | NO | NO | YES | Scope-conditional fixed-pacer gap. |
| Program / car-number assignment regime | FORMAL_RULE_OR_PROGRAM | YES | PARTIAL `car_no`, no assignment policy | NO current effect | NO assignment mechanism | NO | NO | YES | Confounding guard: never infer generic car-number effect without assignment-regime awareness. |
| Program progression: 予選 / 準決 / 決勝 / 特選 | FORMAL_RULE_OR_PROGRAM | YES | NO dedicated stage | NO | NO | NO | NO | YES | Candidate field-composition context only. |
| In-race fall / abandonment / DNF adjudication | FORMAL_RULE_OR_PROGRAM | YES | NO state | NO | NO | NO | NO | YES | Relevant to full simulator/evaluation, not necessarily first static PRE baseline. |
| Interference / prohibited maneuvers / disqualification | FORMAL_RULE_OR_PROGRAM | YES | NO state | NO | NO | NO | NO | YES | Do not invent rates. |
| Re-start / invalid start | FORMAL_RULE_OR_PROGRAM | YES | NO | NO | NO | NO | NO | YES | Applicability boundary sufficient until mechanistic scope. |
| Scratch / withdrawal / active-field change before decision | FORMAL_RULE_OR_PROGRAM | YES | PARTIAL `active` | PARTIAL active candidate set | PARTIAL custom active set | PARTIAL | PARTIAL | YES | Need decision-time freeze + renormalization tests. |
| Invited / foreign-rider population dimension | FORMAL_RULE_OR_PROGRAM | YES | NO explicit origin/population dimension | NO | NO | NO | NO | PARTIAL/YES existence | Keep separate from race regime; pin exact source semantics before feature admission. |
| `番手は有利` | HYPOTHESIS_ONLY | YES hypothesis | Representable | Position terms exist but do not validate benefit | YES where generated | Synthetic assumption can encode sign | Stressable only in current support | NO universal proof | Future stress positive/neutral/adverse. |
| `4車ラインは強い` | HYPOTHESIS_ONLY | YES hypothesis | Representable | PARTIAL in principle | NO support | NO | NO | NO | First close support gap, then sign-neutral stress. |
| `A3はライン通り決まりやすい` | HYPOTHESIS_ONLY | YES hypothesis | Representable | NO current band interaction | PARTIAL | PARTIAL extendable | NO direct | NO | Empirical question only. |
| `S級は荒れやすい` | HYPOTHESIS_ONLY | YES hypothesis | Representable | NO band-specific chaos feature | PARTIAL | PARTIAL generic heavy tail | NO direct | NO | Empirical question only. |
| `強い単騎はライン崩壊時に有利` | HYPOTHESIS_ONLY | YES hypothesis | PARTIAL future transition state | NO | NO explicit transition | NO | NO | NO | Do not encode before explicit state/support/preregistered test. |

## Major findings

### MATERIAL — long-line / position-3+ support
Current generator does not produce lines larger than 3 and current C1 explicit position basis stops at positions 0/1/2. Before any renewed claim of long-line robustness or architecture superiority, close synthetic support under Issue #5, add position-3+ invariants/tests, and use a new preregistered experiment with new fresh worlds. Consumed PR #3 holdout must not be reused for rescue tuning.

### CONDITIONAL-MATERIAL — dynamic topology / timing
Switching, position contest, and race phases are real domain concepts, but explicit transitions are not required merely to produce a static PRE -> final Top3 probability baseline. They become material if Multiverse claims mechanistic, phase-specific, or dynamic-line robustness.

### SCOPE-CONDITIONAL — fixed-pacer
The schema distinguishes fixed-pacer regimes, but audited code does not mechanically prove fixed-pacer -> line-model fail-closed routing. Original-line-only work may proceed with a strict applicability boundary; fixed-pacer model scope requires a guard or separate family first.

### AMBER — 335m
335m is domain-real and absent from current DT generation. This is a support gap, not evidence that 335 differs materially from 333.

### CONFOUNDING WARNING — car number
Midnight/program assignment rules can couple car number with score. Any future car-number feature requires assignment-regime awareness before causal or predictive interpretation.

## Architecture order

1. `DOMAIN REPRESENTATION / COVERAGE`
2. `PROBABILITY MODEL + CALIBRATION`
3. `PRICE ADAPTER` — synthetic / manual real decision-time / optional automated real
4. `EV / BUY-NO-BET`
5. `VIRTUAL BANKROLL / FLAT100`
6. only later, if independently justified, advanced sizing/portfolio methods

Manual Decision-Time Odds Fallback (Issue #6) remains a valid downstream candidate but cannot compensate for upstream domain gaps.

## PR #4 independence

This audit does not modify PR #4 sampling. PR #4 follows its own independent Lab gate.

## Scientific firewall

Unchanged:
- no real-money wagering;
- `ECON_HOLDOUT1000 = SEALED`;
- no DEV2000 C rescue;
- no same-lineage B/C rescue tuning;
- no RESULT/PAYOUT access;
- no untouched real validation opening;
- synthetic scenarios are support/stress evidence, not real frequencies or causal truth.

## Acceptance boundary

Acceptance of this matrix means the inventory/classification is sufficiently accurate. It does **not** mean every listed gap is an immediate implementation blocker. A gap blocks only a claim/experiment that requires that capability.

Next exact action: one final Lab micro-recheck limited to the six classification fixes from the prior `PASS_WITH_FIXES` result.