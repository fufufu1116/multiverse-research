# Research Lane B Completion / Exit Gate v1 — Current-Main Update

Lane B major goal: make the fixed review control plane safe for multiple chats without collision, stale-result adoption, retry deadlock, or routine Owner traffic control.

The completion matrix remains intentionally stricter than “Candidate exists”. A critical row is complete only when it is `ADOPTED_PROVEN`. A frozen Candidate receives partial progress credit but never makes the major goal complete.

Current mechanically computed state:

- critical rows: 11
- `ADOPTED_PROVEN`: 4
- `FROZEN_CANDIDATE`: 7
- `OPEN_INTEGRATION`: 0
- progress: 77.73%
- major goal complete: false

What changed from the prior 71.82% matrix:

- `combined_fault_replay` is no longer an untouched integration row.
- PR #242 created the pre-adoption combined fault replay harness.
- PR #250 integrated publisher freshness, concurrent result canonicalization, and result receipt recovery.
- PR #252 integrated canonical Lab-result consumption, duplicate T2 convergence, and T2 receipt recovery.
- PR #255 composes those integration surfaces with the combined replay harness on one current-main tree.

This advances `combined_fault_replay` from `OPEN_INTEGRATION` to `FROZEN_CANDIDATE`, but does **not** satisfy the exit gate. The final row becomes `ADOPTED_PROVEN` only after the relevant integration is independently reviewed/adopted and the combined replay passes against that adopted lineage.

Handoff invariant:

- Every future Lane B handoff/status report states the Lane B goal, mechanically computed progress, remaining rows, Owner action, and Runtime state.
- `Owner action: none` is not a stop condition while authorized pre-completion Lane B work remains.
- Fixed shared Lab/Auditor Steps remain immutable from this lane.
- RUNTIME remains OFF.
