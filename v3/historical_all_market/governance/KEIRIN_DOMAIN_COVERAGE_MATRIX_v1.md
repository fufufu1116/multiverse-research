# KEIRIN DOMAIN COVERAGE MATRIX v1

Status: WORKING DOMAIN AUDIT — LAB MATERIAL-BLOCK REMEDIATED, PENDING MICRO-RECHECK  
Date: 2026-08-20 JST

## Purpose

Prevent a failure mode where Multiverse/ChatGPT conceptually "knows" keirin terms but the actual repository schema, prediction model, simulator, synthetic truth, and tests do not represent them.

The audit must not treat these as interchangeable:

`KNOWN_DOMAIN_CONCEPT -> SCHEMA_REPRESENTED -> MODEL_CONSUMES -> DIGITAL_TWIN_REPRESENTS_OR_GENERATES -> DIGITAL_TWIN_TRUTH_USES -> TEST_COVERED -> REAL_WORLD_EVIDENCE_VERIFIED`

A concept is not implemented merely because an AI can explain it, because a PRE field exists, or because synthetic truth uses it.

## Normalized evidence classes

Only these classes are used in the matrix:

- `FORMAL_RULE_OR_PROGRAM`: official competition rule, official program, program-format, or official operating rule.
- `OFFICIAL_GUIDE`: KEIRIN.JP official explanatory guide/glossary; confirms a domain concept, not a universal causal effect.
- `OFFICIAL_PRE_FIELD`: official racecard/PRE field semantics.
- `SCOPED_REALITY_ANCHOR`: narrowly scoped real-world observation with explicit selection and claim limits.
- `ENGINEERING_DERIVATION`: Multiverse abstraction derived for representation/testing; not itself an official keirin fact.
- `HYPOTHESIS_ONLY`: empirical/tactical proposition not verified as a general real-world effect.
- `UNVERIFIED_TERM`: terminology or semantics not yet pinned to an admissible source.

## Status legend

- `YES`: explicit current support in the named layer.
- `PARTIAL`: some support exists, but important semantics or coverage are missing.
- `NO`: not currently supported in the named layer.
- `N/A`: not applicable.
- `UNKNOWN`: not audited sufficiently.

For `Model consumes`, `YES` means current C0/C1/N1 prediction code actually reads the information into prediction calculations. A field merely existing in PRE or Digital Twin does not count.

For `DT truth uses`, `YES` means the current synthetic truth mechanism changes probabilities/utilities using that concept. This is engineering truth only and never proves a real causal effect.

## Primary source set used in v1

1. KEIRIN.JP official line guide: https://keirin.jp/pc/static/beginner/basics/lines.html
2. KEIRIN.JP official racecard guide: https://www.keirin.jp/pc/static/beginner/basics/racecard.html
3. KEIRIN.JP official race-flow guide: https://keirin.jp/pc/static/beginner/basics/phases.html
4. KEIRIN.JP official rules guide: https://www.keirin.jp/pc/static/beginner/basics/rules.html
5. KEIRIN.JP official 2026 program materials: https://www.keirin.jp/pc/dfw/portal/guest/data/prize/2026/2026.html
6. KEIRIN.JP glossary / notices for fixed-pacer regimes and KEIRIN ADVANCE.
7. Additional official program/operating material identified in Lab review for race phase, tactics, midnight car-number assignment, DNF/adjudication and rider-population dimensions; exact source pins may be expanded in a later source-index revision without changing the implementation-status findings below.

## Current repository anchors audited

- `v3/historical_all_market/new_lineage/PRE_INTERFACE_SCHEMA_DRAFT_v1.json`
- `v3/historical_all_market/new_lineage/validate_pre_structure_v1.py`
- `v3/historical_all_market/new_lineage/digital_twin_v1.py`
- `v3/historical_all_market/new_lineage/digital_twin_stress_grid_v1.py`
- `v3/historical_all_market/new_lineage/balanced_synthetic_sampler_v1.py`
- `v3/historical_all_market/new_lineage/balanced_synthetic_fit_cal_v1.py`
- `v3/historical_all_market/new_lineage/synthetic_selftest_v1.py`

