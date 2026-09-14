# Minimum Kernel v1 SANDBOX R3 checkpoint

Status: SANDBOX / BENCHMARK ONLY / NOT ADOPTED
Date: 2026-09-14
Base canonical main: `e81f3d310d07d40eb6c11fe8233dade3d72a5ad2`
VNEXT Current State at preparation: generation 15 / `ACCEPTED_FROZEN`
Runtime: OFF

This branch is an evidence pointer only. It does not alter main, grant authority, or constitute an audit verdict.

## R3 changes

- capability schema moved to `MULTIVERSE_SCOPED_CAPABILITY_V2`;
- every capability is one-shot and exactly one action scope;
- atomic `CapabilityUseStore` replay prevention was added;
- P4 capability execution now fails closed with `CAPABILITY_P4_OWNER_RECEIPT_BINDING_NOT_IMPLEMENTED` until a mechanically verifiable Owner Decision Receipt-to-execution binding is separately designed and role-separated reviewed;
- P5 and unclassified scopes remain denied;
- existing Ed25519 public-verifier-only boundary, receipt policy rebinding, receipt hash chain, SQLite/WAL ledger, trace identity, MV-CJSON-1 and optimized-Python hardening remain.

## Local evidence

- normal Python: 56/56 PASS
- `python -O`: 56/56 PASS
- Node fixed MV-CJSON-1 vectors: 6/6 PASS
- deterministic Python->Node differential corpus: 1000/1000 PASS
- ledger concurrency benchmark: 8 processes / 1000 total appends / integrity PASS (~0.304s local only)
- capability replay race: 8 concurrent consumers -> exactly 1 success / 7 replay rejections
- AST scan: no bare `assert`, `eval`, `exec` in kernel modules
- no private-key generation/loading/export/signing surface in kernel modules

Local sandbox ZIP SHA256:
`db90a1a2c602b23cd3f3f42e7eb39222bcb9a20856ff48f32f9ee7b40e11496d`

## Remaining blockers

1. P4 Owner-receipt -> capability -> exact resource/context binding is intentionally NOT implemented.
2. Public-key rotation/revocation and historical-verification semantics are not implemented.
3. External anti-rollback/head anchoring is not implemented for the main ledger or capability-use state.
4. Trusted signer integration is not implemented or tested end-to-end; no secret/private key material is handled here.
5. MV-CJSON-1 still lacks a second strict raw-JSON parser implementation; current Node evidence covers encoding/differential semantics, not duplicate-key raw parsing.
6. Role-separated RED TEAM / independent AUDIT is still required. The authoring ChatGPT context must not self-certify.

## Safe next route

Do not create a merge/adoption claim from this branch. When the system-improvement control lane is ready, materialize the exact R3 source as a repository candidate, bind it to current main, then send it through the existing role-separated Independent Lab/Auditor governance. Any Build/review requiring an Owner Gate remains gated.

`NO_MERGE`
`NO_ADOPTION`
`NO_SECRET_MATERIAL`
`RUNTIME: OFF`
