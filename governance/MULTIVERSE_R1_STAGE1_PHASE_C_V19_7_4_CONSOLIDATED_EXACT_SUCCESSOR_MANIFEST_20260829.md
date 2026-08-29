# MULTIVERSE R1 Stage 1 Phase C v19.7.4 — CONSOLIDATED EXACT SUCCESSOR MANIFEST

Status: DRAFT REVIEW ONLY / NONSECRET / NO LIVE AUTHORITY
Date: 2026-08-29 JST

## Fresh authority basis
- canonical repo: `fufufu1116/multiverse-research`
- canonical main: `74ea95e59ac0654e1a0c1f811a178b3eef7b073c`
- canonical tree: `3d47741b4863411e5c36cb4c28925ac455ab6441`
- predecessor recovery head before this manifest: `a205f4e4143600afa7a348be0f4fbf26e83363e6`
- Independent Lab v19.7.4 PASS: PR #74 comment `5461087416`
- unresolved material items: NONE
- prior v19.6.1 one-shot approval/session: consumed, deleted, nonreusable

This document consolidates the exact successor review unit for Independent Auditor review. It creates no live authority. No Codespace, terminal delivery, OAuth, authenticated API, Step3, Step4, `--apply`, production mutation, merge, writer-key/secret action, or Runtime operation is authorized.

## Governing exact sequence
The baseline exact sequence is the v19.7.3 exact full-sequence manifest:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_3_EXACT_FULL_SEQUENCE_MANIFEST_20260829.md`
- immutable commit: `87f159208d8059f2c5a401fba222d0aeef05bdb4`
- blob: `2437f648d482845351c74f59ddef2aac1d24b6bc`

The following two v19.7.3 artifacts from that manifest are superseded and NONAUTHORITY:
- `governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_3_MEMFD_BOOTSTRAP_PROGRAM_20260829.py`
- `governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_3_MEMFD_BOOTSTRAP_ACTION_20260829.txt`

They are replaced exactly by the v19.7.4 pair below. Every other v19.7.3 artifact and operator boundary remains unchanged and immutable unless an Independent Auditor proves otherwise.

## Exact v19.7.4 replacements
### MEMFD bootstrap program
Path:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_4_MEMFD_BOOTSTRAP_PROGRAM_20260829.py`
- immutable commit: `a057fe59fff82043273d0223a5eaba3703079ca4`
- Git blob: `67d51d6caddfc96f45a98aa5cacac35c51263df5`
- UTF-8 bytes: `3933`
- SHA-256: `4f8f4c5629b5f9198385c88fd8581ca6028b54bcf8dc3409a58ceaf1d67bc199`
- final LF: YES

