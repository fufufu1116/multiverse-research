# Keirin Authority Reconciliation Candidate v1

Status: `DRAFT_NONAUTHORITATIVE_FAIL_CLOSED`

Date: 2026-09-13 JST

## Purpose

Record the currently observed authority conflict between canonical `main` and the long-lived Keirin research branch, preserve V3-V7 evidence without promotion or deletion, and define the smallest safe review path before any further economics / RESULT-PAYOUT / fresh-validation work.

This file is a governance review candidate only. It grants no scientific execution, data access, scope expansion, Runtime, wagering, spend, provider, credential, adoption, merge, or production authority.

## Fresh bindings at candidate construction

- canonical repository: `fufufu1116/multiverse-research`
- canonical main after immediate content-restoring revert of the write incident recorded below: `49a03a01fb401ba3d3a09521928796caef4ecdfa`
- canonical main tree: `fd64de45f68359404300d1c88e2d7778ecaa8401`
- pre-incident content-equivalent main: `e875d491853ab9a27158b617ff185d14ac804039`
- active Keirin research branch observed: `research/keirin-real-evidence-dual-lane-20260901-v1`
- active branch observed head: `862240f0ffd7960eda99108982d068fa4e7fe794`
- control issue: `#394`
- Keirin continuity issue: `#377`
- Control escalation comment: `#394 / 5652502525`
- Keirin fail-closed continuity comment: `#377 / 5652503609`
- Runtime: `OFF`
- automatic betting: `OFF`

Every review must Fresh Read these values again and return stale/no-verdict if relevant bindings moved.

## Controlling main-side evidence currently observed

Canonical `main` still contains the scope-specific 2026-08-21 Keirin authorization chain whose Owner-facing and machine-readable state says execution is Synthetic-only.

Relevant main-side records include:
- `KEIRIN_NOW.md`
- `v3/historical_all_market/governance/CURRENT_STATE_KEIRIN.json`
- `governance/KEIRIN_LIMITED_SYNTHETIC_EXECUTION_AUTHORIZATION_RECEIPT_20260821_v1.json`
- authorization commit `2496636a8782d195c7e7a7f8899dc9cfe2d7ed67`

That authorization explicitly does not extend to economics / bankroll evaluation, real-world or untouched validation, RESULT/PAYOUT, ECON_HOLDOUT1000, model promotion, external provider contact, automated bulk collection, or real-money wagering. It also states the scope-specific Owner Gate cannot be reused for other scope expansions.

Fresh main/PR/issue/commit searches performed during reconciliation did not locate a later canonical scope-specific Owner Gate receipt that explicitly supersedes this Synthetic-only authorization for the historical-economics / RESULT-PAYOUT work represented by V3-V7.

## Conflicting branch-side evidence

The active Keirin branch records later historical/virtual-world economics work through V7, including:
- branch current state successor `v3/historical_all_market/continuity/KEIRIN_CURRENT_STATE_v4.json`;
- append-only experiment ledgers through `KEIRIN_EXPERIMENT_LEDGER_v4.jsonl`;
- V3 positive-but-uncertain economics evidence;
- V4 independent replication failure;
- V5/V6/V7 exposed-only development failures;
- protected-state assertions that `ECON_HOLDOUT1000` stayed sealed, `DEV2000` RESULT/PAYOUT stayed unopened for new tuning/validation, Runtime stayed OFF, automatic betting stayed OFF, and no real money/spend/live/prod authority was used.

Issue `#377` is explicitly a continuity/non-authority surface. Branch CURRENT / rule / ledger records preserve scientific continuity but cannot by themselves widen a main-side Owner Gate.

## Fail-closed classification proposed for independent review

Until a genuine superseding authority is identified or a new governed scope is adopted, classify the V3-V7 branch work as:

`PRESERVE_HISTORICAL_EVIDENCE__AUTHORITY_NOT_VERIFIED__NO_PROMOTION_NO_NEW_EXECUTION`

Meaning:
1. do not delete, rewrite, hide, or relabel the underlying experiment artifacts as if they never happened;
2. do not treat existence of branch commits, workflows, ledgers, successful Actions runs, or scientific preregistration as execution authority;
3. do not use V3-V7 to justify opening a fresh target, RESULT/PAYOUT access, model promotion, live execution, or real-money action;
4. do not launch V8 economics scoring while reconciliation is unresolved;
5. retain negative and positive results as historical evidence for later governance/scientific audit;
6. any future use of already-exposed V3-V7 data must be separately permitted by the authority ultimately adopted; this candidate does not grandfather it.

This classification is a candidate for independent review, not a self-issued canonical status.

## Immediate protected boundaries

