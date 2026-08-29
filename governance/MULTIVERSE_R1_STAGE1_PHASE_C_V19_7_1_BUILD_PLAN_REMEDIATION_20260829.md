# MULTIVERSE R1 Stage 1 Phase C v19.7.1 — Build-Plan Remediation

Status: DRAFT REVIEW ONLY / NONSECRET / NO LIVE AUTHORITY
Date: 2026-08-29 JST

## Fresh binding at design start
- canonical repo: `fufufu1116/multiverse-research`
- canonical main: `74ea95e59ac0654e1a0c1f811a178b3eef7b073c`
- canonical tree: `3d47741b4863411e5c36cb4c28925ac455ab6441`
- predecessor v19.7 request head: `d28dd39417007e4e362d518e04b846b8d621fe16`
- Independent Lab FIX_REQUIRED: PR #74 comment `5460636659`
- prior v19.6.1 one-shot final deletion closure: `5460591186`; consumed/nonreusable

This document is a remediation design only. It does not authorize a Codespace, terminal command, OAuth, authenticated API, Step3, Step4, `--apply`, production mutation, merge, or Runtime operation.

## Material item 1 — ban verified-tempfile -> reopen/source
v19.7.1 explicitly prohibits the historical v7/v8 execution mechanism for Step2.6 and Step3:
- no verified tempfile pathname;
- no write -> verify pathname -> later `.`/`source` pathname reopen;
- no mutable filesystem namespace handoff between integrity verification and execution;
- no streaming pipe where Bash may begin executing before the complete payload has already been received and integrity-verified.

Historical v7 transport remains source evidence for payload-integrity requirements only; its tempfile/source mechanism is NONAUTHORITY and forbidden for the successor.

## Material item 2 — TOCTOU-safe complete-byte execution with persistent current-shell state
The successor candidate shall use **sealed anonymous memfd descriptors**, not tempfiles and not a child-Bash-stdin-only handoff.

Candidate mechanism to be independently reviewed before exact action emission:

1. After the exact post-OAuth `env -i` clean-shell reentry and pure-shell trusted-Python binding PASS, the exact trusted Python interpreter creates two anonymous Linux memfds with `os.memfd_create(..., os.MFD_ALLOW_SEALING)`:
   - FD 3: exact NEW v19.7 Step2.6 payload bytes;
   - FD 4: exact NEW v19.7 NONMUTATING Step3 payload bytes.
2. The Python bootstrap receives or embeds the complete immutable candidate payload bytes and verifies **all bytes before any payload execution** using exact length + SHA-256 + Git blob identity where applicable.
3. Only after complete verification, Python writes the complete bytes to each memfd, verifies the complete memfd contents again using `os.pread` without advancing the execution offset, and applies exactly:
   `F_SEAL_WRITE | F_SEAL_GROW | F_SEAL_SHRINK | F_SEAL_SEAL`.
4. Python verifies the seal set with `F_GET_SEALS`, rewinds both descriptors to offset 0, marks only the required descriptors inheritable, and `dup2`s them to fixed FD 3 and FD 4.
5. Python then **exec-replaces itself** with a fresh Bash process using the already-controlled post-OAuth environment and:
   `/bin/bash --noprofile --rcfile /dev/fd/3 -i`
   so the exact sealed Step2.6 bytes are executed as the rcfile of the resulting persistent Bash itself. Step2.6-created variables/functions (`EXEC_ROOT`, `git_clean`, `phase_c_verify`, etc.) therefore remain in that same Bash for later gates and Step3.
6. `/dev/fd/3` is used only as descriptor indirection to an already-open, sealed anonymous memfd; it is not a repository/tmpfs pathname that can be replaced in the filesystem namespace. Independent Lab must explicitly judge whether this descriptor handoff closes the v19.6/v19.7 TOCTOU class.
7. FD 4 remains unopened by the Step2.6 payload and remains sealed at offset 0. Before Step3, a short exact trusted-Python descriptor gate must inspect **that same inherited FD 4** with `fstat`, `F_GET_SEALS`, and `pread`, prove the exact Step3 length/hash/blob identity while preserving offset 0, and emit a fixed PASS marker.
8. Only after that descriptor PASS may the persistent Bash execute exact NEW Step3 bytes with `. /dev/fd/4`; after success it must close FD 4 and unset the descriptor marker. Because FD 4 is sealed, the bytes proven immediately before source cannot be rewritten, grown, or shrunk between proof and execution.
9. Any memfd creation/write/hash/seal/fd-number/offset/exec/rcfile/descriptor verification anomaly is terminal STOP/delete/no-retry. No alternate tempfile, pipe, process substitution, reconstruction, or fallback path is allowed.

This design intentionally rejects naive `subprocess.run(["/bin/bash"], input=d)` for Step2.6 because child-shell state would not propagate to the persistent shell required by Step3.

## Material item 3 — Git credential helper prompt conflict resolved
The NEW v19.7 successor must explicitly freeze:
- the Git credential-helper prompt is mandatory at the reviewed OAuth launch boundary;
- the only allowed operator response is **No**;
- historical v4 text saying `Yes` is superseded/non-authoritative for v19.7;
- historical v10/v9 explicit-No semantics are the intended source semantics;
- absent prompt, different prompt, auto-helper/no-prompt branch, accidental Yes, or any uncertainty => STOP/delete/no-retry before device authorization when possible.

