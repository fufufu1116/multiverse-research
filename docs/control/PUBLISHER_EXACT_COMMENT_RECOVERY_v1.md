# Publisher Exact-Comment Recovery v1

Parent: Issue #458
Predecessor: Issue #437 / PR #438
Current-main carry-forward base: `a7ad5eae115d24fd2e451bb92604def85663e4dc`
Runtime: OFF

## Observed failure
Independent Lab result publication has repeatedly succeeded on GitHub while Buildkite later ended red in the post-write publication/receipt path.

Historical exact confirmed examples include PR #428 / PR #433 and Build #108 with `POST_WRITE_VISIBILITY_DEADLINE_EXHAUSTED`. On 2026-09-14, PR #451 Independent Lab Build #110 again ended red after the exact trusted Lab PASS result comment `5658043626` had already become durable and Fresh-visible. Owner reported the second Buildkite step errored. GitHub does not expose the exact second-step log text for Build #110, so this document does not claim a specific error string for that build; it records the proven control-level recurrence: result write succeeded, terminal build state failed afterward.

The mutation already returns the exact `published_comment_id`. Retrying the mutation would risk duplicate result comments and is prohibited.

## Candidate repair
After the existing bounded list-visibility checks are exhausted:
1. do not republish;
2. GET the exact GitHub issue-comment resource by the returned `published_comment_id`;
3. require a JSON object;
4. validate the exact comment using the existing trusted lane/marker/canonical-id check over a single-comment set;
5. revalidate legacy artifact bindings;
6. recover the publish receipt from that exact trusted comment;
7. require receipt comment-id equality.

Any direct-read failure, wrong id, wrong marker, untrusted producer, malformed comment or artifact-binding mismatch still fails closed.

## Regression scope
`automation.review_dispatcher_v1.test_publisher_resilience_integration_v1` covers:
- existing canonical recovery;
- normal immediate publication visibility;
- precheck races;
- duplicate rejection;
- request supersession;
- delayed list visibility convergence;
- list deadline followed by exact-comment recovery without repost;
- earlier canonical duplicate winning over a later post;
- freshness recheck failure;
- wrong exact-comment id rejection;
- direct-read failure fail-closed behavior.

## Carry-forward rule
This successor is based on current main instead of merging the stale/non-mergeable PR #438 branch. It carries forward only the previously Lab-PASS publisher recovery behavior while preserving the newer canonical dispatcher/freshness/arbitration code already present on main.

This candidate does not authorize Buildkite mutation, review Build execution, merge/adoption, deployment, credentials, provider calls, spend, live effects or Runtime activation.
