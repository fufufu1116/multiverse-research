# MULTIVERSE R1 Stage 1 Phase C v19.7.11 — EXACT ACTION / COMPLETE-TRANSPORT FAULT HARNESS FREEZE

Status: DRAFT REVIEW ONLY / STATIC ONLY / NO LIVE AUTHORITY
Date: 2026-08-30 JST

## Trigger
Independent Lab v19.7.10 result on PR #74 comment `5463259267` returned `FIX_REQUIRED` with exactly two remaining blockers:
- `TRANSPORT_FAULT_HARNESS_ADEQUATE: FAIL`
- `MOBILE_TRANSPORT_RISK_REDUCTION_STILL_MATERIAL: FAIL`

All v19.7.10 TOCTOU / verified-bytes-to-executed-bytes / fail-closed / shell-fallback properties were PASS and are preserved.

## v19.7.11 remediation
Branch: `agent/r1-stage1-phase-c-v19-7-11-exact-action-fault-harness`

### Exact mobile action
Path:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_11_STEP3_COMPLETE_TRANSPORT_ACTION_20260830.txt`

Identity:
- UTF-8 bytes: `561`
- SHA-256: `12190dece28a387130a28d1033bffeb47b5b03bc6ccbbd76f9907c33b1549793`
- Git blob: `c812a0e573835b4a1946371f0a68caa9b7c92be2`
- one line / no final LF

Transport delta:
- v19.7.8 incident action: `1394` bytes
- v19.7.10 action: `1072` bytes
- v19.7.11 action: `561` bytes
- reduction vs incident action: `59.8%`
- reduction vs v19.7.10: `47.7%`

The action uses a shell brace-group completeness gate:
`{ exec ... || exit 92; }`
The final `}` is required for shell parsing. Static exhaustive prefix testing confirms that the full exact 561-byte action parses, while every strict nonempty prefix of the exact action fails `bash -n` parsing. Thus an incomplete/truncated transport cannot become a syntactically complete partial command; it remains non-executable/incomplete rather than silently dispatching a shortened variant.

### Short immutable runner path
Path: `g/r`
Immutable commit: `a1389e74d4a9e44142d9962e4396fe819245ae8f`
Identity:
- UTF-8 bytes: `1414`
- SHA-256: `8285553a0b8d7593b0382bb97c5925fd61be4d8980923f49c81d2ddc71648d64`
- Git blob: `4f96c8e853357be4b57a864240c365208f755d1d`

This is byte-identical to the reviewed v19.7.9 pinned runner; only the immutable repository pathname is shortened to reduce mobile transport length.

The 561-byte action fetches the immutable runner into Python memory `d`, checks exact length + SHA-256 + Git blob, and hands the same verified `d` bytes directly to `/bin/bash` as stdin. No runner pathname is created or reopened.

## Exact-action fault harness
Path:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_11_EXACT_ACTION_FAULT_HARNESS_20260830.py`
Git blob: `b7d23ee8a12e7b9e2ee733319e1a553c8fe09eac`

The harness reads and tests the exact 561-byte action itself, not a synthetic replacement. It covers:
1. exact action and exact runner identity;
2. full-action shell parse success;
3. exhaustive strict-prefix truncation injection: every prefix length 1..560 fails shell parsing;
4. exact embedded Python payload with tampered runner bytes: exit 92 before dispatch;
5. exact embedded Python payload with fetch failure: dispatch not reached;
6. exact embedded Python payload with verified runner bytes plus injected `/bin/bash` dispatch failure return code 37: exact same runner object is passed and failure propagates;
7. shell-level `exec ... || exit 92` barrier and final brace completeness gate are present in the exact action.

Deterministic local static execution result:
`PHASE_C_V19_7_11_EXACT_ACTION_FAULT_HARNESS_PASS`

## Preserved security properties
- verified runner bytes and executed runner bytes are the same in-memory object;
- mutable pathname TOCTOU remains removed;
- runner fetch/identity failure occurs before runner dispatch;
- original authenticated shell is replaced by shell builtin `exec`; shell-level exec failure has an explicit exit-92 barrier;
- downstream runner/executor failure cannot return to the original authenticated shell;
- v19.7.7 standalone NONMUTATING executor identity/trust model is unchanged;
- canonical NONMUTATING preflight semantics are unchanged.

## Review boundary
Independent Lab should re-review only whether v19.7.11 closes the two remaining v19.7.10 blockers while preserving the already-PASS properties. In particular decide:
- whether the exact-action harness adequately injects truncation/incomplete transport and runner-dispatch failure against the exact action;
- whether exhaustive strict-prefix non-parseability plus a 59.8% reduction from the incident action materially closes mobile transport uncertainty without relying on an unknown empirical cutoff;
- whether the brace-group completeness gate itself introduces any fallback or authority regression;
- whether shortening the immutable runner repository path changes no runner semantics.

## Explicit nonauthority
No Codespace creation, OAuth/live terminal execution, authenticated Step3, Step4, `--apply`, production mutation, provision-fence/Environment mutation, writer-key/secret operation, main/ruleset mutation, merge, Runtime branch/sequence0, activation receipt/tag, workflow dispatch, Runtime state/tasks/Sources/scheduler, or Runtime activation is authorized.

Runtime: `OFF`
