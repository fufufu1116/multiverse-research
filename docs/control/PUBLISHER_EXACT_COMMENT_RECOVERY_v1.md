# Publisher Exact-Comment Recovery v1

Parent: Issue #437
Base main: `e875d491853ab9a27158b617ff185d14ac804039`
Runtime: OFF

## Observed failure
Independent Lab result publication for PR #428 and PR #433 succeeded on GitHub, but Buildkite later exited red with `POST_WRITE_VISIBILITY_DEADLINE_EXHAUSTED` because the PR comment-list rereads did not expose the newly created comment within the bounded four-read window.

The mutation already returned the exact `published_comment_id`. Retrying the mutation would risk duplicate result comments and is therefore prohibited.

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
`automation.review_dispatcher_v1.test_publisher_resilience_integration_v1` now covers:
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

This candidate does not authorize Buildkite mutation, review Build execution, merge/adoption, deployment, credentials, provider calls, spend, live effects or Runtime activation.