## Current prediction-code reality

This section is intentionally explicit because the first matrix overstated model coverage.

- `C0`: consumes rider `score` for prediction.
- `C1`: consumes `score` plus line grouping/line mean, `line_position`, and `line_size` through its current line terms.
- `N1`: consumes the C1 base plus same-line / follower / ordered-chain relationships.
- Current C0/C1/N1 prediction code does **not** consume `style`, `H/B/S`, `nige/makuri/sashi/mark`, rider `class` / `race_band`, `bank_length_m`, `wind_speed_mps`, weather, temperature, or wind direction as prediction features.
- Digital Twin may generate some of those fields and synthetic truth may use some of them. That does not change the `Model consumes` answer.

## Coverage matrix

| Domain concept | Evidence class | Known | Schema | Model consumes | DT represents / generates | DT truth uses | Test | Real evidence | Unresolved gap / action |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Standard original-line keirin regime | FORMAL_RULE_OR_PROGRAM + OFFICIAL_GUIDE | YES | YES | PARTIAL: line models assume/use line context, but `race_regime` itself is not a prediction coefficient | YES | YES through line worlds | PARTIAL | YES existence/semantics | Keep scope explicit; do not claim whole-keirin coverage. |
| International fixed-pacer / KEIRIN ADVANCE | FORMAL_RULE_OR_PROGRAM | YES | YES enum | NO | NO first-class support | NO | NO mechanical model-routing proof | YES existence/rule distinction | **Schema boundary only. Mechanical fixed-pacer -> line-model fail-closed routing is not demonstrated in audited code.** Scope-conditional gap; not a blocker while active scope is original-line only. |
| Girls/L-class international-style regime | FORMAL_RULE_OR_PROGRAM | YES | PARTIAL | NO | NO | NO | NO | YES existence/rule family | Explicit applicability boundary before whole-keirin claims. |
| Standard 7-rider ordinary FI/FII formats | FORMAL_RULE_OR_PROGRAM | YES | PARTIAL via active rider list | PARTIAL: candidate set size affects probability object, but no dedicated field-size feature | YES | YES generically | YES format invariant | YES | Structurally strong for current scope. |
| Designated 9-rider formats | FORMAL_RULE_OR_PROGRAM | YES | PARTIAL | PARTIAL via candidate set / line context | YES `SPECIAL_9` | YES generically | YES basic invariant | YES | Line-shape support incomplete; max generated line size remains 3. |
| Other/special program structures | FORMAL_RULE_OR_PROGRAM | YES | PARTIAL `UNKNOWN_OR_OTHER` fallback | NO program-specific feature | PARTIAL/NO | PARTIAL/NO | NO | YES existence | Audit before extending claims. |
| 2-line / 3-line / 4-line original-keirin structures | OFFICIAL_GUIDE | YES | YES `num_lines`, groups | PARTIAL: line groups consumed, but `num_lines` is not an explicit current coefficient | PARTIAL | YES for generated structures | PARTIAL | YES concept/examples | Generator does not cover full official support. |
| 2-rider / 3-rider lines | OFFICIAL_GUIDE | YES | YES | YES through line group/position/size relations | YES | YES | YES for current motifs | YES concept | Real frequency/effect unmeasured. |
| 4-rider lines | OFFICIAL_GUIDE | YES | YES structurally | PARTIAL: model math can receive size 4, but position 3+ is not properly stress-validated | NO generator support | NO because never generated by supported path | NO | YES official long-line example | **MATERIAL COVERAGE GAP** before line-position robustness claims. Issue #5. |
| 5-rider / longer lines | OFFICIAL_GUIDE | YES | YES structurally | PARTIAL in principle, unvalidated | NO | NO | NO | YES official long-line example | Add as support/stress only; no assumed advantage/frequency. |
| Singleton / solo rider | OFFICIAL_GUIDE + OFFICIAL_PRE_FIELD | YES | YES `is_singleton`, line size 1 | PARTIAL: singleton flag not directly consumed; line size/group structure indirectly distinguish it | YES | YES through generated line structure | YES current motifs | YES concept | Real frequency/effect unmeasured. |
| Line head / position 0 | OFFICIAL_GUIDE | YES | YES | YES C1/N1 line-position context | YES | YES synthetic positional assumptions | PARTIAL | YES role semantics | Real effect unverified. |
| 番手 / position 1 | OFFICIAL_GUIDE | YES | YES | YES C1/N1 line-position/context | YES | YES synthetic positional assumptions | PARTIAL | YES role semantics | Block/spacing/contest states not represented. |
| Third wheel / position 2 | OFFICIAL_GUIDE | YES | YES | YES C1/N1 line-position/context | YES in generated lines | YES synthetic positional assumptions | PARTIAL | YES line-order semantics | Real effect unverified. |
| Fourth wheel and deeper / position 3+ | OFFICIAL_GUIDE | YES | YES structurally | PARTIAL: C1 explicit position basis has 0/1/2 only; position 3+ falls to default 0 | NO generator support | NO supported truth coverage | NO | YES long lines exist | **MATERIAL LONG-LINE GAP.** |
| 番手ブロック | OFFICIAL_GUIDE | YES | NO explicit action/state | NO | NO | NO | NO | YES concept | Optional future action/state if mechanistic robustness enters scope; never hard-code benefit. |
| 車間をあける | OFFICIAL_GUIDE | YES | NO | NO | NO | NO | NO | YES concept | Missing action/state; scope-conditional. |
| 切替 | OFFICIAL_GUIDE | YES | NO transition object | NO | NO explicit transition | NO | NO | YES concept | **Material only if dynamic/mechanistic line robustness is claimed.** Not an unconditional blocker for a static PRE -> Top3 baseline. |
| 番手競り | OFFICIAL_GUIDE | YES | NO | NO | NO | NO | NO | YES concept | Same conditional severity as dynamic topology; do not infer effect. |
| 追走 / mark behavior | OFFICIAL_PRE_FIELD + OFFICIAL_GUIDE | YES | PARTIAL historical `mark` count + static line | NO current prediction use of `mark` count | YES synthetic field | PARTIAL synthetic tactical construction | PARTIAL field/invariant coverage | YES semantics | Historical PRE count != explicit in-race追走 state. |
| 付け直し / reattachment | UNVERIFIED_TERM | PARTIAL | NO | NO | NO | NO | NO | UNKNOWN | Keep unpromoted until exact admissible semantics are sourced. |
| Line collapse / split topology | ENGINEERING_DERIVATION | YES as engineering abstraction | NO explicit transition | NO | PARTIAL: W3 generic disruption only | PARTIAL generic shock/no-line mixture, not literal split | PARTIAL generic disruption only | N/A as literal official term | Derived abstraction from domain behaviors such as switching/contest. **Material only for dynamic/mechanistic robustness claims.** |
| 逃 / 両 / 追 style | OFFICIAL_PRE_FIELD | YES | YES | **NO current C0/C1/N1 prediction use** | YES | YES in synthetic base/style construction | PARTIAL | YES semantics | Real distribution and predictive increment unverified. |
| 逃・捲・差・マ historical PRE counts | OFFICIAL_PRE_FIELD | YES | YES | **NO current prediction use** | YES synthetic fields | PARTIAL synthetic tactical construction | PARTIAL | YES semantics | Historical PRE statistic != upcoming-race action. |
| H / B / S PRE counts | OFFICIAL_PRE_FIELD | YES | YES | **NO current prediction use** | YES | PARTIAL synthetic construction | PARTIAL | YES semantics | Real distributions/predictive increment unverified. |
| Competition score / 競走得点 | OFFICIAL_PRE_FIELD | YES | YES `score` | **YES core current feature** | YES | YES/indirect through latent-to-observed construction and model evaluation context | YES basic use | YES semantics | Preserve point-in-time semantics. |
| S / A1-A2 / A3 class structure | FORMAL_RULE_OR_PROGRAM + OFFICIAL_PRE_FIELD | YES | YES `class`; DT has `race_band` | **NO current C0/C1/N1 prediction use** | YES | YES synthetic class/base utility and balanced strata | YES engineering strata | YES existence/semantics | `A3 is more line-deterministic` / `S is more chaotic` remain hypotheses only. |
| Race-band x line-shape interaction | HYPOTHESIS_ONLY | YES as hypothesis | PARTIAL representable | NO explicit current interaction feature | PARTIAL | PARTIAL | YES only current 3 shapes as engineering strata | NO general effect evidence | Extend only after support coverage. |
| Bank circumference 333/335/400/500 | FORMAL_RULE_OR_PROGRAM + SCOPED_REALITY_ANCHOR | YES | YES `bank_length_m` | **NO current prediction use** | PARTIAL: 333/400/500, omits 335 | YES for generated banks in synthetic truth | PARTIAL | YES domain + scoped anchor | 335 is **AMBER support gap**, not material architecture blocker. Never silently equate 335 and 333. |
| Home straight / bank cant | SCOPED_REALITY_ANCHOR | YES as context candidate | YES candidate fields | NO | NO | NO | NO | PARTIAL source path | Candidate context only. |
| Wind speed | OFFICIAL_GUIDE | YES | YES | **NO current prediction use** | YES | YES synthetic truth/stress | YES stress engineering | YES qualitative relevance; real effect size unverified | Keep magnitude/sign as assumption until measured. |
| Wind direction | OFFICIAL_GUIDE | YES | YES | NO | NO explicit geometry interaction | NO | NO | PARTIAL | Missing direction x bank mechanics. |
| Weather / temperature | OFFICIAL_PRE_FIELD | YES | YES candidate fields | NO | NO | NO | NO | PARTIAL availability/semantics | Add only with measurable hypothesis. |
| Registration geography / local affiliation in line formation | OFFICIAL_GUIDE | YES | NO explicit relationship feature | NO | NO | NO | NO | YES qualitative concept | Requires PRE provenance and leakage audit before feature work. |
| Selected pre-race line observation / lineup forecast | OFFICIAL_GUIDE + OFFICIAL_PRE_FIELD | YES | YES observation type + group/position/size | **YES C1/N1 consume grouping/position/size if supplied** | PARTIAL synthetic | YES synthetic line mechanisms | PARTIAL validator | YES concept; real availability path under PR #4 | Forecast/observed PRE lineup must never become executed-line truth. |
| Race phase: 周回 / 赤板 / 打鐘 / 最終周回 | OFFICIAL_GUIDE | YES | NO explicit phase/timing state | NO | NO explicit phase state | NO | NO | YES domain semantics | **Missing domain coverage.** Required before claiming mechanistic transition timing; not required merely to produce a static PRE probability baseline. |
| Explicit tactics: 抑え先行 / つっぱり先行 / かまし先行 / 捲り / 差し・追込み | OFFICIAL_GUIDE | YES | NO explicit upcoming-race action state | NO | NO explicit action taxonomy | NO | NO | YES concept taxonomy | Distinguish from historical 逃/捲/差/マ counts and broad style labels. |
| Race distance / lap count | FORMAL_RULE_OR_PROGRAM + OFFICIAL_GUIDE | YES | NO dedicated field | NO | NO explicit mechanics | NO | NO | YES existence/variation | Add to domain schema only if needed for regime/phase/mechanistic scope. |
| Bank/regime-specific pacer withdrawal timing | FORMAL_RULE_OR_PROGRAM | YES | PARTIAL regime only; no timing field | NO | NO | NO | NO | YES rule/program semantics | Missing fixed-pacer mechanics; scope-conditional. |
| Program / car-number assignment regime | FORMAL_RULE_OR_PROGRAM | YES | PARTIAL `car_no` exists, assignment policy does not | NO current car-number effect | NO assignment mechanism | NO | NO | YES; Lab identified midnight score-ordered assignment regime | **Confounding guard:** never infer generic `car_no` effect without assignment-regime awareness. |
| Program progression: 予選 / 準決 / 決勝 / 特選 etc. | FORMAL_RULE_OR_PROGRAM | YES | NO dedicated race-stage field | NO | NO | NO | NO | YES existence | Could change field composition; add only with PRE provenance and hypothesis. |
| In-race fall / abandonment / DNF-adjudication state | FORMAL_RULE_OR_PROGRAM | YES | NO explicit in-race state | NO | NO | NO | NO | YES rule/adjudication existence | Missing outcome-state handling; relevant to full race simulator/evaluation, not automatically to first static PRE baseline. |
| Interference / prohibited maneuvers / disqualification | FORMAL_RULE_OR_PROGRAM | YES | NO explicit state | NO | NO | NO | NO | YES rule existence | Do not invent rates; scope decision required. |
| Re-start / invalid start conditions | FORMAL_RULE_OR_PROGRAM | YES | NO | NO | NO | NO | NO | YES rule existence | Explicit applicability boundary is sufficient until mechanistic simulator scope. |
| Scratch / withdrawal / active-field change before decision | FORMAL_RULE_OR_PROGRAM | YES | PARTIAL `active` rider flag | PARTIAL through active candidate set, not a dedicated effect | PARTIAL custom active set | PARTIAL | PARTIAL | YES event reality | Need decision-time freeze and probability re-normalization tests. |
| Invited / foreign-rider population dimension separate from race_regime | FORMAL_RULE_OR_PROGRAM | YES | NO explicit population/origin dimension in audited schema | NO | NO | NO | NO | PARTIAL/YES existence per Lab domain audit | Do not conflate rider population with race regime. Pin exact source semantics before feature admission. |
| `番手は有利` | HYPOTHESIS_ONLY | YES as hypothesis | Representable through position | YES position terms exist in C1/N1 context, but this does not validate benefit | YES where generated | YES synthetic assumption can encode positive effect | Stressable only in existing support | NO universal causal proof | Never hard-code as fact; future stress should include positive/neutral/adverse sign. |
| `4車ラインは強い` | HYPOTHESIS_ONLY | YES as hypothesis | Representable | PARTIAL in principle | NO current support | NO | NO | NO | First close support gap, then sign-neutral stress. |
| `A3はライン通り決まりやすい` | HYPOTHESIS_ONLY | YES as hypothesis | Representable | NO current band interaction feature | PARTIAL | PARTIAL synthetic world could be extended | NO direct test | NO | Empirical question only. |
| `S級は荒れやすい` | HYPOTHESIS_ONLY | YES as hypothesis | Representable | NO current band-specific chaos feature | PARTIAL | PARTIAL generic heavy-tail not band-calibrated | NO direct test | NO | Empirical question only. |
| `強い単騎はライン崩壊時に有利` | HYPOTHESIS_ONLY | YES as hypothesis | PARTIAL only with future transition state | NO | NO explicit topology transition | NO | NO | NO | Do not encode until explicit state/support and preregistered test exist. |

