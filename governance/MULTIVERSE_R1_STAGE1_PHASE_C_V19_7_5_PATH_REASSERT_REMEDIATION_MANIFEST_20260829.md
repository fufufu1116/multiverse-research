# MULTIVERSE R1 Stage 1 Phase C v19.7.5 — PATH REASSERT REMEDIATION MANIFEST

Status: DRAFT REVIEW ONLY / NONSECRET / NO LIVE AUTHORITY
Date: 2026-08-29 JST

## Fresh authority basis
- canonical repo: `fufufu1116/multiverse-research`
- canonical main: `74ea95e59ac0654e1a0c1f811a178b3eef7b073c`
- recovery predecessor head: `fe5d6544cb8cdd42f0035dc9fa2149390697fdfa`
- prior v19.7.4 Owner one-shot session: CONSUMED / CLOSED / CODESPACE OWNER-CONFIRMED DELETED
- production mutation performed: false
- Runtime activation performed: false
- Runtime: OFF

## Observed live failure
The v19.7.4 one-shot reached the exact read-only auth/scope/admin gate and failed before any authenticated repository mutation or Step3 execution with exact nonsecret reason:
`PHASE_C_V19_7_2_AUTH_SCOPE_ADMIN_NONMUTATING_STOP_DELETE_CODESPACE:PATH_NOT_EXACT`

This proves the immediate failure was not a repository-admin verdict. The v19.7.2 auth gate stops in `resolve_gh()` before GET `/user` when ambient `PATH` is not exactly:
`/usr/local/bin:/usr/bin:/bin:/usr/local/python/current/bin`.

The v19.7.4 MEMFD program enters an interactive Bash using sealed Step2.6 as `--rcfile`. Step2.6 previously inherited PATH and did not reassert it. The exact mechanism that changed PATH before the rcfile is not treated as proven here; the remediation is deliberately local and fail-closed: Step2.6 reasserts the already-reviewed controlled PATH at its first safe shell-state boundary before command resolution checks.

## Exact v19.7.5 remediation
### Step2.6 PATH-reassert payload
Path: `governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_5_STEP2_6_PATH_REASSERT_PAYLOAD_20260829.sh`
- immutable commit: `8383efede79e5a3f03d3dbfdf4a38ada46e37c5b`
- Git blob: `680db05323322766be6bdd7f2a2f2ef4607352bc`
- UTF-8 bytes: `3778`
- SHA-256: `a5ba299d8c2a319d6bf3f7ef2f9a773054372c77642bd782c841f008774e9c1c`
- final LF: NO

Only semantic delta from frozen v19.7.3 Step2.6 is immediately after `umask 077`:

```
PATH='/usr/local/bin:/usr/bin:/bin:/usr/local/python/current/bin'
export PATH
hash -r
```

All canonical checkout verification, memory-root/swap checks, trusted-Python binding, `phase_c_verify`, and success marker remain otherwise byte-for-byte inherited.

### v19.7.5 MEMFD bootstrap program
Path: `governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_5_MEMFD_BOOTSTRAP_PROGRAM_20260829.py`
- immutable commit: `76ff3f38cae9aeb87260166491b374378c210546`
- Git blob: `2ab6fb82c30057d1c57a9f9cf83d53437a761ddf`
- UTF-8 bytes: `3947`
- SHA-256: `ba1c5656860574c12a5ef0fa27b5a795baa84083dfe8a86d4780bcbd3e0580ee`
- final LF: YES

It preserves the v19.7.4 sealed-MEMFD/FD3+FD4/fail-closed architecture and changes only the Step2.6 immutable identity plus v19.7.5 failure/name labels. Step3 remains exact frozen v19.7.3 payload.

### v19.7.5 MEMFD bootstrap action
Path: `governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_5_MEMFD_BOOTSTRAP_ACTION_20260829.txt`
- immutable commit: `44a4d71c6e44347f6e7cef542d58e279e863054c`
- Git blob: `fa8d9380c7d893c45cc0e7d5d72b138b5059b59f`
- UTF-8 bytes: `781`
- SHA-256: `8280cbedc087765c29063268167251fe3ccf1e34c2bfa255f1053cec7e361a2f`
- internal LF: 0
- final LF: NO

## Review scope
Independent Lab must verify at minimum:
1. observed failure classification is correctly limited to `PATH_NOT_EXACT` and does not falsely claim an OAuth/admin failure;
2. PATH reassert happens before any PATH-sensitive Step2.6 command resolution;
3. `hash -r` is safe and sufficient to discard inherited Bash command hash state;
4. controlled PATH exactly matches the frozen v19.7.2 auth gate constant;
5. no weakening of the auth gate is introduced;
6. v19.7.4 sealed-MEMFD four-FD coexistence/fail-closed/`exec` semantics are preserved;
7. Step3 identity remains unchanged;
8. no live retry, production mutation, Step4, `--apply`, main/ruleset mutation, writer-key/secret operation, merge, or Runtime activation is authorized by this remediation.

## Authority
- `CAN_PROCEED_TO_INDEPENDENT_LAB_NOW: YES`
- `CAN_PROCEED_TO_INDEPENDENT_AUDITOR_NOW: NO`
- `CAN_PRESENT_TO_OWNER_NOW: NO`
- `CAN_CREATE_CODESPACE_NOW: NO`
- `CAN_DELIVER_TERMINAL_COMMAND_NOW: NO`
- `CAN_START_OAUTH_NOW: NO`
- `CAN_RUN_AUTHENTICATED_API_OR_STEP3_NOW: NO`
- `PRODUCTION_MUTATION_AUTHORIZED_NOW: NO`
- `RUNTIME_ACTIVATION_AUTHORIZED_NOW: NO`
- Runtime: `OFF`

A Lab PASS may permit only a later independent Auditor review. A new live attempt requires Lab PASS + Auditor PASS + a new explicit Owner one-shot approval.