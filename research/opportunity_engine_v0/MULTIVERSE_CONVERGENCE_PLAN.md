# MULTIVERSE CONVERGENCE PLAN

Status: RESEARCH-ONLY / RUNTIME OFF

## Goal
Converge Opportunity Engine into canonical MULTIVERSE with the least rework and smallest review surface. Do not merge PR #310 wholesale.

## Fresh-state rule
Every convergence decision starts with a Fresh GitHub read of canonical main and the currently active control-plane/provider Candidates. Historical SHA, handoff text, and this file are orientation only.

## Convergence trigger
Prepare adoption slices now, but do not request canonical adoption until the currently active MULTIVERSE control-plane and first-live-provider preparation have either:
1. been canonically integrated, or
2. been superseded by an exact fresh-main successor whose interfaces are stable enough to bind against.

At the 2026-09-11 research checkpoint, active examples include the one-shot preflight/read-resilience line and first-live-provider preauthorization line. Their exact PR numbers are not permanent authority; Fresh discovery wins.

## Integration shape
MULTIVERSE remains the authority/control/review/runtime substrate.
Opportunity Engine remains a domain decision module.
The Hundred User service remains a bounded customer-facing experiment layered above both.

No second governance system may be introduced.

## Smallest adoption slices
Adopt in dependency order, not as one 100+ file batch:

### Slice A — Core domain model
Pure deterministic Opportunity Engine scoring/model primitives with no live/network/provider effects.
Exit: repository tests + validator + exact frozen tree.

### Slice B — Forecast integrity
Forecast ledger, revision, trend forecast/retrospective primitives, temporal-integrity and anti-hindsight rules.
Exit: frozen commitment semantics preserved and no later-outcome leakage.

### Slice C — Customer-value / Hundred User evaluation
Customer value, contribution, hundred-user stage, growth-loop assessment.
Exit: vanity metrics cannot promote; unsafe/manipulative loops fail closed; no live authority.

### Slice D — MULTIVERSE bridge
Task/result bridge and independence/advisor integration only after binding to the then-current canonical MULTIVERSE task/review contracts.
Exit: exact current-main compatibility; no duplicate voting/governance logic.

### Slice E — Completion spine
One orchestration path reusing prior slice outputs. It must not recalculate or fork authoritative decisions already made upstream.
Exit: candidate discovery -> frozen forecast -> customer value -> hundred-user evidence -> governed gate can be represented without duplicate state.

## Rework minimization rules
- Never copy canonical MULTIVERSE control-plane code into Opportunity Engine.
- Prefer thin adapters over rewrites.
- Preserve previously frozen evidence; rebind only what current main requires.
- A failure in a downstream stage must not force unrelated upstream research to be rerun.
- Do not create a fresh scoring model when an existing module already owns that decision.
- Do not couple adoption to a specific provider/model unless the canonical interface requires it.
- Treat PR #310 as source evidence, not as the intended merge unit.

## Owner gate
Repository-only preparation may continue autonomously.
Canonical adoption/merge, formal Lab/Auditor execution, live provider use, credentials, spend, publication, customer recruitment, payment collection, live business effect, or Runtime activation remain separately governed Owner actions.

## Hundred User launch condition
Do not launch the first-100-user experiment from the research branch. Launch only from an adopted/fresh-main compatible path where:
- the chosen wedge and success/failure thresholds are frozen before recruitment;
- evidence capture is durable;
- no covert tracking/dark patterns are required;
- kill/redesign rules are explicit;
- the MULTIVERSE review/control substrate is the authority boundary.

## Completion definition
Opportunity Engine research reaches 100% when:
1. no material duplicate decision path remains;
2. the adoption slices and dependencies are frozen;
3. each slice has repository proof appropriate to its scope;
4. the current-main bridge compatibility gap is explicitly bounded;
5. remaining steps are canonical governance/live-market actions rather than more speculative architecture.
