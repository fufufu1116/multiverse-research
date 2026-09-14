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
- provider-neutral drafts exist for mutating execution binding, P4 Owner binding, and public-key lifecycle/rotation/revocation; no private/secret key material is present.

## Additional resumed self-red-team closure

A further HIGH-severity race was reproduced after the prior checkpoint: a failed external-anchor CAS was previously treated as success if a follow-up read already equaled the deterministic desired `entry_hash`. With two cloned local stores sharing one anchor, that can let the CAS loser believe it also acquired the same one-shot transition.

Repair now in local R4 package:
- `False` from anchor CAS is always failure, even when current head already equals the desired new head;
- loser rolls back local SQLite state and hard-stops;
- new negative tests cover this exact same-new-head/false-CAS case for both capability-use state and the main ledger;
- multiprocessing capability races use `spawn` rather than implicit `fork`.

## Current local proof

- normal Python: **78/78 PASS**
- optimized `python -O`: **78/78 PASS**
- Node fixed MV-CJSON-1 vectors: **6/6 PASS**
- encoding differential corpus: **1000/1000 PASS**
- strict Node raw-JSON adversarial parser: **15/15 PASS**
- strict raw-parser differential corpus: **1000/1000 PASS**
- compileall + AST/security surface scan: PASS
- anchored main-ledger benchmark: 8 processes / 1000 total appends / final local+external head equality PASS; ~18.934s local only, not an SLA
- one-shot capability race remains exact-one-success on one shared replay store
- false-CAS/same-new-head loser: fail-closed for capability-use state and ledger

Local R4 ZIP SHA256: `1ea68e7733be680f4c92b95123eaa32cde2826ce0520bcd40ac868732f8fd0d3`

Local manifest SHA256: `72c1a34bee4ee512ac32778d5283891675505912a6d77d5078e0f21b0a737777`

Evidence strength: **高信頼 (local sandbox only)**. Independent review/adoption readiness remains **未証明**.

## Remaining blockers

1. P1/P2/P3 exact execution-request/resource/context/parameter binding is draft-only and execution remains denied.
2. P4 Owner Receipt -> capability -> exact execution request binding is draft-only and execution remains denied.
3. Public verification-key rotation/revocation and historical-verification semantics are draft-only.
4. Production external monotonic anchor backend is not implemented; local tests use a separate SQLite emulator only.
5. Trusted signer integration is not implemented/tested; no secret/private key material is handled here.
6. Role-separated RED TEAM / Independent Lab / Auditor is still required before any adoption.

## Formal-review routing

Do not launch or self-certify a new review Build from this authoring context. Current Control has an unrelated already-authorized PR #483 Independent Auditor one-shot waiting for its Owner UI Build creation; R4 must not bypass or interfere with that role-separated review lane. Branch-only hardening/research may continue. When Control is ready, materialize the exact R4 source as a current-main repository candidate and use the existing role-separated Lab/Auditor path with any required Owner Gate.

`HOLD_FOR_ROLE_SEPARATED_REVIEW`
`NO_MERGE`
`NO_ADOPTION`
`NO_SECRET_MATERIAL`
`RUNTIME: OFF`
