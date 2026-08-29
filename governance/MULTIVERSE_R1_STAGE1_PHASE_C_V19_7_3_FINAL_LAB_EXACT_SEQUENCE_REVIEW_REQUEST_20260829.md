# FINAL LAB EXACT-SEQUENCE REVIEW REQUEST — R1 STAGE 1 PHASE C v19.7.3

Role: Independent Lab / 独立検証室

Fresh Read GitHub first. Do not use Core/prior Lab/Auditor conclusions as substitutes for independent judgment.

Repo: `fufufu1116/multiverse-research`
PR: `#74`

Predecessor Independent Lab authorization-to-build:
- comment `5460755691`
- verdict `LAB_V19_7_2_GH_BINDING_VERDICT: PASS`
- unresolved material items: NONE

Exact full-sequence manifest:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_3_EXACT_FULL_SEQUENCE_MANIFEST_20260829.md`
- immutable manifest commit `87f159208d8059f2c5a401fba222d0aeef05bdb4`
- manifest blob `2437f648d482845351c74f59ddef2aac1d24b6bc`

Independently Fresh-fetch and mechanically verify every exact artifact listed by that manifest. Do not trust the manifest's stated identities without recomputing them.

Review at minimum:

1. All `.txt` live-action candidates are exact single-line/no-final-LF direct-clipboard actions, and each stated commit/path/blob/bytes/SHA-256 binding is exact.
2. Step0/Step0.5/Step1 are NEW v19.7.3 immutable artifacts, even where their bytes intentionally match previously reviewed evidence; historical chat/terminal text remains nonauthority.
3. OAuth launch command is exact, and the separate operator protocol freezes mandatory credential-helper prompt + exact `No`; historical v4 `Yes` is explicitly superseded. No-prompt/helper branch, wrong answer, or uncertainty is fail closed before continuing.
4. Device-code secrecy and acknowledgement boundary is exact: only `DEVICE_CODE_DISPLAYED_NO_CODE_SHARED` while code is visible; after first-party GitHub success only `GITHUB_DEVICE_CONNECTED_NO_CODE_SHARED`; no screenshot/photo/OCR/copied text/transcription/code chars. Core may deliver only one reviewed Enter keystroke after a Fresh binding check.
5. Post-OAuth returned-shell distrust, exact env-i reentry, and pure-shell trusted-Python gate ordering are correct.
6. MEMFD bootstrap wrapper first fetches the exact immutable bootstrap program and verifies exact len/SHA-256/Git blob before executing those same complete bytes in memory.
7. Bootstrap program independently fetches complete Step2.6 and Step3 immutable payload bytes and verifies each exact len/SHA-256/Git blob before any payload execution.
8. Mechanically audit memfd implementation: `MFD_ALLOW_SEALING`; complete-write loop; `pread(len+1,0)==data`; exact four-seal mask; `F_GET_SEALS`; first duplication to collision-safe FD>=10; original close only after both safe duplicates exist; `dup2(...,3/4,inheritable=True)`; high-FD close; fixed-FD inheritable/offset0/seal proof; no CLOEXEC loss of FD4 across Bash exec.
9. Audit exception/failure paths in bootstrap. Any defect that could leave a usable interactive shell or leak a half-established authority must be FIX_REQUIRED. Confirm Step2.6 rcfile outer failures use `exit 93`, not `return`, so failed startup cannot continue as an authorized interactive shell.
10. `/bin/bash --noprofile --rcfile /dev/fd/3 -i` and sealed FD3 preserve Step2.6 state (`CANONICAL_SHA`, `CANONICAL_ORIGIN`, `EXEC_ROOT`, `git_clean`, `phase_c_verify`) in the same persistent shell needed by Step3.
11. Audit Step2.6 byte semantics against Fresh canonical main and predecessor v4/v8 source evidence: tmpfs/ownership/mode, no swap, detached exact canonical checkout, origin, index-suppression checks, three security-critical canonical files, direct Git blob equality, clean worktree, exact PASS marker.
12. Auth-gate-exec wrapper must fetch exact v19.7.2 gate from immutable commit, verify exact 4443 bytes + SHA-256 + Git blob, and execute only those same in-memory bytes. The executed gate must still enforce controlled-PATH GH binding, exact login `fufufu1116`, exact scope equality `{repo, read:org, gist}`, repo admin=true, and exactly two GET API operations.
13. Audit sealed FD4 Step3 action: trusted Python child must inspect same inherited FD4 with `fstat`, `pread` without changing offset, exact len/SHA-256/blob/seals/offset; parent same Bash must source `. /dev/fd/4` only after PASS and close FD4 after return. Check shell `&&`/`;` precedence and failure paths carefully.
14. Audit exact Step3 payload. It must be NONMUTATING: same-shell `phase_c_verify` first, then exact canonical execution-preflight from the already verified external checkout, require `PHASE_C_NONMUTATING_PREFLIGHT_PASS` and false mutation/runtime fields, emit exact `PHASE_C_V19_7_3_NONMUTATING_STEP3_PASS`. It must expose no Step4/apply/mutation primitive.
15. Independently inspect canonical `tools/multiverse_r1_stage1_phase_c_execution_preflight_v1.py` at Fresh main and its canonical admin dependency to ensure the Step3 wrapper does not weaken their requirements.
16. Check that no verified-tempfile→pathname-reopen/source, streaming pipe, process substitution, partial-before-full-verify, mutable-path security identity, or naive child-shell state loss has reappeared.
17. Check FD3/FD4 lifetime, `/dev/fd` semantics, shell startup semantics, subprocess inheritance/close-fds interactions, and whether any normal command or gate could unexpectedly consume/close/seek FD4 before its final verifier. Any material doubt => FIX_REQUIRED.
18. Check complete one-shot failure/consumption rules: fetch/hash/prompt/device disclosure/OAuth/session/extra input/memfd/seal/FD/Step2.6/auth/scope/admin/Step3/missing-marker/unclassifiable-output failure => STOP/delete/no-retry, no live repair/RETRIEVAL/resume.
19. Check exact exclusions: no Step4, `--apply`, fence, Environment mutation, writer-key/secret, main/ruleset mutation, merge, Runtime branch/sequence0, activation receipt/tag, workflow dispatch, Runtime tasks/Sources/scheduler, or Runtime activation.
20. Perform any local static/syntax simulation that is safe and nonproduction, including Python compile and Bash `-n` where applicable. Do not create a Codespace or perform OAuth/API/live Step3.

Required verdict:
`LAB_V19_7_3_EXACT_SEQUENCE_VERDICT: PASS | FIX_REQUIRED`
`UNRESOLVED_MATERIAL_ITEMS: ...`
`ALL_ARTIFACT_IDENTITIES_MECHANICALLY_VERIFIED: YES | NO`
`SINGLE_LINE_DELIVERY_ARTIFACTS_VALID: YES | NO`
`MEMFD_TOCTOU_AND_FD_LIFETIME: PASS | FAIL`
`PERSISTENT_SAME_SHELL_SEMANTICS: PASS | FAIL`
`OAUTH_PROMPT_NO_AND_DEVICE_SECRECY: PASS | FAIL`
`AUTH_SCOPE_ADMIN_NONMUTATING_GATE: PASS | FAIL`
`STEP3_NONMUTATING_SEMANTICS: PASS | FAIL`
`FAIL_CLOSED_ONE_SHOT_BOUNDARY: PASS | FAIL`
`CAN_PROCEED_TO_INDEPENDENT_AUDITOR_AFTER_THIS_VERDICT: YES | NO`
`CAN_PRESENT_TO_OWNER_NOW: NO`
`CAN_CREATE_NEW_CODESPACE_NOW: NO`
`CAN_DELIVER_TERMINAL_COMMAND_NOW: NO`
`CAN_START_OAUTH_NOW: NO`
`CAN_RUN_AUTHENTICATED_API_OR_STEP3_NOW: NO`
`CAN_DELIVER_STEP4_OR_APPLY_NOW: NO`
`PRODUCTION_MUTATION_AUTHORIZED_NOW: NO`
`RUNTIME_ACTIVATION_AUTHORIZED_NOW: NO`

Write the result back to PR #74.

Review only. No Codespace creation, terminal command execution, OAuth/device flow, authenticated API, Step3 execution, Step4/--apply, production/main/ruleset mutation, writer-key/secret operation, merge, or Runtime operation. Runtime remains OFF.