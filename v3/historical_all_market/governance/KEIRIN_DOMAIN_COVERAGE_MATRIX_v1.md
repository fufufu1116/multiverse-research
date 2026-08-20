# KEIRIN DOMAIN COVERAGE MATRIX v1

Status: WORKING DOMAIN AUDIT — NOT MODEL PROMOTION / NOT REAL-EDGE EVIDENCE  
Date: 2026-08-20 JST

## Purpose

Prevent a failure mode where Multiverse/ChatGPT conceptually "knows" keirin terms but the actual repository schema, simulator, model features, and tests do not represent them.

Required ladder for each domain concept:

`KNOWN_DOMAIN_CONCEPT -> SCHEMA_REPRESENTED -> MODEL_FEATURE_AVAILABLE -> DIGITAL_TWIN_SUPPORTED -> TEST_COVERED -> REAL_WORLD_EVIDENCE_VERIFIED`

A concept is not considered implemented merely because an AI can explain it.

## Evidence classes

- `FORMAL_RULE_OR_PROGRAM`: official competition rule, official program, or official program-format material.
- `OFFICIAL_GUIDE`: KEIRIN.JP official explanatory guide/glossary; confirms the concept is part of the domain but is not automatically a causal-effect estimate.
- `OFFICIAL_PRE_FIELD`: official racecard/PRE field semantics.
- `SCOPED_REALITY_ANCHOR`: a narrowly defined real-world observation with explicit selection/scope.
- `HYPOTHESIS_ONLY`: plausible tactical/empirical proposition not yet verified as a general real-world effect.

## Status legend

- `YES`: explicit current support.
- `PARTIAL`: representable or indirectly covered, but important semantics/support are missing.
- `NO`: not currently supported.
- `N/A`: not applicable to that layer.
- `UNKNOWN`: not yet audited sufficiently.

## Primary official source set used in v1

1. KEIRIN.JP official line guide: https://keirin.jp/pc/static/beginner/basics/lines.html
2. KEIRIN.JP official racecard guide: https://www.keirin.jp/pc/static/beginner/basics/racecard.html
3. KEIRIN.JP official race-flow guide: https://keirin.jp/pc/static/beginner/basics/phases.html
4. KEIRIN.JP official rules guide: https://www.keirin.jp/pc/static/beginner/basics/rules.html
5. KEIRIN.JP official 2026 program materials: https://www.keirin.jp/pc/dfw/portal/guest/data/prize/2026/2026.html
6. KEIRIN.JP glossary for fixed-pacer regimes: https://keirin.jp/pc/static/beginner/keirin-glossary/sa-so.html
7. KEIRIN.JP KEIRIN ADVANCE / international fixed-pacer notices (2025-2026).

## Current repository anchors audited

- `v3/historical_all_market/new_lineage/PRE_INTERFACE_SCHEMA_DRAFT_v1.json`
- `v3/historical_all_market/new_lineage/validate_pre_structure_v1.py`
- `v3/historical_all_market/new_lineage/digital_twin_v1.py`
- `v3/historical_all_market/new_lineage/digital_twin_stress_grid_v1.py`
- `v3/historical_all_market/new_lineage/balanced_synthetic_sampler_v1.py`
- `v3/historical_all_market/new_lineage/balanced_synthetic_fit_cal_v1.py`
- `v3/historical_all_market/new_lineage/synthetic_selftest_v1.py`

## Coverage matrix

