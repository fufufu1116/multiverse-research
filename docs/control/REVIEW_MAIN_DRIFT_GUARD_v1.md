# Review Main Drift Guard v1

Parent: Issue #461
Runtime: OFF

## Trigger
Build #111 consumed a valid one-shot before review because canonical `main` advanced in the short gap between Fresh authorization and Owner manual Build creation. The dispatcher correctly failed closed with `NO_EXACT_CURRENT_LAB_REQUEST`, but this creates an avoidable error loop when the main drift is unrelated to the candidate under review.

A procedural issue-comment lease was also observed to be insufficient for already-running chats: 百人将 continued direct-main research commits after the lease had been routed.

## Candidate primitive
`main_drift_guard_v1.py` is a repository-only, non-integrated guard primitive for a future snapshot-bound review design. It does NOT change current dispatcher/reviewer/publisher behavior.

The guard allows a future integration to classify drift as safe only when all of the following are proven:
- request main and live main are valid commit SHAs;
- live main is a direct descendant of request main according to a bounded GitHub compare result;
- compare merge-base equals the request main;
- compare result is not oversized/ambiguous;
- no main-drift file overlaps the candidate changed-file set;
- no main-drift file touches protected review/control prefixes: `automation/review_dispatcher_v1/`, `.github/`, `docs/control/`, `multiverse_vnext/`, or `MULTIVERSE_BOOTSTRAP.md`.

Any overlap, control-path drift, divergent history, malformed compare evidence, or oversized compare fails closed.

## Important boundary
This primitive does not select stale requests, does not alter the review artifact schema, and does not bypass current exact-main binding. Integration into dispatcher/review/publisher requires a separate reviewed candidate and independent Lab/Auditor evidence before adoption.

No Build/Retry/Rebuild, merge/adoption, deployment, credentials, provider calls, spend, live effect, or Runtime authority is granted.
