# Multiverse Hybrid v3.0 — Independent Gemini Audit Gate: FIRST_PRE_G1_G2_RESOLUTION_CANDIDATE_v1

## Audit posture

Perform a hostile, independent pre-first-race audit. Do not assume prior ChatGPT conclusions are correct.

This audit MUST NOT access, request, infer, or score ECON_HOLDOUT1000 RESULT / PAYOUT / Price. Only already-frozen membership metadata may be referenced for collision semantics.

Current scientific state before this audit:
- Shadow250 selected races: 0
- prospective Shadow250 screen count: 0
- prospective v3 scientific trial: last explicit frozen value 0
- global scoring: UNAUTHORIZED
- wagering: UNAUTHORIZED
- ECON_HOLDOUT1000: SEALED

An APPROVE verdict may authorize only freezing the audited G1/G2 implementation and then evaluating a first strictly-post-activation PRE race through all existing frozen gates. It does not authorize scoring, wagering, HOLDOUT access, or changing any frozen source/selection rule.

## Authoritative frozen records

1. `SHADOW250_SOURCE_SET_FINAL_FREEZE_v1.json`
   - approved core SHA-256: `7d15d044c53dde706dfe8565db5b516f0e191f66af4236b7f771d49220e49fc6`
   - key rule: `ANY source/adapter/source-role change requires NEW Shadow universe`
   - Tamano official racecard PDF = frozen five-field racecard source
   - KEIRIN.JP `/pc/racerprofile` = frozen three-field supplement source

2. `SHADOW250_SELECTION_RULE_FINAL_FREEZE_v1.json`
   - approved core SHA-256: `335be03ee68f8ecfc9c4b5afbfeb7e5acce5f7ee90e73bc36c5df3a8fd71fca1`
   - first 250 races satisfying all PRE-only gates
   - OCR prohibited
   - RESULT/PAYOUT eligibility use prohibited
   - unsupported template => PRE_INELIGIBLE_SOURCE_GAP

3. `ECON_HOLDOUT1000_MEMBERSHIP_COLLISION_GATE_FINAL_v1.json`
   - approved core SHA-256: `4f66e3b05a56eaaa179a8708c476ba9069b502dd458b636b5ea62e4e49516b4e`
   - Price/PAYOUT/RESULT/scoring forbidden

4. `SHADOW250_ACTIVATION_FINAL_FREEZE_v1.json`
   - activation: `2026-08-19T00:03:49+09:00`
   - status: FROZEN_APPROVED_ACTIVE
   - selected races: 0

5. `FINAL_FREEZE_SELF_VERIFICATION_v1.json`
   - genesis hash: `c95bad637162f992a27cf9ff24d295ef9183569d0f0d2a7d370fa0276aba0c8e`
   - source/selection/holdout core hashes recomputed PASS

## Candidate under audit

### Candidate record
`FIRST_PRE_G1_G2_RESOLUTION_CANDIDATE_v1.json`
- originating commit: `920aacbad2bcb14f8b6bc6e493f9451895869fe8`
- Git blob SHA: `412a4131a51c4f25dac099f7d4a06118dc2ed2c4`
- status: `PENDING_INDEPENDENT_GEMINI_AUDIT_NO_SHADOW_RACE_SELECTED`

### G1 — Tamano deterministic row parser
`v3/prospective/tamano_racecard_row_parser_v1.py`
- Git blob SHA: `da198c3a6f5c91b676ca570a4a2bb1310c8eb27d`
- method: fixed A3 geometry + private-use car glyph anchors E524..E52A
- OCR: no
- full-document extraction: no
- repo-reported historical real-file tests:
  - `20260728 玉野.pdf` raw PDF SHA-256 `1c5ec1a04f5fe6b77398ed975a49d1633a4d2c59b4c83624a24b871d7b757a5e` => 84 rows / 12 races / PASS
  - `20260729-玉野.pdf` raw PDF SHA-256 `5adf687d7893341c4a6ae0b32c4a47b57f0f99b70c731fead4d214153e654ea6` => 84 rows / 12 races / PASS
- prior semantic audit established that a Tamano PDF can contain prior-day RESULT/PAYOUT on page 1; therefore only exact PRE region extraction is acceptable.
- current parser sets `withdrawn=False` on emitted rows and receives `race_date` as an external argument.

### G2 — KEIRIN registration-number locator guard
`v3/prospective/keirinjp_snum_locator_guard_v1.py`
- Git blob SHA: `4b8d50f0acf35b4b028c6af32d6b0541fbaa6828`
- candidate snum = UNTRUSTED LOCATOR ONLY; must not enter predictive features
- candidate snum must lie in frozen official JKA term registration interval(s)
- final identity authority remains frozen KEIRIN.JP `/pc/racerprofile`
- final exact identity checks: registration_number + normalized name + prefecture + term
- wrong hint => QUARANTINE_FAIL_CLOSED
- seven-rider test currently proves term-range checks plus synthetic verifier behavior; it is NOT recorded as seven live official-profile end-to-end verifications.

Existing frozen KEIRIN.JP hard-limit adapter:
- semantic SHA-256 frozen in source set: `107040fcfbdcb5418c9aef2a9bd68f0601d4ee5d4e86e8d671495f307941da84`
- repository Git blob SHA: `a73a28e9568c326b8cd10b4cfa70bcb573f0f852`
- HTTPS only; host `keirin.jp`; path `/pc/racerprofile`; only query `snum`
- minimum request spacing 5 seconds
- 403/429 => halt/no retry
- redirects rejected
- no login/auth/CAPTCHA/WAF/rate-limit bypass behavior

