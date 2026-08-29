# FINAL LAB REMEDIATION REVIEW REQUEST — R1 STAGE 1 PHASE C v19.7.1

Independent Lab only. Fresh Read GitHub before judging CURRENT/NOW/LATEST. Core conclusions are evidence only, not delegated judgment. Review only; do not create a Codespace, run terminal commands, start OAuth, call authenticated API live, run Step3/Step4, apply, mutate production/main/ruleset, handle writer secrets, merge, or activate Runtime.

## Exact review context
- repo: `fufufu1116/multiverse-research`
- PR: `#74`
- predecessor build-plan request head: `d28dd39417007e4e362d518e04b846b8d621fe16`
- predecessor Lab FIX_REQUIRED: comment `5460636659`
- canonical main expected: `74ea95e59ac0654e1a0c1f811a178b3eef7b073c`
- canonical tree expected: `3d47741b4863411e5c36cb4c28925ac455ab6441`
- prior v19.6.1 final deletion closure: `5460591186`

## Exact remediation target
Design path:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_1_BUILD_PLAN_REMEDIATION_20260829.md`

Design commit:
`257145044265f0332d911fc23e130ce9aafad870`

Design blob:
`becce381b3c023a96d916b43af0f223f53886a62`

Exact auth/scope/admin gate path:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_1_AUTH_SCOPE_ADMIN_NONMUTATING_GATE_20260829.py`

Auth-gate commit:
`2ecdc5345d92a6705644624b4c97d1cd9fbfa822`

Auth-gate identity:
- blob `03f9471ecad04170d3f048d5b006458e970fd11b`
- 3953 UTF-8 bytes
- SHA-256 `230a1424dbaf44dd584d42f64122f090817e59a3a028c268274d3db36c4458d2`
- final LF YES

Canonical comparison evidence:
- `tools/multiverse_r1_stage1_writer_key_admin_channel_v1.py` at canonical main blob `ec05a014964211c15e48c3a2c327648a13f64dcf`
- `tools/multiverse_r1_stage1_phase_c_execution_preflight_v1.py` at canonical main blob `0232c66bcf40cc1f61ce5bcc855604f73fce665a`

## Required independent questions
1. Does the explicit ban on verified-tempfile -> later reopen/source fully resolve material item 1 at the design level?
2. Is the proposed **sealed anonymous memfd** mechanism sound against the v19.6/v19.7 verify→execute TOCTOU class, specifically when complete bytes are verified before execution, the memfd is sealed with WRITE/GROW/SHRINK/SEAL, and later access is only descriptor indirection `/dev/fd/N` to the already-open sealed object?
3. Is `exec` into `/bin/bash --noprofile --rcfile /dev/fd/3 -i` a sound way to execute exact sealed Step2.6 bytes in the resulting persistent Bash itself so that `EXEC_ROOT`, `git_clean`, `phase_c_verify`, and other Step2.6 state persist for later Step3?
4. Does pre-creating sealed FD4 for exact Step3, keeping it at offset 0, re-verifying the same FD with `F_GET_SEALS` + `pread` immediately before `. /dev/fd/4`, and then sourcing it in the same persistent Bash preserve both same-byte and same-shell requirements without mutable-path reopen?
5. Identify any material descriptor-lifetime, Bash rcfile, interactive-shell, fd-offset, seal, `/dev/fd`, inherited-FD, or partial-execution issue that would make this design unsafe or operationally non-equivalent.
6. Is rejecting streaming pipes/process-substitution and naive child-Bash stdin for Step2.6 correct because they respectively risk partial-before-complete execution or loss of parent-shell state?
7. Is the Git credential prompt conflict now unambiguously resolved as mandatory prompt + exact **No**, with historical v4 Yes explicitly superseded/non-authoritative and any prompt mismatch/no-prompt/Yes requiring STOP/delete/no-retry?
8. Does the exact new auth gate mechanically prove authenticated login `fufufu1116`, exact scope set equality `{repo, read:org, gist}`, and repository `permissions.admin == true`, while using only GET requests and exposing no mutation primitive?
9. Is the auth gate's environmental scrubbing and nonsecret fixed-marker output sufficient? Does fixed `GH_BIN=/usr/bin/gh` fit the approved Codespaces/system-binary trust model? If this exact path is not sufficiently established or portable on the approved path, return FIX_REQUIRED rather than silently widening it.
10. Is the candidate order sound:
`env-i -> pure-shell Python binding -> complete Step2.6+Step3 verify/sealed memfd -> persistent Bash/FD3 Step2.6 -> Step2.6 PASS -> auth/scope/admin PASS -> same-FD4 reverify -> exact NONMUTATING Step3 -> STOP/delete`?
11. Does this remediation still exclude Step4, `--apply`, fence, Environment mutation, writer-key/secret, main/ruleset mutation, merge and Runtime?
12. If PASS, may Core proceed only to construct NEW exact immutable v19.7 action artifacts/full sequence, followed by a separate Lab review and Auditor review before Owner presentation? No live authority should follow from this design PASS alone.

## Required return fields
- `LAB_V19_7_1_REMEDIATION_REVIEWED_HEAD`
- `LAB_V19_7_1_REMEDIATION_VERDICT: PASS | FIX_REQUIRED`
- `CANONICAL_MAIN_AND_PR_STATE_FRESH`
- `TEMPFILE_REOPEN_BAN`
- `SEALED_MEMFD_TOCTOU_MODEL`
- `STEP26_PERSISTENT_SHELL_STATE`
- `STEP3_SEALED_FD_SAME_BYTES_SAME_SHELL`
- `DESCRIPTOR_LIFETIME_AND_BASH_RCFILE_SEMANTICS`
- `NO_STREAMING_PARTIAL_EXECUTION`
- `GIT_CREDENTIAL_PROMPT_NO_CONFLICT_RESOLVED`
- `AUTH_GATE_EXACT_IDENTITY`
- `AUTH_LOGIN_SCOPE_SET_ADMIN_PROOF`
- `AUTH_GATE_READ_ONLY_NONMUTATION`
- `GH_BINARY_BINDING`
- `POST_OAUTH_ORDER`
- `FAIL_CLOSED_NO_RETRY`
- `NO_PRODUCTION_OR_RUNTIME_WIDENING`
- `UNRESOLVED_MATERIAL_ITEMS`
- `CAN_CORE_BUILD_NEW_EXACT_V19_7_FULL_SEQUENCE_AFTER_THIS_VERDICT: YES | NO`
- `CAN_PROCEED_DIRECTLY_TO_AUDITOR_NOW: NO`
- `CAN_PRESENT_TO_OWNER_NOW: NO`
- `CAN_CREATE_NEW_CODESPACE_NOW: NO`
- `CAN_DELIVER_TERMINAL_COMMAND_NOW: NO`
- `CAN_START_OAUTH_NOW: NO`
- `CAN_RUN_AUTHENTICATED_API_OR_STEP3_NOW: NO`
- `CAN_DELIVER_STEP4_OR_APPLY_NOW: NO`
- `PRODUCTION_MUTATION_AUTHORIZED_NOW: NO`
- `RUNTIME_ACTIVATION_AUTHORIZED_NOW: NO`

Write the independent result back to PR #74. Runtime remains OFF.
