# MULTIVERSE Cross-Chat Capability Convergence v1

Status: OWNER-ADOPTED REPOSITORY PREPARATION / CANONICALLY INTEGRATED / DISPATCHER HARDENING CANONICALLY INTEGRATED / FIXED SHARED-PIPELINE REINSTALLATION + ROUTING PROOF PENDING.

Purpose

This common operating layer prevents active MULTIVERSE chats from remaining on incompatible old shared procedures after the system improves.

The durable rule is:

Fresh canonical GitHub and the latest adopted common operating baseline outrank chat memory, old handoffs, and locally remembered common procedures.

Domain knowledge remains local to each lane. What converges is the shared operating interface.

Durable canonical state

Repository preparation:
- Owner adoption: Issue #156 / comment `5564870064`
- reviewed PR #153
- initial canonical integration: Issue #158 / completion `5564920334`
- initial canonical main: `8bb7def5a80217a80a7bf8f4ff5901b101afee63`

Dispatcher hardening:
- repair issue: #181
- exact reviewed/adopted PR #182 head: `337185b63d2badec4e2bb5b6b0d13c49765d19f1`
- exact reviewed tree: `879d0a0e1cccd3a09735da52f41e02e9bf989cbe`
- Lab PASS: `5570979079`
- T1 PASS: `5571006210`
- Auditor PASS: `5571163859`
- T2 PASS: `5571166316`
- technical closure: `5571205048`
- Owner adoption: Issue #185 / `5571470468`
- canonical integration: Issue #187 / completion `5571535293`
- current canonical main: `b7ee4cbb758b0c09f3ab90bd243c638e3899d24d`
- current canonical tree: `879d0a0e1cccd3a09735da52f41e02e9bf989cbe`
- canonical tree equals the exact reviewed PR #182 tree.
- PR #173-only extra import-time regression coverage is deferred to follow-up Issue #186.

Required resume behavior

Every active MULTIVERSE chat must:
1. Fresh Read canonical GitHub before claiming CURRENT or NOW.
2. Fresh Read convergence state in Issue #93.
3. Read the latest adopted common operating baseline.
4. Replace superseded common procedures with the latest adopted procedure.
5. Preserve domain-specific research state unless separately superseded.
6. Never ask the Owner to manually courier common protocol updates between chats.
7. While migration lock `5561567913` remains active, research lanes must not edit shared Independent Lab/Auditor Steps.

Shared review infrastructure

MULTIVERSE Independent Lab and MULTIVERSE Independent Auditor are shared infrastructure.

During dispatcher migration they are single-writer control-plane managed.

The repaired dispatcher implementation and repaired repository templates are now canonical through PR #182. This does NOT by itself prove the shared Buildkite Steps are updated to those repaired templates.

Therefore the current shared-infrastructure sequence is:
- fixed shared-pipeline reinstallation under separate single-writer control-plane authority;
- request-only routing proof with no per-job shared-Step edit;
- only after proof, migration-lock release.

Research lanes continue to:
- prepare Candidates;
- freeze exact heads/trees;
- publish durable machine-readable review requests;
- avoid shared Step mutation;
- avoid Build/Retry unless separately authorized.

Review request contract

Requests may use only allowlisted review primitives and remain exactly bound to:
- repo;
- PR;
- head;
- tree;
- base;
- canonical main;
- lane;
- request ID/comment;
- request SHA256;
- proof ceiling;
- execution state.

A request cannot inject arbitrary shell, Buildkite YAML, Python, credentials, merge commands, provider mutation, or Runtime activation.

Request identity and supersession

For one exact lane/repo/PR/head/tree/base/main key:
- the first request has no predecessor digest;
- a later same-envelope request must bind the immediate predecessor request SHA256;
- silent same-head replacement fails closed;
- changing canonical main creates a different exact-current envelope and requires a newly bound request for the new main;
- Auditor binds the exact upstream Lab request SHA256 and T1 provenance.

Migration sequence

- Phase 1 — repository Candidate: COMPLETE via PR #153.
- Phase 2 — Independent Lab -> T1 -> Independent Auditor -> T2 -> Owner adoption: COMPLETE.
- Phase 2.5 — initial canonical integration: COMPLETE via #158.
- Phase 2.6 — dispatcher hardening review/adoption/integration: COMPLETE via PR #182 / #185 / #187.
- Phase 2.7 — deferred import-time regression coverage follow-up: OPEN as #186.
- Phase 3 — one-time reinstall of fixed Lab/Auditor shared-pipeline definitions from repaired canonical main: PENDING.
- Phase 4 — prove a durable request routes without shared-Step editing: PENDING.
- Phase 5 — release migration lock and prohibit legacy per-chat Step replacement: PENDING.

Owner workload target

After proven installation, routine review YAML copy/paste count is zero.

Authority ceiling

This metadata sync grants no shared-pipeline installation/mutation, merge, canonical-main mutation, ruleset mutation, workflow dispatch/rerun, provider mutation, Runtime activation, production, protected-data access, live business effect, or spend.

Runtime remains OFF.
