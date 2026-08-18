# Multiverse Hybrid v3.0 — Independent Gemini Re-Audit Package: Shadow250-v2 Candidate v1

## Audit posture

Perform a hostile, independent re-audit of the **NEW Shadow250-v2 candidate** created after the prior verdict `CONDITIONAL APPROVE` and explicit instruction:

`NEW_SHADOW_UNIVERSE_REQUIRED_BEFORE_ANY_RACE`

Do not assume ChatGPT's fixes are correct. Do not silently repair them. If you cannot inspect the exact public GitHub files and verify the stated Git blobs / candidate bindings, treat that limitation as unresolved and do not return APPROVE.

Repository: `fufufu1116/multiverse-research`
Audit snapshot commit: `db5f0aabc68b27752f40f156a81c2fa0080ebec9`

This re-audit MUST NOT access, request, infer, or score ECON_HOLDOUT1000 RESULT / PAYOUT / Price. Only already-frozen membership metadata may be referenced for collision semantics.

## Current state — must remain unchanged during audit

- predecessor Shadow250-v1 selected races: `0`
- predecessor prospective screen count: `0`
- predecessor prospective v3 scientific trial: `0`
- Shadow250-v2 status: `NOT_ACTIVE_PENDING_INDEPENDENT_GEMINI_REAUDIT`
- Shadow250-v2 selected races: `0`
- Shadow250-v2 prospective screen count: `0`
- Shadow250-v2 prospective v3 scientific trial: `0`
- global scoring: `UNAUTHORIZED`
- wagering: `UNAUTHORIZED`
- Lane-E: `UNAUTHORIZED`
- final-v3 proof: `UNAUTHORIZED`
- ECON_HOLDOUT1000: `SEALED`

No audit action itself selects a race or activates v2.

## Prior independent verdict being remediated

Prior verdict: `CONDITIONAL APPROVE`

Prior issues:

1. `ISSUE-G1-DATE-BINDING` — P1_MATERIAL
2. `ISSUE-G1-WITHDRAWN-HARDCODE` — P1_MATERIAL
3. `ISSUE-CLASS-PROGRAM-GATE-MISSING` — P0_BLOCKER
4. `ISSUE-G2-SNUM-PROVENANCE-UNBOUND` — P1_MATERIAL
5. `ISSUE-GOV-ADAPTER-HASH-REBINDING` — P1_MATERIAL / NEW universe required

Formal receipt:
`v3/prospective_shadow250_v2/governance/GEMINI_CONDITIONAL_APPROVE_RECEIPT_v1.json`

## New-universe governance candidates

### Source set candidate

File:
`v3/prospective_shadow250_v2/governance/SHADOW250_V2_SOURCE_SET_FREEZE_CANDIDATE_v1.json`

Candidate core SHA-256:
`a24dd6d4874e389cf43832a4ea98e61005595aed4924ee764318a641219431df`

Key semantics:

- Tamano official PDF remains the predictive five-field racecard source: `score, quinella_rate, S, B, class`.
- KEIRIN.JP `/pc/racerprofile` remains the predictive three-field supplement source: `style, win_rate, trio_rate`.
- New KEIRIN.JP `/pc/search` role is explicitly admitted only as `IDENTITY_LOCATOR_ONLY_ZERO_PREDICTIVE_FIELDS`.
- Locator query basis is only racecard PRE identity metadata: `prefecture + term + active_only`.
- candidate snum is untrusted routing metadata only.
- no provider fallback.
- no other source may enter.

### Selection rule candidate

File:
`v3/prospective_shadow250_v2/governance/SHADOW250_V2_SELECTION_RULE_FREEZE_CANDIDATE_v1.json`

Candidate core SHA-256:
`ea8c0a3fc956b148b0b503d25e286536d9d6b460f49eb62e5473d7b206a88e0e`

Additional gates versus predecessor include:

