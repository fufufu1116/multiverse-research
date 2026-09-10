# MULTIVERSE — Remote Multi-Host Render No-Effect Evidence v1

This directory contains the bounded real PRE_PRODUCTION two-worker evidence workload authorized by Issue #129 comment `5553241915` and executed under Issue #130.

## Exact target

`RENDER_PREPRODUCTION_TWO_SERVICE_SHARED_POSTGRES_NO_EFFECT_v1`

Planned services:

- `multiverse-preprod-multihost-worker-a-v1`
- `multiverse-preprod-multihost-worker-b-v1`

Shared state:

- Render Postgres `dpg-dadou0on74is73b09570-a`
- existing free PRE_PRODUCTION database
- dedicated table namespace `mv_mh1_`

## Real database mechanism

Lease acquisition and mutation authorization use PostgreSQL transactions and `SELECT ... FOR UPDATE` against the shared control row. Every new acquisition after expiry increments a durable fencing token.

The real drill is designed to prove:

1. worker A acquires token 1;
2. worker B is rejected before expiry;
3. worker B acquires token 2 after expiry;
4. stale owner A is rejected;
5. stale token 1 is rejected after B owns token 2;
6. same idempotency key/payload after failover does not create a second durable operation;
7. same key/different payload is rejected;
8. split-brain acquisition is rejected while B holds the lease;
9. restarted worker A later acquires token 3;
10. operation count remains one across restart and failover.

## HTTP boundary

Read-only:

- `GET /health`
- `GET /ready`
- `GET /evidence`

All POST/PUT/PATCH/DELETE requests return HTTP 403 with `state_changes_disabled_over_http`.

## Fail-closed environment gate

The service will not start unless all exact PRE_PRODUCTION no-effect bindings are present, including:

- `DATABASE_URL`
- exact worker ID
- exact Render service ID
- target class
- execution authorization
- Runtime OFF
- live business effect false
- protected Keirin data false
- production credentials false
- incremental spend USD 0
- exact shared Postgres ID
- exact drill ID

The database connection string must never be committed to GitHub or copied into chat.

## Proof ceiling

`REMOTE_MULTI_HOST_PREPRODUCTION_RENDER_NO_EFFECT_EVIDENCE_ONLY`

This workload does not authorize or implement production deployment, protected data access, live betting/trading/action effects, additional spend, merge/adoption, or Runtime activation.

Runtime remains **OFF**.
