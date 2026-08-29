# MULTIVERSE R1 STAGE 1 PHASE C v19.7.16 — HOST-VISIBLE EXIT-CODE OBSERVABILITY REQUIREMENTS

Status: DRAFT / READINESS RE-REVIEW REQUIRED / NO LIVE AUTHORITY
Date: 2026-08-30 JST

## Incident basis

The exact independently reviewed v19.7.15 v5d one-shot diagnostic session terminated fail-closed with the Owner-facing VS Code host reporting `/bin/bash` exit code `88`. The fixed `PHASE_C_V19_7_15_FAIL_*` terminal marker was not recovered before the dedicated Codespace became unavailable. The session and Owner receipt are consumed/nonreusable. Root cause remains INDETERMINATE.

A later Core governance-writing mistake advanced canonical `main`, but the containment commit restored the exact prior production-content tree. Current Fresh binding at this revision is:
- main commit: `5c1403c1f5aabb80d29e8c868440aede8888ce61`
- main tree: `3d47741b4863411e5c36cb4c28925ac455ab6441`
- prior exact-main binding `74ea95e59ac0654e1a0c1f811a178b3eef7b073c` is consumed/stale for any future exact-main authority decision.

Tree identity proves there is no remaining production-content delta from the contained incident. It does NOT erase the main-SHA governance incident, restore old authority, or permit silent inheritance of the prior exact-main SHA.

This remediation MUST NOT infer which v5d gate fired. Its sole purpose is to make a future reviewed fail-closed class recoverable from the host-visible process exit code even when the terminal transcript is lost.

## Required design

1. Preserve the reviewed fixed-marker transcript contract. Before `PHASE_C_V19_7_15_RUNNER_START`, successful completed gates may emit only the exact ordered fixed PASS-marker prefix; a loader-controlled failure emits its exact fixed failure marker to stderr and exits nonzero. No dynamic sensitive output may be added before the handoff.

2. Replace the single generic loader failure exit code with this exact frozen one-to-one map. The dedicated map uses `90..101`, avoiding conventional sysexits `64..78`, shell-reserved `126/127`, and the conventional `128+signal` space:

- `PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES` -> 90
- `PHASE_C_V19_7_15_FAIL_FRESH_PATHS` -> 91
- `PHASE_C_V19_7_15_FAIL_TMPFS_TRUST` -> 92
- `PHASE_C_V19_7_15_FAIL_GIT_CONTROL` -> 93
- `PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN` -> 94
- `PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD` -> 95
- `PHASE_C_V19_7_15_FAIL_REPO_STATE` -> 96
- `PHASE_C_V19_7_15_FAIL_RUNNER_TRUST` -> 97
- `PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND` -> 98
- `PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_MISMATCH` -> 99
- `PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH` -> 100
- `PHASE_C_V19_7_15_FAIL_RUNNER_RETURN` -> 101

The executable candidate MUST independently verify that this range does not collide with any project-local wrapper exit semantics used by the exact reviewed chain.

3. Unknown or unmapped failure-marker input MUST fail closed with exact fallback exit code `102`. Code `102` is outside the reviewed class map and the reserved/conventional ranges above. Mechanical proof MUST assert `102` is not present in the reviewed marker->code map, and no reviewed class may alias the fallback.

4. The mapping is diagnostic metadata only. It MUST NOT change gate order, success behavior, retry policy, OAuth/device-code secrecy, runner ownership after `RUNNER_START`, Step2.6, scope/admin checks, v19.7.14 NONMUTATING Step3, or any authorization boundary.

5. A failure code MUST be produced only through the reviewed loader failure path for its bound class. Unknown/unmapped marker input MUST NOT silently default to another reviewed class.

6. Every literal reviewed `fail <MARKER>` call site MUST be mechanically bound to exactly its declared exit code. The proof MUST inspect the exact frozen loader source, collect every literal call-site occurrence, prove full reviewed failure-class coverage, and fail if a call site is rebound, removed, duplicated into a conflicting class, or an expected mapping entry is wrong.

7. The v5d mechanical PASS-prefix binding remains required. For every actual pre-handoff failure call site, the proof MUST still derive the number of real preceding PASS-marker positions from exact source positions and assert equality with the reviewed expected prefix count.

