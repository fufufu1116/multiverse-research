# MULTIVERSE Existing-Result Receipt Recovery v1

Status: repository-only Research Lane B Candidate for Issue #233 / parent #201.

RUNTIME: OFF.

## Failure mode

A fixed publisher can successfully POST the exact trusted PASS result comment and then crash before `review_publish_receipt.json` is written or uploaded. A later retry currently sees that the result already exists and fails, even though the durable GitHub result is valid.

## Recovery rule

Recovery is allowed only from a caller-supplied canonical result comment. The helper Fresh-validates that:
- the comment producer is trusted for the exact lane;
- the exact result marker matches request_id/head/request-comment/request-SHA;
- the embedded published artifact equals the current artifact byte-for-JSON-object;
- request_id, request comment, request SHA, head, tree, and main all match the current job;
- verdict is PASS and findings are empty.

If all checks pass, reconstruct the same publish receipt fields using the durable GitHub comment ID and lane producer identity, with `recovered: true`.

## Composition with result canonicalization

This helper intentionally does not choose among duplicate results. Issue #231 / PR #232 defines that selection primitive. A later integration Candidate should first select the canonical exact result, then pass only that comment into `recover_publish_receipt(...)`. A noncanonical duplicate must never be recoverable.

## Safety / liveness

- valid published result survives process crash before receipt persistence;
- retry does not publish a second PASS merely to recover progress;
- wrong producer, wrong marker, artifact drift, binding drift, or non-PASS result fail closed;
- no provider mutation is required for recovery beyond reading the durable comment.

Proof ceiling:
`EXISTING_CANONICAL_RESULT_RECEIPT_RECOVERY_PRIMITIVE_REPOSITORY_PREPARATION_ONLY`

No machine-readable review request, Owner Gate, T1, Auditor request, Build/Retry, shared Steps mutation, merge/main/ruleset mutation, Runtime/provider/production/protected-data/live-effect/spend authority.

RUNTIME: OFF.
