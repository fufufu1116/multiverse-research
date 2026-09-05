# Future Remote Multi-Host Evidence Requirements v1

This document is a preparation artifact only. It does not authorize or claim remote execution.

## Planned target class

`RENDER_PREPRODUCTION_TWO_SERVICE_SHARED_POSTGRES_NO_EFFECT_v1`

A later separately authorized execution phase must bind two distinct provider service identities and one shared PostgreSQL identity. Placeholder identities in the preparation contract are not evidence of deployed resources.

## Required real evidence

A future remote execution Candidate must durably bind all of the following:

1. **Exact provider identities**
   - distinct worker-A service identity;
   - distinct worker-B service identity;
   - one exact shared PostgreSQL identity;
   - region/account/environment binding without publishing secrets.

2. **Lease acquisition**
   - worker A acquires a lease while worker B is denied before expiry;
   - later successor acquisition is permitted only at or after the exact expiry/transfer condition;
   - each successful new acquisition produces a strictly larger fencing token.

3. **Fencing**
   - a stale owner cannot commit after successor ownership;
   - the current owner using an old token cannot commit;
   - stale tokens must be rejected at the shared authority state, not merely by process-local memory.

4. **Split-brain negative control**
   - two workers attempt ownership within a bounded overlap window;
   - at most one may hold write authority;
   - the loser produces an explicit rejection receipt.

5. **Cross-worker idempotency**
   - one worker records an idempotency key and payload digest;
   - after failover, the successor repeats the same key/digest;
   - the durable operation count remains one;
   - same key with a different payload digest is rejected;
   - `duplicate_external_effect=false`.

6. **Restart plus failover**
   - provider evidence must show distinct worker/service instances or process identities;
   - durable shared state survives restart;
   - successor ownership after restart is demonstrated without resetting the fencing sequence.

7. **Database semantics**
   - evidence must identify the exact transaction/locking/CAS mechanism used by PostgreSQL;
   - a repository-only state machine is not sufficient proof;
   - race-sensitive behavior must be demonstrated against the real shared database.

8. **Observability**
   - logs from both workers;
   - CPU/memory or equivalent provider metrics from both workers;
   - lease owner/fence/rejection events attributable to exact worker identities;
   - no HTTP SLO claim unless HTTP latency/error metrics are actually collected.

9. **No-effect boundary**
   - no live betting/trading/action provider integration;
   - no protected Keirin data;
   - no production credential;
   - no production deployment;
   - no Runtime activation;
   - explicit incremental spend authority must be separately granted before any resource creation.

## Required negative controls

The later evidence harness must fail closed for:

- same worker identity presented for both workers;
- stale Candidate head/tree/base/main;
- missing shared-state identity;
- non-monotonic fence token;
- stale owner accepted;
- stale token accepted;
- concurrent owners both accepted;
- duplicate idempotency request increments durable operation count;
- same key/different payload accepted;
- proof ceiling widened;
- any authority boolean not exact `false` unless separately authorized;
- secret-bearing connection strings persisted to GitHub.

## Current proof ceiling

`MULTI_HOST_PREPRODUCTION_SYNTHETIC_NO_EFFECT_PREPARATION_ONLY`

Runtime remains **OFF**.
