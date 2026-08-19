# Multiverse Hybrid v3.0 — Final Independent Gemini Re-Audit: Shadow250-v2 Candidate v3

## Audit posture

Perform a hostile, independent audit of the final **NOT-ACTIVE Shadow250-v2 Candidate v3**.
Do not assume ChatGPT's remediation is correct. Do not silently repair defects.

Repository: `fufufu1116/multiverse-research`
Exact audit snapshot commit: `ca8c28b21fbb64d450dfaf3b512d074804392a05`

This audit is PRE-only governance/source validation. It MUST NOT access, request, infer, or score ECON_HOLDOUT1000 RESULT/PAYOUT/Price.

## State that must remain unchanged during audit

- Shadow250-v1 selected races = `0`; predecessor is immutable.
- Shadow250-v2 selected races = `0`.
- Shadow250-v2 prospective screen count = `0`.
- prospective v3 scientific trial = `0`.
- Shadow250-v2 = `NOT_ACTIVE_PENDING_INDEPENDENT_GEMINI_REAUDIT`.
- ECON_HOLDOUT1000 = `SEALED`.
- global scoring / Lane-E / final-v3 proof / wagering = `UNAUTHORIZED`.
- Prediction model change = `PROHIBITED`.
- Candidate A Prediction Lock remains exactly:
  `2defade77042f5e2e78a68c831d4cb67330882b4d8977c6e3d9d44546988aada`

Even an APPROVE verdict authorizes only creation of exact final Freeze records and a **separate later activation record**. This audit itself does not activate the universe or select a race.

---

# 1. Why this re-audit exists

The previous Gemini re-audit returned `CONDITIONAL APPROVE` because all prior G1/G2/class/hash issues were resolved in design, but the exact audited snapshot lacked a live-smoke receipt.

When live smoke was actually run **before activation and before any selected race**, it correctly exposed several real runtime assumptions. None were hidden or post-hoc outcome fixes; every failure was recorded while selected=0/screen=0/trial=0.

Formal remediation history:
`v3/prospective_shadow250_v2/governance/SHADOW250_V2_LIVE_SMOKE_REMEDIATION_RECEIPT_v1.json`

Final runtime evidence:
`v3/prospective_shadow250_v2/runtime_receipts/SHADOW250_V2_FINAL_CANDIDATE_RUNTIME_EVIDENCE_v1.json`
Git blob: `598de0096298d649793724ab4b3efd4e22d7d8dc`
Status: `PASS`

---

# 2. Candidate v3 governance bindings

## Source Set Candidate v3

File:
`v3/prospective_shadow250_v2/governance/SHADOW250_V2_SOURCE_SET_FREEZE_CANDIDATE_v3.json`

Core SHA-256:
`d872652f0b6a83b126a9c1a3537bbe40faa992f02358681207b5bae8b7a1d818`

## Selection Rule Candidate v3

File:
`v3/prospective_shadow250_v2/governance/SHADOW250_V2_SELECTION_RULE_FREEZE_CANDIDATE_v3.json`

Core SHA-256:
`26459bbe8db0766918a7511069f0c13354fb8b75d952a1633bbc3b8325f099d6`

## Genesis Candidate v3

File:
`v3/prospective_shadow250_v2/governance/SHADOW250_V2_GENESIS_CANDIDATE_v3.json`

Status:
`NOT_ACTIVE_PENDING_INDEPENDENT_GEMINI_REAUDIT`

Exact executable bindings:

- Tamano parser v4 Git blob:
  `397ed3c8839b1ad4ffa4835924dd759397e2124c`
- KEIRIN identity locator v3 Git blob:
  `c97d1d7c736e8cd778029446ffc704a684d4938e`
- KEIRIN racerprofile parser v4 Git blob:
  `d8ce951abd1f008f872bc093d6bb12a50d62ca16`
- race-level KEIRIN batch v3 Git blob:
  `b0cdb1fa49d3fcf033c09b273a44a47bab9ab4eb`
- Tamano 5+3 fusion guard v2 Git blob:
  `a74ab32d2c0bd3957995fccfccb403ac3ae225fe`
- final runtime evidence Git blob:
  `598de0096298d649793724ab4b3efd4e22d7d8dc`

