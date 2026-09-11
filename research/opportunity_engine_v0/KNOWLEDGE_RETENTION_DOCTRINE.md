# Knowledge Retention Doctrine

Status: research-only / non-authoritative. Runtime remains OFF.

## Goal

Opportunity Engine must not depend on conversational recall for durable project knowledge. Useful information can originate in casual chats, research notes, external evidence, forecasts, experiments, review results or Owner constraints, but anything important enough to influence later decisions should be converted into a durable, provenance-bound project artifact.

## Core rule

Conversation is an intake surface, not the system of record.

The repository should preserve only the useful decision-bearing fragment, with enough context to reconstruct why it matters, while avoiding unnecessary personal or sensitive detail.

## Required classes

Retained information should be classified into one of these buckets:

1. `OWNER_CONSTRAINT`
   - durable operating constraints that change what opportunities are suitable;
   - store the operational implication, not unnecessary personal history.

2. `BUSINESS_PATTERN`
   - reusable monetization, distribution, product, workflow or market structure.

3. `HYPOTHESIS`
   - plausible but unverified claim requiring research.

4. `EVIDENCE`
   - externally checkable, source-bound fact or measured result.

5. `DECISION_RULE`
   - a stable screening, ranking, fail-closed or escalation rule.

6. `FORECAST`
   - a frozen prediction version that must not be rewritten after outcomes become known.

7. `SETTLED_OUTCOME`
   - externally checkable result used for calibration, advisor scoring and retrospective learning.

8. `SUPERSEDED`
   - historical information retained for traceability but no longer current.

## Minimum metadata

Every durable item should carry, where applicable:

- stable `item_id`;
- class/type;
- concise statement;
- source kind and source reference;
- observed/created time;
- verification state;
- current/superseded state;
- links to related case, forecast, decision, test or doctrine;
- sensitivity classification;
- whether the item can influence ranking, blocking or execution readiness.

## Anti-burial rules

1. Important material must not live only inside a long conversation transcript.
2. Repeated mentions of the same idea do not increase evidence weight unless they are independent evidence.
3. Duplicate or near-duplicate intake should point to an existing item instead of creating artificial confidence.
4. New facts that conflict with old facts should create a new version or supersession relation; do not silently overwrite history.
5. Frozen forecasts remain immutable after outcomes are known.
6. Owner constraints should be summarized at the minimum necessary level and must not be propagated into external review packets unless required and authorized.
7. Sensitive personal material must not be copied into reusable research corpora merely because it appeared in conversation.
8. Handoff/recovery should begin from Fresh GitHub state plus the durable knowledge index, not remembered chat state.

## Retrieval shape

The engine should be able to answer four recovery questions without reading the whole chat history:

- What is currently believed?
- What is only a hypothesis?
- What evidence supports or contradicts it?
- What changed, and what did it supersede?

## Authority boundary

Knowledge retention is not authority. Storing a hypothesis, constraint, pattern or evidence item does not authorize provider calls, spend, publication, personal-data processing, live execution, adoption, merge or Runtime activation.
