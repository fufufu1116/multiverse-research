# Research Lane B Completion / Exit Gate v2 — Final Convergence Candidate

Lane B major goal: make the fixed review control plane safe for multiple chats without collision, stale-result adoption, retry deadlock, or routine Owner traffic control.

The completion matrix remains stricter than “Candidate exists”. A critical row is complete only when it is `ADOPTED_PROVEN`. A frozen Candidate receives partial progress credit but never makes the major goal complete.

Current mechanically computed state:

- critical rows: 11
- `ADOPTED_PROVEN`: 4
- `FROZEN_CANDIDATE`: 7
- `OPEN_INTEGRATION`: 0
- progress: 77.73%
- major goal complete: false

Current final convergence lineage:

- request arbitration v6: PR #225, composed into PR #258;
- publisher resilience: PR #250, composed into PR #258;
- T2 resilience: PR #252, composed into PR #258;
- completion matrix / exit gate: PR #257, composed into PR #258;
- pre-adoption combined fault replay: PR #242, now accompanied in PR #258 by tests that import and execute actual `model`, `publisher`, and `t2` module APIs.

PR #258 is the current final pre-adoption convergence Candidate. PR #255 is superseded and must not be progressed.

This does **not** satisfy the exit gate. The seven frozen rows become complete only after the integrated lineage is independently reviewed/adopted and the combined fault replay passes against that adopted lineage.

Handoff invariant:

- Every future Lane B handoff/status report states the Lane B goal, mechanically computed progress, remaining rows, Owner action, and Runtime state.
- `Owner action: none` is not a stop condition while authorized pre-completion Lane B work remains.
- Fixed shared Lab/Auditor Steps remain immutable from this lane.
- RUNTIME remains OFF.
