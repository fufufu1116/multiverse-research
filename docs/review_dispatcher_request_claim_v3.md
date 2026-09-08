# MULTIVERSE Review Request Claim v3

Status: repository-only Research Lane B Candidate for Issue #201.

RUNTIME: OFF.

## Why v3 supersedes v2 research

PR #209 v2 improved the primitive by moving claims out of the branch namespace and binding claim bytes directly to a Git blob. Follow-up review found one remaining protocol flaw: one permanent ref per exact envelope would allow only one request for that envelope forever, which conflicts with the existing valid same-envelope supersession chain.

The current dispatcher permits a later request for the same exact envelope only when its `supersedes_request_sha256` equals the exact immediate predecessor. Therefore serialization must be per request-generation, not merely per envelope.

## Exact envelope

`repo + pr + lane + head + tree + base + main`

## Request generation

A generation is:

`exact envelope + immediate predecessor request SHA256`

The predecessor is `null` for the first request on an exact envelope.

Generation key:

`sha256(canonical({ envelope, predecessor_sha256 }))`

Deterministic claim ref:

`refs/tags/multiverse-review-claims/v3/<generation-sha256>`

Competing publishers that both observed the same predecessor race on the same generation ref, so only one can win. After a valid request exists, its SHA256 becomes the predecessor for the next generation, producing a different ref and preserving legitimate supersession.

## Blob-bound single-winner protocol

1. Fresh Read the exact envelope and current immediate predecessor request SHA256.
2. Build the canonical claim payload binding envelope, generation SHA256, request_id, claimant, nonce and predecessor SHA256.
3. Compute the exact Git blob SHA-1 locally using `sha1("blob <len>\\0" + payload)`.
4. Create the blob through the provider and require the returned SHA to equal the locally derived SHA.
5. Atomically create the deterministic generation tag ref pointing directly to that blob.
6. Only the create-ref winner may publish the matching request.
7. A losing publisher must not append a request; it Fresh Reads and converges on the winner.
8. Future dispatcher integration verifies that the generation ref still points to the exact request-bound blob and that the request's predecessor equals the generation predecessor.

GitHub documents lightweight tags as tag references that can be created without an annotated tag object, and Git allows lightweight tags to name Git objects directly. The fixed Candidate does not perform provider mutation itself; this document describes the future Control-owned publication helper contract.

## Why predecessor belongs in the ref key

Using only the exact envelope as the ref key over-serializes: the first durable ref permanently blocks every later legitimate same-envelope supersession.

Including `predecessor_sha256` gives the required behavior:
- same envelope + same predecessor: one winner;
- same envelope + new predecessor: next legitimate generation;
- stale publisher using old predecessor: collides with the already-won old generation and cannot publish;
- head/tree/base/main drift: changes the envelope and therefore the generation key.

## Failure semantics

- provider blob SHA mismatch: deny before ref creation;
- generation ref already exists: deny publication and Fresh Read;
- observed ref points to another blob: deny;
- request_id drift: deny;
- predecessor drift: deny;
- malformed envelope/predecessor: deny;
- no generation claim in a future integrated path: deny.

## Compatibility boundary

This Candidate deliberately does not modify:
- `MULTIVERSE_REVIEW_REQUEST_v1`;
- `dispatcher.py` acceptance behavior;
- current request publication;
- fixed Independent Lab/Auditor Steps;
- Buildkite configuration.

Recommended later integration, only after independent review and separate authority:
1. version the request contract with claim binding fields;
2. add a sole-Control publication helper that acquires a generation claim before posting;
3. make dispatcher discovery validate the exact generation ref/blob binding;
4. preserve unique `request_id` and immediate-predecessor SHA256 chain checks;
5. preserve immutable shared Steps and all existing nonauthority boundaries.

No Owner Gate, T1, Auditor request, Build/Retry, shared-Steps mutation, merge/main/ruleset mutation, Runtime/provider/production/protected-data/live-effect/spend authority is implied by this Candidate.
