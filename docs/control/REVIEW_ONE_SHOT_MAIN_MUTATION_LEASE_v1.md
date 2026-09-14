# Review One-Shot Main-Mutation Lease v1

Control: #394
Runtime: OFF

## Problem
A manual external Lab/Auditor Build can start seconds after Sole Control Fresh-validates an exact request. If another lane mutates canonical `main` in that gap, the dispatcher discovers the newer live main and rejects the already-authorized request as `NO_EXACT_CURRENT_<LANE>_REQUEST`. Build #111 on PR #459 demonstrated this race: the request was bound to `a7ad5eae...`, while two Owner-free 百人将 commits advanced main to `55b97ca8...` immediately before the Build.

## Lease rule
For future exact one-shot Lab/Auditor launches:
1. Before Sole Control declares an exact Owner Gate `AUTHORIZED_NOT_ATTEMPTED`, create an ACTIVE review-launch lease in Control #394 naming the PR, lane, request comment/SHA, candidate head/tree/base and expected main.
2. While the lease is ACTIVE, all Owner-free lanes MUST NOT mutate canonical `main`. They may continue research, issues/comments, local work, and branch-only repository work.
3. Every lane preparing a canonical-main mutation must Fresh-check Control #394 for an ACTIVE review-launch lease immediately before that mutation.
4. Sole Control Fresh-checks main immediately before handing Owner the New Build instruction. If drift is already present, no Build instruction is issued; refresh request/envelope first.
5. Lease ends on Build creation/attempt, explicit cancellation, or stale/drift invalidation. Sole Control records RELEASED/CONSUMED/CANCELLED in #394.
6. No Retry/Rebuild/rerun is created by this lease. A consumed one-shot remains consumed.

## Scope
This is coordination/fail-closed hardening only. It does not expand Build, merge, deploy, provider, credential, spend, live-effect, or Runtime authority.
