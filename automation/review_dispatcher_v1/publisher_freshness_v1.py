from __future__ import annotations

from typing import Any

from automation.review_dispatcher_v1.model import (
    latest_exact_current_owner_request,
    require,
    sha256_json,
)


def assert_job_request_still_canonical(
    job: dict[str, Any],
    comments: list[dict[str, Any]],
) -> None:
    request_comment, request, _ = latest_exact_current_owner_request(
        comments,
        repo=job["repo"],
        pr=job["pr"],
        lane=job["lane"],
        head=job["head"],
        tree=job["tree"],
        base=job["base"],
        main=job["main"],
    )
    request_sha256 = sha256_json(request)
    require(
        request_comment == job["request_comment"],
        (
            "PUBLISH_REQUEST_NO_LONGER_CANONICAL_COMMENT:"
            f"{job['request_comment']}!={request_comment}"
        ),
    )
    require(
        request_sha256 == job["request_sha256"],
        "PUBLISH_REQUEST_NO_LONGER_CANONICAL_SHA256",
    )
    require(
        request == job["request"],
        "PUBLISH_REQUEST_NO_LONGER_CANONICAL_BODY",
    )
