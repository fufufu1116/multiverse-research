# Review Main Drift Guard v1

Parent: Issue #461
Candidate: PR #462
Runtime: OFF

## Trigger
Build #111 consumed a valid one-shot before review because canonical `main` advanced in the short gap between Fresh authorization and Owner manual Build creation. The dispatcher correctly failed closed with `NO_EXACT_CURRENT_LAB_REQUEST`, but this creates an avoidable error loop when live-main movement is unrelated to the candidate under review.

A procedural issue-comment lease was also proven insufficient for already-running chats: 百人将 continued direct-main research commits after the lease had been routed.

## Candidate primitive
`main_drift_guard_v1.py` is a repository-only, non-integrated safety primitive for a future snapshot-bound review design. It does **not** change current dispatcher/reviewer/publisher behavior.

The guard is deliberately allowlist-based rather than denylist-based. A future integration may classify live-main movement as safe only when all of the following are proven:

- request main, live main and candidate base are valid commit SHAs;
- candidate compare is strictly ahead of its bound base, has the exact merge-base, and is not behind;
- live main is strictly ahead of request main, is not behind, and has the exact request-main merge-base;
- drift is bounded to at most 64 commits and at most 128 compare paths;
- compare evidence is not marked oversized;
- every live-main drift path is under `research/`;
- rename history is included by checking both `filename` and `previous_filename`;
- no live-main drift path overlaps any candidate path, including rename-source paths.

Anything outside `research/` fails closed. This intentionally rejects dispatcher, workflow, Control, bootstrap, root, dependency or unknown-path changes without trying to infer them safe.

## Fresh real-race replay
On 2026-09-14, Issue #461 replayed the actual post-lease race:

- request main: `7893a915d18db8069aa077665ecc069448d0917b`
- observed later main: `1943652ab35c96e29d8e6e583376db6460f16be8`
- drift status: ahead by 4 commits
- merge-base: exactly the request main
- drift files: four files, all under `research/opportunity_engine_v0/solo_income/`
- PR #462 candidate files: four files under `.github/workflows/`, `automation/review_dispatcher_v1/`, and `docs/control/`
- candidate/drift overlap: none

That observed race is the intended `SAFE_UNRELATED_MAIN_DRIFT` class after a future reviewed integration. This replay is evidence only; current production review semantics remain exact-main.

## Important boundary
This primitive does not:

- select a stale review request;
- change the review request or artifact schema;
- bypass current exact-main binding;
- authorize a Build, Retry, Rebuild or rerun;
- authorize merge/adoption or ruleset mutation.

Integration into dispatcher/review/publisher is a separate Candidate and requires Independent Lab/Auditor evidence before adoption. The current review chain remains authoritative until that happens.

No deployment, credentials, provider calls, spend, live effect or Runtime authority is granted.
