# Minimum Kernel v1 SANDBOX R4 checkpoint

Status: SANDBOX / BENCHMARK ONLY / NOT ADOPTED
Date: 2026-09-14
Parent tracking: #499
Base canonical main: `e81f3d310d07d40eb6c11fe8233dade3d72a5ad2`
VNEXT Current State at Fresh Read: generation 15 / `ACCEPTED_FROZEN`
Runtime: OFF

This branch is an evidence pointer and recovery checkpoint only. It does not alter main, grant authority, or constitute an independent audit verdict.

## R4 hardening completed locally

- capability schema advanced to `MULTIVERSE_SCOPED_CAPABILITY_V4`;
- signed `replay_domain` binds a one-shot capability to its persistent capability-use store, closing fresh-store replay;
- `required_subject` exact binding added, closing actor-substitution use;
- only P0 capability execution remains enabled in sandbox; P1/P2/P3 fail closed until exact execution-request/resource/parameter binding exists; P4 separately fails closed pending exact Owner Decision Receipt binding; P5/unclassified remain denied;
- immutable `PolicyRegistry` digest is signed into capability and current-policy drift is denied;
- capability replay state is hash-chained, persistent-store-id namespaced and externally anchored;
- automatic anchor-behind healing was removed after self-red-team found it could hide anchor rollback;
- `SQLiteLedger` now requires persistent `ledger_id`, namespaced external monotonic anchor, exact local/external head equality, and anchor-before-local-commit append ordering;
- whole-store / whole-ledger rollback against newer external head is detected;
- top-level package API no longer exports `VerifiedCapability` or bare `verify_capability` as authority-bearing convenience surfaces;
- provider-neutral drafts added for mutating execution binding, P4 Owner binding, and public-key lifecycle/rotation/revocation. No private/secret key material is present.

## Local proof

- normal Python: **76/76 PASS**
- optimized `python -O`: **76/76 PASS**
- Node fixed MV-CJSON-1 vectors: **6/6 PASS**
- encoding differential corpus: **1000/1000 PASS**
- strict Node raw-JSON adversarial parser: **15/15 PASS**
- strict raw-parser differential corpus: **1000/1000 PASS**
- compileall + AST/security surface scan: PASS
- anchored main-ledger benchmark: 8 processes / 1000 total appends / final local+external head equality PASS; ~18.985s local only, not an SLA
- one-shot capability concurrency remains exact-one-success under 8 simultaneous consumers

Local R4 ZIP SHA256:
`5162abeaa63b8aaa4b9c44a512bf8697727e8dae94c42c212f43fe255a386842`

Local manifest SHA256:
`159170115efddaffa938b02fad0774522a8b5a01679110815eda69cf1c0c1665`

## Self-red-team finding of note

An intermediate R4 anchor design attempted to auto-advance an anchor that was behind a verified local chain. That behavior was removed: given the actual anchor-before-local-commit ordering, local-ahead is not a normal crash state and auto-healing could hide rollback of the external anchor. R4 now hard-stops on any head mismatch.

## Remaining blockers

1. P1/P2/P3 exact execution-request/resource/context/parameter binding is draft-only and execution remains denied.
2. P4 Owner Receipt -> capability -> exact execution request binding is draft-only and execution remains denied.
3. Public verification-key rotation/revocation and historical-verification semantics are draft-only.
4. Production external monotonic anchor backend is not implemented; local tests use a separate SQLite emulator only.
5. Trusted signer integration is not implemented/tested; no secret/private key material is handled here.
6. Role-separated RED TEAM / Independent Lab / Auditor is still required before any adoption.

## Formal-review routing

Do not create a merge/adoption claim from this branch. Current Control also has an unrelated already-authorized PR #483 Independent Auditor one-shot waiting for its Owner UI Build creation; R4 must not bypass or interfere with that role-separated review lane. When Control is ready, materialize the exact R4 source as a current-main repository candidate, bind the review request exactly, and use the existing Independent Lab/Auditor governance. Any required Owner Gate remains required.

`HOLD_FOR_ROLE_SEPARATED_REVIEW`
`NO_MERGE`
`NO_ADOPTION`
`NO_SECRET_MATERIAL`
`RUNTIME: OFF`
