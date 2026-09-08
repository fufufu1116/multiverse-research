# MULTIVERSE Review Request Claim v2

Status: repository-only Research Lane B Candidate for Issue #201.

RUNTIME: OFF.

## Why v2 supersedes v1 research

The first isolated primitive (PR #208) proved that one deterministic provider ref can serialize exact-envelope publication. Follow-up research found two hardening gaps:

1. `refs/heads/...` behaves as a branch namespace and may interact with normal branch/CI policy;
2. an arbitrary claim commit SHA is not enough unless the referenced Git object is cryptographically bound to the exact claim payload.

v2 keeps the single-winner idea but removes both gaps.

## Exact envelope

`repo + pr + lane + head + tree + base + main`

## v2 primitive

1. Canonicalize the claim JSON.
2. Compute its exact Git blob SHA-1 using Git object framing: `sha1("blob <len>\\0" + payload)`.
3. Ask GitHub to create that exact blob and require the returned SHA to equal the locally derived SHA.
4. Atomically create one deterministic lightweight tag ref:

`refs/tags/multiverse-review-claims/v2/<sha256(canonical envelope)>`

5. Point that ref directly at the claim blob.
6. Only the writer whose create-ref succeeds may publish the matching review request.
7. Future dispatcher integration fetches the deterministic ref and requires it to point to the exact request-bound claim blob SHA.

The ref name is unique for the exact envelope. Competing publishers therefore race on one provider object; one wins and later creates fail instead of replacing it.

## Claim payload binding

The claim blob binds:
- exact envelope;
- envelope SHA256;
- deterministic tag ref;
- request_id;
- claimant identity;
- nonce;
- exact immediate-predecessor request SHA256 or null.

Because the tag points directly to the Git blob whose SHA is derived from those bytes, changing any bound field changes the blob SHA and invalidates the binding.

## Failure semantics

- provider returns a blob SHA different from the locally derived SHA: deny before ref creation;
- deterministic claim ref already exists: losing publisher denies publication and Fresh Reads the winner;
- observed ref points to any other blob: dispatcher denies;
- request_id or predecessor SHA drifts: dispatcher denies;
- envelope drifts: deterministic ref changes;
- claim absent: future integrated publication/dispatch path denies.

## Compatibility

This Candidate remains primitive-only. It does not change `MULTIVERSE_REVIEW_REQUEST_v1`, `dispatcher.py`, fixed Lab/Auditor Steps, Buildkite configuration, or current review execution behavior.

Recommended later integration, only after independent review/adoption of the primitive:
1. add versioned claim fields to the request contract;
2. add a sole-Control publication helper that creates blob -> atomic tag ref -> verifies ownership -> publishes request;
3. add dispatcher-side ref/blob verification;
4. preserve unique request_id and immediate-predecessor SHA256 chaining;
5. keep shared Lab/Auditor Steps immutable.

No Owner Gate, T1, Auditor request, same-envelope machine review request, Build/Retry, merge/main/ruleset mutation, Runtime/provider/production/protected-data/live-effect/spend authority is implied.
