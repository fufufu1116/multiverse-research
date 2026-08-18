# Multiverse Hybrid v3.0 — Independent Gemini Audit Package v2

## Scope

Perform one hostile, independent pre-first-race audit covering BOTH:

1. `FIRST_PRE_G1_G2_RESOLUTION_CANDIDATE_v1`
2. race-level class / program compatibility for the Tamano parser and frozen B1a prediction pipeline

Do not assume ChatGPT conclusions are correct. Do not silently repair issues. Identify every P0/P1 before any first Shadow250 race is selected.

This audit is governance-only. It MUST NOT change model weights, source set, selection rule, scientific trial counts, Shadow250 membership, or authorization by itself.

## Absolute prohibitions

- ECON_HOLDOUT1000 remains SEALED.
- Do NOT access, request, infer, or score ECON_HOLDOUT1000 RESULT / PAYOUT / Price.
- Only already-frozen HOLDOUT membership metadata may be referenced for collision semantics.
- No source/provider fallback.
- No login/auth/CAPTCHA/WAF/rate-limit circumvention.
- No post-outcome replacement.
- No OCR.
- No global scoring, Lane-E, final-v3 proof, or wagering.

## Current scientific state before audit

- Shadow250 selected races: `0`
- prospective Shadow250 screen count: `0`
- prospective v3 scientific trial: last explicit frozen value `0`
- global scoring: `UNAUTHORIZED`
- wagering: `UNAUTHORIZED`
- ECON_HOLDOUT1000: `SEALED`

An `APPROVE` verdict may authorize only freezing the exact audited implementation and then evaluating a first strictly-post-activation PRE race through every existing frozen gate. It does NOT itself select a race.

## Authoritative frozen records

### Source set
`SHADOW250_SOURCE_SET_FINAL_FREEZE_v1.json`
- approved core SHA-256: `7d15d044c53dde706dfe8565db5b516f0e191f66af4236b7f771d49220e49fc6`
- key rule: `ANY source/adapter/source-role change requires NEW Shadow universe`
- Tamano official racecard PDF = frozen five-field racecard source
- KEIRIN.JP `/pc/racerprofile` = frozen three-field supplement source

### Selection rule
`SHADOW250_SELECTION_RULE_FINAL_FREEZE_v1.json`
- approved core SHA-256: `335be03ee68f8ecfc9c4b5afbfeb7e5acce5f7ee90e73bc36c5df3a8fd71fca1`
- membership = first 250 races satisfying all frozen PRE-only gates
- OCR prohibited
- RESULT/PAYOUT eligibility use prohibited
- unsupported template => `PRE_INELIGIBLE_SOURCE_GAP`
- after Prediction Lock, selected race can never be replaced

### HOLDOUT collision gate
`ECON_HOLDOUT1000_MEMBERSHIP_COLLISION_GATE_FINAL_v1.json`
- approved core SHA-256: `4f66e3b05a56eaaa179a8708c476ba9069b502dd458b636b5ea62e4e49516b4e`
- Price/PAYOUT/RESULT/scoring forbidden

### Activation
`SHADOW250_ACTIVATION_FINAL_FREEZE_v1.json`
- activation: `2026-08-19T00:03:49+09:00`
- status: `FROZEN_APPROVED_ACTIVE`
- selected races: `0`

### Final freeze self-verification
`FINAL_FREEZE_SELF_VERIFICATION_v1.json`
- genesis hash: `c95bad637162f992a27cf9ff24d295ef9183569d0f0d2a7d370fa0276aba0c8e`
- source/selection/holdout core hashes recomputed PASS

## Candidate under audit

### Candidate record
`FIRST_PRE_G1_G2_RESOLUTION_CANDIDATE_v1.json`
- originating commit: `920aacbad2bcb14f8b6bc6e493f9451895869fe8`
- Git blob SHA: `412a4131a51c4f25dac099f7d4a06118dc2ed2c4`
- status: `PENDING_INDEPENDENT_GEMINI_AUDIT_NO_SHADOW_RACE_SELECTED`

## G1 — Tamano deterministic row parser

File:
`v3/prospective/tamano_racecard_row_parser_v1.py`

Git blob SHA:
`da198c3a6f5c91b676ca570a4a2bb1310c8eb27d`

Current design:
- fixed A3 geometry
- private-use car-number glyph anchors E524..E52A = car 1..7
- OCR: no
- full-document extraction: no
- row class regex accepts `SS|S1|S2|A1|A2|A3|L1`
- current parser sets `withdrawn=False`
- `race_date` is supplied externally

Repo-reported historical real-file tests:
- `20260728 玉野.pdf`
  - raw PDF SHA-256: `1c5ec1a04f5fe6b77398ed975a49d1633a4d2c59b4c83624a24b871d7b757a5e`
  - 84 rows / 12 races / PASS
