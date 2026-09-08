# T2 resilience integration v1

Repository-only Research Lane B Candidate under Issue #251 / parent #201.

This integration composes the frozen T2 primitives from PR #236 and PR #237 around the adopted T2 implementation without editing fixed shared Lab/Auditor Steps.

Behavior:

- The referenced Lab PASS must be the canonical trusted result for its exact marker: the smallest trusted GitHub comment ID.
- Later same-marker trusted Lab duplicates remain durable but are non-consumable and are filtered only from the legacy T2 comment view.
- The adopted T2 implementation is preserved byte-for-byte as `t2_legacy_v1.py`.
- If an exact canonical trusted T2 already exists, the wrapper validates exact request/repo/PR/head/tree/base/main/auditor/proof/execution/nonauthority binding and reconstructs `t2_publish_receipt.json` instead of posting another T2.
- If no T2 exists, the legacy T2 path publishes normally.
- If another concurrent T2 wins the race, the wrapper Fresh-reads and recovers the canonical earliest trusted T2.
- After a new T2 publication, the wrapper Fresh-reads and requires the published comment itself to be canonical before returning a successful receipt.
- Wrong producer, body, request, upstream, head/tree/base/main, T1, Auditor, proof-ceiling, execution-state, or nonauthority binding fails closed.

Validator architecture:

- Legacy T2 invariants are checked against `t2_legacy_v1.py`.
- Wrapper/idempotence/recovery invariants are checked against `t2.py`, `t2_idempotence_v1.py`, and `t2_receipt_recovery_v1.py`.
- The legacy common validator continues to check the rest of the fixed dispatcher surface.

Proof ceiling: `T2_CANONICAL_UPSTREAM_DUPLICATE_AND_RECEIPT_RECOVERY_INTEGRATION_REPOSITORY_PREPARATION_ONLY`.

RUNTIME: OFF.
