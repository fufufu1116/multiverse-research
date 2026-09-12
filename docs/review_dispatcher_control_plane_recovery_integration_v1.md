# Canonical result/recovery primitive integration contract v1

This repository-only Candidate composes the exact frozen implementation primitives from PRs #232, #234, #236, and #237 without reimplementing their algorithms.

## Flow under test

1. `canonical_result_comment_id` chooses the smallest trusted result comment ID for one exact result marker and lane.
2. `recover_publish_receipt` reconstructs the review publish receipt only from that exact trusted result comment and exact job/artifact binding.
3. `assert_referenced_result_is_canonical` proves downstream references the same canonical result rather than a later duplicate.
4. `canonical_trusted_comment_id` / `assert_published_t2_is_canonical` choose the smallest trusted exact T2 comment and reject later duplicates.
5. `recover_t2_receipt` reconstructs the T2 receipt only from the exact canonical trusted T2 comment and exact request/head/tree/main/Auditor binding.

## Negative boundaries

The integration tests reject noncanonical duplicate result references, artifact drift, noncanonical duplicate T2 publication, and untrusted comments. Individual frozen primitive suites retain their deeper per-module negative coverage for producer/app identity, marker mismatch, request/head/tree/main drift, clean-PASS requirements, and missing trusted evidence.

## Proof ceiling

This proves Python-level interface compatibility of the four frozen primitives on one candidate tree. It does not wire them into the adopted publisher/T2 execution path, mutate fixed Lab/Auditor Steps, run or retry a Build, satisfy the post-adoption combined-fault replay exit row, or grant merge/main/ruleset/Runtime/provider/production/protected-data/live-effect/spend authority.

RUNTIME: OFF.