Device-code secrecy remains exact:
- while code visible, Owner reports only `DEVICE_CODE_DISPLAYED_NO_CODE_SHARED`;
- no screenshot/photo/screen-recording/OCR/copied terminal output/transcription/code characters to Core/chat;
- after first-party GitHub connection success, Owner reports only `GITHUB_DEVICE_CONNECTED_NO_CODE_SHARED`;
- any device-code disclosure => consumed session / STOP / delete / no retry.

## Material item 4 — exact technical auth/scope/admin/nonmutation implementation
A NEW standalone review-only candidate gate has been emitted:

Path:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_1_AUTH_SCOPE_ADMIN_NONMUTATING_GATE_20260829.py`

Immutable candidate commit:
`2ecdc5345d92a6705644624b4c97d1cd9fbfa822`

Candidate identity:
- Git blob: `03f9471ecad04170d3f048d5b006458e970fd11b`
- UTF-8 bytes: `3953`
- SHA-256: `230a1424dbaf44dd584d42f64122f090817e59a3a028c268274d3db36c4458d2`
- final LF: YES

The gate is deliberately read-only. Its only GitHub API operations are exact GETs through `/usr/bin/gh api --method GET` to:
- `/user`
- `/repos/fufufu1116/multiverse-research`

It mechanically requires:
- Codespaces identity present;
- exact `GH_CONFIG_DIR=/dev/shm/multiverse-r1-stage1-phase-c-gh-auth`;
- no ambient GH/GitHub token variables, proxy variables, custom CA variables, or debug variables;
- exact authenticated login `fufufu1116`;
- exact effective OAuth scope set equality `{repo, read:org, gist}` from `x-oauth-scopes` (no subset/superset acceptance);
- repository `permissions.admin is true`;
- no mutation endpoint/method;
- success marker exactly `PHASE_C_V19_7_AUTH_SCOPE_ADMIN_NONMUTATING_PASS`;
- all gate failures exit `91` with prefix `PHASE_C_V19_7_AUTH_SCOPE_ADMIN_NONMUTATING_STOP_DELETE_CODESPACE:`.

Independent review must additionally determine whether fixed `/usr/bin/gh` is valid under the approved Codespaces system-binary trust model. If not, return FIX_REQUIRED; Core must not silently widen or substitute the binary binding.

Canonical implementation evidence used for comparison, not delegated authority:
- `tools/multiverse_r1_stage1_writer_key_admin_channel_v1.py` on canonical main: blob `ec05a014964211c15e48c3a2c327648a13f64dcf`, which independently defines expected login, exact scopes, read-only fixed endpoints and repo-admin check.
- `tools/multiverse_r1_stage1_phase_c_execution_preflight_v1.py` on canonical main: blob `0232c66bcf40cc1f61ce5bcc855604f73fce665a`; this remains the canonical NONMUTATING Step3 program semantics source.

The final successor must not import/reopen either canonical file by mutable pathname as its security-critical implementation identity. Exact NEW v19.7 artifacts must bind any executed bytes.

## Candidate post-OAuth order after remediation
The full successor, if later built and independently approved, must be exactly ordered in principle as:

`post-OAuth env-i reentry`
-> `pure-shell trusted-Python binding`
-> `complete Step2.6 + Step3 byte verification and sealed-memfd creation`
-> `exec into persistent Bash whose rcfile is sealed FD3 Step2.6`
-> exact `PHASE_C_POST_OAUTH_CLEAN_SHELL_REENTRY_PASS`
-> `NEW immutable auth/scope/admin nonmutating gate`
-> exact `PHASE_C_V19_7_AUTH_SCOPE_ADMIN_NONMUTATING_PASS`
-> `same-FD4 seal/hash/offset re-verification`
-> `source sealed FD4 exact NONMUTATING Step3 in the same persistent Bash`
-> exact Step3 PASS
-> STOP
-> Owner deletes Codespace.

No Step4 or `--apply` exists in this authority unit.

## Failure and authority boundary
Any prompt mismatch, device-code disclosure, transport/integrity mismatch, memfd/seal/descriptor mismatch, auth/scope/admin mismatch, missing marker, unexpected output preventing exact classification, shell/session loss, accidental extra input, or delivery-time Fresh/mechanical-gate failure consumes the future one-shot session and requires STOP/delete/no-retry.

No diagnosis/repair/resume/RETRIEVAL improvisation is authorized live.

## Current authority
- `CAN_BUILD_EXACT_FULL_SEQUENCE_FROM_THIS_DOCUMENT_ALONE: NO`
- `CAN_PROCEED_TO_AUDITOR_NOW: NO`
- `CAN_PRESENT_TO_OWNER_NOW: NO`
- `CAN_CREATE_CODESPACE_NOW: NO`
- `CAN_DELIVER_TERMINAL_COMMAND_NOW: NO`
- `CAN_START_OAUTH_NOW: NO`
- `CAN_RUN_AUTHENTICATED_API_OR_STEP3_NOW: NO`
- `CAN_DELIVER_STEP4_OR_APPLY_NOW: NO`
- `PRODUCTION_MUTATION_AUTHORIZED_NOW: NO`
- `RUNTIME_ACTIVATION_AUTHORIZED_NOW: NO`
- Runtime: `OFF`

Next required action is Independent Lab re-review of this remediation design and exact auth gate candidate. Only a Lab PASS may permit Core to build the exact immutable v19.7 successor action set; that exact action set will still require a separate Lab review and Auditor review before Owner presentation/live authority.
