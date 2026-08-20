# MULTIVERSE FOUNDATION LAB REMEDIATION PLAN — 2026-08-20 v1

Status: `DRAFT_NONCANONICAL_REMEDIATION_PLAN`

This plan is fixed after independent Lab results on PR #16/#17/#18/#20/#21 and before remediation implementation on this branch.

## Evidence inputs

- PR #16 exact head `45b1721c73bafffcf1635af46e56e5f6c06f4a55` — `PASS_WITH_FIXES`, comment `5356392738`.
- PR #17 exact head `3d95f20d65eaaa0647f0c854b6bcebc31258938a` — `MATERIAL_BLOCK`, comment `5356396200`.
- PR #18 exact head `5240242543f475bb72fa5eaed4bb4d2db892062e` — `PASS_WITH_FIXES`, `G5_MAY_BE_ACCEPTED=YES`, comment `5356399606`.
- PR #20 exact head `0d896bc5349c8eb5837ec90f79de336af761d00c` — `PASS`, workflow-exposure evidence usable for G1, comment `5356402581`.
- PR #21 exact head `2bd3799bcb70200df68892f4fc1f7b79fe288b5d` — `PASS_WITH_FIXES`, G2/G3 require fresh refresh, comment `5356410689`.

Canonical main Fresh Read before this plan remains `819afb723c8f14000757b2e53b6664d71ab01227`.

## Locked remediation scope

1. **G4 — Zero-History Resume**
   - preserve blocked v1 as historical evidence;
   - create v2 as **orientation-only**;
   - v2 must be structurally incapable of authorizing scientific execution;
   - any embedded/self-asserted execution authorization must fail closed;
   - scientific execution authorization belongs to a separate future canonical Execution/Authorization Gate.

2. **G1 — Pause Guard containment semantics**
   - preserve v1 as historical evidence;
   - create v2 where `REVERSIBLE_CONTAINMENT` is not an unconditional Safe-Mode allow;
   - until a separately reviewed/auditable scoped repair authorization exists, containment is denied by this guard;
   - audit/recovery/evidence reads remain permitted and Keirin scientific execution remains denied under Owner pause.

3. **G2/G3 — State and Lifecycle freshness**
   - preserve v2 snapshot as historical evidence;
   - create v3 from Fresh Read evidence after the Lab final results;
   - represent `current_head`, reviewed head, Lab verdict and acceptance state separately;
   - PR #17 must be represented as `MATERIAL_BLOCK`, not PASS;
   - PR #18 may record G5 Lab allowance without treating the stacked G4 as repaired;
   - PR #20 may be used as bounded G1 workflow-exposure evidence;
   - PR #21 must be represented as stale-for-current-state after its own Lab result changed the review landscape.

4. **Integration check**
   - exact-head CI may execute governance/selftest code only;
   - it must not execute Keirin scientific workflows, open RESULT/PAYOUT, open holdout, inspect PR #15 quarantined metrics, open untouched validation or promote a model.

## Explicit non-scope

- no change to Accepted/Frozen vNext;
- no change to G5 Owner Assurance logic unless compatibility repair is strictly required;
- no Keirin model/scientific simulation execution;
- no PR #15 quarantined metric/artifact inspection;
- no ECON_HOLDOUT1000 access;
- no RESULT/PAYOUT access;
- no untouched validation;
- no model promotion;
- no external provider contact;
- no real-money wagering.

## Gate

This remediation does **not** permit Keirin scientific resume. After implementation and exact-head CI, independent Lab micro-review is required. Auditor review remains downstream of a clean Lab result.