8. The exact loader harness MUST exercise the actual complete loader boundary, not only isolated fragments, for every reviewed loader-controlled failure class and verify simultaneously:
- exact nonzero exit code from the frozen map;
- stdout equals only the exact ordered already-completed PASS prefix;
- stderr equals the exact fixed failure marker plus line ending for pre-handoff failures;
- no retry and no fallthrough;
- no dynamic path/env/tool/Git diagnostic leakage before `RUNNER_START`.

It MUST also exercise at least one unknown/unmapped-marker fixture and verify exact exit `102`, nonzero/fail-closed behavior, no reviewed-class alias, no retry, and no fallthrough.

9. `PHASE_C_V19_7_15_FAIL_RUNNER_RETURN` remains post-handoff Option-B semantics only. A harmless synthetic runner MUST deliberately emit reviewed synthetic stdout/stderr, run exactly once, return nonzero, and the loader MUST preserve that runner output before emitting the fixed RETURN marker and exiting with code `101`. Code `101` means only: RUNNER_START occurred, exact runner returned nonzero, loader failed closed, no loader retry/fallthrough. It does not identify the runner's internal root cause and does not strengthen secrecy claims.

10. Harmless successful runner behavior MUST remain unchanged except for no use of any failure exit code. `RUNNER_START` remains the one-way loader-to-historical-runner output/ownership boundary.

11. Host-visible exit-code observability MUST be treated as an additional nonsecret recovery channel, not as guaranteed persistent storage. If the host surfaces a final process exit code after terminal loss, Core may classify only the exact mapped loader failure class. Exit `102` means only unknown/unmapped loader failure input; it does not identify a reviewed class. If no code is surfaced, or a code outside `90..102` is surfaced, root cause remains INDETERMINATE and the session fails closed.

12. Owner-facing reporting at this boundary MUST require only the nonsecret host exit code (for example, `EXIT_CODE_94`) or a screenshot that contains no device code, credential, token, or other secret. Core MUST NOT request a screenshot while a GitHub one-time device code is visible. Device-code secrecy remains exactly unchanged.

13. Exact-main rebind is mandatory in the future executable candidate. Loader, chain, freeze and any exact-main proof MUST explicitly bind:
- expected main commit `5c1403c1f5aabb80d29e8c868440aede8888ce61`
- expected main tree `3d47741b4863411e5c36cb4c28925ac455ab6441`

They MUST NOT silently inherit `74ea95e59ac0654e1a0c1f811a178b3eef7b073c`. Any subsequent Fresh main SHA or tree drift before independent review or live use MUST fail closed and require a new reviewed rebind.

14. Transport integrity remains mandatory for any executable candidate:
- exact repository path/blob/UTF-8 byte length/SHA-256;
- one shell line / zero internal LF / no final LF for the direct-copy loader action;
- deterministic builder equality;
- full Bash parse;
- every nonempty strict prefix fails parse, or an independently equivalent complete truncation/copy-transport proof;
- repository exact-artifact direct-copy only;
- Core MUST NOT manually reconstruct, retype, split, normalize, recompose, or regenerate Owner-facing executable text in chat.

15. The implementation delta MUST be minimized and independently auditable. Historical reviewed runner bytes and v19.7.14 Step3 bytes MUST remain unchanged unless separately reviewed. Any necessary loader/builder/harness/contract/chain/freeze changes MUST be frozen together as one exact current review unit.

16. The future exact candidate MUST bind the full diagnostic-only chain as one review unit:
fresh dedicated Codespace -> exact loader -> fixed-marker + exit-code observability -> `RUNNER_START` -> historical reviewed OAuth/device-code secrecy contract -> post-OAuth clean-shell reentry -> trusted Python -> Step2.6 -> exact effective scopes/admin checks -> unchanged NONMUTATING Step3 -> STOP/delete.

17. No implementation self-test is Independent Lab approval. Any executable-byte change invalidates prior Lab/Auditor binding for live use and requires fresh Independent Lab PASS, fresh Independent Auditor PASS, Core Owner presentation, and fresh explicit one-shot Owner approval before a new dedicated session.

## Non-authority

This requirements artifact authorizes only Independent Lab implementation-readiness re-review. It does NOT authorize a new Codespace, OAuth/device flow, device-code handling, credential/token operation, live Step3, Step4, `--apply`, production mutation, main/ruleset mutation, writer secret, merge, workflow dispatch, Runtime operation, or Runtime activation.

Runtime: OFF.
