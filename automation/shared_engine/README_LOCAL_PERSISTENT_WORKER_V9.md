# Shared Engine Local Persistent Worker v9 — Candidate only

This layer proves a **bounded local process loop** on top of the independently validated Shared Engine v8 exact head `61f4e330fd5b1945dbfbceb223cbc71d205860f2` and the actual stacked PR #88 v7 deterministic local adapter `4a72ef46116043094c7a8e494404956925a5b3bf`.

It is not a deployed service, daemon, scheduler, continuous autonomous agent, or Runtime activation.

## Authority model

`automation/shared_engine/db.py` remains the sole workflow-state authority. The v9 worker does not expose task creation, GitHub mutation, policy application/widening, provider/network, credential, spend, production, Core adoption, Keirin adoption, or Runtime surfaces. It consumes only tasks that already exist in the reviewed Shared Engine database.

The worker generates its own bounded local process identity (`lpw9-...`). That identifier is only a local fencing identity. It is **not authenticated external worker identity** and must not be represented as such.

## Durable restart model

The worker uses only reviewed Shared Engine claim/reclaim/renew/transition gates and the existing PR #88 provider receipt path. It does not add another completion journal or second task authority.

Role operation identity is stable across lease reclaim: semantic generation is derived from durable Shared Engine transition events to `LAB_FIX_REQUIRED` / `AUDIT_FIX_REQUIRED`, not from the claim-generation fencing token. Therefore a crash/reclaim can change the fencing generation while replaying the same deterministic provider operation for the same role attempt. A new semantic retry after FIX_REQUIRED gets a new operation identity.

Covered bounded cases:

- restart before local role execution;
- crash after a durable deterministic provider receipt but before Shared Engine transition;
- restart after LAB FIX_REQUIRED;
- live heartbeat preventing premature reclaim;
- dead worker expiry followed by generation-bump reclaim;
- stale old worker/result fencing;
- two independent local processes dividing already-enqueued work;
- one local process crash followed by another process reclaiming and converging;
- graceful idle stop and active-stop behavior that never force-releases active authority.

## Polling and liveness ceilings

- lease: `0 < lease <= 120s`;
- heartbeat: positive and strictly less than half the configured lease;
- poll interval: `0.01s .. 5s`;
- one `run()` call: maximum 1000 bounded cycles.

There is no busy-spin and no unbounded retry loop. Active tasks are never silently released on shutdown. If a process disappears, existing lease-expiry/reclaim rules are the recovery boundary.

## Domain and provider boundary

Core and Keirin test tasks traverse the same worker class and the same exact PR91/PR88 execution path. Existing Keirin protected-resource/result/payout/real-money/model-promotion and related reviewed firewalls remain upstream of execution; this Candidate uses no protected Keirin data.

Only the existing sealed `DeterministicLocalAdapter` is executed. v9 does not import or use HTTP clients, sockets, provider SDKs, environment credentials, tokens, secrets, payment surfaces, or any live provider. PR #89's simulated-remote protocol is not silently substituted into this stack.

## Proof ceiling

A future Independent Lab/Auditor PASS may establish only the exact bounded local process-loop semantics at the reviewed v9 head. It does **not** prove or authorize:

- a deployed or always-running daemon/scheduler;
- continuous autonomous multi-agent operation;
- authenticated worker/provider/reviewer identity;
- remote-provider exactly-once behavior;
- distributed/network lease safety;
- production portability or adoption readiness;
- canonical/Core/Keirin adoption;
- merge/main/ruleset/production mutation;
- network/external effect/spend/secret use;
- workflow dispatch/rerun;
- Runtime activation.

Governance reality checkpoint `5528561753` and PR #91 independent closure `5528780140` remain part of the review provenance. Implementation and CI are evidence only and cannot self-sign Independent Lab or Independent Auditor verdicts.
