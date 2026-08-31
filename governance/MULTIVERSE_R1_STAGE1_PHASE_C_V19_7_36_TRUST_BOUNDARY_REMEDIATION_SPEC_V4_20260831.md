# MULTIVERSE R1 Stage 1 Phase C — V19.7.36 Trust-Boundary Remediation Spec v4

Status: REVIEW-ONLY / NONCANONICAL / NO LIVE AUTHORITY
Date: 2026-08-31 JST
Supersedes v3 for successor-design review.

All v2 and v3 requirements remain mandatory. This v4 closes the final same-UID verify-to-use TOCTOU ambiguity identified by Independent Lab comment 5478365873.

## Mandatory no-race same-UID rule
For any security-relevant material that is mutable by the session UID, **pathname-based pre-exec/pre-load/pre-read verification is never a sufficient trust condition**, even when performed immediately before use. A frozen implementation MUST NOT authorize subsequent pathname `exec`, dynamic load, import, config read, helper discovery, CA/TLS read, credential read, or other security-relevant use merely because that pathname was just re-verified.

Every mutable same-UID security-relevant object MUST satisfy exactly one reviewed trust class at the instant of actual use:

### Class A — fd-bound / exact-byte-bound same-object use
The implementation once-opens the object with race-resistant flags/semantics appropriate to its type, authenticates the bytes/metadata from that opened object, and actual use is mechanically bound to that same opened object or to a sealed exact-byte derivative produced from those authenticated bytes. No pathname reopen is permitted between authentication and use.

For executable/code/data cases this means, as applicable, fd-bound execution, same-memory compile/exec, sealed memfd, exact opened-fd parsing/loading, or an equivalent mechanism that proves the used object is the authenticated object. If a platform/API cannot consume the already-authenticated object without pathname re-resolution, Class A is unavailable for that object.

### Class B — mechanically immutable against the session UID
The object and every authority capable of replacing or redirecting it are placed on a substrate that the session UID cannot mutate for the entire verify/use interval. This includes the object, containing directory chain, symlink/mount namespace relevant to resolution, backing content and configuration authority. Ordinary tmpfs ownership/mode such as `0600`/`0700` under the same UID is NOT immutable and does not qualify.

The implementation must prove the immutability mechanism, not infer it from convention. If the same UID can rename, unlink, rewrite, remount, redirect, alter a parent, or change a controlling config/search path, Class B fails.

### Class C — independent root-controlled immutable anchor
The object is resolved entirely through an independently trusted root-controlled/platform anchor whose complete path/dependency/configuration authority is not mutable by the session UID. The implementation must mechanically verify the applicable ownership/mode/type/mount/path-chain predicate and any exact identity required by the reviewed platform anchor contract. A same-UID writable parent, loader authority, helper/config path or dependency disqualifies the anchor.

## Prohibited shortcut
`verify(path); exec/load/read(path)` is explicitly forbidden as a trust-preserving pattern for mutable same-UID material. “Immediately before use”, “same command”, “same shell line”, `stat`+hash, or a second pathname hash does not close the race.

If an object cannot be consumed under Class A, B, or C, the implementation MUST fail closed before it can influence OAuth, GitHub identity/scope, ruleset/main/fence/environment decisions, dependency readiness, Step3, receipts, or any later authority.

## Subprocess closure strengthening
V3 subprocess closure remains mandatory, with this replacement for its post-auth drift barrier:

- Every executable, ELF loader, transitive/dynamic library, helper, exec-path component, config, credential material, CA/TLS material, repository-discovery input and other security-relevant subprocess authority must be Class A, B, or C at actual use.
- Re-verification alone is diagnostic only; it is not an authorization primitive for same-UID mutable material.
- If normal kernel dynamic loading necessarily reopens pathname-based libraries/config after verification, those dependencies must be Class B or C, or execution must move to a reviewed substrate that removes the same-UID mutation race. Exact hashing immediately before `execve(path)` is insufficient.
- PATH/environment closure cannot convert mutable pathname material into trusted material; executable/dependency resolution must independently satisfy A/B/C.
- Any helper dynamically selected after launch must already be within the frozen A/B/C closure; otherwise fail closed.

## Python/runtime strengthening
The same A/B/C rule applies to the bootstrap/authenticated Python boundary, Python executable, ELF loader, startup shared libraries, pure stdlib, stdlib zip, lib-dynload/native extensions and their transitive dependencies. No design may solve subprocess TOCTOU while leaving Python itself on verify-then-pathname-use semantics.

## Outermost Live-entry strengthening
The eventual reviewed Owner transport must itself obey the same rule. The startup artifact may not be pasted/executed as unauthenticated raw frozen contents and may not be pathname-verified then reopened. The outermost transport must once-open exact startup bytes, verify exact Git blob plus frozen SHA-256/size, and execute the same opened/in-memory authenticated bytes or an A/B/C-equivalent substrate.

## Matrix / receipt additions
The pre-OAuth matrix must explicitly record the selected trust class (A/B/C) and proof mechanism for every security-relevant object. `PREEXEC_REVERIFY_PASS` by itself can never satisfy a matrix row.

Required nonsecret failure categories include:
- `SAME_UID_TRUST_CLASS_UNSATISFIED_*`
- `FD_BOUND_IDENTITY_*`
- `IMMUTABLE_SUBSTRATE_*`
- `ROOT_ANCHOR_*`
- `PATHNAME_REOPEN_FORBIDDEN_*`
- `DYNAMIC_LOAD_TRUST_CLASS_*`
- `OUTERMOST_ENTRY_IDENTITY_*`

All prior stage-specific receipt and Python-not-started fallback requirements remain mandatory.

## Preserved safety/nonauthority
No weakening of v2/v3 bootstrap root of trust, subprocess full closure, sealed dependency handling, isolated Python, sanitized environment, current-main rebootstrap, exact ADMIN/PREFLIGHT/Step3 bindings, cause-preserving receipts, parent-shell survival or Owner-burden gate is authorized.

This design spec authorizes no Live execution, OAuth, Step3, Step4, `--apply`, production/main/ruleset mutation, writer-secret work, merge, workflow dispatch, Runtime state/tasks/Sources/scheduler, Runtime branch/sequence0, activation receipt/tag, or Runtime activation.

Runtime remains OFF.