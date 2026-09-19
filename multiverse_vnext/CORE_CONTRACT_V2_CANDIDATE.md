# MULTIVERSE Core Contract v2 — Candidate Design

Status: CANDIDATE_ONLY
Runtime: OFF
Authority expansion: NONE

## Purpose
Make the iPhone Commander and future Mac Core speak one simple, truthful protocol without binding MULTIVERSE to one AI provider.

## Owner-visible flow
Owner command -> Commander -> Core intake -> task queue -> capability router -> provider/tool -> evidence -> verification -> state update.

## Task lifecycle
DRAFT -> QUEUED -> RUNNING -> SUCCESS_CLAIMED -> VERIFIED -> CLOSED

Exception states:
- FAILED
- BLOCKED
- QUARANTINED

No claimed success may become VERIFIED without evidence. No claimed revenue may become realized revenue merely because a provider says a task succeeded.

## Revenue lifecycle
CLAIMED -> VERIFIED -> REALIZED

- CLAIMED: expected or reported value only.
- VERIFIED: evidence checked.
- REALIZED: actually received/settled value.
Game rank/XP is separate from real money state.

## Truthful status
Commander must display these separately:
- UI: available/unavailable
- Core connection: connected/disconnected
- Provider: available/unavailable
- Canonical verification: fresh/stale/unknown
- Safety mode: normal/degraded/safe-mode

The UI must not say Core is online merely because local JavaScript is running.

## Execution boundary
Unknown or ambiguous commands do not cause side effects.
Real-money actions, betting, purchases, credentials, production changes, and other gated actions remain behind the existing Owner Gate and permission model.
Runtime remains OFF under this candidate.

## Provider neutrality
Troop/role != provider.
Tasks declare required capability. A router selects an eligible provider later.
No provider receives authority merely by being selected.

## Evidence record
Every claimed task result should be able to point to:
- task_id
- provider/tool used
- result summary
- evidence reference(s)
- timestamp
- verification status
- verifier role
- uncertainty / failure reason

## iPhone-before-Mac target
Before Mac integration, Commander may support local drafting, task/state viewing, evidence records, simulations, export/import, and offline use.
Local iPhone state is operational/runtime state, never canonical project authority.

## Research engine contract
The future research layer reuses the same evidence rules:
Model Registry -> Feature Registry -> Prediction Record -> Outcome Record -> Evaluation -> Experiment -> Promotion Candidate.

Predictions must be frozen before outcomes are known.
Initial Keirin work is simulation/paper research only. Real wagering is not authorized by this design.

## Required hardening before implementation can be treated as complete
1. Fix module/import layout so Core starts reliably.
2. Make chat intake actually create/route a task or clearly say it did not.
3. Make state endpoint return real state, not a fixed success sentence.
4. Verify request integrity instead of accepting an unchecked checksum field.
5. Replace unconditional execution validation with evidence-based verification.
6. Make task/revenue/audit updates atomic where required.
7. Add idempotency so retries cannot duplicate tasks or revenue.
8. Separate claimed, verified, and realized revenue in storage.
9. Add tamper-evident audit chaining or equivalent integrity protection.
10. Keep independent audit separate from implementation ownership.

## Promotion rule
This file is a design candidate only.
Do not merge/adopt as final authority solely because Core authored it.
Independent review and existing governance remain required.
