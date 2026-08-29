# MULTIVERSE R1 Stage 1 Phase C v19.7.7 — STEP3 EPHEMERAL EXECUTOR REDESIGN

Status: DRAFT REVIEW ONLY / NONSECRET / NO LIVE AUTHORITY
Date: 2026-08-29 JST

## Fresh authority basis
- canonical repo: `fufufu1116/multiverse-research`
- canonical main: `74ea95e59ac0654e1a0c1f811a178b3eef7b073c`
- canonical tree: `3d47741b4863411e5c36cb4c28925ac455ab6441`
- predecessor remediation head: `9f7d97fe01b46d951009a489aef3dbdd1d7cc111`
- predecessor branch: `agent/r1-stage1-phase-c-v19-7-6-step3-fd-offset-remediation`
- predecessor live result: `EXIT_92_AT_V19_7_6_STEP3_FD_VERIFY_ONLY`
- predecessor Owner one-shot approval: CONSUMED / CLOSED / NONREUSABLE
- predecessor Codespace: OWNER-CONFIRMED DELETED
- production mutation performed: false
- Runtime activation performed: false
- Runtime: OFF

## Problem statement
v19.7.6 removed the ambient-offset dependency by explicitly reseeking inherited FD4 before sourcing Step3, but it retained a broader architectural dependency: the exact Step3 payload was materialized before OAuth, assigned to fixed low descriptor 4, inherited into an interactive Bash, retained across the OAuth/post-OAuth/auth-gate sequence, and only much later reverified and sourced.

The v19.7.6 live session still terminated with exit code 92 at the Step3 boundary. The visible Owner evidence proves only exit 92; it does not prove which v19.7.6 verifier predicate failed. Therefore this redesign MUST NOT claim that FD-number reuse, descriptor replacement, seal drift, offset drift, or any other single predicate is the proven root cause.

The design defect being removed is narrower and independently supportable: security-critical Step3 execution should not require a long-lived fixed low descriptor to survive an interactive authenticated shell lifecycle when the same NONMUTATING semantics can instead be instantiated only after the read-only auth/scope/admin gate has passed.

## v19.7.7 architecture
### Remove long-lived Step3 FD custody
- Do not pre-materialize Step3 before OAuth.
- Do not reserve FD4 for Step3 across interactive Bash.
- Do not require Step3 bytes to survive the OAuth/device flow, post-OAuth reentry, trusted-Python gate, Step2.6 shell initialization, or auth/scope/admin gate.
- Step2.6 may remain independently protected as required for the authenticated shell bootstrap, but Step3 custody is decoupled from it.

### Post-gate ephemeral Step3 instantiation
Only after the unchanged read-only v19.7.2 auth/scope/admin gate returns PASS:
1. Fresh-fetch the exact reviewed standalone v19.7.7 NONMUTATING Step3 program from an immutable GitHub commit.
2. Verify exact UTF-8 length, SHA-256, and Git blob before execution.
3. Execute it immediately with trusted `/usr/local/python/current/bin/python -B` in a child process or process-replacing boundary that cannot return a usable authenticated shell after security-critical failure.
4. The program itself must be self-contained: it must not rely on inherited Bash functions, shell aliases, hashed command locations, a long-lived low descriptor, or a path-reopened temporary payload.
5. The program must reperform the required local canonical-execution-root verification before running the canonical NONMUTATING preflight.
6. It must perform zero production mutation, zero Step4, zero `--apply`, zero main/ruleset mutation, zero writer-key/secret operation, and zero Runtime activation.

### Diagnostic observability
The successor Step3 executor must emit bounded nonsecret terminal markers that distinguish at least:
- trusted Python binding failure;
- canonical execution-root verification failure with bounded categorical stage;
- canonical preflight subprocess nonzero;
- canonical preflight JSON parse/semantic failure;
- explicit success.

Raw auth material, token values, raw credential config, and unbounded stderr/stdout are prohibited.

A terminal/VS Code process exit must not collapse every predecessor failure into an indistinguishable generic `92` from the Owner perspective. The externally visible status must identify the bounded stage before process termination where technically possible.

## Fault-injection requirement before any live review
A deterministic offline/static harness must exercise the standalone executor logic or an isomorphic verifier layer for at least:
- normal success fixture;
- wrong canonical HEAD fixture;
- dirty worktree fixture;
- wrong critical-file blob fixture;
- preflight nonzero fixture;
- malformed preflight JSON fixture;
- preflight status mismatch fixture;
- `production_mutation_performed != false` fixture;
- `runtime_activation_performed != false` fixture.

Each injected fault must map to one expected bounded failure class. A generic-only exit result is insufficient.

## Required review unit
Independent Lab and later Auditor must review as one unit:
1. this redesign manifest;
2. exact standalone v19.7.7 Step3 NONMUTATING executor program;
3. exact immutable loader/action;
4. deterministic fault-injection harness and results;
5. preservation of the unchanged OAuth/device secrecy protocol and read-only v19.7.2 auth/scope/admin gate;
6. removal of the long-lived Step3 FD4 dependency;
7. fail-closed behavior with no usable authenticated-shell fallback after critical executor failure.

## Nonauthority
This document does not authorize a new Codespace, OAuth, terminal command delivery, authenticated Step3 execution, Step4, `--apply`, production mutation, provision-fence/Environment mutation, writer-key/secret operations, main/ruleset mutation, merge, Runtime branch/sequence0, activation receipt/tag, workflow dispatch, Runtime state/tasks/Sources/scheduler, or Runtime activation.

- `CAN_PROCEED_TO_IMPLEMENT_STATIC_V19_7_7_ARTIFACTS_NOW: YES`
- `CAN_PROCEED_TO_INDEPENDENT_LAB_NOW: NO`
- `CAN_PROCEED_TO_INDEPENDENT_AUDITOR_NOW: NO`
- `CAN_PRESENT_TO_OWNER_NOW: NO`
- `CAN_CREATE_CODESPACE_NOW: NO`
- `CAN_DELIVER_TERMINAL_COMMAND_NOW: NO`
- `PRODUCTION_MUTATION_AUTHORIZED_NOW: NO`
- `RUNTIME_ACTIVATION_AUTHORIZED_NOW: NO`
- Runtime: `OFF`
