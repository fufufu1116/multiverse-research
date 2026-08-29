# MULTIVERSE R1 Stage 1 Phase C v19.7.2 — GH Binary Binding Remediation

Status: DRAFT REVIEW ONLY / NONSECRET / NO LIVE AUTHORITY
Date: 2026-08-29 JST

## Fresh authority basis
- canonical repo: `fufufu1116/multiverse-research`
- canonical main: `74ea95e59ac0654e1a0c1f811a178b3eef7b073c`
- canonical tree: `3d47741b4863411e5c36cb4c28925ac455ab6441`
- predecessor recovery head: `d6d625c9d536f116fcd3e6ae2ff081d29cbbd20e`
- Independent Lab v19.7.1 FIX_REQUIRED: PR #74 comment `5460729983`

This document remediates only the remaining GH binary binding blocker. It does not authorize Codespace creation, terminal execution, OAuth, authenticated API, Step3, Step4, `--apply`, production mutation, merge, or Runtime.

## Accepted v19.7.1 design findings retained
The Independent Lab already returned design-level PASS for:
- the verified-tempfile/reopen ban;
- sealed anonymous memfd complete-byte verification and sealing model;
- persistent Bash rcfile execution of sealed FD3 for Step2.6;
- sealed FD4 immediate re-verification and same-shell source for Step3;
- mandatory Git credential prompt + exact `No`, with historical v4 `Yes` superseded;
- exact login / exact effective scope set `{repo, read:org, gist}` / repository-admin / read-only semantics;
- post-OAuth ordering, subject only to the GH binding blocker.

Those accepted findings are not widened here.

## Remaining blocker
v19.7.1 froze `GH_BIN=/usr/bin/gh`. Lab found no Fresh reviewed evidence that `/usr/bin/gh` itself was an already-approved exact Codespaces/system-binary path. Canonical main instead uses `shutil.which("gh")` and bare `gh` under a controlled PATH.

v19.7.2 therefore removes the unsupported `/usr/bin/gh` assumption rather than trying to justify it retroactively.

## New exact successor binding semantics
New gate candidate:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_2_AUTH_SCOPE_ADMIN_NONMUTATING_GATE_20260829.py`

Immutable candidate commit:
`864202e5821755d4adfbf897c6f0420b83f04211`

Git blob:
`8436ccb6d0c9f7799546bba43116d3fa56bf8159`

The GH binding is now defined mechanically as **controlled-PATH resolution**, not as an unproven hard-coded filesystem location:

1. The current post-OAuth shell must have PATH exactly:
   `/usr/local/bin:/usr/bin:/bin:/usr/local/python/current/bin`
2. The gate runs `shutil.which("gh", path=CONTROLLED_PATH)` and requires a result.
3. The resolved result must be absolute, an executable regular file, and `shutil.which("gh")` under the current exact PATH must resolve to that same result.
4. The exact resolved absolute value is then carried as `gh_bin` into both API subprocess calls. The subprocess receives the same exact controlled PATH.
5. No fallback path, alternate `gh`, shell alias/function, PATH widening, hard-coded `/usr/bin/gh`, or silent substitution is allowed.
6. If PATH differs, resolution is missing/invalid, or explicit/current resolution differs, the gate exits 91 with the fixed STOP/delete prefix.

This deliberately matches the canonical trust model more closely than v19.7.1: canonical main checks `shutil.which("gh")` and invokes `gh` under the controlled process environment. The successor strengthens that model by freezing the PATH equality and passing the already-resolved absolute executable to the two read-only subprocesses.

## Auth gate semantics unchanged except marker version
The candidate still performs only two GitHub API reads with `--method GET`:
- `/user`
- `/repos/fufufu1116/multiverse-research`

It still requires:
- Codespaces identity;
- exact GH_CONFIG_DIR;
- absence of ambient GH/GitHub token, proxy, custom CA and debug variables;
- exact authenticated login `fufufu1116`;
- exact effective OAuth scope set equality `{repo, read:org, gist}`;
- repository `permissions.admin is true`;
- no mutation endpoint/method.

Success marker:
`PHASE_C_V19_7_2_AUTH_SCOPE_ADMIN_NONMUTATING_PASS`

Failure prefix:
`PHASE_C_V19_7_2_AUTH_SCOPE_ADMIN_NONMUTATING_STOP_DELETE_CODESPACE:`

## Review question
Independent Lab must determine whether this exact controlled-PATH resolution contract is sufficiently bound and consistent with the already-approved Codespaces trust surface. If not, return FIX_REQUIRED and identify the missing proof. Do not silently substitute another path or binary-binding model.

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

Next action: Independent Lab micro re-review of this sole remaining GH binding remediation. Only PASS may return Core to exact full-sequence construction; that later exact sequence still requires separate independent Lab and Auditor review before any Owner presentation or live authority.