## Major v1 findings after Lab remediation

### RED-1 — Long-line / position-3+ support is materially incomplete

Official domain material includes long-line structures, while the current repository-supported generator produces no line larger than 3. C1 has an explicit position basis only for positions 0/1/2.

Minimum correction before future line-model robustness or architecture-comparison claims:
- close synthetic support first under Issue #5;
- add position-3+ invariants/tests;
- do not reuse consumed PR #3 holdout for rescue tuning;
- any renewed architecture ranking uses a new preregistered experiment and fresh worlds.

### CONDITIONAL-RED — Dynamic topology / timing is missing for mechanistic claims

Switching and position contest are official domain concepts, and the Lab also identified race-phase/timing as missing. Current W3 is not a literal topology transition.

This is **not an unconditional blocker** for a static PRE -> final Top3 probability baseline. It becomes material if Multiverse claims dynamic-line robustness, transition mechanics, or phase-specific causal behavior.

Minimum correction before such claims:
- add explicit phase/timing representation for synthetic transition research;
- add sign-neutral transition motifs such as intact -> tail split / switch / isolation / contest;
- do not present synthetic transition rates as real frequencies.

### SCOPE-CONDITIONAL — Fixed-pacer breadth and routing

The schema distinguishes `INTERNATIONAL_FIXED_PACER`, but the audited validator does not itself prove that C1/N1 invocation is mechanically rejected or rerouted. The prior matrix overstated this.