Prediction model is unchanged.

---

# 3. G1 — Tamano racecard parser v4

File:
`v3/prospective_shadow250_v2/tamano_racecard_row_parser_v4.py`

Git blob:
`397ed3c8839b1ad4ffa4835924dd759397e2124c`

## Event-day binding

Live evidence proved the permitted PRE clips contain no usable meeting-date string. Therefore the abandoned internal-Reiwa-date assumption is NOT used.

v4 requires:

1. source URL is HTTPS `www.tamano-keirin.jp`;
2. path begins `/wp-content/uploads/` and ends `.pdf`;
3. URL basename begins the exact externally supplied `YYYYMMDD` race date;
4. that URL must be the exact event-day href selected through the official Tamano `/racepdf/` discovery path upstream;
5. SHA-256 of the bytes parsed must exactly equal the transport receipt SHA-256;
6. template/PRE-region/POST-sentinel gates still run independently.

The parser never expands into prior-day RESULT/PAYOUT regions to manufacture a date.

## Field-size marker

Live mapping of all 12 races showed each `(7車立)` marker immediately below the seven entrant rows. v4 checks a dedicated PRE-only marker band:

- x = `ox + 60 .. ox + 150`
- y = `ymax .. ymax + 30`

Entrant extraction geometry itself is NOT widened.

## Other retained gates

- exactly two pages / frozen dimensions;
- only frozen PRE clips;
- POST sentinel zero;
- private-use car glyph anchors 1..7;
- current-row withdrawal/exclusion/cancellation token guard;
- 84 rows / 12 races / 7 cars each;
- race-level program/class compatibility;
- only frozen five racecard predictive fields.

Live source validation PASS:
- 84 rows / 12 races;
- A12=5 races, L1=2, S=5;
- raw PDF SHA-256 `a2328d364eec4308adb7024efbb0b0fc7851472dc72a3fad465b5fa5cdc24317`;
- no RESULT/PAYOUT/Price use;
- no scientific trial/screen consumption.

### G1 hostile questions

A. Is official-discovery exact-href + URL date prefix + exact parsed-byte SHA binding a valid PRE-safe event-day identity replacement for the nonexistent in-PDF date?
B. Is relying on the date prefix in the official discovered filename an unacceptable hidden degree of freedom, or sufficiently fail-closed when cardinality must equal one and raw SHA is bound?
C. Is discovery allowed before the measured 120-second source window, provided the exact PDF data capture window begins immediately before the selected PDF HTTP request and all feature-bearing captures are inside the window?
D. Does the dedicated marker band remain safely inside PRE-only content and sufficiently isolated from adjacent races?
E. Can a withdrawal token appear outside the guarded current-row identity/core strip while seven car anchors and `(7車立)` remain, producing a false active entrant? If yes, classify severity and exact correction.
F. Does seven-car-only eligibility remain a legitimate source-constrained target rather than an unannounced population claim?

---

# 4. G2 — KEIRIN identity locator v3

File:
`v3/prospective_shadow250_v2/keirinjp_identity_locator_v3.py`

Git blob:
`c97d1d7c736e8cd778029446ffc704a684d4938e`

Live source semantics established:

- landing `/pc/search`;
- visible form `PJ0501_02InputForm`;
- search button calls `sensyuSearchExec()`;
- values are copied into hidden `PJ0501_02SubmitForm`;
- GET result path `/pc/racersearchresult`;
- active-only uses `stgt=1`;
- profile link semantics use `sensyuLink('snum')` and `PJ0504SensyuLinkForm` -> `/pc/racerprofile`.

Locator query basis is only:

- prefecture;
- graduation term;
- active-only.

All other search filters are blank.

The result page may physically contain other PRE columns, but the locator executable consumes only:

- displayed rider name;
- `snum` from exact `sensyuLink('digits')` routing control.

It does not return or persist search-result score/class/rates.
Raw HTML is not persisted.
Exactly one normalized-name candidate is required.
Final `/pc/racerprofile` identity authority requires registration number + normalized name + prefecture + term.

Locator v3 fixed only the synthetic-fixture UTF-8 declaration relative to the live-proven v2 semantics; bundled synthetic and live validation both PASS.

