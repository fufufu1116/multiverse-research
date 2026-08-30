# v19.7.16 executable-v2 — Revision-B proof specification

Status: FROZEN-CANDIDATE SUPPORT / NONCANONICAL / NO LIVE AUTHORITY

The Independent Lab must reject this candidate unless the implementation evidence mechanically establishes all items below against the exact frozen loader bytes.

## Outer status map
103 PLATFORM_CODESPACES
104 FRESH_PATHS
105 TMPFS_TRUST
106 GIT_CONTROL
107 CANONICAL_MAIN
108 RECOVERY_HEAD
109 REPO_STATE
110 RUNNER_TRUST
111 RUNNER_SHA256_COMMAND
112 RUNNER_SHA256_MISMATCH
113 RUNNER_LAUNCH
114 RUNNER_RETURN
115 UNKNOWN/UNMAPPED fallback only

## Complete-loader matrix
A conforming harness must invoke the complete exact loader entrypoint, not a copied fail() function and not an isolated gate fragment. It must provide controlled command/environment fixtures which permit all preceding gates to complete and force the selected target gate. Every 103..114 class must be reached through that complete entrypoint. It must additionally cover 115, harmless success through the handoff boundary, and Option-B runner nonzero. For each pre-handoff failure, assert exact preceding PASS-marker stdout prefix, exact fixed marker on stderr, exact outer status, no later PASS/RUNNER_START, no retry/fallthrough, and no dynamic path/environment/tool/Git leakage. For 114, assert RUNNER_START occurred, synthetic runner was invoked exactly once, its reviewed synthetic stdout/stderr are preserved, the fixed RETURN marker follows on stderr, outer status is 114, and no retry/fallthrough occurs.

A test that merely invokes fail(), copies one gate, or executes only a handoff fragment is explicitly nonconforming.

## Dependency collision proof
Mechanically fetch/read the immutable historical runner bytes at recovery head 19a14cfd019cceab199571b5d03d4dd0ba5bcd22, path governance/MULTIVERSE_R1_STAGE1_PHASE_C_PRE_OAUTH_CONTINUITY_RECOVERY_RUNNER_20260827_v1.sh, expected blob bc2b638b0db7fa8a0c23f0988cd9946f9e24b590; and unchanged Step3 ACTION blob c9459751e4b50c70fde1b94413b9c441dfbfccc4. Scan shell exit/return, Python os._exit/sys.exit and equivalent fixed exit mechanisms. Assert no fixed dependency status occupies 103..115. Dynamic child nonzero is not a separate outer status: after RUNNER_START the loader maps it to 114.

The candidate does not claim its own branch path equals the historical runner blob. Authority is recovery-head immutable dependency binding.

## Exact-byte transport proof
Bind loader path, Git blob, byte length and SHA-256. Assert UTF-8/ASCII-compatible exact bytes, one shell line, zero internal LF and no final LF. Deterministic builder output must byte-equal the exact action. Full action must parse with Bash. Every nonempty strict byte prefix must fail Bash parse, unless an independently equivalent complete truncation/copy-transport proof demonstrates no strict prefix can become a valid executable transport. Evidence from older loader bytes does not count.

## Canonical binding
Loader must bind both current reviewed main commit 5c1403c1f5aabb80d29e8c868440aede8888ce61 and tree 3d47741b4863411e5c36cb4c28925ac455ab6441. Old 74ea95e... authority is stale and must not be inherited.

## Immutable behavior
Historical runner OAuth/device-code secrecy contract remains unchanged. v19.7.14 NONMUTATING Step3 remains unchanged. No Step4, --apply, production mutation, merge, writer key, workflow dispatch, Runtime state/task/source/scheduler operation, or Runtime activation is authorized.

Runtime: OFF.
