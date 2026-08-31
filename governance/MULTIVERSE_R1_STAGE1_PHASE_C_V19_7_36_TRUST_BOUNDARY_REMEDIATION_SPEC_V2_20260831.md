# MULTIVERSE R1 Stage 1 Phase C — V19.7.36 Trust-Boundary Remediation Spec v2

Status: REVIEW-ONLY / NONCANONICAL / NO LIVE AUTHORITY
Date: 2026-08-31 JST
Supersedes v1 for successor-design review.

## Trigger and invariant
V19.7.35 failed closed pre-OAuth with `PHASE_C_V19_7_35_READINESS_DENIED:STDLIB_WRITABLE_OR_UNOWNED` and startup rc 92. OAuth did not start. The consumed approval is not reusable.

The remediation MUST NOT weaken same-UID mutation resistance, trust ambient mutable Python merely because it is installed by Codespaces, or manufacture trust by recursively chown/chmod of the ambient installation.

## 1. Bootstrap root of trust — must be defined before Python execution
The successor MUST have an outer bootstrap whose security decision does not depend on importing or executing code from the ambient Python stdlib before that code has been authenticated.

The frozen implementation review MUST enumerate every executable/object used before the first authenticated Python byte executes, including at minimum:
- outer shell/transport executable and its exact absolute path;
- the selected Python ELF executable;
- ELF interpreter/dynamic loader resolved from that executable;
- every directly loaded shared object required to start that Python process before the authenticated boundary;
- any external utility invoked by the outer bootstrap.

For each item the implementation MUST either:
A. bind exact bytes to a frozen cryptographic digest from the reviewed candidate and once-open those bytes where execution mechanics permit; or
B. establish an independently justified immutable/root-controlled platform trust anchor that same UID cannot modify, with owner/mode/type/link/path-chain checks performed without depending on unauthenticated Python.

If neither A nor B can be established for any pre-boundary executable/object, fail closed before OAuth. No ambient user-writable executable, library, loader, PATH lookup, LD_PRELOAD/LD_LIBRARY_PATH, shell function/alias, or custom loader path may become bootstrap authority.

The implementation review MUST include the concrete bootstrap inventory and expected identities/trust predicates; prose such as “trusted system Python” is insufficient.

## 2. Authenticated Python runtime boundary
The Python executable is not sufficient by itself. The successor MUST explicitly bind the runtime material that can influence security-sensitive imports/execution.

### 2.1 Pure-Python stdlib
The implementation MUST provide a manifest of every pure-Python stdlib module/package reachable by the reviewed readiness/post-OAuth path before handoff to already exact canonical modules. Each entry MUST have a reviewed exact digest/size/source identity. Material must be once-open/read, authenticated, and then supplied from immutable memory-backed storage or an exact-byte in-memory importer. Authentication-then-pathname-reopen is forbidden.

### 2.2 stdlib zip
If a pythonXY.zip participates, its complete bytes MUST be exact-digest bound, once-open authenticated, and loaded only from immutable/exact-byte-bound storage. If it does not participate, it MUST be absent from effective import authority and this must be mechanically checked.

### 2.3 lib-dynload/native stdlib extensions
Every native stdlib extension reachable by the reviewed path MUST be enumerated and exact-byte bound. Preferred mechanism is sealed memfd, with exact digest, size, regular-file/source checks, full write, sealing, seal verification, readback digest, and exact `/proc/self/fd/<fd>` loading. Its transitive ELF dependencies must also be covered by the bootstrap/runtime native dependency trust model; sealing only the top-level `.so` is insufficient if its dependencies remain same-UID mutable.

### 2.4 Import authority
After boundary establishment, effective `sys.path`, `sys.meta_path`, importer cache and environment must be a reviewed closed set. `-I -S -B` remains mandatory. Ambient PYTHONPATH, user site, cwd, sitecustomize, usercustomize and unexpected namespace/package locations are denied. No fallback to ambient stdlib is allowed after the authenticated boundary.

## 3. Authenticated source and verifier
The successor implementation MUST state exactly where expected digests/bytes originate and who verifies them.
- Git-governed candidate/runtime material: exact Git blob plus SHA-256/size frozen in reviewed source or manifest.
- Third-party wheels: pinned URL plus exact SHA-256 already reviewed; direct HTTPS/no redirect plus post-download exact-byte reauthentication remains mandatory.
- Platform/bootstrap executable and ELF dependency identities: exact reviewed digest manifest or explicit immutable platform anchor predicate from section 1.

A verifier MUST NOT rely on material whose trust is established only by the result it is trying to verify. Circular trust is forbidden.

