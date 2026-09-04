# Shared Engine separate-process consume-only worker v10 — Candidate

This successor exists because PR #96 Independent Lab correctly blocked a same-Python-process capability claim: Python function globals and monkeypatching are not a security boundary. v10 therefore moves the full reviewed PR91 -> PR88 v7 execution capability into a distinct local OS process and gives the client only a narrow local `AF_UNIX` JSON protocol.

The client module does not import or retain Shared Engine, the v9 worker, task DB, provider adapter, receipt stores, candidate binding, broker replay DB, or DB paths. Its protocol is exactly `PING`, `STEP`, and `STOP`; there is no task-id-directed call, submit/create-task opcode, arbitrary attribute/method dispatch, generic import, arbitrary path/command/env operation, pickle/marshal/eval/exec, or file-descriptor transfer. Unknown opcodes, malformed JSON, duplicate/extra keys, oversized messages and response binding errors fail closed.

## Two-finding strict-schema / inode-alias remediation

Independent Lab result `5535444044` found two additional material defects on exact head `0058edc00c3a3ec9f58e4af63bae69052108c48d`: JSON protocol version type confusion and replay-DB hard-link aliasing. Owner receipt `5535736466` authorizes only bounded v10-local closure of those two findings.

The broker now requires protocol version to be an **exact JSON integer** equal to `1`. JSON `true`, `1.0`, strings, null and every other wrong type are rejected before durable replay reservation, so they cannot consume replay capacity or reach `PING/STEP/STOP` dispatch.

Replay DB separation now checks both canonicalized path strings and existing filesystem identity via inode-equivalence checks. This closes distinct-path hard-link aliases where `realpath()` strings differ but task/bridge/provider/replay paths name the same underlying file. The reviewed boundary still excludes a malicious same-OS-user/root/filesystem controller racing the filesystem after validation.

Fresh canonical main advanced after the earlier freeze to `a6f56facc80709f2e7b8218d927484d522bfa356` via the Owner-authorized Shared Engine v8 canonical merge. The inherited v10 stack still carries its historical exact PR91/PR88 construction binding to `040d37f0a4e426cf2e119706484c90cbb48f0e56`. This Candidate records those as two different facts: **Fresh repository main observation** versus **inherited stack binding**. This remediation does not rewrite inherited PR96/PR91/PR88 files or claim a new inherited-stack rebind.

## Durable replay boundary

Before any syntactically valid request reaches broker dispatch, the privileged broker reserves its exact `request_id` plus canonical request fingerprint in a private SQLite deny-only anti-replay store. The reservation commits **before dispatch**. The store is bounded to exactly 256 accepted request IDs, has no TTL, no automatic eviction, and no reset/rotation API. A replayed request ID is therefore rejected across broker/serve-loop/process restart before a second dispatch or authoritative PR91 workflow mutation. Reuse of an old ID with a different opcode/body is conflict-rejected before dispatch.

Capacity exhaustion is intentionally fail closed: once 256 unique valid request IDs have been durably reserved, every unseen ID is rejected with no dispatch; existing IDs remain replay-denied. This Candidate does not provide or authorize replay-store reset, epoch rotation, garbage collection, TTL expiry, or automatic eviction. Any such lifecycle would be separate Owner-gated successor work because forgetting an old ID could reopen replay.

The anti-replay store is subordinate transport denial state, not a second workflow/task authority. It stores only request identity/fingerprint and fixed schema metadata; it stores no task workflow state, role result, provider receipt, completion state, or task-advance method. PR91 SQLite remains the sole workflow-state authority.

The reservation-before-dispatch ordering deliberately prefers safety over liveness. If the broker crashes after the durable reservation commits but before dispatch, that control pulse is lost: after restart the old ID stays denied and a fresh request ID is required to process the still-pending task. If dispatch already advanced a task but the response is lost, replaying the old request after restart is likewise denied, so it cannot consume a second preexisting task.

Broker-side `STEP` consumes only already-enqueued tasks through the inherited v9 worker, whose task-state authority remains PR91 SQLite and whose role execution remains the actual PR91 -> PR88 v7 deterministic local adapter/receipt path. PR #89 simulated remote behavior is not substituted.

The address-space boundary matters: client-side `__globals__`, class mutation or monkeypatching can damage the client process, but cannot rewrite broker process globals. Even if the client locally widens its own opcode allowlist, the independently running broker rejects every opcode outside its fixed schema. This Candidate does not claim that importing source code locally is impossible; it claims the client cannot obtain or mutate the broker process's engine object/address space through the reviewed IPC capability.

This is bounded offline process-isolation evidence, **not a deployed service or always-running daemon**. It is not authenticated external worker identity, does not protect against a same-OS-user debugger/root or a malicious party controlling the broker/filesystem or replay database, does not prove remote-provider exactly-once or distributed/network lease safety, and grants no production portability/adoption, merge, main/ruleset mutation, Core/Keirin adoption, protected Keirin data, provider/network/external effect, spend, secret/writer-key, workflow-dispatch/rerun, or Runtime activation authority.

Core and PIT-safe Keirin tasks use the same broker/worker path. Existing Keirin RESULT/PAYOUT/holdout/post-race/model-promotion/same-lineage-rescue/real-money boundaries are inherited without widening.

Independent Lab and Auditor must Fresh Read the exact Candidate and independently reproduce the former cross-broker-restart replay defect and current closure: same-ID STEP after restart, reservation-before-dispatch crash, response-lost-after-dispatch restart, concurrent same-ID reservations, conflicting reuse, PING/STOP replay, persistent capacity exhaustion with no eviction, malformed frames not consuming capacity, and anti-replay nonauthority. They must also recheck the former same-process reflective attack from the client side, malformed/expanded IPC attempts, distinct-PID/address-space evidence, inherited crash/restart/heartbeat/reclaim/fencing/multiprocess regressions, actual PR91/PR88 execution path, domain firewalls, CI history and the proof ceiling above. Candidate/CI cannot self-sign those verdicts.