### G2 hostile questions

G. Is loading a search-result HTML document that physically contains other PRE predictive columns acceptable under an identity-only source role when executable extraction is allowlisted to name+snum and raw HTML is not persisted?
H. Or does mere transport exposure to those unused PRE columns make `/pc/racersearchresult` a broader predictive source role requiring a different architecture?
I. Is the exact two-form/JS semantic validation sufficiently deterministic and fail-closed under website drift?
J. Could `sensyuLink('snum')` parsing or normalized-name matching create a false accept rather than a false reject?
K. Does the new source role remain properly isolated because this is a new, never-activated Shadow250-v2 candidate rather than mutation of active Shadow250-v1?

---

# 5. Racerprofile parser v4 — update-boundary semantics

File:
`v3/prospective_shadow250_v2/keirinjp_racerprofile_parser_v4.py`

Git blob:
`d8ce951abd1f008f872bc093d6bb12a50d62ca16`

Old parser weakness found by seven-rider live batch:
- it collected global datetime strings, deduplicated them, then assigned first/second;
- this did not explicitly bind a timestamp to the semantic section/table;
- nested layout tables also created ambiguous recursive table matches.

v4 requires:

- row belongs to a table only when its nearest parent table is that table;
- cell belongs to row only when its nearest parent row is that row;
- normal `<tbody>` wrappers are therefore allowed, nested child-table rows cannot be stolen by an outer layout table;
- `profile_updated_at` = unique datetime between nearest preceding exact `プロフィール` label and owned basic/profile target table;
- `recent4m_updated_at` = unique datetime between nearest preceding exact `近況成績` label and owned recent-4-month target table;
- missing/ambiguous section timestamp => Fail-Closed;
- timestamp remains synchronization/update-boundary metadata only, never a predictive feature.

Live parser v4 PASS for `snum=015918`, with both section-bound timestamps and valid style/win/trio fields. Predictive values were not persisted in validation receipts.

### Profile hostile questions

L. Does nearest-parent table ownership safely solve the nested-layout-table ambiguity without becoming permissive?
M. Can duplicate semantic section labels before a target table bind the wrong timestamp? Examine document-order logic adversarially.
N. Is a unique section-bound timestamp sufficient to preserve frozen `supplement_update_boundary_crossing = QUARANTINE_FAIL_CLOSED` semantics?
O. Does reusing the same single racerprofile HTTP response for both four-field identity verification and the three supplement fields preserve source-role integrity and avoid timing inconsistency?

---

# 6. Race-level KEIRIN batch v3

File:
`v3/prospective_shadow250_v2/keirinjp_race_batch_identity_supplement_v3.py`

Git blob:
`b0cdb1fa49d3fcf033c09b273a44a47bab9ab4eb`

Required invariants:

- exactly 7 entrants;
- one shared `requests.Session` and one shared provider limiter across the entire race;
- minimum 5 seconds between every KEIRIN request;
- landing fetched once;
- one result search per unique `(prefecture, term)` group;
- exactly one profile fetch per verified rider;
- any candidate/profile transport or parse ambiguity HALTS entire race;
- search-result predictive fields consumed = none;
- predictive supplement fields only from racerprofile parser v4;
- batch elapsed <=90 seconds;
- whole source window from immediately before Tamano PDF request through final racerprofile capture <=120 seconds.

Final runtime evidence:

- 7 riders verified;
- 15 KEIRIN requests in worst-case seven unique pref/term groups;
- KEIRIN batch = `75.846s`;
- measured Tamano-PDF-to-final-profile source window = `76.96s`;
- limit = `120s`;
- all seven historical identity-validation examples resolved to expected snums;
- no predictive values were persisted by diagnostic receipt;
- no historical Tamano/current-profile fusion or prediction was executed.

### Batch hostile questions

P. Does one shared limiter actually prevent cross-rider spacing reset?
Q. Are `<=90s` batch and `<=120s` full-source gates sufficiently conservative given observed `76.96s`, or is there hidden timeout/order ambiguity?
R. Must the official discovery-page HTTP request itself be inside the 120-second source window, or is it non-feature-bearing routing metadata that may precede the feature-bearing PDF request?
S. Could grouping by `(prefecture, term)` change scientific eligibility or ranking, or is it purely deterministic request de-duplication?

