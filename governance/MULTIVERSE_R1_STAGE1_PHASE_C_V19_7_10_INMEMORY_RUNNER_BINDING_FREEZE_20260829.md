# MULTIVERSE R1 Stage 1 Phase C v19.7.10 — IN-MEMORY RUNNER BINDING FREEZE

Status: DRAFT REVIEW ONLY / STATIC ONLY / NO LIVE AUTHORITY
Date: 2026-08-29 JST

## Trigger
Independent Lab v19.7.9 result on PR #74 comment `5463165492` returned `FIX_REQUIRED` because the 476-byte short action verified a runner stored at `/dev/shm/x` and then reopened the same mutable pathname for `exec /bin/bash $p`. Lab therefore marked `RUNNER_PIN_AND_HASH_BINDING: FAIL`, `FAIL_CLOSED_BEFORE_RUNNER_EXEC: FAIL`, and required an additional transport fault harness.

## Exact remediation
New action:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_10_STEP3_INMEMORY_RUNNER_ACTION_20260829.txt`

- UTF-8 bytes: `1072`
- SHA-256: `f322cea79d42c801716d6f9cd8e0897b5c0a1b80903ea405c68adef8c8ed11fb`
- Git blob: `df2afb73d5b5f558cc8088d82a700dba6f21d3e4`
- one line / no final LF

The action preserves sanitized `env -i` replacement of the authenticated shell. It fetches the immutable v19.7.9 runner directly into Python memory (`d=r.stdout`), verifies exact runner length + SHA-256 + Git blob, and then supplies that exact verified byte object directly as Bash stdin via `subprocess.run(["/bin/bash"], input=d)`. No runner pathname is created, no runner pathname is reopened, and `/dev/shm/x` is removed from the execution design.

Pinned runner remains unchanged:
- immutable commit: `64b6e01dc17a737bcefc06ec0b864e604fc9c2e8`
- path: `governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_9_STEP3_PINNED_RUNNER_20260829.sh`
- bytes: `1414`
- SHA-256: `8285553a0b8d7593b0382bb97c5925fd61be4d8980923f49c81d2ddc71648d64`
- Git blob: `4f96c8e853357be4b57a864240c365208f755d1d`

## Fail-closed properties
1. curl nonzero exits 92 before runner dispatch.
2. length/SHA-256/Git-blob mismatch exits 92 before runner dispatch.
3. there is no mutable runner pathname custody/reopen interval.
4. the bytes checked in `d` are the bytes passed to `/bin/bash` as stdin.
5. shell-level `exec` failure is caught by the existing outer failure barrier and exits 92.
6. after successful shell `exec`, the prior authenticated shell has been replaced by `/usr/bin/env`/Python; downstream runner or standalone executor failure cannot return to it.
7. v19.7.7 standalone NONMUTATING executor identity and canonical preflight semantics are unchanged because the pinned runner is unchanged.

## Transport fault harness
Path:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_10_INMEMORY_BINDING_HARNESS_20260829.py`

- UTF-8 bytes: `1384`
- SHA-256: `f430d0df6abed6fec52e5e9a09ebbcdcc9b3a979d896b9516f3c0ff808c89d0e`
- Git blob: `546dc3783a25f14a3798fb9e1affbf5412e9b8ed`

Static local execution evidence:
- `tamper_rejected_before_exec:PASS`
- `verified_bytes_direct_to_bash_stdin:PASS`
- `no_runner_pathname_reopen:PASS`
- `PHASE_C_V19_7_10_INMEMORY_BINDING_HARNESS_PASS`

The harness is intentionally limited to the v19.7.9 Lab blocker: executed-byte binding and rejection-before-dispatch. It does not claim live Codespaces evidence.

## Review boundary
Independent Lab should determine whether this exact v19.7.10 remediation closes comment `5463165492`, specifically:
- whether verified bytes and executed bytes are now sufficiently bound without pathname TOCTOU;
- whether failure before runner dispatch is fail-closed;
- whether the additional transport harness is adequate for this blocker;
- whether the v19.7.7 standalone executor trust and canonical NONMUTATING preflight semantics remain unchanged;
- whether 1072-byte mobile transport remains a material risk reduction versus the historical 1394-byte direct loader, while acknowledging it is longer than v19.7.9's rejected 476-byte action.

## Explicit nonauthority
No Codespace creation, OAuth, live terminal execution, authenticated Step3, Step4, `--apply`, production mutation, provision-fence/Environment mutation, writer-key/secret operation, main/ruleset mutation, merge, Runtime branch/sequence0, activation receipt/tag, workflow dispatch, Runtime state/tasks/Sources/scheduler, or Runtime activation is authorized.

- `CAN_PROCEED_TO_INDEPENDENT_LAB_RE_REVIEW_NOW: YES`
- `CAN_PROCEED_TO_INDEPENDENT_AUDITOR_NOW: NO`
- `CAN_PRESENT_TO_OWNER_NOW: NO`
- `PRODUCTION_MUTATION_AUTHORIZED_NOW: NO`
- `RUNTIME_ACTIVATION_AUTHORIZED_NOW: NO`
- Runtime: `OFF`