## 4. Required pre-OAuth prerequisite matrix
The frozen successor MUST mechanically check, before Owner OAuth whenever technically possible:
1. Codespaces identity variables present and exact expected class of environment.
2. Linux/x86_64 and supported Python ABI/version.
3. zero active swap.
4. `/dev/shm` memory-fs and required capacity/permissions.
5. `/proc/self/fd` availability and semantics needed by sealed loading.
6. memfd creation and all required sealing constants/operations, including readback.
7. bootstrap inventory exact identities/trust predicates: shell/transport, Python ELF, loader, shared libraries, utilities.
8. sanitized environment: no token/proxy/custom-CA/debug/PYTHON*/LD_* authority except explicitly allowed fixed values.
9. exact effective import authority closure after authenticated runtime construction.
10. pinned PyNaCl/pycparser/cffi network reachability, HTTP status/no redirect, exact SHA reauthentication, wheel structure, native-extension set, sealed load and PyNaCl 1.6.2 SealedBox roundtrip.
11. git executable/trust predicate and ability to create a fresh memory-backed execution checkout without mutation of canonical repo.
12. canonical main expected commit/tree reachability and exact comparison.
13. exact ADMIN/PREFLIGHT/Step3 Git blobs/bytes/size/SHA and once-open/same-memory feasibility.
14. required GitHub CLI/browser-device-flow client presence/trust predicate and nonsecret device-flow prerequisites that can be tested without starting OAuth.
15. receipt primary/fallback memory-fs paths fresh, non-symlink, exclusive-create capable, owner/mode/type/link/readback semantics.
16. no preexisting pydeps/execution/receipt roots that would make a one-shot ambiguous.

Anything in this list that cannot be checked before OAuth MUST be explicitly marked `POST_OAUTH_ONLY` in the reviewed implementation with a reason; silent deferral is forbidden.

## 5. Failure/receipt taxonomy, including pre-Python failures
The outermost transport MUST preserve the parent shell and produce a nonsecret stage-specific reason even when Python never starts.
Required categories include at minimum:
- `BOOTSTRAP_TRANSPORT_*`
- `BOOTSTRAP_EXECUTABLE_IDENTITY_*`
- `BOOTSTRAP_ELF_LOADER_*`
- `BOOTSTRAP_SHARED_LIBRARY_*`
- `BOOTSTRAP_ENVIRONMENT_*`
- `AUTH_RUNTIME_PURE_STDLIB_*`
- `AUTH_RUNTIME_STDLIB_ZIP_*`
- `AUTH_RUNTIME_LIB_DYNLOAD_*`
- `AUTH_RUNTIME_IMPORT_AUTHORITY_*`
- `PRE_OAUTH_MEMFD_*`
- `PRE_OAUTH_PROC_FD_*`
- `PRE_OAUTH_NETWORK_*`
- `PRE_OAUTH_PYNACL_*`
- `PRE_OAUTH_GIT_*`
- `PRE_OAUTH_CANONICAL_BINDING_*`
- `PRE_OAUTH_OAUTH_CLIENT_PREREQ_*`
- `RECEIPT_PRIMARY_*` / `RECEIPT_FALLBACK_*` / distinct receipt-write failure marker.

Every foreseeable exception/error path in the reviewed chain must normalize into a category plus nonsecret detail sufficient to avoid blind repetition. Raw generic rc without a reason is not acceptable when the outer transport can still report safely.

## 6. Existing closures that remain mandatory
- once-open -> exact bytes -> exact Git blob/SHA/size where applicable -> same-memory execution;
- no verify-path-then-reopen execution;
- sealed memfd wheel/native-extension loading for PyNaCl/cffi;
- direct pinned downloads and exact post-download reauthentication;
- current-main rebootstrap and exact canonical ADMIN/PREFLIGHT/Step3 bindings;
- receipt O_EXCL/O_NOFOLLOW/owner/mode/type/nlink/full-write/fsync/readback protections;
- one-line non-exec parent-shell-preserving Owner transport;
- stage-specific observability;
- Runtime OFF and NONMUTATING pre-OAuth/readiness scope.

## 7. Owner-burden gate
No Owner Codespace creation, OAuth, or new approval request until:
1. successor implementation is frozen;
2. Independent Lab PASSes the implementation and the concrete bootstrap/prerequisite inventory;
3. Independent Auditor independently PASSes it;
4. Core presents the exact frozen candidate.

A failed one-shot is never retried in the same Codespace. A discovered Live-only prerequisite must be added to the pre-OAuth matrix when technically checkable so the same class of Owner loop does not recur.

## 8. Explicit nonauthority
This spec authorizes no Live execution, OAuth, Step3, Step4, `--apply`, production mutation, main/ruleset mutation, writer-secret work, merge, workflow dispatch, Runtime state/tasks/Sources/scheduler, Runtime branch/sequence0, activation receipt/tag, or Runtime activation.

Runtime remains OFF.