---

# 7. 5+3 fusion guard v2 and canonical class semantics

File:
`v3/prospective_shadow250_v2/tamano_5plus3_fusion_guard_v2.py`

Git blob:
`a74ab32d2c0bd3957995fccfccb403ac3ae225fe`

The predecessor frozen fusion rule already required:
- class = `exact canonical match`;
- score = exact at 0.01 resolution;
- quinella_rate = exact at 0.001 fraction resolution.

Executable candidate now makes canonical class mapping explicit and closed:

- `Ｓ級Ｓ班 -> SS`
- `Ｓ級１班 -> S1`
- `Ｓ級２班 -> S2`
- `Ａ級１班 -> A1`
- `Ａ級２班 -> A2`
- `Ａ級３班 -> A3`
- `Ｌ級１班 -> L1`

Unknown labels fail closed.

Duplicate comparisons:
- score -> Decimal 0.01 resolution;
- racerprofile `2連対率` percent -> fraction -> Decimal 0.001 resolution;
- class -> exact canonical equality.

Predictive ownership remains:
- Tamano: score, quinella_rate, S, B, class;
- racerprofile: style, win_rate, trio_rate.

The fusion guard was deliberately NOT live-fused against the historical Tamano 2026-07-24 PDF because that would combine historical racecard state with current racerprofile state, violating `historical_current_profile_replay = PROHIBITED`. Its mapping/consistency behavior is synthetic-tested instead.

### Fusion hostile questions

T. Is this seven-label map exactly the correct canonicalization needed by the already-frozen `exact canonical match` rule, or does it introduce a new scientific degree of freedom?
U. Are the 0.01 score and 0.001 fraction comparisons implemented without material rounding ambiguity?
V. Is it scientifically correct to refuse a live fusion test on a historical PDF and wait until a strictly prospective PRE race after activation, while validating the fusion mechanics synthetically before Freeze?
W. Does converting win_rate/trio_rate percent strings to fractions alter the frozen B1a prediction in any material way? Explicitly account for the fact that Candidate A/B1a numeric features are race-locally standardized before the frozen logits.
X. Confirm `race_program`, timestamps, snum, routing metadata, and duplicate-only profile class/score/quinella do NOT enter the predictive feature vector.

---

# 8. Rider class changes over time

Audit explicitly:

- rider identity key contains name + prefecture + term, NOT class;
- current prospective class comes from current racecard;
- profile class is only duplicate consistency metadata;
- A1 -> S2 -> A1 is therefore represented at each race's current class rather than permanent rider class;
- mismatch/update-boundary ambiguity quarantines the race;
- no current profile is replayed into historical training/racecard state;
- no synthetic cross-program matchup is constructed;
- B1a/Candidate A remains race-local.

Return `ACCEPTABLE`, `UNPROVEN`, or `NOT_ACCEPTABLE` for these temporal semantics.

---

# 9. Universe-boundary question — MUST answer explicitly

Shadow250-v1 was frozen/activated but consumed zero races. Gemini previously required a NEW Shadow universe before any race because v1's frozen adapter/source role changed. Shadow250-v2 was therefore created as a separate universe candidate.

Shadow250-v2 has **never been activated**, selected zero races, consumed zero screens and zero scientific trials. During its required pre-activation live-smoke qualification, implementation defects were found and candidate files were repeatedly replaced/rebound. No prior Shadow250-v2 candidate was ever final-frozen or activated.

Decide explicitly:

Y. Is it governance-valid to bind the corrected final code into **Shadow250-v2 Candidate v3** before its first final Freeze/activation?

Return exactly one for Y:

- `SHADOW250_V2_CANDIDATE_REBIND_IS_VALID_BEFORE_FIRST_FREEZE`
- `ANOTHER_NEW_SHADOW_UNIVERSE_REQUIRED_BEFORE_ANY_RACE`

Explain why. Do not infer approval merely from selected=0; distinguish predecessor v1 frozen-state mutation from edits to a never-frozen/non-active v2 candidate.

---

# 10. Runtime evidence and leakage

