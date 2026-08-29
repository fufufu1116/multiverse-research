# MULTIVERSE R1 STAGE 1 PHASE C v19.7.16 — HOST-VISIBLE EXIT-CODE OBSERVABILITY REQUIREMENTS

Status: DRAFT / READINESS REVIEW REQUIRED / NO LIVE AUTHORITY
Date: 2026-08-30 JST

## Incident basis

The exact independently reviewed v19.7.15 v5d one-shot diagnostic session terminated fail-closed with the Owner-facing VS Code host reporting `/bin/bash` exit code `88`. The fixed `PHASE_C_V19_7_15_FAIL_*` terminal marker was not recovered before the dedicated Codespace became unavailable. The session and Owner receipt are consumed/nonreusable. Root cause remains INDETERMINATE.

This remediation MUST NOT infer which v5d gate fired. Its sole purpose is to make a future reviewed fail-closed class recoverable from the host-visible process exit code even when the terminal transcript is lost.

## Required design

1. Preserve the reviewed fixed-marker transcript contract. Before `PHASE_C_V19_7_15_RUNNER_START`, successful completed gates may emit only the exact ordered fixed PASS-marker prefix; a loader-controlled failure emits its exact fixed failure marker to stderr and exits nonzero. No dynamic sensitive output may be added before the handoff.

2. Replace the single generic loader failure exit code with an exact allowlisted one-to-one mapping from reviewed failure class to process exit code. Proposed frozen mapping:

- `PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES` -> 70
- `PHASE_C_V19_7_15_FAIL_FRESH_PATHS` -> 71
- `PHASE_C_V19_7_15_FAIL_TMPFS_TRUST` -> 72
- `PHASE_C_V19_7_15_FAIL_GIT_CONTROL` -> 73
- `PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN` -> 74
- `PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD` -> 75
- `PHASE_C_V19_7_15_FAIL_REPO_STATE` -> 76
- `PHASE_C_V19_7_15_FAIL_RUNNER_TRUST` -> 77
- `PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND` -> 78
- `PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_MISMATCH` -> 79
- `PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH` -> 80
- `PHASE_C_V19_7_15_FAIL_RUNNER_RETURN` -> 81

3. The mapping is diagnostic metadata only. It MUST NOT change gate order, success behavior, retry policy, OAuth/device-code secrecy, runner ownership after `RUNNER_START`, Step2.6, scope/admin checks, v19.7.14 NONMUTATING Step3, or any authorization boundary.

4. A failure code MUST be produced only through the reviewed loader failure path for its bound class. Unknown/unmapped marker input MUST fail closed with a separately fixed non-success code and MUST NOT silently default to another reviewed class.

5. Every literal reviewed `fail <MARKER>` call site MUST be mechanically bound to exactly its declared exit code. The proof MUST inspect the exact frozen loader source, collect every literal call-site occurrence, prove full reviewed failure-class coverage, and fail if a call site is rebound, removed, duplicated into a conflicting class, or an expected mapping entry is wrong.

6. The v5d mechanical PASS-prefix binding remains required. For every actual pre-handoff failure call site, the proof MUST still derive the number of real preceding PASS-marker positions from exact source positions and assert equality with the reviewed expected prefix count.

7. The exact loader harness MUST exercise the actual complete loader boundary, not only isolated fragments, for every reviewed loader-controlled failure class and verify simultaneously:
- exact nonzero exit code from the frozen map;
- stdout equals only the exact ordered already-completed PASS prefix;
- stderr equals the exact fixed failure marker plus line ending for pre-handoff failures;
- no retry and no fallthrough;
- no dynamic path/env/tool/Git diagnostic leakage before `RUNNER_START`.

8. `PHASE_C_V19_7_15_FAIL_RUNNER_RETURN` remains post-handoff Option-B semantics only. A harmless synthetic runner MUST deliberately emit reviewed synthetic stdout/stderr, run exactly once, return nonzero, and the loader MUST preserve that runner output before emitting the fixed RETURN marker and exiting with code 81. Code 81 means only: RUNNER_START occurred, exact runner returned nonzero, loader failed closed, no loader retry/fallthrough. It does not identify the runner's internal root cause and does not strengthen secrecy claims.

9. Harmless successful runner behavior MUST remain unchanged except for no use of any failure exit code. `RUNNER_START` remains the one-way loader-to-historical-runner output/ownership boundary.

10. Host-visible exit-code observability MUST be treated as an additional nonsecret recovery channel, not as a guaranteed persistent storage service. If the host surfaces a final process exit code after terminal loss, Core may classify only the exact mapped loader failure class. If the host does not surface a code, or surfaces a value outside the frozen map, root cause remains INDETERMINATE and the session fails closed.

11. Owner-facing reporting at this boundary MUST require only the nonsecret host exit code (for example, `EXIT_CODE_74`) or a screenshot that contains no device code, credential, token, or other secret. Core MUST NOT request a screenshot while a GitHub one-time device code is visible. Device-code secrecy remains exactly unchanged.

12. Transport integrity remains mandatory for any executable candidate:
- exact repository path/blob/UTF-8 byte length/SHA-256;
- one shell line / zero internal LF / no final LF for the direct-copy loader action;
- deterministic builder equality;
- full Bash parse;
- every nonempty strict prefix fails parse, or an independently equivalent complete truncation/copy-transport proof;
- repository exact-artifact direct-copy only;
- Core MUST NOT manually reconstruct, retype, split, normalize, recompose, or regenerate Owner-facing executable text in chat.

13. The implementation delta MUST be minimized and independently auditable. Historical reviewed runner bytes and v19.7.14 Step3 bytes MUST remain unchanged unless separately reviewed. Any necessary loader/builder/harness/contract/chain/freeze changes MUST be frozen together as one exact current review unit.

14. The future exact candidate MUST bind the full diagnostic-only chain as one review unit:
fresh dedicated Codespace -> exact loader -> fixed-marker + exit-code observability -> `RUNNER_START` -> historical reviewed OAuth/device-code secrecy contract -> post-OAuth clean-shell reentry -> trusted Python -> Step2.6 -> exact effective scopes/admin checks -> unchanged NONMUTATING Step3 -> STOP/delete.

15. No implementation self-test is Independent Lab approval. Any executable-byte change invalidates prior Lab/Auditor binding for live use and requires fresh Independent Lab PASS, fresh Independent Auditor PASS, Core Owner presentation, and fresh explicit one-shot Owner approval before a new dedicated session.

## Non-authority

This requirements artifact authorizes only Independent Lab implementation-readiness review. It does NOT authorize a new Codespace, OAuth/device flow, device-code handling, credential/token operation, live Step3, Step4, `--apply`, production mutation, main/ruleset mutation, writer secret, merge, workflow dispatch, Runtime operation, or Runtime activation.

Runtime: OFF.
