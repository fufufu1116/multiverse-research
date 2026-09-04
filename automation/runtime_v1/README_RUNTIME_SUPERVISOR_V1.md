# MULTIVERSE Runtime Supervisor v1 — construction

Runtime Supervisor v1 is a **sealed dry-run lifecycle layer** on top of canonical Shared Engine v8. It exists to prove bounded process lifecycle mechanics before any deployment/activation decision.

## Canonical binding

- canonical repo: `fufufu1116/multiverse-research`
- canonical main at branch cut: `a6f56facc80709f2e7b8218d927484d522bfa356`
- canonical tree: `2c957c4ad8a553b3a0e7122ebcdb22e75398afaf`
- parent Runtime readiness gate: issue #103
- construction issue: #104
- Runtime: OFF

## What v1 proves in construction

- durable SQLite supervisor metadata, journal and checkpoints using WAL/FULL;
- restart/incarnation journal and checkpoint survival;
- default-engaged kill switch;
- injected HMAC worker identity verification with bounded token age and no key persistence;
- bounded local step/loop execution;
- crash path journals failure and does not manufacture a success checkpoint;
- Independent Lab/Auditor role labels are explicitly rejected by the supervisor;
- all authority flags default false;
- no provider/network client exists in this runtime surface.

## Critical separation

The supervisor cannot manufacture Independent Lab or Independent Auditor verdicts. Formal review remains an external execution lane. Runtime may later route work to those lanes, but a local role label is never review authority.

## Candidate-only test control

The kill switch may be disabled only with the literal `TEST_ONLY_LOCAL_CANDIDATE` authority marker, and even then this module can execute only an injected local Python callback. This is test scaffolding, not a production activation API.

## Proof ceiling

This construction does **not** prove or authorize:

- deployed daemon/service availability;
- production credential provisioning or hardware-backed identity;
- live provider/network contact;
- external side effects or spend;
- protected Keirin data access;
- distributed leases or multi-host failover;
- provider-specific remote idempotency/exactly-once behavior;
- production portability;
- canonical Runtime activation.

Required sequence remains: construction CI -> exact-head Runtime Candidate freeze -> Independent Lab -> Independent Auditor -> separate Runtime activation authority.
