from __future__ import annotations

from typing import Any

from automation.review_dispatcher_v1.model import (
    ReviewContractError,
    github_comment_id,
    lane_result_comment_trusted,
)


def canonical_result_comment_id(
    comments: list[dict[str, Any]],
    *,
    lane: str,
    marker: str,
) -> int:
    matching: list[int] = []
    for comment in comments:
        body = comment.get("body") or ""
        if marker not in body:
            continue
        if not lane_result_comment_trusted(comment, lane):
            continue
        matching.append(github_comment_id(comment, "RESULT_COMMENT_ID"))
    if not matching:
        raise ReviewContractError("NO_TRUSTED_RESULT_FOR_MARKER")
    return min(matching)


def assert_published_result_is_canonical(
    comments: list[dict[str, Any]],
    *,
    lane: str,
    marker: str,
    published_comment_id: int,
) -> int:
    canonical = canonical_result_comment_id(
        comments,
        lane=lane,
        marker=marker,
    )
    if published_comment_id != canonical:
        raise ReviewContractError(
            f"NONCANONICAL_DUPLICATE_RESULT:{published_comment_id}!={canonical}"
        )
    return canonical
