# MULTIVERSE BOOTSTRAP — Stable Recovery Locator

Status: STABLE_LOCATOR_CANDIDATE — MUTABLE_CAS_POINTER  
Purpose: reconstruct Multiverse project state after chat/runtime loss without treating conversation memory as canonical.

## Canonical repository

`fufufu1116/multiverse-research`

Accepted-state authority is the verified GitHub canonical lineage. Recovery mirrors are non-authoritative copies.

## Normal bootstrap

1. Read `multiverse_vnext/VNEXT_CURRENT_STATE_v0.json` from canonical `main`.
2. Verify its `state_generation`, parent/supersession chain and pinned artifact identities.
3. Follow its pinned Keirin pause receipt and recovery manifest/receipt locators.
4. Reconstruct current phase, protected boundaries, next gate and open Owner Gates.
5. Continue from the stated next action. Do not replay completed work merely because chat history is missing.

## Pre-merge / active-vNext fallback

If `main` does not yet contain this bootstrap/current-state pair:

1. List open pull requests in `fufufu1116/multiverse-research`.
2. Select the **single** open draft PR whose title begins `[ACTIVE-VNEXT]`.
3. Require its base SHA to equal the observed current `main` HEAD or stop with `ACTIVE_VNEXT_BASE_DRIFT`.
4. Read this bootstrap and `multiverse_vnext/VNEXT_CURRENT_STATE_v0.json` from that PR head.
5. Verify the Current State CAS lineage before using it.
6. If zero or more than one `[ACTIVE-VNEXT]` PR exists, stop with `RECOVERY_AMBIGUOUS`.

Current Batch-1 recovery candidate:
- PR: `#2`
- working branch: `agent/multiverse-vnext-bootstrap-batch1`
- paused canonical main: `ea2559b429bf04a1bd0acee13412ed783e92be5d`

## Second physical root

Google Drive folder:
- name: `MULTIVERSE_VNEXT_RECOVERY`
- id: `1-9uS0-_6oXj9aFbeykonk5-8ss6SpkH4`
- role: `NON_AUTHORITATIVE_RECOVERY_COPY`

Use a Drive package only to recover bytes/state candidates. Before any mutation or promotion, reconcile recovered identities against GitHub canonical history.

## Keirin firewall

Bootstrap/restore must use governance metadata only.

Never open or consume:
- `ECON_HOLDOUT1000`;
- DEV2000 C for new-lineage rescue;
- protected RESULT/PAYOUT material.

Expected protected state at the recorded pause:
- `ECON_HOLDOUT1000 = SEALED`
- new-lineage DEV2000 C scoring count = 0
- new untouched validation not opened
- resume gate = `DIGITAL_TWIN_REALITY_CALIBRATION_PLUS_C0_C1_N1_MULTI_WORLD_STRESS_BEFORE_NEW_UNTOUCHED_REAL_VALIDATION`

A later legitimate verified canonical Keirin state may supersede the pause receipt. Older memory/handoff may not roll it back.

## Failure modes

- conflicting states -> `RECOVERY_AMBIGUOUS`
- missing current external facts -> `UNKNOWN`, `STALE`, or `OFFLINE_UNAVAILABLE`
- stale state writer -> `FAIL_CLOSED_NO_WRITE`
- Drive-only state with no GitHub reconciliation -> `RECOVERY_COPY_NOT_CANONICAL`

END
