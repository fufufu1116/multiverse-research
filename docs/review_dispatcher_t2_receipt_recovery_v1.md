# MULTIVERSE T2 Receipt Recovery v1

Status: repository-only Research Lane B Candidate for Issue #235 / parent #201.

RUNTIME: OFF.

## Failure mode

T2 can be successfully published to GitHub and then the process can crash before `t2_publish_receipt.json` is persisted. A retry should not need to publish a second T2 merely to recover progress.

## Recovery rule

Recovery is allowed only from a caller-supplied canonical trusted Auditor T2 comment. The helper verifies:
- trusted Auditor producer identity;
- exact T2 marker for request_id/head/auditor-pass-comment/request-SHA;
- embedded T2 artifact exactly equals the expected current T2 artifact;
- request SHA, head, tree, main, and auditor-pass binding match the current job;
- gate is T2, verdict is PASS, and Auditor login/app identity are exact.

If all checks pass, reconstruct the T2 publish receipt with the durable canonical T2 comment ID and `recovered: true`.

## Composition

Issue #235 / PR #236 defines canonical downstream/T2 comment selection. A later integration Candidate should first select the canonical T2 comment, then call `recover_t2_receipt(...)`. Noncanonical duplicates must never be recoverable.

## Safety / liveness

- valid T2 survives process crash before receipt persistence;
- retry does not create a second T2 merely for recovery;
- wrong producer, marker, artifact, request, Auditor binding, or verdict fail closed.

Proof ceiling:
`CANONICAL_T2_RECEIPT_RECOVERY_PRIMITIVE_REPOSITORY_PREPARATION_ONLY`

No machine-readable review request, Owner Gate, T1, Auditor request, Build/Retry, shared Steps mutation, merge/main/ruleset mutation, Runtime/provider/production/protected-data/live-effect/spend authority.

RUNTIME: OFF.