- `20260729-玉野.pdf`
  - raw PDF SHA-256: `5adf687d7893341c4a6ae0b32c4a47b57f0f99b70c731fead4d214153e654ea6`
  - 84 rows / 12 races / PASS

Prior semantic audit established that a Tamano PDF may contain prior-day RESULT/PAYOUT on page 1. Therefore only exact current-day PRE regions may enter normalization.

## G2 — KEIRIN registration-number locator guard

File:
`v3/prospective/keirinjp_snum_locator_guard_v1.py`

Git blob SHA:
`4b8d50f0acf35b4b028c6af32d6b0541fbaa6828`

Current design:
- candidate `snum` = `UNTRUSTED LOCATOR ONLY`
- must not enter predictive features
- candidate snum must lie in official JKA term registration interval(s)
- final identity authority remains frozen KEIRIN.JP `/pc/racerprofile`
- final identity checks: registration_number + normalized_name + prefecture + term
- wrong hint => `QUARANTINE_FAIL_CLOSED`
- seven-rider examples currently prove term-range checks + synthetic verifier behavior only; they are NOT recorded as seven live official-profile end-to-end verifications

Existing frozen KEIRIN.JP hard-limit adapter:
- semantic SHA-256 frozen in source set: `107040fcfbdcb5418c9aef2a9bd68f0601d4ee5d4e86e8d671495f307941da84`
- repository Git blob SHA: `a73a28e9568c326b8cd10b4cfa70bcb573f0f852`
- HTTPS only
- host `keirin.jp`
- path `/pc/racerprofile`
- only query `snum`
- minimum request spacing 5 seconds
- 403/429 => halt/no retry
- redirects rejected
- no login/auth/CAPTCHA/WAF/rate-limit bypass

## Race-level class / program compatibility

Official race-program semantics to verify against primary KEIRIN/JKA materials:

- A級3班 = A級チャレンジ / A3 race program.
- A級1・2班 = A1/A2 race program.
- S級 = S-class race program.
- FI may contain both S-class races and A1/A2 races in the same meeting, but S-class and A-class riders must not be treated as sharing a normal race.
- SS/S1/S2 mixtures may exist within an S-class race.
- A1/A2 mixtures may exist within an A1/A2 race.
- A3 races are A3-class.
- L1 is a separate Girls program.

Therefore the parser/pipeline must be audited for impossible same-race cross-program mixtures such as:
- `{A3,A2}`
- `{A3,S1}`
- `{A1,S2}`
- `{L1,A3}`

Recovered B1a behavior:
- prediction normalization is race-local: logits/softmax are computed only across one race record's entrants
- frozen class feature set: `SS,S1,S2,A1,A2,A3,L1`
- recovered final beta values include:
  - class_SS = `1.0770873580301035`
  - class_S1 = `-0.12658801568020364`
  - class_S2 = `-0.9504993423499002`
  - class_A1 = `0.10862511799550383`
  - class_A2 = `-0.10862511799550574`
  - class_A3 ≈ `0` (`4.991005121158697e-16`)
  - class_L1 ≈ `0` (`-1.446593378458555e-16`)

Interpretation to audit:
- if every entrant has the same class category (e.g. A3-only or L1-only), that class contribution is constant and cancels under race-local softmax
- A1/A2 and SS/S1/S2 class differences may influence relative probability only inside legitimately mixed race programs
- no synthetic cross-race or cross-program matchup may be created by training, preprocessing, or inference

Current known parser gap:
- row-level class values are validated independently
- there is currently NO explicit race-level admissible class/program composition gate
- therefore malformed extraction could theoretically create an impossible mixed class set under one race_id and still pass row-level category validation

## Recovery limitations that MUST remain visible

- Both Tamano historical PDFs are visible in ChatGPT File Library, but no matching executable raw copy was found in connected Google Drive during recovery.
- Therefore G1 was NOT independently re-run in the current runtime.
- Official-web supplementary search during recovery did not yield a new proven deterministic name/prefecture/term -> snum discovery path.
- Do not promote repo receipts into current-runtime byte-level re-verification.

# Required hostile audit questions

## A. Freeze boundary / source-set semantics

1. Does adding `tamano_racecard_row_parser_v1.py` merely complete the already-authorized Tamano adapter implementation, or does it constitute an `adapter change` under the frozen rule requiring a NEW Shadow universe?
2. Does using an externally discovered candidate `snum`, even as untrusted locator-only metadata later verified by the frozen official racerprofile page, constitute a new source or source-role dependency?
3. If either answer is YES, is a NEW Shadow universe mandatory before any race, given selected_count=0?
4. If locator-only metadata can sit outside the predictive source set, what exact provenance restrictions are required to ensure it never becomes a hidden third feature/data source?
5. Does adding a race-level class/program compatibility guard constitute safety completion before first Freeze, or an adapter change requiring a NEW Shadow universe?

## B. G1 parser safety

