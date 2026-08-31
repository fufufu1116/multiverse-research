# MULTIVERSE R1 Stage 1 Phase C — V19.7.36 Trust-Boundary Remediation Spec v1

Status: REVIEW-ONLY / NONCANONICAL / NO LIVE AUTHORITY
Date: 2026-08-31 JST

## Trigger
V19.7.35 one-shot pre-OAuth readiness failed closed with exact nonsecret reason:
`PHASE_C_V19_7_35_READINESS_DENIED:STDLIB_WRITABLE_OR_UNOWNED`
Startup chain returned rc 92. OAuth did not start. No Step3/Step4/apply/production/Runtime action occurred. The V19.7.35 approval is consumed.

## Safety objective
Do not solve this by accepting a mutable same-UID Python stdlib. Preserve the previously reviewed same-UID mutation threat model while removing the false assumption that the ambient Codespaces Python installation is root-owned/non-writable.

## Required architecture for successor implementation
1. Ambient `/usr/local/python/current` is bootstrap-only and must not become post-bootstrap import authority merely because its ownership/mode is convenient.
2. Before security-sensitive imports/execution, derive the exact Python stdlib/lib-dynload material needed by the reviewed path from a frozen, authenticated source or authenticate exact bytes before use.
3. Any material copied into the execution trust boundary must be placed in memory-backed storage, created fresh with restrictive ownership/mode, and then made immutable or otherwise exact-byte bound before import/execution.
4. Native extension loading must retain the sealed-memfd mechanism already reviewed for PyNaCl/cffi.
5. No pathname may be authenticated and then reopened as execution authority. Once-open -> exact bytes -> exact Git/blob/SHA identity where applicable -> same-memory execution remains mandatory.
6. Preserve isolated interpreter startup (`-I -S -B`, empty/sanitized environment) and reject ambient PYTHONPATH/user-site/sitecustomize/usercustomize/cwd authority.
7. Preserve direct pinned wheel download, exact SHA-256 reauthentication, sealed memfd wheel/native-extension loading, PyNaCl 1.6.2 roundtrip, exact ADMIN/PREFLIGHT/Step3 binding, current-main rebootstrap, and all nonmutation fences.
8. Add explicit stage-specific denial categories for every new trust-bootstrap operation; no foreseeable exception should collapse to an uninformative rc.
9. Preserve receipt durability/visibility and parent-shell survival.
10. Sweep all remaining pre-OAuth and post-OAuth assumptions that depend on Codespaces ownership, mode, mount, Python layout/version, executable path, `/proc/self/fd`, memfd sealing, tmpfs, swap, TLS/download behavior, Git availability, OAuth prerequisites, and exact canonical-main/Step3 inputs. Any assumption that can be checked before Owner OAuth should be checked before Owner OAuth.

## Forbidden shortcut
Do not globally `chown`, `chmod`, or otherwise mutate the ambient Codespaces Python installation to manufacture trust. Do not weaken the ownership/mutability gate without an equivalent exact-byte/immutability replacement.

## Owner-burden objective
No new Owner Codespace or approval until successor implementation is frozen and passes Independent Lab and Independent Auditor. Future Live should require the minimum practical Owner actions and must not retry a failed one-shot in the same session.

Runtime remains OFF. This spec itself authorizes no Live action.