- internal current-PRE PDF date must equal bound `race_date`;
- current field-size / active-entry gate must PASS;
- race-program metadata + class-set compatibility must PASS;
- KEIRIN identity locator must PASS with unique four-field racerprofile verification;
- locator elapsed time <=60 seconds;
- any candidate transport / HTTP / parse ambiguity HALTS the whole race;
- source capture skew still <=120 seconds;
- no post-outcome replacement.

### Genesis candidate

File:
`v3/prospective_shadow250_v2/governance/SHADOW250_V2_GENESIS_CANDIDATE_v1.json`

Git blob at audit snapshot should correspond to the version binding:

- source-set core: `a24dd6d4874e389cf43832a4ea98e61005595aed4924ee764318a641219431df`
- selection-rule core: `ea8c0a3fc956b148b0b503d25e286536d9d6b460f49eb62e5473d7b206a88e0e`
- Tamano parser v2 Git blob: `fa6dea35c5933181f9b04610ecb698e4889b0aca`
- KEIRIN identity locator v1 Git blob: `f40d444508dbb1afacaf42d44e0b94ece33e8a47`
- prediction lock SHA-256: `2defade77042f5e2e78a68c831d4cb67330882b4d8977c6e3d9d44546988aada`
- prediction model change: `PROHIBITED`

The predecessor Shadow250-v1 is not mutated.

# Exact executable candidates to audit

## G1 — Tamano parser v2

File:
`v3/prospective_shadow250_v2/tamano_racecard_row_parser_v2.py`

Git blob:
`fa6dea35c5933181f9b04610ecb698e4889b0aca`

Required code-level checks:

1. The parser opens exactly a 2-page PDF with the predecessor frozen dimensions.
2. It reads only predecessor PRE clips:
   - page 1: `[610,0,1190.55,841.88]`
   - page 2: `[0,0,1190.55,720]`
3. Any POST sentinel inside those clips HALTS.
4. `_bind_race_date` extracts Reiwa date strings only from those PRE clips, converts Reiwa year to Gregorian using `2018 + reiwa_year`, and requires the set of internal dates to be exactly `{external race_date}`.
5. Any missing, extra, malformed, or mismatched internal date fails closed.
6. Per race, `_field_size` requires exactly one `(7車立)` marker after normalization.
7. Per race, exactly car anchors 1..7 are required.
8. Per current row, `_current_row_status` scans only the current-entry identity/core strip `x=ox+70..ox+330`, `y=cy-6..cy+15` and rejects `欠場`, `欠`, `除外`, `取消`, `欠車`.
9. `withdrawn=False` is emitted only after the above active-entry evidence plus complete-row and final cardinality gates pass.
10. `_program_label` derives a unique A/S/L program label from the same current PRE race block, using an `A級/S級/L級` token or nearest same-line A/S/L token to `級`.
11. `_validate_program_classes` allows only:
    - S: nonempty subset `{SS,S1,S2}`
    - A12: nonempty subset `{A1,A2}`
    - A3: exactly `{A3}`
    - L1: exactly `{L1}`
12. Any cross-program mixture is `PRE_INELIGIBLE_SOURCE_GAP`.
13. Predictive field ownership remains exactly the prior five fields; `race_program` and active-status basis are governance/eligibility metadata only, not predictive features.
14. OCR, derivation, and missing-field synthesis remain prohibited.

### G1 adversarial questions

A. Can any prior-day RESULT/PAYOUT token/date enter `_bind_race_date` or row parsing through the permitted clips?
B. Is requiring the *set* of Reiwa dates to equal one date safe, or can benign PRE content create a false accept? False reject is acceptable; false accept is not.
C. Is the `x=70..330` current-row status strip sufficiently tied to **current entry status** rather than prior performance/status history? If not, classify as P0/P1 and specify the exact geometry/invariant required.
D. Could a withdrawn rider remain printed with `(7車立)` and seven car anchors while the withdrawal token sits outside the guarded strip? If yes, the current fix is insufficient.
E. Is the unique program-label extraction independently anchored enough to avoid accidentally using a rider class token or adjacent race label?
F. Could program/class parsing silently accept A3+A1/A2, A+S, or L+non-L mixtures? Prove from code.
G. Does adding `race_program` metadata accidentally enter the B1a feature vector anywhere downstream? It must not.
H. Is seven-car-only behavior correctly fail-closed as source-constrained eligibility rather than silently redefining the target population?