6. Verify that fixed extraction regions cannot include prior-day RESULT/PAYOUT content from mixed Tamano PDFs.
7. Verify private-use glyph anchors and fixed geometry fail closed on template drift.
8. Is external `race_date` adequately bound to actual PDF/event identity, or is a document-date/event binding check required?
9. Is hard-coded `withdrawn=False` safe under frozen active-entrant semantics? If not, require a precise upstream/downstream invariant or parser correction.
10. Are seven-car-only expectations compatible with all eligible Tamano races? If not, specify exact fail-closed behavior.
11. Are class/name/prefecture/term/score/quinella_rate/S/B windows sufficiently guarded against adjacent-column silent capture?
12. Does G1 preserve frozen five-field ownership and prohibit deriving/synthesizing missing fields?

## C. Race-level class/program compatibility

13. Must first prospective use include an explicit race-level class/program compatibility gate?
14. Should admissible class sets be exactly:
   - S program: subset of `{SS,S1,S2}`
   - A1/A2 program: subset of `{A1,A2}`
   - A3 program: exactly `{A3}`
   - Girls program: exactly `{L1}`
   with all cross-program mixtures rejected fail-closed?
15. Is entrant-class-set validation sufficient, or is meeting/race program metadata also required to prevent false acceptance?
16. If an impossible mixture such as `{A3,A2}` or `{A1,S2}` appears, must the race be QUARANTINE / `PRE_INELIGIBLE_SOURCE_GAP` with no post-outcome replacement?
17. Verify that no training/preprocessing/inference step creates synthetic cross-class or cross-program matchups; all probability normalization must remain strictly race-local.
18. Determine whether historical training data should be audited for impossible same-race class mixtures before relying on the frozen B1a coefficients. If yes, say whether this is validation-only or would invalidate/reopen a frozen scientific artifact.

## D. G2 identity resolution / provenance

19. Verify JKA term interval table against the official registration-date source, including non-contiguous late-registration exceptions.
20. The guard validates a candidate snum but does not define where candidate snum values originate. Is missing locator provenance a P0/P1 blocker?
21. Must candidate-snum discovery be frozen as a deterministic PRE-safe process before first use?
22. Must the seven rider examples be live-verified through the frozen KEIRIN.JP adapter before G2 can be frozen, or are synthetic verifier tests sufficient because every real use fails closed on official mismatch?
23. Could a wrong but in-range snum cause accepted wrong-rider data? Verify all four identity checks prevent this.
24. Could name normalization, old/new kanji, prefecture normalization, or term representation cause a false match? Distinguish false reject from false accept.
25. Confirm registration number remains identity/routing metadata only and cannot enter ranking, model features, outcome-based eligibility, or candidate selection beyond deterministic identity resolution.

## E. Leakage, trials, authorization

26. Confirm no RESULT/PAYOUT/Price is read or inferred by G1/G2/class compatibility checks.
27. Confirm the two historical Tamano PDFs are parser/source validation only and do not consume a scientific trial or Shadow screen count.
28. Confirm counts remain selected=0, prospective screen=0, prospective v3 scientific trial=0 unless an authoritative record explicitly says otherwise.
29. Confirm no global scoring, Lane-E, final-v3 proof, or wagering is authorized by this audit.
30. Confirm no source switch/provider fallback may occur mid-run.
31. Identify any hidden degree of freedom, post-hoc choice, source drift, parser ambiguity, identity ambiguity, class/program ambiguity, or provenance omission not listed above.

# Required issue format

For EVERY issue provide:
- ID
- section/file
- exact failure scenario
- whether it can change race membership, features, or Prediction Lock
- exact correction
- severity: `P0_BLOCKER` / `P1_MATERIAL` / `P2_NON_BLOCKING`
- whether correction requires `NEW_SHADOW_UNIVERSE_REQUIRED_BEFORE_ANY_RACE`

# Required explicit state confirmation

Before the final verdict, state explicitly:

- `ECON_HOLDOUT1000 = SEALED`
- `Shadow250 selected races = 0`
- `prospective Shadow250 screen count = 0`
- `prospective v3 scientific trial = 0` unless authoritative evidence proves otherwise
- `global scoring = UNAUTHORIZED`
- `wagering = UNAUTHORIZED`

# Final verdict

Return EXACTLY one:

`APPROVE`

`CONDITIONAL APPROVE`

`REJECT`

Meaning:

- `APPROVE` only if no unresolved P0/P1 remains before the first selected race AND source/adapter/source-role drift questions are explicitly resolved.
- `CONDITIONAL APPROVE` = NOT FREEZABLE / DO NOT SELECT A RACE.
- `REJECT` = HALT / DO NOT SELECT A RACE.

If any required fix changes a frozen source, adapter, or source role, explicitly state:

`NEW_SHADOW_UNIVERSE_REQUIRED_BEFORE_ANY_RACE`

ECON_HOLDOUT1000 must remain SEALED under every verdict.
