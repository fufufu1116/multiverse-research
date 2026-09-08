# MULTIVERSE Deterministic Request Arbitration v6

Status: repository-only Research Lane B Candidate for Issue #224 / parent #201.

RUNTIME: OFF.

## Problem

T2.4 serializes publication by chat discipline, but two chats can still publish requests for the same exact envelope before observing each other. The current model then requires every exact request, ordered by GitHub comment ID, to form one strict predecessor chain. Two generation-zero requests therefore poison the envelope even though GitHub has already durably ordered those comments.

The v5 branch-claim approach provides atomic ownership but introduces a provider-side risk: creating a branch can trigger CI. It also adds a second durable object that must be acquired before the request comment.

## v6 canonical arbitration

v6 uses the existing GitHub request comments as the only durable publication objects.

For one exact `repo/pr/lane/head/tree/base/main` envelope:

1. Collect trusted owner-authored machine-readable requests and sort by GitHub comment ID ascending.
2. Partition them by `supersedes_request_sha256`.
3. Generation zero is predecessor `null`.
4. In each reachable generation, the request with the smallest GitHub comment ID is the canonical winner.
5. The next reachable generation is keyed by the canonical SHA256 of that winner.
6. Later requests with the same predecessor are collision losers and are non-consumable, but they do not poison the canonical chain.
7. A request derived from a collision loser or unknown predecessor fails closed.
8. A successor whose comment ID predates its predecessor winner fails closed.
9. Duplicate request IDs still fail closed.
10. The latest canonical winner is the request selected by dispatcher and Auditor upstream validation.

## Stability property

Once a generation has a winner, a later comment cannot obtain a smaller GitHub comment ID. Therefore a later same-generation collision cannot change the winner already selected. This avoids a stabilization timer or lease expiry.

Legitimate same-envelope supersession remains possible: it references the SHA256 of the canonical winner and enters the next generation.

## Compatibility strategy

The adopted dispatcher model is preserved byte-for-byte as `model_legacy_v1.py`. A thin `model.py` compatibility wrapper re-exports the full legacy namespace and overrides only:

- `exact_current_owner_requests`
- `latest_exact_current_owner_request`

with v6 arbitration. Existing dispatcher, review, publisher, Auditor upstream, request/result schemas, and fixed Lab/Auditor Steps remain unchanged.

## Safety boundary

v6 does not silently accept arbitrary broken chains. Only same-predecessor siblings of a reachable canonical generation are tolerated as collision losers. Unknown-predecessor requests, loser-derived successors, duplicate request IDs, and predecessor/comment-order inversions remain fail-closed.

No claim branch/tag is created, so v6 adds no provider branch-trigger surface and requires no Owner courier or extra connector mutation capability.

## Proof ceiling

`DETERMINISTIC_GITHUB_COMMENT_ORDER_REQUEST_ARBITRATION_REPOSITORY_PREPARATION_ONLY`

No machine-readable review request, Owner Gate, T1, Auditor request, Build/Retry, shared-Step mutation, merge/main/ruleset mutation, Runtime/provider/production/protected-data/live-effect/spend authority.

RUNTIME: OFF.