| Domain concept | Evidence class | Known | Schema | Model feature | Digital Twin | Test | Real evidence | Unresolved gap / action |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Standard original-line keirin regime | FORMAL_RULE_OR_PROGRAM + OFFICIAL_GUIDE | YES | YES | YES | YES | PARTIAL | YES (existence/semantics) | Keep as explicit regime; do not assume all keirin shares same regime. |
| International fixed-pacer regime / KEIRIN ADVANCE | FORMAL_RULE_OR_PROGRAM | YES | YES (`INTERNATIONAL_FIXED_PACER`) | NO for line-dependent families; fail-closed boundary exists | NO | PARTIAL (routing boundary only) | YES (existence/rule distinction) | Material domain gap if these races enter scope: requires separate simulator/model family, not line-model reuse. |
| Girls/L-class international-style regime | FORMAL_RULE_OR_PROGRAM | YES | PARTIAL via regime enum, no sex/class-specific regime object | NO | NO | NO | YES (existence/rule family) | Explicit applicability boundary needed before claiming whole-keirin coverage. |
| Standard 7-rider ordinary FI/FII formats | FORMAL_RULE_OR_PROGRAM | YES | PARTIAL (active rider list; no dedicated field-size enum in PRE schema) | YES | YES | YES | YES | Current 7-rider support is strong structurally. |
| Designated 9-rider formats | FORMAL_RULE_OR_PROGRAM | YES | PARTIAL | PARTIAL | YES (`SPECIAL_9`) | YES basic format invariant | YES | 9-rider line-shape support is incomplete; current generator max line size 3. |
| Other/special program structures (GP/GI/GII/GIII/rookie/etc.) | FORMAL_RULE_OR_PROGRAM | YES | PARTIAL (`UNKNOWN_OR_OTHER` fallback) | NO generic program-structure feature | PARTIAL/NO | NO | YES (existence) | Audit program-specific field sizes, advancement rules, and applicability before extending model claims. |
| 2-line / 3-line / 4-line original-keirin structures | OFFICIAL_GUIDE | YES | YES (`num_lines`, group IDs) | YES generic line context | PARTIAL | PARTIAL | YES (concept/examples) | Generator coverage is narrow and does not span official long-line examples. |
| 2-rider / 3-rider lines | OFFICIAL_GUIDE | YES | YES | YES | YES | YES in current 7-rider motifs | YES (concept) | Real frequency/effect unmeasured. |
| 4-rider lines | OFFICIAL_GUIDE | YES | YES (`line_size` arbitrary positive integer structurally) | PARTIAL | NO in repository-supported generator | NO | YES (official guide gives 4-person line example) | **MATERIAL COVERAGE GAP** for future line-model comparison. See Issue #5. |
| 5-rider line / long-line support | OFFICIAL_GUIDE | YES | YES structurally | PARTIAL | NO | NO | YES (official guide gives 5-4 example) | Add only as support/stress, not as assumed advantage/frequency. |
| Singleton / solo rider | OFFICIAL_GUIDE + schema semantics | YES | YES (`is_singleton`) | YES | YES | YES | YES (concept) | Real frequency/effect unmeasured. |
| Line head / self-powered front | OFFICIAL_GUIDE | YES | YES (`line_position=0`) | YES | YES | PARTIAL | YES (role semantics) | Leader-ability x line-length effects remain hypothesis/stress parameters. |
| Second wheel / 番手 | OFFICIAL_GUIDE | YES | YES (`line_position=1`) | PARTIAL generic positional basis | PARTIAL | PARTIAL | YES (official role semantics) | Block, spacing, contest-for-position are not explicit model states. |
| Third wheel | OFFICIAL_GUIDE/inferred from line ordering | YES | YES (`line_position=2`) | PARTIAL | YES when generated | PARTIAL | YES for line ordering, not causal effect | Position-specific real effect unverified. |
| Fourth wheel and deeper positions | OFFICIAL_GUIDE long-line examples | YES | YES structurally | PARTIAL; C1 current position basis falls to 0 after position 2 | NO in generator | NO | YES (long lines exist) | **MATERIAL COVERAGE GAP** before claiming line-position robustness. |
| 番手ブロック / defensive support | OFFICIAL_GUIDE | YES | NO explicit action/state | NO explicit feature | NO | NO | YES (concept) | Represent as optional transition/action hypothesis if needed; do not hard-code benefit. |
| 車間をあける | OFFICIAL_GUIDE | YES | NO | NO | NO | NO | YES (concept) | Missing tactical state/action. |
| 切替 (switching to another line after being passed) | OFFICIAL_GUIDE | YES | NO transition object | NO | NO | NO | YES (concept) | **MATERIAL DYNAMIC-TOPOLOGY GAP** for race-evolution modeling. |
| 番手競り / contest for position | OFFICIAL_GUIDE | YES | NO | NO | NO | NO | YES (concept) | **MATERIAL GAP** if race-state interactions are modeled. Must not infer winner/effect without evidence. |
| 追走 / mark behavior | OFFICIAL_PRE_FIELD + OFFICIAL_GUIDE | YES | PARTIAL (`mark` historical PRE count; line structure) | YES historical count | YES as synthetic tactical variable | PARTIAL | YES semantics | Historical count is not the same as an explicit in-race追走 state. |
| 付け直し / reattachment | HYPOTHESIS/terminology not yet fully source-audited in v1 | PARTIAL | NO | NO | NO | NO | UNKNOWN | Do not promote as official-fact row until exact admissible source semantics are located. |
| Line collapse / split topology | Tactical domain concept; partly implied by official switching/line battle | YES conceptually | NO explicit transition | NO explicit topology state | PARTIAL only via W3 shock/no-line mixture | PARTIAL as generic disruption, not topology | PARTIAL | **MATERIAL GAP**: current W3 is not a literal line split/switch transition. |
| 逃 / 両 / 追 style | OFFICIAL_PRE_FIELD | YES | YES (`style`) | YES | YES | PARTIAL | YES semantics | Distribution by band/position remains unmeasured. |
| 逃・捲・差・マ counts | OFFICIAL_PRE_FIELD | YES | YES | YES | YES synthetic | PARTIAL | YES semantics; real distribution not yet calibrated | Counts are historical PRE statistics, not causal tactic labels for the upcoming race. |
| H / B / S PRE counts | OFFICIAL_PRE_FIELD | YES | YES | YES candidate fields | YES synthetic | PARTIAL | YES semantics | Real distributions and predictive increment remain unverified. |
| Competition score / 競走得点 | OFFICIAL_PRE_FIELD | YES | YES (`score`) | YES core feature | YES | YES basic use | YES semantics | Score calibration / temporal semantics must remain point-in-time. |
| S / A1-A2 / A3 class structure | FORMAL_RULE_OR_PROGRAM + OFFICIAL_PRE_FIELD | YES | YES (`class`, race band concept) | YES | YES | YES balanced synthetic strata | YES existence/semantics | **Hypotheses such as 'A3 follows lines more' or 'S is more chaotic' remain UNVERIFIED.** |
| Race-band x line-shape interaction | HYPOTHESIS_ONLY | YES as testable hypothesis | YES | PARTIAL | PARTIAL | YES only for current 3 line shapes | NO general real effect evidence | Extend support after domain coverage; do not hard-code band-specific tactical rules. |
| Bank circumference 333/335/400/500 | FORMAL/official bank data + scoped anchor | YES | YES (`bank_length_m`) | YES | PARTIAL: current DT uses 333/400/500 and omits 335 | PARTIAL | YES domain and scoped schedule anchor | Add 335 as explicit support or explicit equivalence rule; do not silently collapse 335 into 333. |
| Home straight / bank cant | Official venue/bank data candidate | YES | YES candidate fields | NO current model use | NO | NO | PARTIAL | Candidate context only until calibrated and admissible source path is fixed. |
| Wind speed | OFFICIAL_GUIDE qualitative + context source candidate | YES | YES | YES | YES | YES stress ranges | YES qualitative relevance; real effect size unverified | Keep effect sign/magnitude as assumption range until measured. |
| Wind direction | Context candidate | YES | YES | NO/limited | NO explicit directional geometry | NO | PARTIAL | Missing direction x bank geometry mechanics. |
| Weather / temperature | Context candidate | YES | YES | NO current core | NO | NO | PARTIAL | Do not add merely because available; require measurable hypothesis. |
| Registration geography / local affiliation in line formation | OFFICIAL_GUIDE | YES | NO explicit geography relationship feature in current PRE draft beyond source-dependent identity possibilities | NO | NO | NO | YES qualitative line-formation guidance | Candidate explanatory/context feature, but requires PRE provenance and leakage audit. |
| Selected pre-race line observation / leg-show lineup | OFFICIAL_GUIDE + schema design | YES | YES (`LEGSHOW_OBSERVED_LINE` / `PRE_EVENT_EXPECTED_LINE`) | YES line models can consume grouping | PARTIAL synthetic | PARTIAL validator | YES concept; availability path still under Batch 2 audit | Must distinguish forecast/observed PRE lineup from post-race executed truth. |
| Pacer / leader-retirement timing and fixed-pacer rules | FORMAL_RULE | YES | PARTIAL regime only | NO | NO | NO | YES | Important regime-specific mechanics missing from simulator. |
| Interference / prohibited maneuvers / disqualification | FORMAL_RULE / OFFICIAL_RULE_GUIDE | YES | NO explicit race-state/legal-state object | NO | NO | NO | YES rule existence | Scope decision required: prediction model may need pre-race risk features, simulator may need outcome-state handling, but never invent rates. |
| Re-start / invalid start conditions | FORMAL_RULE / OFFICIAL_RULE_GUIDE | YES | NO | NO | NO | NO | YES | Operational race-state gap; may be irrelevant for first PRE probability model but must be explicit applicability boundary. |
| Scratch/withdrawal/active-field changes | Operational domain requirement | YES | PARTIAL (`active` rider flag) | PARTIAL | PARTIAL via custom active set only | PARTIAL | YES general event reality | Need decision-time freeze semantics and probability object re-normalization tests after field changes. |
| Program progression (予選/準決/決勝/特選 etc.) | FORMAL_PROGRAM | YES | NO dedicated race-stage field in current PRE schema | NO | NO | NO | YES | Could affect field composition/regime; add only if predictive hypothesis and PRE provenance justify it. |
| "番手は有利" | HYPOTHESIS_ONLY (official guide says role is important, not a universal numeric advantage) | YES as hypothesis | Representable | PARTIAL | Assumption-coded positional bonus exists | Stressable | NO universal causal proof | Never hard-code as fact. Test positive/neutral/adverse worlds. |
| "4車ラインは強い" | HYPOTHESIS_ONLY | YES as hypothesis | Representable | PARTIAL | NO support today | NO | NO | Never hard-code. First close support gap, then test sign-neutral ranges. |
| "A3はライン通り決まりやすい" | HYPOTHESIS_ONLY | YES as hypothesis | Representable | PARTIAL | PARTIAL | NO direct test | NO | Treat as empirical question only. |
| "S級は荒れやすい" | HYPOTHESIS_ONLY | YES as hypothesis | Representable | PARTIAL | PARTIAL heavy-tail world not band-calibrated | NO band-specific real test | NO | Treat as empirical question only. |
| "強い単騎はライン崩壊時に有利" | HYPOTHESIS_ONLY | YES as hypothesis | Representable only with future transition state | NO | NO explicit topology transition | NO | NO | Do not encode until explicit state/support and preregistered test exist. |

