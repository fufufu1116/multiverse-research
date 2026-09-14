# Minimum Kernel v1 SANDBOX R4 checkpoint

Status: SANDBOX / BENCHMARK ONLY / NOT ADOPTED
Date: 2026-09-14
Parent tracking: #499
Base canonical main: `e81f3d310d07d40eb6c11fe8233dade3d72a5ad2`
VNEXT Current State at Fresh Read: generation 15 / `ACCEPTED_FROZEN`
Runtime: OFF

This branch is an evidence/recovery checkpoint only. It does not alter main, grant authority, or constitute an Independent Lab/Auditor verdict.

## R4 hardening completed locally

- capability schema is `MULTIVERSE_SCOPED_CAPABILITY_V4`;
- signed `replay_domain` binds one-shot capability use to a persistent capability-use store;
- exact `required_subject` binding closes actor substitution;
- only P0 capability execution remains enabled in sandbox; P1/P2/P3 fail closed until exact execution-request/resource/parameter binding exists; P4 separately fails closed pending exact Owner Decision Receipt binding; P5/unclassified remain denied;
- immutable `PolicyRegistry` digest is signed and current-policy drift is denied;
- capability replay state and `SQLiteLedger` are hash-chained, persistent-ID namespaced, and require an external monotonic head anchor;
- anchor rollback is never auto-healed;
- whole-store / whole-ledger rollback against a newer external head is detected;
- top-level package API does not export `VerifiedCapability` or bare `verify_capability` as convenience authority surfaces;
- provider-neutral drafts exist for mutating execution binding, P4 Owner binding, public-key lifecycle/rotation/revocation, and the production external-head-anchor contract; no private/secret key material is present.

## Additional resumed self-red-team closure

**R4-F7 — false-CAS/same-new-head split-brain risk (HIGH):** an earlier R4 draft treated a failed external-anchor CAS as success if a follow-up read already equaled the deterministic desired next hash. With cloned local stores sharing one anchor, the CAS loser could incorrectly believe it also acquired the same one-shot transition.

Repair:
- `False` from external-anchor CAS is always failure, even when the current head already equals the desired next hash;
- loser rolls back local SQLite state and hard-stops;
- direct negative tests cover this for capability-use state and the main ledger;
- real two-process/two-local-DB clone races sharing one anchor now prove exactly one successful caller for the same capability and for the same deterministic ledger transition;
- capability multiprocessing tests use `spawn` rather than implicit `fork`.

## Current local proof

- normal Python: **80/80 PASS**
- optimized `python -O`: **80/80 PASS**
- Node fixed MV-CJSON-1 vectors: **6/6 PASS**
- encoding differential corpus: **1000/1000 PASS**
- strict Node raw-JSON adversarial parser: **15/15 PASS**
- strict raw-parser differential corpus: **1000/1000 PASS**
- compileall + AST/security surface scan: PASS
- anchored main-ledger benchmark: 8 processes / 1000 total appends / final local+external head equality PASS; ~18.934s local only, not an SLA
- one shared replay-store one-shot race: exact one success
- two cloned replay stores sharing one anchor with the same capability: exact one success
- two cloned ledgers sharing one anchor with the same deterministic append: exact one success

Local R4 ZIP SHA256: `9295e6d37a1d8223e6e7f78faca714b414504dbbf4a4d3c6be0e5e87f58ef030`

Local manifest SHA256: `68bce576b1c66496197bacff4cd84d8e776fcc6994ec75c0abb05d4996bb9178`

Evidence strength: **高信頼 (local sandbox only)**. Independent review/adoption readiness remains **未証明**.

## Remaining blockers

1. P1/P2/P3 exact execution-request/resource/context/parameter binding is draft-only and execution remains denied.
2. P4 Owner Receipt -> capability -> exact execution request binding is draft-only and execution remains denied.
3. Public verification-key rotation/revocation and historical-verification semantics are draft-only.
4. Production external monotonic anchor backend is not implemented. `spec/EXTERNAL_HEAD_ANCHOR_DRAFT.md` now fixes required linearizable CAS, strict false-CAS semantics, rollback-domain separation, failure handling, adversarial tests, and explicit recovery requirements, but no production backend is yet proven.
5. Trusted signer integration is not implemented/tested; no secret/private key material is handled here.
6. Role-separated RED TEAM / Independent Lab / Auditor is still required before any adoption.

## Fresh control reconciliation after timeout recovery

The earlier checkpoint sentence saying PR #483 was still waiting for its authorized Auditor Build is superseded by Fresh canonical receipts:
- Gate #486 was consumed by an Auditor infrastructure/bootstrap failure (`ModuleNotFoundError: No module named 'automation'`); no Auditor verdict was produced for PR #483 and no retry is allowed under that Gate;
- the repair moved to #489 / PR #496;
- Gate #497 was consumed by Build #115 and produced an authentic Independent Lab PASS on PR #496 (`5664255039`, findings `[]`, test_count `9`);
- a later duplicate dispatcher was correctly rejected after the trusted result already existed;
- no Auditor Build or Steps mutation for PR #496 is authorized by Gate #497.

## Formal-review routing

Do not launch or self-certify a new R4 review Build from this authoring context. R4 remains branch-only SANDBOX evidence. The system-improvement review path must first reconcile the current post-Lab state of PR #496 and any separately gated Auditor-Steps bootstrap action required to restore the independent Auditor lane. Only after that control path is Fresh-resolved should the exact R4 source be materialized as a current-main Candidate and sent through the normal role-separated Lab/Auditor governance with any required Owner Gate.

`HOLD_FOR_ROLE_SEPARATED_REVIEW`
`NO_MERGE`
`NO_ADOPTION`
`NO_SECRET_MATERIAL`
`RUNTIME: OFF`