Fail closed now:
- `V8_ECONOMICS_SCORING = DENY`
- `NEW_RESULT_PAYOUT_ACCESS = DENY`
- `NEW_FRESH_VALIDATION_TARGET_ACCESS = DENY`
- `ECON_HOLDOUT1000 = SEALED_DO_NOT_ACCESS`
- `DEV2000_RESULT_PAYOUT_FOR_NEW_TUNING_OR_VALIDATION = DO_NOT_OPEN`
- `PROBABILITY_RETUNE = DENY`
- `REAL_MONEY = DENY`
- `AUTOMATIC_BETTING = OFF`
- `RUNTIME = OFF`
- `PROVIDER_CONTACT = NO_NEW_AUTHORITY`
- `SPEND = NO_NEW_AUTHORITY`
- `CREDENTIAL_USE = NO_NEW_AUTHORITY`
- `LIVE_OR_PRODUCTION = NO_NEW_AUTHORITY`

## Minimal remediation sequence proposed

1. **Independent governance/scientific classification** of this exact candidate and the cited main/branch evidence. Determine whether any later authority exists that this search missed; if yes, identify the exact receipt/comment/PR/commit and exact scope.
2. If no superseding authority exists, formally classify V3-V7 as preserved historical evidence with no promotion/new-execution authority. Do not retroactively invent authorization.
3. If the Owner still wants historical offline economics research to continue, construct a new, scope-specific authorization candidate from Fresh canonical main. It must precisely define source/data-rights assumptions, PRE/PRICE vs RESULT/PAYOUT separation, allowed historical data, evidence class, fresh-holdout rules, no-real-money/no-live boundaries, and fail-closed limits.
4. Route that exact scope through the existing independent sequence required for material scientific authority expansion: Independent Lab -> Independent Auditor -> scope-specific Owner Gate -> separate canonical adoption/transition.
5. Only after the new authority is canonically adopted may a successor experiment be preregistered and executed. Scientific design may use external AI review as advisory input, but no advisory model can supply authority.
6. Keep `ECON_HOLDOUT1000` sealed unless a later, explicit holdout-opening gate separately authorizes it. A general historical-economics gate must not silently include that final holdout.

## Future scientific design held pending authority

If authority is later restored, the preferred next scientific step is not another broad threshold search. The first candidate should be a preregistered fixed-policy reproducibility/convergence diagnostic or another independently justified lineage, with no post-result rescue, meeting-disjoint evaluation, meeting-level uncertainty, and clear multiple-testing control. This section is planning only and authorizes no scoring or data access.

## Review questions

Independent reviewers should answer:
1. Does canonical main still control the Keirin scientific scope as Synthetic-only absent a later exact superseding gate?
2. Is any later canonical Owner Gate / Auditor / adoption receipt sufficient to authorize V3-V7 historical economics and RESULT/PAYOUT? Cite exact evidence if yes.
3. If no, is the proposed preservation classification appropriate without deleting or scientifically rewriting V3-V7 evidence?
4. What is the minimum new scope-specific authorization sequence required before historical economics can resume?
5. Must source/data-rights admission be resolved as part of, or before, that scope expansion?
6. Which already-exposed V3-V7 datasets may be used after future authorization, and under what evidence classification?
7. Confirm that this candidate itself grants zero execution/data-access authority.

## Repository-write incident during preparation

During this reconciliation session, an erroneous tool call created an empty file `governance/THIS_WILL_NOT_BE_CREATED` directly on `main` in commit `6890187571686ebcefd106792d761ef42d380a46`. It was immediately deleted in commit `49a03a01fb401ba3d3a09521928796caef4ecdfa` without force-resetting or rewriting history. Fresh verification shows the post-revert main tree is exactly `fd64de45f68359404300d1c88e2d7778ecaa8401`, the same tree as pre-incident main `e875d491853ab9a27158b617ff185d14ac804039`. Therefore repository content is restored exactly, while the two history-only commits remain visible for audit. The incident itself grants no authority and is not hidden.

Prevention rule for this work: never use default/main as a file-write probe; create/verify a dedicated branch first, and perform candidate writes only there.

## Explicit nonauthority

This candidate does not authorize:
- merge/adoption;
- scientific execution;
- historical economics scoring;
- RESULT/PAYOUT access;
- fresh holdout selection/access;
- ECON_HOLDOUT1000 opening;
- DEV2000 protected-result use;
- source admission;
- provider/network contact;
- credentials;
- spend;
- production/live effects;
- real-money wagering;
- Runtime activation.

`KEIRIN_AUTHORITY_RECONCILIATION_CANDIDATE_ONLY`
`FAIL_CLOSED`
`RUNTIME: OFF`
`AUTOMATIC BETTING: OFF`
