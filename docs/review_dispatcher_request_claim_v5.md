# MULTIVERSE Connector-Executable Request Claim v5

Status: repository-only Research Lane B Candidate research for Issue #213 / parent #201.

RUNTIME: OFF.

## Why v5 supersedes the tag-ref v4 design

The tag-ref design had the desired single-winner semantics but was not executable through the current sole-Control GitHub connector without adding a new arbitrary-tag mutation path or Owner/provider courier step. That violates the #201 goal of mechanical serialization without Owner courier work.

v5 uses only GitHub operations already available to sole Control: create commit and create branch.

## Generation key

One serialization generation is:

`repo + pr + lane + head + tree + base + main + immediate predecessor request SHA256`

The null predecessor is generation zero. A legitimate later supersession binds the newly current predecessor and therefore obtains a different generation key.

## Claim object

The canonical claim binds:
- exact review envelope;
- generation SHA256;
- deterministic claim branch ref;
- request_id;
- canonical SHA256 of the complete existing `MULTIVERSE_REVIEW_REQUEST_v1` JSON;
- claimant identity;
- nonce;
- exact immediate predecessor SHA256.

The existing request JSON schema is unchanged.

## Provider serialization primitive

1. Build canonical claim JSON.
2. Encode it as the exact commit message after marker `MULTIVERSE_REVIEW_REQUEST_CLAIM_V5`.
3. Create an empty Git commit whose parent is the request's exact canonical main and whose tree is identical to that parent.
4. Atomically create the deterministic branch:

`refs/heads/multiverse-review-claims/v5/<generation-sha256>`

5. Only the writer whose branch creation succeeds may publish the matching request comment.
6. A competing writer in the same generation creates a different claim commit but loses when attempting to create the already-existing deterministic branch.

## Dispatcher verification

In the real fixed-dispatcher runtime, `MULTIVERSE_DISPATCHER_REF` is mandatory. When present, request discovery must Fresh verify:
- deterministic claim branch exists;
- ref object type is commit;
- claim commit has exactly one parent equal to request `main`;
- claim commit tree equals the parent main tree, proving the claim commit is content-empty;
- commit message marker and canonical claim JSON are valid;
- claim ref, generation, envelope, request_id, complete request SHA256, and predecessor all match the selected request.

The library-level `discover_request()` helper retains an offline unit-test seam when `MULTIVERSE_DISPATCHER_REF` is absent, but the CLI `main()` fails closed if that dispatcher ref is absent. The fixed shared Buildkite dispatcher already exports this ref before invoking dispatcher.py.

## Failure properties

- request body drift changes request SHA and fails verification;
- same-generation parallel writers have one branch winner;
- changed predecessor creates a new legitimate generation;
- wrong parent main fails;
- non-empty claim commit fails;
- ref retargeting to a different commit is revalidated from the new commit and cannot silently preserve a mismatched claim;
- claim/comment publication crash remains fail-closed. Current T2.4 exact-envelope retirement remains the safe fallback; lease expiry/recovery is not claimed here.

## Shared infrastructure

No fixed Independent Lab/Auditor Steps are edited. If this dispatcher code is later adopted into canonical main, fixed shared pipelines continue fetching dispatcher code from canonical main as today.

## Proof ceiling

`CONNECTOR_EXECUTABLE_FULL_REQUEST_CLAIMED_DISPATCHER_ACCEPTANCE_REPOSITORY_PREPARATION_ONLY`

No machine-readable review request, Owner Gate, T1, Auditor request, Build/Retry, shared-Step mutation, merge/main/ruleset mutation, Runtime/provider/production/protected-data/live-effect/spend authority.

RUNTIME: OFF.
