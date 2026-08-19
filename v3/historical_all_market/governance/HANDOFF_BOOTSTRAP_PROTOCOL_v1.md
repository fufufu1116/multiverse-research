# Multiverse Keirin — Durable Handoff / Bootstrap Protocol v1

Status: OPERATIONAL GOVERNANCE — DOES NOT CHANGE SCIENTIFIC FREEZES
Created: 2026-08-19 JST

## Purpose

Make new-chat continuation low-friction and fail-closed. The Owner should not have to reconstruct long research history, re-upload known artifacts, or restate frozen boundaries every time a conversation rolls over.

This protocol changes only recovery/orientation procedure. It does not authorize model refits, result access, settlement access, holdout opening, network collection, or semantic changes to a frozen lineage.

## Canonical storage roles

1. **GitHub `fufufu1116/multiverse-research` = canonical source of truth** for:
   - code;
   - governance / preregistration / Freeze documents;
   - current-state manifests;
   - artifact identity / SHA records;
   - audit history;
   - continuation checkpoints;
   - lessons learned.
2. **Google Drive = heavy-artifact / execution storage** for large CSV/JSON/ZIP/raw outputs and Colab run products.
3. **ChatGPT File Library / current-chat attachments = recovery/fallback sources**, not automatic canonical truth.
4. **Conversation memory/context = convenience only**. It may point to artifacts, but must not upgrade an artifact to verified status.

## Stable bootstrap entrypoints

Every new chat should try to load, in this order:

1. `v3/historical_all_market/governance/CURRENT_STATE_KEIRIN.json`
2. `v3/historical_all_market/governance/HANDOFF_BOOTSTRAP_PROTOCOL_v1.md`
3. `v3/historical_all_market/governance/ARTIFACT_POINTER_REGISTRY_KEIRIN_v1.json`
4. latest immutable `CONTINUATION_CHECKPOINT_*`
5. latest relevant Lessons-Learned / independent-audit artifacts referenced by CURRENT_STATE.

The stable `CURRENT_STATE_KEIRIN.json` is updated in place after material milestones. Immutable dated checkpoints remain append-only history.

## New-chat automatic recovery algorithm

On a keirin continuation trigger, No.3 must:

### Step 1 — recover before asking

Attempt, without asking the Owner to restate history:

- GitHub canonical files;
- Google Drive folders/files referenced by the pointer registry;
- current-chat attachments;
- File Library when relevant;
- active runtime files when available.

Do not ask for re-upload until the documented recovery routes have been exhausted or a connector attempt actually fails.

### Step 2 — classify every important object

Use the following evidence ladder:

`REFERENCED -> LOCATED -> READABLE -> BYTE_ACCESSIBLE -> HASH_VERIFIED -> CANONICAL`

Never skip levels silently.

A SHA written in a handoff text or old receipt is a claimed identity until the corresponding bytes/blob are available and verified in the current recovery path. A GitHub blob fetched directly may be treated as GitHub-verified for that file/version; a Drive artifact is byte-verified only after its actual bytes/hash are checked.

### Step 3 — emit a compact startup state

Internally and, when useful, visibly summarize:

- `RECOVERED`: artifacts/state actually found;
- `UNPROVEN`: referenced but not byte/SHA verified;
- `MISSING`: expected artifact not found after recovery attempts;
- `SEALED`: boundaries that must not be opened;
- `NEXT GATE`: exact safe action to resume.

Contradictions between memory, handoff text, GitHub and Drive must be surfaced. GitHub canonical governance wins unless a later independently verified superseding artifact exists.

### Step 4 — enforce hard boundaries before work

Current research boundaries must be loaded from CURRENT_STATE, not guessed from memory.

At minimum, while the current state says so:

- `ECON_HOLDOUT1000 = SEALED`;
- current DEV2000 C is not to be repurposed/rescored for new-lineage rescue;
- no same-lineage B/C rescue tuning;
- no unauthorized RESULT/PAYOUT access;
- no unverified artifact may be treated as confirmed;
- no unauthorized network collection;
- no semantic Freeze/promotion without the required independent audit gate.

Any ambiguity about a protected boundary is FAIL-CLOSED.

### Step 5 — resume instead of re-explaining

If CURRENT_STATE and required artifacts are coherent, continue directly from `next_exact_actions` / `next_gate`.

Do not make the Owner repeat completed stages, known SHAs, model coefficients, or prior diagnostics unless a contradiction genuinely requires human resolution.

## Handoff maintenance rule

No.3 must maintain handoff readiness continuously rather than waiting for the conversation limit.

After every **material milestone** (new Freeze, audit verdict, lineage status change, protected-boundary change, major diagnostic conclusion, new canonical artifact identity, or new next-gate decision):

1. write/append the immutable scientific or diagnostic receipt as appropriate;
2. update `CURRENT_STATE_KEIRIN.json`;
3. update `ARTIFACT_POINTER_REGISTRY_KEIRIN_v1.json` only if storage identities/locations changed;
4. create a new immutable continuation checkpoint only when the restart point materially changes.

Routine code edits, retries, I/O fixes, and minor diagnostics do not require a new handoff document if CURRENT_STATE still points to the correct next gate.

## Owner effort target

Normal new-chat command should be only:

`Multiverse競輪ver 引き継ぎ起動。実物優先で自動回収し、CURRENT_STATEから続行。`

Even this full sentence is not mandatory if the conversation clearly indicates continuation; it is simply the deterministic bootstrap phrase.

## Artifact write discipline

- Never overwrite immutable receipts/checkpoints.
- Stable pointer files (`CURRENT_STATE_KEIRIN.json`, pointer registry) may be updated in place with Git history preserving prior versions.
- Every canonical scientific artifact should expose identity, role, provenance and SHA where applicable.
- Large Drive-only artifacts must have a GitHub-side pointer/receipt sufficient to locate and verify them without relying on chat memory.
- If a Drive folder/file ID changes, update the pointer registry before relying on the new location.

## Separation of state types

Do not mix:

- **scientific state**: Freeze/trial/validation/seal status;
- **operational state**: what file/run is currently being recovered or implemented;
- **diagnostic state**: postmortem lessons that cannot rescue the closed lineage;
- **design candidate state**: proposals not yet independently approved/frozen.

CURRENT_STATE must label these separately.

## Final keirin-to-core handoff

When the keirin research is formally complete, create a separate final artifact:

`MULTIVERSE_KEIRIN_TO_CORE_FINAL_LESSONS_AND_HANDOFF_v1`

Only then should keirin-derived governance improvements be proposed for Multiverse Core adoption. Until then, Core work must not alter the active keirin Freeze/seal history.

END OF PROTOCOL
