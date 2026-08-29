# MULTIVERSE R1 Stage 1 Phase C v19.7.4 — MEMFD / FAIL-CLOSED REMEDIATION MANIFEST

Status: DRAFT REVIEW ONLY / NONSECRET / NO LIVE AUTHORITY
Date: 2026-08-29 JST

## Fresh basis
- canonical repo: `fufufu1116/multiverse-research`
- canonical main Fresh-read: `74ea95e59ac0654e1a0c1f811a178b3eef7b073c`
- canonical tree: `3d47741b4863411e5c36cb4c28925ac455ab6441`
- predecessor exact-sequence request head Fresh-read: `77b0b30daa18b396a3c32d132ced01f4970bb8ba`
- Independent Lab v19.7.3 result: PR #74 comment `5460982313` = `FIX_REQUIRED`
- material blockers from that review: exactly (1) original-memfd close ordering mismatch and (2) bootstrap child failure returning to usable authenticated post-OAuth shell.

All v19.7.3 findings explicitly marked PASS by comment `5460982313` are inherited as evidence only and are not modified here. This successor changes only the MEMFD bootstrap program and its terminal action. Historical v19.7.3 bootstrap program/action are superseded/NONAUTHORITY for any future live sequence.

## NEW exact artifacts
### v19.7.4 bootstrap program
Path:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_4_MEMFD_BOOTSTRAP_PROGRAM_20260829.py`

Immutable commit: `a057fe59fff82043273d0223a5eaba3703079ca4`
Git blob: `67d51d6caddfc96f45a98aa5cacac35c51263df5`
UTF-8 bytes: `3933`
SHA-256: `4f8f4c5629b5f9198385c88fd8581ca6028b54bcf8dc3409a58ceaf1d67bc199`

The program retains both original sealed memfds and both collision-safe `F_DUPFD_CLOEXEC >=10` duplicates until both payloads have successfully completed fetch, identity verification, memfd write, pread, sealing, seal verification and high-FD duplication. Only after `len(originals)==2`, `len(highs)==2`, and all four descriptors are distinct does the success path close the two originals. It then maps the two safe high duplicates to fixed inherited FD3/FD4. Failure cleanup may close already-created descriptors because the authority process must terminate; the frozen ordering requirement applies to the successful transition toward fixed FD3/FD4.

### v19.7.4 bootstrap terminal action
Path:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_4_MEMFD_BOOTSTRAP_ACTION_20260829.txt`

Immutable commit: `e47fdcc1ef6a82ae3ea5ba25f241ba9d15b40a7f`
Git blob: `5e2cbf8dc140ebd3363c2f5e5a00cf36b816d9db`
UTF-8 bytes: `781`
SHA-256: `78a4a9bbec16d51946cf3354fa160cd544d3fe8c9118a755a4ede632d1e6ce2d`
Internal LF: `0`
Final LF: `NO`

The terminal action now begins with shell builtin `exec /usr/local/python/current/bin/python ...`. Therefore the authenticated post-OAuth clean shell is replaced by the trusted Python authority process before any bootstrap fetch/hash/write/seal work. If wrapper fetch/identity/compile/exec fails, or the bootstrap program exits 93 before successful Bash exec, there is no parent interactive authority shell to return to. On success, the same process is subsequently `os.execve`-replaced by `/bin/bash --noprofile --rcfile /dev/fd/3 -i`.

## Exact successor state-machine delta
The v19.7.3 full sequence remains unchanged through post-OAuth trusted-Python PASS. Its old Step13-17 bootstrap program/action are replaced only by the two exact v19.7.4 artifacts above.

Required transition:
`post-OAuth exact trusted-Python PASS -> Fresh/mechanical verification of v19.7.4 terminal action -> exec-replacing v19.7.4 wrapper -> exact complete program identity proof -> both exact payload identities -> both sealed originals + both safe high duplicates simultaneously live -> success-path close both originals -> dup2 high duplicates to inheritable FD3/FD4 -> fixed-FD verification -> execve persistent Bash with sealed FD3 rcfile -> exact Step2.6 PASS -> unchanged v19.7.3 auth gate -> unchanged sealed-FD4 Step3 -> exact NONMUTATING Step3 PASS -> STOP/delete`

Any wrapper/bootstrap failure terminates the authority process; it is never a return-to-shell event. No retry, repair, RETRIEVAL, resume, alternate path, second Codespace under the same approval, or ad-hoc command is authorized.

## Explicit nonauthority
This remediation does not authorize Codespace creation, terminal command delivery, OAuth/device flow, authenticated API/Step3, Step4, `--apply`, production mutation, main/ruleset mutation, writer-key/secret operation, merge, Runtime branch/activation/workflow/tasks/Sources/scheduler, or Runtime activation.

- `CAN_PROCEED_TO_AUDITOR_NOW: NO`
- `CAN_PRESENT_TO_OWNER_NOW: NO`
- `CAN_CREATE_CODESPACE_NOW: NO`
- `CAN_DELIVER_TERMINAL_COMMAND_NOW: NO`
- `PRODUCTION_MUTATION_AUTHORIZED_NOW: NO`
- `RUNTIME_ACTIVATION_AUTHORIZED_NOW: NO`
- Runtime: `OFF`

Next gate: Independent Lab micro re-review of the two material blockers plus regression check. A PASS may permit Core to send the exact v19.7.4 successor sequence to Independent Auditor; it does not itself authorize live execution.