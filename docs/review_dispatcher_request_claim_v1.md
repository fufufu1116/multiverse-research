# MULTIVERSE Review Request Claim v1

Status: repository-only Candidate research for Issue #201.

RUNTIME: OFF.

## Problem

The current request-only dispatcher validates exact envelopes and immediate-predecessor SHA256 chaining after review requests exist. Parallel publishers can still post two requests for the same exact envelope before either sees the other. The resulting chain fails closed, but the collision has already happened.

Exact envelope:

`repo + pr + lane + head + tree + base + main`

The required property is stronger: for one exact envelope, only one publication attempt may acquire writer ownership.

## Proposed primitive

Use one deterministic Git ref per exact envelope:

`refs/heads/multiverse-review-claims/v1/<sha256(canonical envelope)>`

GitHub ref creation is the serialization point. Creating a ref name that already exists fails instead of silently replacing the existing ref. Competing writers therefore race on one deterministic provider object and exactly one create operation can win.

The ref must point to a dedicated claim commit, not directly to the Candidate head. The claim commit records:

- exact envelope;
- envelope SHA256;
- deterministic claim ref;
- request_id;
- claimant identifier;
- nonce;
- exact immediate-predecessor request SHA256, or null for the first request.

The eventual request publication must bind the winning claim commit SHA. A future dispatcher integration can fetch the deterministic ref and require that it still points to that exact claim commit before accepting the request. A losing publisher's different claim commit therefore cannot be accepted even if it ignores the create-ref failure and posts a comment anyway.

## Why a ref instead of an issue/comment lease

GitHub issue titles and issue comments do not provide a unique-create constraint for a deterministic key. Two simultaneous publishers can both succeed. A Git ref name is a provider-enforced unique key suitable for compare-and-create style ownership.

## Compatibility strategy

This Candidate deliberately does not change `MULTIVERSE_REVIEW_REQUEST_v1`, the fixed Lab/Auditor Steps, or the current dispatcher acceptance path. It isolates and tests the serialization primitive first.

Recommended next integration after independent review:

1. add a versioned request claim binding to the request contract;
2. add a single Control-owned publication helper that creates the claim commit, atomically creates the deterministic ref, verifies ownership, and only then publishes the request;
3. make dispatcher discovery fail closed unless the exact claim ref points to the request-bound claim commit;
4. preserve current unique request_id and immediate-predecessor SHA256 rules;
5. preserve immutable shared Lab/Auditor Steps;
6. never delete or rewrite a winning claim ref as part of normal publication, so the ownership record remains durable.

## Failure semantics

- claim ref already exists: publication denied; caller must Fresh Read and converge on the winner;
- observed ref points elsewhere: publication denied;
- request_id drift: denied;
- predecessor SHA drift: denied;
- envelope drift: deterministic ref changes, so the old claim cannot authorize the new envelope;
- no claim: future integrated path should deny publication/dispatch.

No retry/build/shared-Steps/merge/main/ruleset/Runtime/provider-production/protected-data/live-effect/spend authority is implied by this Candidate.
