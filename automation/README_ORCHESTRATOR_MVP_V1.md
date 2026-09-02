# MULTIVERSE Automation Candidate Lane — Session-Independent Orchestrator MVP v1

Status: **CANDIDATE / NONCANONICAL / NO PRODUCTION AUTHORITY**

## Mission

Prove the minimum session-independent loop:

`TASK -> IMPLEMENT -> MECHANICAL GATE -> LAB -> AUDIT -> AUTO FIX LOOP -> DONE`

without using Chat UI as the execution engine and without touching the current Core Critical Path.

## Frozen common interface

The state vocabulary is domain-neutral and intentionally limited to:

`PENDING`, `IN_IMPLEMENT`, `MECH_GATE_FAIL`, `IN_LAB`, `LAB_FIX_REQUIRED`, `IN_AUDIT`, `AUDIT_FIX_REQUIRED`, `OWNER_GATE`, `DONE`, `ROLLED_BACK`.

Every task carries a `domain`. Core/Keirin/domain-specific behavior belongs behind the `RoleWorker` adapter; orchestration state does not branch by domain.

## Persistence and recovery

- one Python process is the MVP concurrency model;
- mutable orchestration state lives in SQLite;
- transactions are used for state/event changes;
- WAL + `synchronous=FULL` are enabled;
- every role call is checkpointed before and after;
- a stale active claim older than the heartbeat timeout is recovered without consuming a semantic retry;
- semantic failures and transient process/API/network-style failures use separate counters.

## Deterministic safety gate

Automatic continuation is allowed only when all of these are explicitly known and safe:

- candidate-only = true;
- no Stable/production effect;
- no secret/credential handling;
- no external effect;
- no money/spend;
- no protected data;
- no irreversible operation;
- no authority expansion;
- no unknown risk.

Unknown or risky values fail closed to `OWNER_GATE`. The worker/LLM never self-declares permission.

## Mechanical limits

- semantic retry budget = **2 retries after the initial attempt**, preserving a total of **3 attempts** while matching the existing Stage-1 retry budget of 2;
- heartbeat timeout = **300 seconds**, matching the existing Stage-1 five-minute invocation lease;
- transient retry budget = 3, candidate-local MVP recovery limit;
- diff budget = 500 changed lines, candidate-local MVP limit, not a global governance value;
- per-role returned execution budget = 300 seconds, candidate-local MVP limit;
- cost budget = 0 micro-USD for this proof.

The implementation denies widening the semantic retry or heartbeat ceiling. Candidate-local values are not written into accepted governance.

Two consecutive identical semantic failure fingerprints are treated as an abnormal loop and routed to `OWNER_GATE` even when retry budget remains.

## Worker boundary

`RoleWorker` is the common executor interface. A future direct-LLM adapter can implement it, but this MVP deliberately uses `ScriptedRoleWorker` only. The fixture performs no network calls, provider contact, secrets, spend, GitHub mutation, production mutation, or protected-data access.

This proves the orchestrator/recovery semantics without silently creating a new external-effect or spend authority.

## E2E proof target

The deterministic demo performs:

1. IMPLEMENT ready;
2. Mechanical Gate pass;
3. LAB returns one `FIX_REQUIRED`;
4. automatic remediation returns to IMPLEMENT;
5. Mechanical Gate pass;
6. LAB pass;
7. AUDIT pass;
8. DONE.

Required terminal counters are all zero:

- `OWNER_COPY_PASTE_COUNT=0`
- `OWNER_CONTINUE_PROMPT_COUNT=0`
- `OWNER_KEEP_ALIVE_COUNT=0`

Failure injection tests separately cover process crash/stale-step recovery, transient failure recovery, repeated failure fingerprint escalation, deterministic unsafe/unknown gating, and candidate rollback.

## Reuse boundary

This candidate is an upper orchestration layer. It does not replace the existing R1 Stage-1 runtime/CAS/authority components. Those existing components remain useful for authority, durable task semantics, leases, checkpointing and receipts when a future adoption gate connects a real executor.

## Explicit nonauthority

No main/ruleset/production mutation, Runtime activation, Step4, `--apply`, merge, workflow dispatch, writer-key/secret operation, protected Keirin data, provider contact, live external LLM call, or spend is authorized or performed by this MVP.

Independent Lab and Auditor review are still required before any broader adoption. Production/Core/Keirin adoption is a separate later gate.
