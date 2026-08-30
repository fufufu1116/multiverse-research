# MULTIVERSE R1 STAGE 1 PHASE C v19.7.16 — HOST-VISIBLE EXIT-CODE OBSERVABILITY REQUIREMENTS

Status: DRAFT / REVISION B / READINESS RE-REVIEW REQUIRED / NO LIVE AUTHORITY
Date: 2026-08-30 JST

## Incident basis

The exact independently reviewed v19.7.15 v5d one-shot diagnostic session terminated fail-closed with the Owner-facing VS Code host reporting `/bin/bash` exit code `88`. The fixed `PHASE_C_V19_7_15_FAIL_*` terminal marker was not recovered before the dedicated Codespace became unavailable. The session and Owner receipt are consumed/nonreusable. Root cause remains INDETERMINATE.

The v19.7.16 executable-v1 exact-candidate review returned FIX_REQUIRED in PR #74 comment `5465628157`. Revision B closes the requirements-level collision defect before any further executable implementation. It does not infer which v5d gate fired.

## Required design

1. Preserve the reviewed fixed-marker transcript contract. Before `PHASE_C_V19_7_15_RUNNER_START`, successful completed gates may emit only the exact ordered fixed PASS-marker prefix; a loader-controlled failure emits its exact fixed failure marker to stderr and exits nonzero. No dynamic sensitive output may be added before the handoff.

2. Replace the generic loader failure exit with this exact outer-loader host-visible map:

- `PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES` -> 103
- `PHASE_C_V19_7_15_FAIL_FRESH_PATHS` -> 104
- `PHASE_C_V19_7_15_FAIL_TMPFS_TRUST` -> 105
- `PHASE_C_V19_7_15_FAIL_GIT_CONTROL` -> 106
- `PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN` -> 107
- `PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD` -> 108
- `PHASE_C_V19_7_15_FAIL_REPO_STATE` -> 109
- `PHASE_C_V19_7_15_FAIL_RUNNER_TRUST` -> 110
- `PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND` -> 111
- `PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_MISMATCH` -> 112
- `PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH` -> 113
- `PHASE_C_V19_7_15_FAIL_RUNNER_RETURN` -> 114

Unknown/unmapped loader marker input MUST fail closed with exact fallback exit `115`. Fallback 115 is non-classifying and MUST NOT alias a reviewed class.

3. Collision scope is the final outer loader process status namespace visible to the Owner-facing host. The executable candidate MUST mechanically inspect the exact historical runner and unchanged Step3 for fixed literal exit mechanisms, including shell `exit`, shell `return`, Python `os._exit`, Python `sys.exit`, and equivalent fixed wrapper exits, and prove that no fixed literal 103..115 is used by those exact dependencies. Known historical inner codes 88/89/90/91/92 and Step3 `os._exit(92)` are therefore outside the revised outer range.

4. Dynamic child return values from the historical runner are not directly host-visible through the outer loader: after `RUNNER_START`, any nonzero historical-runner return is converted by the reviewed outer loader to `PHASE_C_V19_7_15_FAIL_RUNNER_RETURN` / exit 114. The collision proof MUST verify this encapsulation rather than treating arbitrary dynamic child return values as distinct outer-loader host statuses.

5. The mapping is diagnostic metadata only. It MUST NOT change gate order, success behavior, retry policy, OAuth/device-code secrecy, runner ownership after `RUNNER_START`, Step2.6, scope/admin checks, v19.7.14 NONMUTATING Step3, or any authorization boundary.

6. Every literal reviewed `fail <MARKER>` call site MUST be mechanically bound to exactly its declared exit code. The proof MUST inspect the exact frozen loader source, collect every literal call-site occurrence, prove full reviewed failure-class coverage, and fail if a call site is rebound, removed, duplicated into a conflicting class, or an expected mapping entry is wrong.

7. The v5d mechanical PASS-prefix binding remains required. For every actual pre-handoff failure call site, the proof MUST derive the number of real preceding PASS-marker positions from exact source positions and assert equality with the reviewed expected prefix count.

8. The executable candidate MUST include a true whole-loader failure matrix. For every reviewed loader-controlled failure class 103..114, the test MUST begin from the complete exact frozen loader entrypoint/source, preserve the complete gate sequence up to the injected failure, and verify simultaneously:
- exact mapped outer process exit code;
- stdout equals only the exact ordered already-completed PASS prefix before `RUNNER_START`;
- stderr equals the exact fixed failure marker plus line ending for pre-handoff failures;
- no retry and no fallthrough;
- no dynamic path/env/tool/Git diagnostic leakage before `RUNNER_START`;
- each intended gate is reached through all preceding complete-loader gates rather than by direct `fail()` invocation or isolated gate fragment.

