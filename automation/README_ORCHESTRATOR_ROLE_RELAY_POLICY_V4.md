# MULTIVERSE Automation Candidate Lane — Policy-Bound Role Relay v4

Status: **CANDIDATE / STACKED ON VALIDATED PR #84 / NO CANONICAL OR LIVE AUTHORITY**

## Why v4 exists

PR #84 independently validated the durable v3 relay on current canonical main, but the v3 relay still hard-binds one candidate branch name in code. That is safe for one exact candidate but is not a reusable architecture for future Candidate Lane tasks.

v4 removes only that architectural limitation. It does **not** add a live LLM/provider, production mutation, secrets, spend, Runtime, Core adoption, Keirin adoption, or canonical-main adoption.

## Validated predecessor

The stacked base is PR #84 exact independently validated successor:
- PR #84 head at v4 construction: `422bb9c9214f6ceec9584efb48ce829d12f782b3`
- PR #84 Independent Lab PASS: `5522266540`
- PR #84 Independent Auditor PASS: `5522335044`
- PR #84 Candidate closure: `5522390222`
- canonical main at construction: `040d37f0a4e426cf2e119706484c90cbb48f0e56`

Every review must Fresh Read all values again.

## v4 design

New policy adapter:
- `automation/orchestrator_role_relay_policy_v4.py`

The underlying validated v3 queue/concurrency methods are inherited unchanged. v4 adds:
1. immutable `CandidateBindingPolicy` containing an exact canonical repository plus exact `(domain, candidate_branch)` pairs;
2. candidate branches must be conservative `agent/...` refs; main/master/state/research/gate/runner-style non-agent refs are not valid policy entries;
3. task input cannot widen policy — the task repo/domain/branch must exactly match a separately constructed policy entry;
4. one relay DB can support more than one explicitly pre-authorized candidate binding;
5. policy is durably pinned in SQLite metadata by canonical JSON + SHA-256 fingerprint;
6. reopening the same DB with a changed policy fails closed;
7. v4 uses relay DB schema version `2`, so the predecessor v3 `RelayStore` rejects a v4 DB instead of silently bypassing the v4 policy layer;
8. existing v3 operation-key, exact head/main replay binding, leases, recovery, stale-claim rejection, result-head binding, durable fixture receipt and concurrency behavior remain inherited.

The policy is exact-pair based rather than independent sets. For example, allowing `(automation, agent/a)` and `(keirin, agent/k)` does **not** allow `(automation, agent/k)`.

## Proof target

The v4 mechanical gate must independently execute:
- predecessor v3 relay unit regressions, including concurrent enqueue and recovery/heartbeat/completion races;
- v4 policy tests for multi-binding support, cross-pair denial, malformed/non-agent denial, DB policy pinning, changed-policy rejection, v3-adapter rejection, replay branch/head/main conflicts, repo/safety/spend denial, review-head binding, crash replay count exactly one and transport delay;
- exact-head full v2 Orchestrator + v4 policy relay E2E using the **runtime-selected current candidate branch** rather than a hardcoded source constant;
- Owner zero-touch metrics all `0`.

## Proof ceiling

v4 proves only a reusable **candidate-binding transport policy** around the deterministic fixture and validated v3 relay. It does not prove:
- arbitrary live-provider replay safety or exactly-once semantics;
- autonomous branch creation or GitHub mutation authority;
- generic production/Core/Keirin adoption;
- canonical deployment or Runtime activation.

Any live worker/provider adapter needs its own durable idempotency contract and separate Independent Lab/Auditor review. Any canonical adoption remains a separate Owner-gated transaction.

## Authority ceiling

- merge: NO
- canonical main mutation: NO
- ruleset mutation: NO
- production adoption: NO
- Core adoption: NO
- Keirin adoption: NO
- live provider integration/contact: NO
- spend: NO
- secrets/writer keys: NO
- protected Keirin data: NO
- workflow dispatch/rerun: NO
- Runtime activation: NO

Required sequence: push-only exact-head CI -> Candidate freeze -> Independent Lab -> Independent Auditor -> Candidate closure. The stacked PR must remain review-only unless a later separate adoption gate explicitly says otherwise.