## Major v1 findings

### RED-1 — Dynamic line topology is underrepresented

Schema/model mostly treat a line as a static PRE grouping. Official KEIRIN.JP material explicitly includes switching (`切り替え`) and contesting the position behind a strong leader (`競り`). Current W3 is a probabilistic mixture of stable-line truth and shocked/no-line utilities; it is **not** an explicit topology transition.

Minimum correction before any model claims dynamic line robustness:
- introduce a separate synthetic transition representation (not necessarily a production PRE feature);
- support at least intact -> tail split, intact -> switch, intact -> leader isolation, and position contest stress motifs;
- use assumption ranges with positive/neutral/adverse consequences, never a claimed-real transition rate.

### RED-2 — Long-line support is materially incomplete

Official KEIRIN.JP line guide gives examples including `4-3-2` and `5-4`, proving >3-rider lines are domain-real concepts. Current generator produces no line larger than 3. C1 has explicit position basis only for positions 0/1/2.

Minimum correction:
- close synthetic support first (Issue #5);
- add long-line position invariants/tests;
- do not reuse consumed PR #3 holdout for rescue tuning;
- if architecture comparison resumes, use a new preregistered experiment and fresh worlds.

### RED-3 — Race-regime separation exists in schema but not in simulator breadth

The schema correctly distinguishes `STANDARD_ORIGINAL_LINE_KEIRIN` from `INTERNATIONAL_FIXED_PACER`, and validators can fail closed for line-dependent models. This is good. However, Multiverse does not yet simulate/model the international fixed-pacer regime as a first-class family.

Minimum correction:
- maintain fail-closed routing;
- do not claim whole-keirin coverage from original-line results;
- create a separate regime family only when that domain enters active scope.

### AMBER-1 — Official PRE fields are represented better than their real distributions are calibrated

Class/style/score/H/B/S/逃捲差マ are mostly represented, but real distributions, band interactions, and incremental predictive value are largely unmeasured. PR #4 is correctly addressing public PRE-only calibration without opening result/payout evidence.

### AMBER-2 — Bank support omits 335m as an explicit simulator category

The current PRE schema can hold any numeric bank length, but `digital_twin_v1.py` samples only 333/400/500. The project already has official evidence that 335m exists. This is a support gap, not evidence that 335 differs materially from 333.

### GREEN-1 — Provenance/fail-closed PRE design is strong

`PRE_INTERFACE_SCHEMA_DRAFT_v1` and `validate_pre_structure_v1.py` explicitly separate decision timestamps, race regimes, line snapshot provenance, active riders, and post-race reconstruction prohibition. This is a strong foundation for later domain expansion.

## Architecture order after this audit

1. `DOMAIN REPRESENTATION / COVERAGE`
2. `PROBABILITY MODEL + CALIBRATION`
3. `PRICE ADAPTER` (synthetic / manual real decision-time / optional automated real)
4. `EV / BUY-NO-BET DECISION`
5. `VIRTUAL BANKROLL / FLAT100`
6. only later, if independently justified, advanced sizing/portfolio methods

Manual decision-time odds fallback remains valid as a downstream adapter candidate (Issue #6), but it must not compensate for upstream domain-model omissions.

## Scientific firewall

Unchanged:
- no real-money wagering;
- `ECON_HOLDOUT1000 = SEALED`;
- no DEV2000 C rescue;
- no same-lineage B/C rescue tuning;
- no RESULT/PAYOUT access;
- no untouched real validation opening;
- synthetic scenarios are support/stress evidence, not real frequencies or causal truth.

## Next audit actions

1. Lab review this matrix for missing major keirin concepts and false positives.
2. Keep PR #4 PRE sample unchanged; do not alter the preregistered sample because of this audit.
3. Queue only material support gaps as separate work items.
4. Do not implement hypotheses as facts; require preregistered sign-neutral stress or real evidence.
