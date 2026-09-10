# Target Selection Authority v1

Issue: #114

## Owner delegation

Owner delegated selection of the bounded target-environment class and asked the control-plane/Commander to choose the safest practical next step.

## Selection

- environment_class: `PRE_PRODUCTION`
- target_id: `MULTIVERSE_PREPRODUCTION_LOCAL_SINGLE_HOST_NO_EFFECT_v1`
- runtime: `OFF`
- network: `DENY`
- external_effect: `DENY`
- spend: `DENY`
- protected_keirin_data: `DENY`
- production_credentials: `DENY`

This target ID denotes the bounded evidence target specification to be constructed and tested. It does **not** assert that a deployed host currently exists.

## Why this target

`PRE_PRODUCTION` is the least-authority class accepted by the target-environment contract. A local/single-host/no-effect target minimizes external dependencies and irreversible surfaces while allowing state-store, restart, lease/fencing, observability, kill-switch, backup/restore, and rollback drills to be specified and mechanically exercised before any production-shadow or activation-phase request.

## Required binding before Candidate seal

The Candidate must not claim real-target completion until all required evidence domains have concrete durable evidence refs, including artifact and rollback digests. Any evidence that is simulated/local must say so explicitly. Missing real infrastructure must fail closed rather than be represented as executed.

## Authority ceiling

This selection grants no Runtime activation, network, live provider, external effect, spend, protected Keirin data, production credential, merge, main/ruleset mutation, workflow dispatch/rerun, or production authority.

A later sealed Candidate still requires Independent Lab, Independent Auditor, target-environment closure, and separate `AUTHORIZE_RUNTIME_ACTIVATION_PHASE` authority.
