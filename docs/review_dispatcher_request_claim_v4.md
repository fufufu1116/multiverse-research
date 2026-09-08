# MULTIVERSE Claimed Request Full Binding v4

Status: repository-only Research Lane B Candidate research for Issue #213 / parent #201.

RUNTIME: OFF.

## Problem carried forward from v3

The generation-aware v3 primitive can serialize writers for one exact envelope + immediate-predecessor generation, but its claim does not bind the entire machine-readable review request. A writer could retain the same request_id/envelope/predecessor while changing proof ceiling, recipe, upstream, execution state, or nonauthority fields.

The fixed dispatcher currently discovers owner-authored request comments and computes the canonical request SHA256 only after selection. v4 makes that complete request hash part of the provider-backed serialization proof.

## Design

The existing `MULTIVERSE_REVIEW_REQUEST_v1` JSON schema is intentionally unchanged.

For one request:

1. Validate the existing request exactly as today.
2. Derive the generation from:
   - repo / PR / lane / head / tree / base / main;
   - exact `supersedes_request_sha256` (null for generation zero).
3. Compute the canonical SHA256 of the complete existing request JSON.
4. Build a canonical claim blob containing:
   - exact envelope;
   - generation SHA256;
   - deterministic claim ref;
   - request_id;
   - complete request SHA256;
   - claimant identity and nonce;
   - exact immediate predecessor SHA256.
5. Compute the exact Git blob SHA-1 from those canonical bytes.
6. Create that blob and require the provider-returned SHA to equal the local Git-object digest.
7. Atomically create one deterministic lightweight-tag ref for the generation.
8. Only after claim acquisition may the matching request comment be published.
9. During dispatcher discovery, Fresh fetch the deterministic ref and exact blob and reject the request unless all bindings match.

Claim ref:

`refs/tags/multiverse-review-claims/v4/<generation-sha256>`

## Security properties

- Same generation has one provider-backed ref name and therefore one create winner.
- A changed request body changes `request_sha256` and claim blob SHA even if request_id and envelope are unchanged.
- A losing publisher cannot make its different request acceptable by posting a comment after losing the ref race.
- Ref retargeting, wrong object type, wrong blob bytes, request drift, predecessor drift, or envelope drift fail closed at dispatcher discovery.
- Legitimate supersession remains possible because a new immediate predecessor produces a new generation ref.
- Shared Independent Lab/Auditor Steps remain immutable.

## Crash boundary

This Candidate deliberately does not claim to solve every publication-liveness failure. If a writer acquires a claim and crashes before posting the request comment, that generation remains claimed. The safe recovery is fail closed; the current T2.4 rule already permits retiring a poisoned exact envelope and moving to a new exact head/main envelope. A future lease/receipt design may improve liveness, but must not weaken the single-winner safety property.

## Integration boundary

v4 changes dispatcher acceptance behavior, so it is a successor integration Candidate rather than a primitive-only Candidate. It does not edit shared Buildkite Steps. If adopted later, the fixed dispatcher code fetched from canonical main would enforce the new claim requirement without per-Candidate shared-Step edits.

Publication-side provider calls are not executed by this Research Candidate. The module exposes pure construction/acquisition primitives and tests with fake provider objects only.

## Proof ceiling

`FULL_REQUEST_SHA_CLAIM_BOUND_DISPATCHER_ACCEPTANCE_REPOSITORY_PREPARATION_ONLY`

No machine-readable review request, Owner Gate, T1, Auditor request, Build/Retry, merge/main/ruleset mutation, shared-Step mutation, Runtime/provider/production/protected-data/live-effect/spend authority.

RUNTIME: OFF.
