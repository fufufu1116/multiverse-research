# MULTIVERSE Multi-Host PRE_PRODUCTION No-Effect Preparation v1

This lane prepares the next evidence phase after adoption of the single-Render-service PRE_PRODUCTION evidence package.

## Exact planned topology

`RENDER_PREPRODUCTION_TWO_SERVICE_SHARED_POSTGRES_NO_EFFECT_v1`

Design target:

- two distinct planned Render PRE_PRODUCTION service workers;
- one planned shared PostgreSQL authority surface;
- exact worker identities `worker-a` and `worker-b`;
- monotonic fencing tokens;
- one lease owner before expiry;
- successor ownership at or after expiry;
- stale-owner and stale-fence writes rejected;
- cross-worker idempotency shared through the authority state;
- split-brain attempts rejected.

No actual second Render service, database, hostname, endpoint, credential, or provider resource is created by this package.

## Deterministic synthetic drill

The synthetic drill exercises:

1. worker A acquires fence token 1;
2. worker A applies one synthetic idempotent operation;
3. worker B is rejected before lease expiry;
4. worker B succeeds at expiry with fence token 2;
5. stale worker A is rejected;
6. worker B using stale token 1 is rejected;
7. worker B repeats the same idempotency key/payload and produces no second synthetic effect;
8. same key with a different payload is rejected;
9. split-brain acquisition is rejected while worker B owns the lease;
10. state snapshot/restore is canonical;
11. worker A later succeeds as the next owner with fence token 3;
12. prior worker B is rejected after the second failover.

Run:

`python -m unittest automation.multi_host_preprod_noeffect_preparation_v1.test_multi_host_contract -v`

## Future remote evidence requirements

A later separately authorized execution phase must independently prove, with real provider identities and real shared-state receipts:

- two distinct worker/provider identities;
- shared state identity;
- concurrent acquisition rejection;
- monotonic fencing across separate workers;
- stale-owner and stale-token rejection;
- successor failover;
- split-brain rejection;
- cross-worker idempotency;
- restart plus failover;
- provider logs and CPU/memory for both workers;
- database transaction/locking evidence appropriate to the real implementation.

## Proof ceiling

`MULTI_HOST_PREPRODUCTION_SYNTHETIC_NO_EFFECT_PREPARATION_ONLY`

Runtime remains **OFF**.
