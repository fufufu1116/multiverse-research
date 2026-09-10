# MULTIVERSE Runtime Activation Integration Preparation v1

This directory is the repository-only preparation surface for Issue #136.

It starts from the exact Owner-adopted convergence Candidate lineage (PR #134 / head
`6778bbfada03dd70ffe47b1e715c470b6a671585` / tree
`538b98c6cd7d98207cf96871af620f43f42f629e`) and adds only the missing activation-
integration architecture model.

## What is prepared

- a deterministic distributed lease/fence state model;
- worker + instance identity bound to the current lease grant;
- monotonic fencing and stale-owner/stale-fence/expired-lease rejection;
- fence-bound inert checkpoints with restart/resume semantics;
- cross-worker idempotency by request key + payload digest;
- a static PostgreSQL schema/query contract mirroring the safety properties already
  demonstrated by the adopted real multi-host no-effect evidence;
- fail-closed readiness evaluation.

## What remains deliberately disabled

- durable kill switch: engaged by default;
- provider-effect adapter: disabled;
- Runtime activation bridge: disabled;
- Runtime activation readiness: false;
- Runtime: OFF.

The PostgreSQL material in this Candidate is a **static adapter contract only**. Candidate
tests do not import a database client, connect to Render, mutate provider state, read secrets,
or dispatch workflows.

## Proof ceiling

`RUNTIME_ACTIVATION_INTEGRATION_REPOSITORY_PREPARATION_ONLY`

Integration state:

`ACTIVATION_INTEGRATION_PREPARATION_NOT_ACTIVATABLE`

This is not an activation-ready claim. A later separately authorized/reviewed phase must
implement and remotely validate the PostgreSQL adapter and activation bridge before any
Runtime ON decision can be considered.

## Review path

`Candidate freeze -> Independent Lab -> T1 -> Independent Auditor -> T2 -> separate Owner decision`

Prior PR #134 review artifacts are provenance/adopted inputs only; they cannot satisfy the
new Candidate's Independent Lab/Auditor gates after this head changes.
