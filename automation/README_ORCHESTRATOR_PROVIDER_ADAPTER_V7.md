# MULTIVERSE Automation Provider-Adapter Contract v7 — Candidate only

v7 stacks on independently validated PR #87 and introduces the next bounded transport layer: a **provider-neutral request/receipt contract** between the durable role relay and a role executor.

The runnable v7 adapter is deliberately sealed to `deterministic_local_fixture`. It performs no network access, provider contact, external effect, secret use or spend. Runtime injection of arbitrary adapter classes is denied. A real OpenAI/Anthropic/other provider implementation is **not** part of this Candidate and remains a separate future Owner-gated Independent Lab/Auditor review.

## Exact predecessor and authority ceiling

- predecessor PR #87 exact reviewed head: `e8c27fafcdb2e9ed4c54fdbc4f72d6d2fd386f0f`
- canonical main binding: `040d37f0a4e426cf2e119706484c90cbb48f0e56`
- v7 branch: `agent/automation-orchestrator-provider-adapter-contract-v7-20260903-v1`
- v7 manifest SHA-256: `35a769362d97af06259c49b7d415e5885f258c215c84f3eab63528b98c639652`

No policy widening is performed. v7 integration exercises only the already-reviewed v5 policy binding `automation-v5` + `agent/automation-orchestrator-policy-source-v5-20260903-v1`. A task that substitutes the new v7 branch is expected to fail the existing policy gate.

## Contract

`ProviderAdapterManifest` pins exact repository/source-branch/predecessor/main identity and an exact all-false authority object. `DeterministicLocalAdapter` is the only accepted runtime adapter class. `ProviderAdapterReceiptStore` pins the manifest in a separate SQLite database and serializes identical operation-key execution under `BEGIN IMMEDIATE`.

The provider-neutral request binds operation key, task, role, semantic generation, candidate head/branch, canonical main, objective, adapter identity and an all-false execution authority envelope. Before a result may become a durable adapter receipt, v7 validates the full bounded role schema and re-validates it on replay. IMPLEMENT requires `status=READY`, exact `candidate_head`, nonnegative integer `diff_lines`, exact zero `cost_microusd`, and nonempty `evidence_ref`. LAB/AUDIT require exact `reviewed_head`, nonempty `evidence_ref`, and `verdict` limited to `PASS` or `FIX_REQUIRED`; `FIX_REQUIRED` additionally requires a nonempty string `code` and string `detail`. Invalid output is rolled back before receipt/execution insertion and cannot become a durable poison receipt. A pre-existing malformed stored receipt is rejected on replay. Relay and receipt-store connections are closed on success, rejection and crash-injection paths.

Crash injection covers:

`relay claim -> deterministic local execution -> schema-validated durable adapter receipt -> crash before relay completion -> lease recovery -> same operation -> receipt reuse -> schema revalidation -> relay completion`.

The durable execution count remains one for this sealed local adapter after a crash **after the receipt**. This does not prove exactly-once for a future live provider. In particular, a crash during or after an external provider call but before a local durable receipt would require provider-specific idempotency and separate review.

## Fail-closed boundaries

- altered manifest or capability widening: denied;
- arbitrary runtime adapter subclass/object: denied;
- conflicting request replay under one operation key: denied;
- malformed IMPLEMENT/LAB/AUDIT result schema, wrong result head/reviewed head or missing evidence: rejected before durable receipt;
- malformed pre-existing stored receipt: rejected on replay;
- v7 branch substitution into the existing v5 policy: denied;
- network/live-provider/external-effect/spend/secret capability: absent and false;
- merge/main/ruleset/production/Core/Keirin/Runtime authority: absent.

## Proof ceiling

The v7 integration fixture deliberately scripts IMPLEMENT, LAB and AUDIT outputs to exercise the end-to-end transport contract. That fixture is **not evidence of independent reviewer identity or role separation**. Independent Lab and Independent Auditor remain separate external review stages. v7 also does not authenticate a future live worker identity, provider identity, provider receipt or provider-side idempotency token.

The SQLite writer transaction is safe here only because the accepted adapter is a deterministic local no-effect fixture. A future remote provider call must not simply be inserted into this transaction; it needs a separately reviewed provider-specific idempotency and crash-recovery design.

## Required review sequence

Exact push CI -> Candidate freeze -> Independent Lab -> Independent Auditor -> Candidate closure.

Candidate validation, if achieved, proves only the sealed provider-neutral contract with deterministic local execution. Any actual provider adapter, provider credential, network call, spend, authenticated worker/provider identity, canonical deployment, policy widening/application, merge or Runtime activation is a separate later gate.
