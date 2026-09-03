# MULTIVERSE Automation Provider Idempotency v8 — Candidate only

This v8 successor starts from independently validated PR #88 exact head `4a72ef46116043094c7a8e494404956925a5b3bf` and addresses one specific v7 proof ceiling: a future remote effect can commit before a local receipt is durable. v8 does **not** contact a provider. It uses two independent local SQLite databases to model a local journal and a provider-side durable idempotency ledger.

## Protocol

The request binds operation key, task, role, semantic generation, candidate branch/head, canonical main, objective, protocol/adapter identity and an all-false real-authority envelope. `request_fingerprint` is SHA-256 of canonical request bytes. `idempotency_key` is deterministically derived from that fingerprint; callers cannot choose or rotate it.

The local sequence is intentionally split:

1. `BEGIN IMMEDIATE` on the local journal; create or verify `PREPARED`.
2. Commit and release the local writer transaction.
3. Call the independent `DeterministicRemoteSimulator` using the exact derived idempotency key.
4. The simulator commits one provider-side receipt/effect in its own database. Same key + same request converges; conflicts fail closed.
5. Start a **new** local writer transaction, verify provider receipt ID, request fingerprint, result hash, protocol version, effect count and the full inherited v7 role-result schema, then persist `OBSERVED`.
6. Only the validated result may be completed into the inherited relay.

A simulated provider call is forbidden while the local journal connection reports an open transaction.

## Crash/recovery model

v8 mechanically covers: crash before remote effect; remote effect committed but response lost before local receipt; local receipt committed before relay completion; and concurrent/replayed workers. Response loss after provider commit is recovered by lookup/reconciliation using the same idempotency key. The simulated provider logical effect count must remain exactly one.

Timeout/unknown state without a retrievable exact-key receipt fails closed as `V8_REMOTE_STATUS_REQUIRED`. v8 never invents a new key or blindly resends under uncertainty.

## Integrity and capability boundary

Provider receipt ID, request fingerprint, idempotency key, result hash and protocol version are bound before local durability. Malformed/tampered results reuse v7 `_validate_result_for_request()` and cannot become an `OBSERVED` local receipt. Exact runtime classes are required; subclasses/arbitrary adapters are denied.

Capability flags are exact: simulated_remote_effect=true; real_external_effect=false; network=false; live_provider=false; credential=false; spend=false; runtime=false. The implementation imports no network/provider client and reads no credentials or tokens.

## Policy boundary

v8 does not widen policy. End-to-end integration continues to use only the already-reviewed v5 task binding `automation-v5` + `agent/automation-orchestrator-policy-source-v5-20260903-v1`. The v8 branch existing in the repository does not authorize task execution on that branch.

## Proof ceiling

A PASS can prove only this local **simulated provider-side idempotency and reconciliation protocol**. It does not prove that any real provider supports equivalent idempotency keys, status lookup or receipt semantics. It does not authenticate provider, worker or reviewer identity. It authorizes no network, provider contact, credential use, spend, production, Core/Keirin adoption, merge, main/ruleset mutation or Runtime activation.

A later real-provider candidate must Fresh-review official provider-specific idempotency/status semantics, network/credential/spend boundaries, provider receipt integrity and crash/reconciliation behavior.

Runtime: OFF.