Current requirement:
- original-line-only research may proceed with an explicit applicability boundary;
- do not claim whole-keirin coverage;
- before fixed-pacer races enter model scope, implement and test a mechanical routing guard or separate model family.

### AMBER-1 — PRE-field representation exceeds current prediction-feature use

The repository represents many official PRE/context fields, but current C0/C1/N1 prediction features are narrower. In particular style, H/B/S, 逃捲差マ counts, class/race band, bank and wind are not currently consumed by the prediction code.

This is not a demand to add all fields. Feature admission remains hypothesis-, provenance-, leakage-, and evidence-gated.

### AMBER-2 — 335m simulator support

335m is a real bank-domain value, but current Digital Twin generation uses 333/400/500. This is a real support gap, but currently AMBER rather than a material architecture blocker. Never silently collapse 335 into 333 without an explicit rule/evidence basis.

### DOMAIN-CONFOUNDING WARNING — car-number assignment regime

`car_no` must not be treated as a universal causal feature without program context. Lab identified an official midnight regime where car numbers are assigned in score order. Any future `car_no` effect could therefore be structurally confounded by assignment policy.

## Architecture order

1. `DOMAIN REPRESENTATION / COVERAGE`
2. `PROBABILITY MODEL + CALIBRATION`
3. `PRICE ADAPTER` — synthetic / manual real decision-time / optional automated real
4. `EV / BUY-NO-BET DECISION`
5. `VIRTUAL BANKROLL / FLAT100`
6. only later, if independently justified, advanced sizing/portfolio methods

Manual Decision-Time Odds Fallback (Issue #6) remains a valid downstream architecture candidate, but it must never mask an upstream domain-coverage gap.

## PR #4 independence

PR #7 does not change PR #4 sampling. The Lab explicitly found that PR #4 may remain unchanged by this domain audit. PR #4 still follows its own independent Lab gate.

## Scientific firewall

Unchanged:
- no real-money wagering;
- `ECON_HOLDOUT1000 = SEALED`;
- no DEV2000 C rescue;
- no same-lineage B/C rescue tuning;
- no RESULT/PAYOUT access;
- no untouched real validation opening;
- synthetic scenarios are support/stress evidence, not real frequencies or causal truth.

## Acceptance boundary for this audit document

This matrix is an inventory and gap-classification artifact. Acceptance of the matrix does **not** mean every listed gap must be implemented before any research continues.

A gap becomes a blocker only when the project is about to make a claim that requires that capability. The exception is a direct support gap that would invalidate the immediate experiment, such as long-line robustness being claimed without long-line support.

Next exact action: Lab micro-recheck the remediated matrix for (1) model-feature accuracy, (2) evidence-class normalization, (3) newly added missing concepts, and (4) corrected conditional severities.