### MEMFD bootstrap terminal action
Path:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_4_MEMFD_BOOTSTRAP_ACTION_20260829.txt`
- immutable commit: `e47fdcc1ef6a82ae3ea5ba25f241ba9d15b40a7f`
- Git blob: `5e2cbf8dc140ebd3363c2f5e5a00cf36b816d9db`
- UTF-8 bytes: `781`
- SHA-256: `78a4a9bbec16d51946cf3354fa160cd544d3fe8c9118a755a4ede632d1e6ce2d`
- internal LF: `0`
- final LF: NO

The exact action begins with shell builtin `exec`, so the authenticated post-OAuth authority shell is replaced by trusted Python before wrapper fetch/hash/compile/bootstrap. Bootstrap failure cannot return to the prior usable authenticated shell.

## v19.7.4 MEMFD success ordering
On the successful transition path:
1. immutable Step2.6 and Step3 payloads are each completely fetched and exact length/SHA-256/Git-blob verified before execution;
2. each payload is completely written to an anonymous `MFD_ALLOW_SEALING` memfd;
3. `pread` proves exact full contents before execution;
4. exact `F_SEAL_WRITE | F_SEAL_GROW | F_SEAL_SHRINK | F_SEAL_SEAL` is applied and verified;
5. each still-open original gets a collision-safe `F_DUPFD_CLOEXEC` high duplicate `>=10`;
6. both originals plus both high duplicates must coexist and be four distinct FDs before either original is closed;
7. only then are both originals closed;
8. high duplicates are mapped to fixed FD3/FD4 with `inheritable=True`;
9. high duplicates are closed;
10. FD3/FD4 inheritable state, exact offset0 and exact seals are reverified;
11. Python `os.execve`s `/bin/bash --noprofile --rcfile /dev/fd/3 -i`;
12. sealed FD3 Step2.6 becomes the persistent Bash startup rcfile while sealed FD4 survives for later same-shell Step3 verification/source.

Failure cleanup may close partially-created descriptors only while terminally unwinding a failed process; it does not authorize recovery, retry or resumption.

## Consolidated future one-shot state machine
Only after Independent Auditor PASS and a later explicit Owner approval may one future fresh session use exactly:

`new dedicated Codespace`
-> exact v19.7.3 Step0
-> exact clean shell
-> exact v19.7.3 Step0.5 + `PHASE_C_TRUSTED_PYTHON_BINDING_PASS`
-> exact v19.7.3 Step1 + `PHASE_C_STEP1_CHUNKED_TRANSPORT_AND_SOURCE_PASS`
-> exact v19.7.3 OAuth launch
-> mandatory Git credential-helper prompt
-> exact Owner response `No`
-> device-code display
-> Owner reports only `DEVICE_CODE_DISPLAYED_NO_CODE_SHARED`
-> Core immediate Fresh authority/binding check
-> exactly one reviewed Enter keystroke
-> first-party GitHub device authorization
-> Owner reports only `GITHUB_DEVICE_CONNECTED_NO_CODE_SHARED`
-> returned shell treated as nonauthority
-> exact v19.7.3 post-OAuth env-i reentry
-> exact v19.7.3 pure-shell trusted-Python gate + `PHASE_C_POST_OAUTH_PRELOADER_TRUSTED_PYTHON_BINDING_PASS`
-> NEW exact v19.7.4 exec MEMFD bootstrap action/program
-> persistent Bash sealed-FD3 Step2.6 + `PHASE_C_POST_OAUTH_CLEAN_SHELL_REENTRY_PASS`
-> exact v19.7.3 auth-gate-exec action + `PHASE_C_V19_7_2_AUTH_SCOPE_ADMIN_NONMUTATING_PASS`
-> exact v19.7.3 sealed-FD4 immediate reverify/source
-> exact NONMUTATING Step3 + `PHASE_C_V19_7_3_NONMUTATING_STEP3_PASS`
-> STOP
-> Owner deletes Codespace.

## Device-code secrecy
While the one-time code is visible, no screenshot, photo, screen recording, OCR, copied terminal output, transcription, or code characters may be sent to Core/chat. Only `DEVICE_CODE_DISPLAYED_NO_CODE_SHARED` is allowed. After first-party GitHub connection success, only `GITHUB_DEVICE_CONNECTED_NO_CODE_SHARED` is allowed. Any disclosure, prompt mismatch, accidental extra input, session loss or uncertainty consumes the future one-shot and requires STOP/delete/no-retry.

## Technical nonmutation gates
The reviewed v19.7.2 auth gate remains exact and requires:
- controlled-PATH `gh` resolution;
- exact authenticated login `fufufu1116`;
- effective OAuth scopes exactly `{repo, read:org, gist}`;
- repository `permissions.admin == true`;
- only GET `/user` and GET `/repos/fufufu1116/multiverse-research`.

Step3 remains NONMUTATING. It first uses same-shell `phase_c_verify`, then only canonical `tools/multiverse_r1_stage1_phase_c_execution_preflight_v1.py` from the exact verified external checkout, and requires canonical PASS evidence including `production_mutation_performed=false` and `runtime_activation_performed=false`.

## Fail-closed boundary
Any Fresh-delivery gate failure, identity mismatch, fetch/hash/blob mismatch, prompt mismatch, device-code disclosure, unexpected output preventing exact classification, OAuth/session loss, extra input, memfd/write/pread/seal/FD collision/inheritance/offset error, Step2.6 failure, auth/scope/admin mismatch, FD4 mismatch, Step3/preflight failure, missing exact marker, or any material deviation consumes the future one-shot session. Required response: STOP, Owner deletes Codespace, no retry. No live diagnosis, repair, RETRIEVAL, alternate transport/path, resume, or command reconstruction from chat/history is authorized.

## Explicit exclusions
The consolidated successor contains no Step4, `--apply`, provision-fence creation, Environment mutation, writer-key/secret generation/storage/readback/test, main/ruleset mutation, merge, Runtime branch/sequence0, activation receipt/tag, workflow dispatch, Runtime state/tasks/Sources/scheduler, or Runtime activation.

## Current authority
- `CAN_PROCEED_TO_INDEPENDENT_AUDITOR_NOW: YES`
- `CAN_PRESENT_TO_OWNER_NOW: NO`
- `CAN_CREATE_CODESPACE_NOW: NO`
- `CAN_DELIVER_TERMINAL_COMMAND_NOW: NO`
- `CAN_START_OAUTH_NOW: NO`
- `CAN_RUN_AUTHENTICATED_API_OR_STEP3_NOW: NO`
- `CAN_DELIVER_STEP4_OR_APPLY_NOW: NO`
- `PRODUCTION_MUTATION_AUTHORIZED_NOW: NO`
- `RUNTIME_ACTIVATION_AUTHORIZED_NOW: NO`
- Runtime: `OFF`

Next gate: one consolidated Independent Auditor review of this manifest, the exact v19.7.4 replacements, and all inherited v19.7.3 immutable artifacts/operator boundaries. Auditor PASS may permit return to Core for Owner presentation only; it does not itself authorize live execution.