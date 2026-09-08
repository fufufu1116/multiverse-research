from __future__ import annotations

import time

from automation.review_dispatcher_v1 import publisher_legacy_v1 as _legacy
from automation.review_dispatcher_v1.publisher_freshness_v1 import (
    assert_job_request_still_canonical,
)
from automation.review_dispatcher_v1.receipt_recovery_v1 import (
    recover_publish_receipt,
)
from automation.review_dispatcher_v1.result_canonicalization_v1 import (
    assert_published_result_is_canonical,
    canonical_result_comment_id,
)

_original_fresh_verify = _legacy._fresh_verify
_original_publish = _legacy.publish

POST_WRITE_VISIBILITY_MAX_READS = 4
POST_WRITE_VISIBILITY_DELAY_SECONDS = 1.0


def _fresh_verify(job):
    comments = _original_fresh_verify(job)
    assert_job_request_still_canonical(job, comments)
    return comments


def _canonical_comment_or_none(comments, *, lane, marker):
    try:
        canonical_id = canonical_result_comment_id(
            comments,
            lane=lane,
            marker=marker,
        )
    except _legacy.ReviewContractError as exc:
        if str(exc) == "NO_TRUSTED_RESULT_FOR_MARKER":
            return None
        raise

    for comment in comments:
        if _legacy.github_comment_id(comment, "RESULT_COMMENT_ID") == canonical_id:
            return comment
    raise _legacy.ReviewContractError("CANONICAL_RESULT_COMMENT_NOT_FOUND")


def _await_published_result_canonical(
    job,
    *,
    marker,
    published_comment_id,
):
    for read_index in range(POST_WRITE_VISIBILITY_MAX_READS):
        comments = _fresh_verify(job)
        try:
            return assert_published_result_is_canonical(
                comments,
                lane=job["lane"],
                marker=marker,
                published_comment_id=published_comment_id,
            )
        except _legacy.ReviewContractError as exc:
            if str(exc) != "NO_TRUSTED_RESULT_FOR_MARKER":
                raise

        if read_index + 1 < POST_WRITE_VISIBILITY_MAX_READS:
            time.sleep(POST_WRITE_VISIBILITY_DELAY_SECONDS)

    raise _legacy.ReviewContractError(
        "POST_WRITE_VISIBILITY_DEADLINE_EXHAUSTED"
    )


def _validate_recovery_artifact(job, artifact):
    expected_login, expected_app_id, _ = _legacy._lane_identity(job["lane"])
    exact = {
        "schema_version": "MULTIVERSE_FIXED_REVIEW_ARTIFACT_v1",
        "lane": job["lane"],
        "request_id": job["request_id"],
        "request_comment": job["request_comment"],
        "request_sha256": job["request_sha256"],
        "reviewed_repo": job["repo"],
        "reviewed_pr": job["pr"],
        "reviewed_head": job["head"],
        "reviewed_tree": job["tree"],
        "reviewed_base": job["base"],
        "reviewed_main": job["main"],
        "verdict": "PASS",
        "findings": [],
    }
    for key, expected in exact.items():
        _legacy.require(
            artifact.get(key) == expected,
            f"RECOVERY_LEGACY_BINDING_{key.upper()}",
        )
    producer = artifact.get("producer") or {}
    _legacy.require(
        producer.get("github_login") == expected_login,
        "RECOVERY_LEGACY_BINDING_PRODUCER_LOGIN",
    )
    _legacy.require(
        producer.get("github_app_id") == expected_app_id,
        "RECOVERY_LEGACY_BINDING_PRODUCER_APP_ID",
    )


def _recover_existing(job, artifact, comments, marker):
    canonical = _canonical_comment_or_none(
        comments,
        lane=job["lane"],
        marker=marker,
    )
    if canonical is None:
        return None
    _validate_recovery_artifact(job, artifact)
    return recover_publish_receipt(
        job=job,
        artifact=artifact,
        canonical_result_comment=canonical,
    )


def publish(job, artifact):
    comments = _fresh_verify(job)
    marker = _legacy.result_marker(
        job["request_id"],
        job["head"],
        job["request_comment"],
        job["request_sha256"],
    )

    recovered = _recover_existing(job, artifact, comments, marker)
    if recovered is not None:
        return recovered

    try:
        receipt = _original_publish(job, artifact)
    except _legacy.ReviewContractError as exc:
        if not str(exc).startswith("CURRENT_REQUEST_RESULT_ALREADY_EXISTS:"):
            raise
        comments = _fresh_verify(job)
        recovered = _recover_existing(job, artifact, comments, marker)
        if recovered is None:
            raise _legacy.ReviewContractError(
                "EXISTING_RESULT_RACE_WITHOUT_CANONICAL_RECOVERY"
            ) from exc
        return recovered

    _await_published_result_canonical(
        job,
        marker=marker,
        published_comment_id=receipt["published_comment_id"],
    )
    return receipt


_legacy._fresh_verify = _fresh_verify
_legacy.publish = publish

for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)


def main() -> int:
    return _legacy.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (_legacy.ReviewContractError, _legacy.GitHubAppError) as exc:
        print(f"PUBLISH_FIX_REQUIRED:{exc}")
        raise SystemExit(1)