## G2 — deterministic KEIRIN identity locator

File:
`v3/prospective_shadow250_v2/keirinjp_identity_locator_v1.py`

Git blob:
`f40d444508dbb1afacaf42d44e0b94ece33e8a47`

Required code-level checks:

1. Initial source is only `https://keirin.jp/pc/search`.
2. Same-origin HTTPS is mandatory; redirects rejected.
3. 403/429 is persistent halt / no retry.
4. Search form is identified only if one form contains all expected official player-search labels.
5. The form controls for `府県`, `卒業期`, and `現役選手のみ` must resolve uniquely.
6. Search payload uses only hidden server fields plus prefecture, term, active-only and at most the unique submit control. No class, score, win rate, outcome, ranking, or other predictive criterion is supplied.
7. Search action must remain in the unauthenticated `/pc/search` namespace.
8. Candidate links must be exact same-origin `/pc/racerprofile?snum=<5-or-6-digits>`.
9. Pagination is rejected rather than silently truncating.
10. Candidate count >10 is rejected.
11. Each candidate profile must be fetched successfully; any transport/HTTP/parse ambiguity HALTS the entire resolution. It may NOT be converted into NONMATCH.
12. A candidate becomes NONMATCH only after a successfully parsed identity disagrees.
13. Final accepted cardinality must be exactly one.
14. Final identity checks are registration number + normalized name + canonical prefecture + term.
15. Locator elapsed budget is <=60 seconds.
16. Locator emits no predictive feature and persists no raw HTML.
17. The verified snum is routing metadata only; the predictive 3-field supplement still comes from the separately frozen racerprofile adapter.

### G2 adversarial questions

I. Does dynamic parsing of the official search form introduce hidden degrees of freedom or an uncontrolled adapter surface? Would static field-name binding after a live smoke be required before Freeze?
J. Is `prefecture + term + active_only` sufficiently deterministic and PRE-safe as a locator query while avoiding predictive filtering?
K. Could a malformed/changed search page cause an incorrect snum rather than a Fail-Closed rejection?
L. Could pagination, duplicate candidate links, or profile parse differences yield a false accept?
M. Is the 60-second locator budget sufficient to preserve the independent <=120-second source-capture-skew gate when combined with Tamano capture and final supplement capture? If not, specify a stricter bound or orchestration order.
N. Does reading candidate racerprofile pages expose predictive fields in raw HTML in a way that violates the zero-predictive-field locator role, even though the locator parser emits only identity? If yes, require an exact alternative; if no, explain why source-role separation is sufficient.
O. The official search page is a **new source role** versus Shadow250-v1. Confirm that creating Shadow250-v2 rather than mutating v1 correctly resolves the prior source-set-drift requirement.

# Rider class changes over time — required temporal validation

The project explicitly must handle riders moving A3 -> A2/A1 -> S2/S1 and later dropping back without treating class as a permanent rider identity.

Audit these invariants:

1. `rider_key` must not contain class; identity remains name/prefecture/term based.
2. Prospective `class` must come from the **current racecard for that race**, not from a permanent rider master.
3. KEIRIN racerprofile `class` is only a duplicate-consistency check for the current PRE capture and may not silently overwrite racecard class.
4. Class mismatch/update-boundary ambiguity must quarantine, not pick whichever source is convenient.
5. Historical B1a validation must not backfill today's/current profile class into older races. `historical_current_profile_replay` remains prohibited.
6. If the available historical evidence is insufficient to prove race-time class provenance, report that as a validation limitation. Do not open RESULT/PAYOUT/Price and do not silently reopen the frozen scientific lineage unless actual evidence of a violation is found.

# Runtime validation status — deliberately UNPROVEN unless receipt exists

