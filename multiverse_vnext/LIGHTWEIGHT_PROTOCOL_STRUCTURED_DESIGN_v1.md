# MULTIVERSE Lightweight Protocol — Structured Design v1

Status: `CANDIDATE_ONLY`  
Authority: canonical GitHub `main` + existing control substrate  
Runtime: `OFF`  
Parent control: Issue #394  
Design baseline: canonical main `4af04dfbbb590daa755be2c9f0dccb9168bf7a9b`

## Purpose

Provide a provider-agnostic, compact, portable continuation protocol so a replacement AI can recover the minimum required project context from canonical records without relying on chat history or a giant emergency handoff.

This document is repository-only design. It does not create Runtime, provider, credential, spend, production, Buildkite, betting, or canonical-adoption authority.

## A. Compact Bootstrap

A new lane/chat starts from a small bootstrap containing only:

1. formal role/unit name;
2. canonical repository and branch;
3. current-state pointer;
4. active control/governance pointer;
5. lane-specific pointer when applicable;
6. current objective;
7. next executable owner-free step;
8. stop conditions / Owner Gate boundary.

The bootstrap is a pointer set, not a duplicate project-state database. It must be followed by a Fresh Read of canonical GitHub state.

## B. Modular Task Packet

Work is represented as a small task packet rather than a narrative handoff.

Minimum fields:

```yaml
id: stable task identifier
role: formal unit identifier
objective: exact task objective
scope: allowed work
out_of_scope: prohibited work
canonical_refs: exact GitHub pointers
inputs: required evidence/artifacts
next_step: next executable owner-free action
stop_conditions: Owner Gate / credential / spend / irreversible / audit / safety blockers
output_contract: required result and evidence pointers
```

Task packets are disposable execution context; canonical records remain authoritative.

## C. Canonical Pointer Set

Pointers are resolved in this order:

1. canonical current state / repository state;
2. authoritative primary governance or lane record;
3. independent corroboration where required;
4. discovery/community material only for orientation.

A pointer does not itself establish current truth. Every PRIMARY pointer must be Fresh-verified at resume time. Missing, duplicate, ambiguous, or stale authority is `FAIL_CLOSED`.

## D. Context Compression Rules

Compress by preserving decision-relevant state, not by preserving the whole transcript.

Preserve:
- current objective and scope;
- exact canonical refs;
- fixed rules and Owner corrections;
- material failures/lessons and supersessions;
- next executable step;
- consumed one-shot status where relevant;
- evidence/artifact locations.

Discard from routine bootstrap:
- repeated narration;
- already-receipted intermediate chatter;
- duplicated source text;
- stale SHA/PR/current-state claims;
- context that is not required for the next safe decision.

Compression must never remove a safety boundary, authority binding, evidence qualifier, or unresolved blocker.

## E. Checkpoint / Resume

Before consequential or gate-adjacent actions, create or update a compact durable checkpoint when the existing control protocol requires one.

Use explicit receipt states:

`RECEIPTED | NOT_RECEIPTED | UNCERTAIN`

After interruption:
- Fresh-read canonical state;
- locate the latest durable receipt/checkpoint;
- do not replay a one-shot action when its receipt is already confirmed;
- if side-effect state is uncertain, fail closed rather than guessing;
- resume from the first genuinely uncommitted safe step.

Narration is not a receipt.

## F. Provider Fallback

ChatGPT, Gemini, Claude, Codex, agents, and other providers are interchangeable execution/advisor adapters.

Provider replacement procedure:

1. load Compact Bootstrap;
2. Fresh Read canonical GitHub state;
3. verify control/lane boundaries;
4. load only task-relevant artifacts;
5. execute the next safe step;
6. externalize durable results/evidence before context exhaustion.

Provider-specific memory is never project authority. Provider fallback does not imply identical capability, quota, cost, or reliability. `ZERO_WHEN_POSSIBLE` / `FREE_TIER_WHEN_AVAILABLE` is a cost target, not a guarantee.

## G. Owner-Burden Reduction

Owner is not a routine courier between lanes.

The active control unit should retrieve GitHub status, issues, PRs, artifacts, and other connector-available evidence itself. Owner intervention is reserved for genuine authority decisions or unavoidable manual actions.

When Owner action is required, report exactly:

1. 操作場所
2. 開くリンク
3. 記入するもの（なければ「なし」）
4. 何を押すか
5. 完了後ここへ何と返すか

Routine progress reports are not a stop condition.

## H. Fail-Closed / Safety Boundary

Ambiguity, stale authority, missing evidence, conflicting state, unavailable required information, or unsafe scope expansion causes `FAIL_CLOSED`.

This protocol does not widen any existing authority.

Keirin protected boundary remains unchanged. In particular, this design does not authorize access to or use of:

- RESULT / PAYOUT / outcome;
- odds / price / economics;
- `ECON_HOLDOUT1000`;
- DEV2000 C outcome access;
- real-data fitting or pretraining;
- model promotion;
- real-money wagering;
- external provider contact;
- new automated bulk collection;
- Runtime activation.

Runtime remains `OFF`.

## I. Role / Audit Separation

Owner is final authority and Owner Gate holder, not the independent auditor of the same work.

Gemini/ChatGPT/Claude/etc. may execute or research, but use of a provider does not establish independence.

Independent Lab/Auditor status must be established by the existing governance path when required. This design cannot self-assign an independent auditor and cannot bypass required review.

## J. Artifact / Evidence Pointer

Detailed evidence belongs in durable repository artifacts or the relevant canonical issue/PR, rather than repeated into chat.

Every material output should identify:

- artifact path or canonical issue/PR;
- exact commit/SHA when relevant;
- provenance/source class;
- validation status;
- adoption status;
- superseded/predecessor relation when relevant.

Candidate artifacts must remain explicitly distinguishable from adopted canonical behavior.

## Validation Plan

1. **Provider-switch recovery test:** a replacement AI uses only the compact bootstrap plus Fresh GitHub reads and reconstructs role, objective, scope, current state, next step, and stop conditions.
2. **Compression integrity test:** removal of duplicated narrative does not remove authority, evidence, safety, or unresolved-blocker information.
3. **Interruption test:** receipt/checkpoint state prevents replay of consumed one-shot actions and resumes from the first uncommitted safe step.
4. **Owner-burden test:** connector-available evidence is retrieved by the active unit rather than delegated to Owner.
5. **Negative boundary test:** prohibited Keirin fields/actions and Runtime/provider/spend/credential escalation fail closed.
6. **Adoption separation test:** this candidate cannot be represented as adopted without the existing Owner Gate and required governance evidence.

## Definition of Done

- A replacement chat can resume from a compact packet plus Fresh GitHub read.
- No giant emergency handoff is required as the normal continuity mechanism.
- Durable Owner corrections are externalized to canonical control records.
- Artifact pointers replace repeated result narration.
- Interruption recovery does not depend on chat transport continuity.
- Provider switching does not change authority boundaries.
- Owner remains final authority and is not a routine courier.
- Required independent review remains separate.
- Runtime remains OFF.

## Adoption Boundary

This design is a repository-only Candidate. `CANDIDATE_ONLY / NOT_ADOPTED / NOT_PERFORMED` until the normal review and Owner Gate process establishes otherwise.