9. The whole-loader matrix MUST also include:
- unknown/unmapped marker -> exact fallback 115, nonzero, no class alias;
- harmless full-loader success through loader handoff using a reviewed synthetic historical-runner substitute boundary;
- Option-B full-loader runner-nonzero case: RUNNER_START occurs once, harmless synthetic child stdout/stderr are preserved, child executes once, loader emits fixed RETURN marker, outer exit is 114, no retry/fallthrough.

10. `PHASE_C_V19_7_15_FAIL_RUNNER_RETURN` remains post-handoff Option-B semantics only. Exit 114 means only: RUNNER_START occurred, exact runner returned nonzero, loader failed closed, and no loader retry/fallthrough. It does not identify the runner's internal root cause and does not strengthen secrecy claims.

11. Transport integrity is mandatory for the exact changed loader bytes. The executable candidate MUST freeze exact repository path/blob/UTF-8 byte length/SHA-256, one shell line, zero internal LF, no final LF, deterministic builder equality, full Bash parse, and an exhaustive proof that every nonempty strict byte prefix of that exact loader fails Bash parse, or an independently equivalent complete truncation/copy-transport proof explicitly bound to the same exact bytes. Prior-v5d prefix evidence cannot substitute for changed-loader evidence.

12. The exact candidate MUST reconcile the historical runner dependency. The candidate branch path `governance/MULTIVERSE_R1_STAGE1_PHASE_C_PRE_OAUTH_CONTINUITY_RECOVERY_RUNNER_20260827_v1.sh`, every proof input, consolidated chain, and freeze MUST all resolve consistently to immutable historical blob `bc2b638b0db7fa8a0c23f0988cd9946f9e24b590` from recovery head `19a14cfd019cceab199571b5d03d4dd0ba5bcd22`, unless a separately reviewed dependency model explicitly uses the immutable recovery-head object without making a false branch-path equality claim. No contradictory freeze assertion is allowed.

13. The future executable loader/chain/freeze/exact-main proof MUST bind both current main commit `5c1403c1f5aabb80d29e8c868440aede8888ce61` and exact tree `3d47741b4863411e5c36cb4c28925ac455ab6441`. Silent inheritance of prior `74ea95e59ac0654e1a0c1f811a178b3eef7b073c` is prohibited. Any subsequent main SHA or tree drift before review/live use MUST fail closed and require a new reviewed rebind.

14. The main-tree identity proves no remaining production-content delta from the contained accidental Core write, but does not erase the main-SHA governance incident, restore prior authority, or make consumed receipts reusable.

15. Device-code secrecy remains unchanged. Owner reporting at this boundary may use only a nonsecret host exit code or a screenshot confirmed to contain no device code, credential, token, or other secret. Core MUST NOT request a screenshot while a one-time device code is visible.

16. Historical reviewed runner behavior and v19.7.14 Step3 executable bytes MUST remain unchanged unless separately reviewed. The implementation delta MUST be minimized and all loader/builder/harness/proof/contract/chain/freeze changes frozen together as one exact current review unit.

17. The future exact candidate MUST bind the full diagnostic-only chain as one review unit:
fresh dedicated Codespace -> exact loader -> fixed-marker + host-visible exit-code observability -> `RUNNER_START` -> historical reviewed OAuth/device-code secrecy contract -> post-OAuth clean-shell reentry -> trusted Python -> Step2.6 -> exact effective scopes/admin checks -> unchanged NONMUTATING Step3 -> STOP/delete.

18. No implementation self-test is Independent Lab approval. Any executable-byte change requires fresh Independent Lab exact-candidate PASS, then fresh Independent Auditor PASS, Core Owner presentation, and fresh explicit one-shot Owner approval before a new dedicated session.

## Non-authority

This Revision B requirements artifact authorizes only Independent Lab implementation-readiness re-review. It does NOT authorize executable acceptance, Auditor review of an unfrozen implementation, a new Codespace, OAuth/device flow, device-code handling, live Step3, Step4, `--apply`, production mutation, main/ruleset mutation, writer secret, merge, workflow dispatch, Runtime operation, or Runtime activation.

Runtime: OFF.