## Recovery note

`HANDOFF_STATE_RECEIPT_20260819_v1.json` was created only as a recovery receipt and explicitly changes no scientific/Freeze state.

Current independent re-execution limitations must remain visible:
- both Tamano historical PDFs are visible in ChatGPT File Library, but no matching raw executable copy was found in connected Google Drive during recovery;
- therefore G1 was not independently re-run in the current runtime;
- official-web supplementary search was attempted during recovery but the search backend returned 503, so no new official identity claim was promoted to proven.

## Required hostile audit questions

### A. Freeze-boundary / source-set semantics
1. Does adding `tamano_racecard_row_parser_v1.py` constitute merely completing the already-authorized Tamano adapter implementation, or does it constitute an `adapter change` under the frozen rule requiring a NEW Shadow universe?
2. Does using any externally discovered candidate `snum`, even as an untrusted locator-only value that never becomes a predictive feature and is independently verified by the frozen official racerprofile page, constitute a new `source` or `source-role` dependency?
3. If the answer to either 1 or 2 is YES, is a NEW Shadow universe mandatory before any race, given selected_count=0?
4. If locator-only metadata can be outside the predictive source set, what exact governance language/provenance constraints are required so that this does not become a hidden third feature/data source?

### B. G1 parser safety and semantics
5. Verify that fixed regions cannot include prior-day RESULT/PAYOUT content from mixed Tamano PDFs.
6. Verify that the private-use glyph anchors and fixed geometry fail closed on template drift.
7. Is external `race_date` input adequately bound to the actual PDF/event identity, or is a document-date/event binding check required before first prospective use?
8. Is hard-coded `withdrawn=False` safe under the frozen active-entrant semantics? If a withdrawn/scratched rider can remain printed in the PDF, require a precise correction or upstream invariant. If the existing source/template guarantees exclusion, cite that invariant.
9. Are seven-car-only expectations consistent with the source-constrained Shadow250 selection rule, or could a valid Tamano A3 race with a different active field size be incorrectly treated in an outcome-affecting way?
10. Are class/name/prefecture/term/score/quinella_rate/S/B coordinate windows deterministic and sufficiently guarded against silent adjacent-column capture?
11. Does G1 preserve the frozen 5-field ownership exactly and avoid deriving/synthesizing any missing feature?

### C. G2 identity resolution and provenance
12. Verify the JKA term interval table against the official registration-date source, including non-contiguous late-registration exceptions.
13. The guard validates a candidate snum but does not itself define where candidate snum values come from. Is this missing provenance a P0/P1 blocker before first race?
14. Must candidate-snum discovery be frozen as a deterministic PRE-safe process before first use?
15. Must the seven rider examples be live-verified through the already-frozen KEIRIN.JP adapter before this implementation can be frozen, or are synthetic verifier tests sufficient when every real prospective use will fail closed on official identity mismatch?
16. Could a wrong but in-range snum cause accepted data for the wrong rider? Verify that all four identity checks prevent this.
17. Could name normalization, old/new kanji, prefecture normalization, or term representation create a false match or false reject? False reject is acceptable only if fail-closed and does not create post-outcome replacement.
18. Verify that registration number remains identity/routing metadata only and cannot enter model features, ranking, eligibility based on outcome, or candidate selection other than deterministic identity resolution.

### D. Leakage, trials, and authorization
19. Confirm no RESULT/PAYOUT/Price is read or inferred by G1/G2.
20. Confirm the two historical Tamano PDFs are source/parser validation artifacts only and do not consume a scientific trial or Shadow screen count.
21. Confirm current counts remain selected=0, prospective screen=0, prospective v3 scientific trial=0 unless an authoritative record explicitly says otherwise.
22. Confirm no global scoring, Lane-E, final-v3 proof, or wagering is authorized by this audit.
23. Confirm no source switch/provider fallback may occur mid-run.
24. Identify any hidden degree of freedom, post-hoc choice, source drift, parser ambiguity, identity ambiguity, or provenance omission not listed above.

## Issue format

For every issue provide:
- ID
- section/file
- exact failure scenario
- whether it can change race membership, features, or Prediction Lock
- exact correction
- severity: `P0_BLOCKER` / `P1_MATERIAL` / `P2_NON_BLOCKING`
- whether correction would require a NEW Shadow universe

## Final verdict

Return exactly one final verdict:

`APPROVE`

`CONDITIONAL APPROVE`

`REJECT`

### Meaning

**APPROVE** only if no unresolved P0/P1 remains before the first selected race and the auditor explicitly resolves the source-set-drift question. APPROVE may authorize freezing only the exact audited G1/G2 implementation. It does not itself select a race.

**CONDITIONAL APPROVE** = NOT FREEZABLE / DO NOT SELECT A RACE.

**REJECT** = HALT / DO NOT SELECT A RACE.

If any required fix changes a frozen source, adapter, or source role, state explicitly:
`NEW_SHADOW_UNIVERSE_REQUIRED_BEFORE_ANY_RACE`.

ECON_HOLDOUT1000 must remain SEALED under every verdict.
