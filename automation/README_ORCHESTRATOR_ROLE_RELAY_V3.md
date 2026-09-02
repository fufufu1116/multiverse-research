# MULTIVERSE Automation Candidate Lane — Durable Role Relay v3

Status: **CANDIDATE / NONCANONICAL / NO PRODUCTION AUTHORITY**

Predecessor independently validated candidate:
- PR #82 exact head at closure: `ab5fe2879c0e4f7aa92690f664240834804e7fd8`
- Independent Lab PASS: `5513971534`
- Independent Auditor PASS: `5514055456`
- Candidate validation closure: `5514114729`

This v3 successor does **not** merge or adopt v2. It starts from the independently validated v2 head and adds only the next missing transport layer: a durable role-relay contract between the v2 Orchestrator and future separately-running IMPLEMENT / LAB / AUDIT workers.

## Why v3 exists

v2 proved the bounded state machine, exact-head binding, crash recovery, retry accounting, safety gates, hard timeout/heartbeat, and replay-safe operation-key contract.

The remaining architectural gap is that the v2 `RoleWorker` is still invoked as a child process of the Orchestrator. Real session-independent operation needs a durable handoff so a role worker can run outside the Orchestrator process and can finish after the originating chat/process disappears.

v3 adds that durable handoff without adding a live LLM/provider.

## v3 candidate design

New module:
- `automation/orchestrator_role_relay_v3.py`

The relay uses a **separate SQLite database** from the v2 orchestration-state database:
- WAL journal mode;
- synchronous FULL;
- one durable job per stable v2 `operation_key`;
- exact task / role / semantic generation / candidate branch / candidate head / canonical main binding;
- candidate-only safety and zero-spend requirement;
- `QUEUED -> CLAIMED -> COMPLETE` transport state;
- bounded claim lease (`<=60s`);
- worker heartbeat that renews the lease;
- expired claim recovery back to the same durable job;
- stale-claim completion rejected;
- identical enqueue replay is idempotent;
- conflicting duplicate result is rejected;
- IMPLEMENT result must bind exact `candidate_head`;
- LAB/AUDIT result must bind exact `reviewed_head`;
- every result requires a nonempty evidence reference.

`RelayRoleWorker` implements the already-validated v2 `RoleWorker` contract and declares `replay_safe = True`. On replay it reuses the same durable operation key/job rather than creating a second logical role job.

## External-worker replay proof boundary

The candidate includes `DurableFixtureReceiptStore`, a deterministic stand-in for a future external worker/provider adapter.

The failure injection is deliberately at the dangerous boundary:

1. relay job is claimed;
2. fixture performs the logical role operation;
3. fixture durably records the operation-key receipt;
4. worker crashes **before** completing the relay job;
5. claim lease expires;
6. another worker reclaims the same job;
7. the receipt is reused;
8. relay result completes;
9. fixture execution count remains exactly `1`.

This proves the required durable replay contract for the fixture. It does **not** prove exactly-once behavior for an arbitrary future LLM/provider. Any future live adapter must provide its own durable operation-key receipt/idempotency mechanism and pass a separate Independent Lab/Auditor adoption gate.

## Exact-head integration proof

The v3 integration test runs the existing v2 Orchestrator unchanged with `RelayRoleWorker` as its worker adapter and a separately-running fixture agent.

Expected route:

`IMPLEMENT -> LAB FIX_REQUIRED -> IMPLEMENT -> LAB PASS -> AUDIT PASS -> DONE`

Required result:
- exact candidate head preserved;
- one semantic remediation retry;
- `OWNER_COPY_PASTE_COUNT=0`;
- `OWNER_CONTINUE_PROMPT_COUNT=0`;
- `OWNER_KEEP_ALIVE_COUNT=0`.

## Mechanical gate

On the exact v3 candidate checkout:

`python automation/mechanical_gate_orchestrator_role_relay_v3.py --expected-head <V3_HEAD> --canonical-main <FRESH_MAIN_SHA>`

The gate:
- rejects checkout/head drift;
- AST-parses v3 source/tests;
- rejects common live-network/provider imports;
- checks relay safety/replay source invariants;
- runs relay unit tests;
- runs exact-head full v2-Orchestrator + v3-relay integration E2E;
- prints explicit zero-touch and nonauthority markers.

## Explicit authority ceiling

This candidate authorizes **none** of the following:
- merge;
- canonical main mutation;
- ruleset mutation;
- production adoption;
- Core adoption;
- Keirin adoption;
- live direct-LLM/provider integration;
- provider contact;
- provider spend;
- secret/writer-key use;
- protected Keirin data access;
- workflow dispatch/rerun;
- Runtime activation.

The GitHub pre-Lab workflow is push-only on the v3 candidate branch, read-only (`contents: read`), and exists only to produce exact-head independent execution evidence.

The next valid sequence is:
1. exact-head push CI;
2. Candidate freeze;
3. Independent Lab;
4. Independent Auditor;
5. Candidate closure;
6. separate later adoption gate.