Audit exact receipt:
`v3/prospective_shadow250_v2/runtime_receipts/SHADOW250_V2_FINAL_CANDIDATE_RUNTIME_EVIDENCE_v1.json`
Git blob:
`598de0096298d649793724ab4b3efd4e22d7d8dc`

It reports:
- all five expected Git blobs exactly matched;
- all synthetic guards PASS;
- Tamano live source validation PASS 84 rows / 12 races;
- race batch live PASS seven riders;
- source window `76.96s <=120s`;
- prediction executed = false;
- cross-source scientific fusion performed = false;
- predictive values persisted = false;
- raw HTML/PDF persisted = false;
- HOLDOUT accessed = false;
- RESULT/PAYOUT/Price accessed = false;
- scientific trial consumed = false;
- shadow screen consumed = false;
- global scoring/wagering = false.

Determine whether diagnostic source-validation of seven known riders and a historical Tamano PDF, without fusion/prediction/outcome use, legitimately consumes zero scientific trials/screens.

---

# 11. Required issue format

For every issue:

- ID
- exact file/section
- failure scenario
- effect on membership / features / identity / Prediction Lock
- exact correction
- severity: `P0_BLOCKER`, `P1_MATERIAL`, or `P2_NON_BLOCKING`
- whether correction requires another universe rebind

Do not hide a defect merely because live evidence passed.

---

# 12. Required explicit decisions

Before final verdict state:

1. Tamano transport-provenance event-day binding: ACCEPTABLE / NOT_ACCEPTABLE
2. dedicated `(7車立)` marker band: ACCEPTABLE / NOT_ACCEPTABLE
3. withdrawal/active-entry guard: ACCEPTABLE / NOT_ACCEPTABLE
4. race-program/class compatibility: ACCEPTABLE / NOT_ACCEPTABLE
5. KEIRIN `/pc/racersearchresult` identity-only consumption: ACCEPTABLE / NOT_ACCEPTABLE
6. locator v3 deterministic identity semantics: ACCEPTABLE / NOT_ACCEPTABLE
7. racerprofile parser v4 section timestamp/table ownership: ACCEPTABLE / NOT_ACCEPTABLE
8. seven-rider shared-limiter batch v3: ACCEPTABLE / NOT_ACCEPTABLE
9. 90s batch + 120s source-window gates: ACCEPTABLE / NOT_ACCEPTABLE
10. canonical class mapping / duplicate consistency fusion guard: ACCEPTABLE / NOT_ACCEPTABLE
11. rider-class temporal semantics: ACCEPTABLE / UNPROVEN / NOT_ACCEPTABLE
12. final runtime evidence: PRESENT_AND_VALID / NOT_VALID
13. universe-boundary decision Y: return exactly one of the two specified strings.

Then state:

- `ECON_HOLDOUT1000 = SEALED`
- `Shadow250-v1 selected races = 0`
- `Shadow250-v2 selected races = 0`
- `Shadow250-v2 = NOT_ACTIVE`
- `prospective Shadow screen count = 0`
- `prospective v3 scientific trial = 0`
- `global scoring = UNAUTHORIZED`
- `wagering = UNAUTHORIZED`

---

# 13. Final verdict

Return EXACTLY one:

`APPROVE`

`CONDITIONAL APPROVE`

`REJECT`

`APPROVE` requires:
- no unresolved P0/P1;
- all exact candidate bindings verified;
- final runtime evidence accepted;
- source-role boundaries accepted;
- universe-boundary decision does not require another universe.

If universe-boundary decision Y is `ANOTHER_NEW_SHADOW_UNIVERSE_REQUIRED_BEFORE_ANY_RACE`, final verdict cannot be APPROVE for Shadow250-v2.

`CONDITIONAL APPROVE` = DO NOT FINAL-FREEZE / DO NOT ACTIVATE / DO NOT SELECT A RACE.

`REJECT` = HALT / DO NOT FINAL-FREEZE / DO NOT ACTIVATE / DO NOT SELECT A RACE.

Even `APPROVE` only permits ChatGPT to create exact final Freeze records for these audited hashes, perform a freeze self-verification, and then create a separate activation record. It does not itself consume race 1.

ECON_HOLDOUT1000 remains SEALED under every verdict.
