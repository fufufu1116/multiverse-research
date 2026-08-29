# MULTIVERSE R1 Stage 1 Phase C v19.7.12 — ABSOLUTE CURL BINDING FREEZE

Status: DRAFT REVIEW ONLY / STATIC ONLY / NO LIVE AUTHORITY
Date: 2026-08-30 JST

## Trigger
Independent Lab v19.7.11 result on PR #74 comment `5463395112` returned `FIX_REQUIRED` solely because the 561-byte exact action regressed the pre-dispatch fetch executable from absolute `/usr/bin/curl` to bare PATH-resolved `curl`.

The same Lab result independently PASSed the v19.7.11 exact-action identity, exhaustive strict-prefix truncation gate, exact-action fault harness, runner dispatch failure boundary, mobile-transport closure for the reviewed truncation class, verified/executed bytes binding, pathname-TOCTOU removal, shell exec failure barrier, no authenticated-shell fallback, v19.7.7 standalone executor trust, and canonical NONMUTATING preflight semantics.

## Exact remediation
New action:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_12_STEP3_COMPLETE_TRANSPORT_ACTION_20260830.txt`

Only security-semantic delta from v19.7.11 action: the `subprocess.check_output` fetch argv executable is changed from bare `curl` to exact absolute `/usr/bin/curl`.

Exact action identity:
- UTF-8 bytes: `570`
- SHA-256: `d0b677cf5babb538da439646487f8b74b044b0c8db43b7441ce13505464cc689`
- Git blob: `eb224cd040946f6b1421ebc7d8e5d95ecbfa30e5`
- one line / no final LF

Preserved runner:
- immutable runner commit: `a1389e74d4a9e44142d9962e4396fe819245ae8f`
- runner path: `g/r`
- runner bytes: `1414`
- runner SHA-256: `8285553a0b8d7593b0382bb97c5925fd61be4d8980923f49c81d2ddc71648d64`
- runner Git blob: `4f96c8e853357be4b57a864240c365208f755d1d`

## Exact-action harness update
Path:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_12_EXACT_ACTION_FAULT_HARNESS_20260830.py`

Git blob: `bae6c90d0d311e7d2220a537438e0fde600b0941`

The harness retains exact-action identity, exhaustive strict-prefix parse gating, tamper rejection, fetch failure, same verified bytes -> Bash stdin, dispatch-failure propagation, and final shell completeness barrier checks. It additionally asserts the actual extracted exact payload calls `subprocess.check_output` with argv[0] exactly `/usr/bin/curl` in success, tamper, and fetch-failure injected paths.

Core separately mechanically checked the exact 570-byte candidate with `/bin/bash -n -c`: complete action parses; no strict nonempty prefix 1..569 parses.

## Review boundary
Independent Lab micro re-review should focus on whether comment `5463395112` is closed without regressing the already-PASS v19.7.11 properties. In particular:
- exact pre-dispatch fetch executable is pinned to `/usr/bin/curl` and cannot be PATH-substituted;
- fetch failure still occurs before runner dispatch;
- runner identity and same-verified-bytes dispatch are unchanged;
- exact action remains complete-transport gated under every strict truncation;
- updated harness materially covers executable resolution rather than mocking away the argv identity question.

## Explicit nonauthority
No Codespace creation, OAuth/live terminal execution, live Step3, Step4, `--apply`, production mutation, main/ruleset mutation, provision-fence/Environment mutation, writer-key/secret operation, merge, Runtime branch/state/tasks/Sources/scheduler, or Runtime activation is authorized.

- `CAN_PROCEED_TO_INDEPENDENT_LAB_RE_REVIEW_NOW: YES`
- `CAN_PROCEED_TO_INDEPENDENT_AUDITOR_NOW: NO`
- `CAN_CREATE_CODESPACE_NOW: NO`
- `PRODUCTION_MUTATION_AUTHORIZED_NOW: NO`
- `RUNTIME_ACTIVATION_AUTHORIZED_NOW: NO`
- Runtime: `OFF`
