# MULTIVERSE Concurrent Result Publication Canonicalization v1

Status: repository-only Research Lane B Candidate for Issue #231 / parent #201.

RUNTIME: OFF.

## Problem

The fixed publisher checks for an existing trusted result before posting. Two builds for the same exact request can still race: both can observe no result and then both publish PASS.

## Canonicalization rule

For one exact result marker and lane, collect all trusted result comments and choose the smallest GitHub comment ID. That comment is the only canonical result.

A later same-request duplicate may remain as durable history, but it is non-consumable. A publisher that posts a later duplicate must fail before emitting a successful publish receipt.

Untrusted comments never participate in the election. LAB and AUDITOR canonicalization are independent because trusted producer identity is lane-specific.

## Safety properties

- one deterministic canonical result for any finite set of duplicate trusted results;
- result does not depend on API return order;
- attacker/untrusted comments cannot preempt the canonical result;
- later duplicate result fails closed;
- missing trusted result fails closed.

## Integration boundary

This Candidate proves the deterministic result-selection primitive and focused regressions only. A follow-up integration Candidate should call `assert_published_result_is_canonical(...)` after the publisher POST and Fresh refetch of issue comments, before writing a successful publish receipt. Shared Lab/Auditor Steps must remain unchanged.

Proof ceiling:
`DETERMINISTIC_CONCURRENT_RESULT_CANONICALIZATION_PRIMITIVE_REPOSITORY_PREPARATION_ONLY`

No machine-readable review request, Owner Gate, T1, Auditor request, Build/Retry, shared Steps mutation, merge/main/ruleset mutation, Runtime/provider/production/protected-data/live-effect/spend authority.

RUNTIME: OFF.
