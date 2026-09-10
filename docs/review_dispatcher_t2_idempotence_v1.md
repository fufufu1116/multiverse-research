# MULTIVERSE T2 Canonical Result Consumption / Idempotence v1

Status: repository-only Research Lane B Candidate for Issue #235 / parent #201.

RUNTIME: OFF.

## Problem

Current T2 requires the trusted Lab result set to be exactly one comment. That fails when two concurrent builds publish the same trusted PASS, even if one deterministic canonical result is available. T2 publication itself can also race and produce duplicate trusted T2 comments.

## Canonical rules

For a given exact marker and lane, the smallest trusted GitHub comment ID is canonical.

- Downstream Lab/Auditor consumption must validate that the referenced result comment ID equals the canonical ID; later trusted duplicates are ignored as non-consumable history.
- T2 publication must similarly accept only the smallest trusted exact T2 comment ID as canonical.
- Untrusted comments never participate.
- LAB and AUDITOR producer namespaces remain independent.

## Focused properties

- late duplicate Lab result does not block progress when the canonical earliest result is referenced;
- a later duplicate cannot be referenced as upstream proof;
- concurrent T2 duplicates converge to one canonical trusted comment;
- attacker comments cannot preempt canonical ownership;
- missing canonical evidence fails closed.

## Integration boundary

This Candidate proves the downstream/T2 canonical-selection rules only. T2 receipt recovery after a post-publication crash remains part of Issue #235 follow-up integration. Fixed shared Lab/Auditor Steps are unchanged.

Proof ceiling:
`CANONICAL_DOWNSTREAM_RESULT_AND_T2_SELECTION_PRIMITIVE_REPOSITORY_PREPARATION_ONLY`

No machine-readable review request, Owner Gate, T1, Auditor request, Build/Retry, shared Steps mutation, merge/main/ruleset mutation, Runtime/provider/production/protected-data/live-effect/spend authority.

RUNTIME: OFF.
