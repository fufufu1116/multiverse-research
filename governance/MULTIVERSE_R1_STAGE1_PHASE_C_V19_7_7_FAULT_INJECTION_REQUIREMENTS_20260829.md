# MULTIVERSE R1 Stage 1 Phase C v19.7.7 — FAULT-INJECTION REQUIREMENTS

Status: DRAFT REVIEW ONLY / NONSECRET / NO LIVE AUTHORITY

The v19.7.7 standalone Step3 executor is not eligible for Independent Lab review until a deterministic static/offline test harness demonstrates bounded failure classification for every required injected fault.

Required cases and expected bounded class:

| Case | Required expected class |
|---|---|
| baseline valid fixture | `PHASE_C_V19_7_7_NONMUTATING_STEP3_PASS` |
| controlled PATH mismatch | `PATH` |
| GH_CONFIG_DIR mismatch | `GH_CONFIG_DIR` |
| Codespaces binding mismatch | `CODESPACE_BINDING` |
| trusted interpreter mismatch | `TRUSTED_PYTHON` |
| wrong canonical HEAD | `HEAD` |
| attached HEAD | `DETACHED_HEAD` |
| wrong origin | `ORIGIN` |
| dirty worktree | `WORKTREE_DIRTY` |
| wrong critical-file blob | `CRITICAL_FILE_BLOB` or earlier exact critical-file metadata class if fixture intentionally changes metadata |
| preflight child nonzero | `PREFLIGHT_NONZERO:<rc>` |
| malformed preflight JSON | `PREFLIGHT_JSON` |
| wrong preflight status | `PREFLIGHT_STATUS` |
| `production_mutation_performed` not exactly false | `PRODUCTION_MUTATION_FLAG` |
| `runtime_activation_performed` not exactly false | `RUNTIME_ACTIVATION_FLAG` |

The harness must not use real GitHub authentication, real OAuth, repository mutation, production mutation, real ruleset changes, writer keys/secrets, or Runtime activation. Fixtures may use temporary directories and local temporary Git repositories only.

Acceptance conditions:
1. every injected case produces exactly the expected bounded class;
2. no case depends on a long-lived inherited FD3/FD4;
3. no generic-only `92` is considered sufficient diagnostic evidence;
4. the production executor and harness share or mechanically mirror the same classification contract;
5. harness output contains no secrets and is safe for PR review;
6. Runtime remains OFF.

Until these conditions are met:
- `CAN_PROCEED_TO_INDEPENDENT_LAB_NOW: NO`
- `CAN_CREATE_CODESPACE_NOW: NO`
- `CAN_DELIVER_TERMINAL_COMMAND_NOW: NO`
- `PRODUCTION_MUTATION_AUTHORIZED_NOW: NO`
- `RUNTIME_ACTIVATION_AUTHORIZED_NOW: NO`