Workflow candidate:
`.github/workflows/shadow250-v2-candidate-smoke.yml`

Expected PASS receipt path:
`v3/prospective_shadow250_v2/runtime_receipts/SHADOW250_V2_CANDIDATE_LIVE_SMOKE_v1.json`

At audit package creation, this receipt was **NOT PRESENT** in the repository. Therefore:

- G1 real-file execution of parser v2 is NOT proven by this package.
- G2 live `/pc/search -> /pc/racerprofile` E2E is NOT proven by this package.
- ChatGPT synthetic tests are not sufficient to promote either to runtime-proven.
- If the receipt is absent at the audited commit, keep this limitation explicit.
- If the receipt appears later, it belongs to a different commit and must be separately hash-bound/re-audited; do not silently import later evidence into this snapshot.

# Leakage / scientific-state audit

Confirm all of the following:

- no ECON_HOLDOUT1000 RESULT/PAYOUT/Price access;
- no holdout scoring;
- no global outcome-bearing scoring;
- no wager generation;
- no first-race selection;
- no screen count consumed by parser/source diagnostics;
- no prospective v3 scientific trial consumed by parser/source diagnostics;
- no post-outcome replacement;
- no provider fallback;
- predecessor Shadow250-v1 remains selected=0 and immutable;
- Shadow250-v2 remains selected=0 and NOT_ACTIVE unless a later independent APPROVE is followed by a separate activation Freeze.

# Required issue format

For every issue provide:

- ID
- section/file
- exact failure scenario
- whether it can change race membership, features, identity resolution, or Prediction Lock
- exact correction
- severity: `P0_BLOCKER` / `P1_MATERIAL` / `P2_NON_BLOCKING`
- whether correction changes source/adapter/source-role and therefore requires another new-universe rebind

# Required explicit decisions before verdict

State explicitly:

1. `ISSUE-G1-DATE-BINDING`: RESOLVED / UNRESOLVED
2. `ISSUE-G1-WITHDRAWN-HARDCODE`: RESOLVED / UNRESOLVED
3. `ISSUE-CLASS-PROGRAM-GATE-MISSING`: RESOLVED / UNRESOLVED
4. `ISSUE-G2-SNUM-PROVENANCE-UNBOUND`: RESOLVED / UNRESOLVED
5. `ISSUE-GOV-ADAPTER-HASH-REBINDING`: RESOLVED / UNRESOLVED
6. Shadow250-v2 source-role separation `/pc/search` vs `/pc/racerprofile`: ACCEPTABLE / NOT_ACCEPTABLE
7. rider-class temporal semantics: ACCEPTABLE / UNPROVEN / NOT_ACCEPTABLE
8. live-smoke evidence at this exact snapshot: PRESENT_AND_VALID / ABSENT_OR_UNPROVEN

Then state:

- `ECON_HOLDOUT1000 = SEALED`
- `Shadow250-v1 selected races = 0`
- `Shadow250-v2 selected races = 0`
- `Shadow250-v2 = NOT_ACTIVE` unless separately authorized later
- `prospective Shadow screen count = 0`
- `prospective v3 scientific trial = 0`
- `global scoring = UNAUTHORIZED`
- `wagering = UNAUTHORIZED`

# Final verdict

Return EXACTLY one:

`APPROVE`

`CONDITIONAL APPROVE`

`REJECT`

Meaning:

- `APPROVE` only if no unresolved P0/P1 remains in the candidate design/code at this audit snapshot. If live smoke is considered mandatory before Freeze, then absence of the receipt prevents APPROVE.
- `CONDITIONAL APPROVE` = NOT FREEZABLE / DO NOT ACTIVATE / DO NOT SELECT A RACE.
- `REJECT` = HALT / DO NOT ACTIVATE / DO NOT SELECT A RACE.

Even an `APPROVE` verdict authorizes only creation of a separate final Freeze + activation record for the exact audited Shadow250-v2 hashes. It does NOT itself activate the universe or select the first race.

ECON_HOLDOUT1000 must remain SEALED under every verdict.
