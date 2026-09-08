from __future__ import annotations

from typing import Any

from automation.review_dispatcher_v1.model import (
    ReviewContractError,
    github_comment_id,
    lane_result_comment_trusted,
)


def canonical_trusted_comment_id(
    comments: list[dict[str, Any]],
    *,
    lane: str,
    marker: str,
) -> int:
    ids = [
        github_comment_id(comment, "CANONICAL_COMMENT_ID")
        for comment in comments
        if marker in (comment.get("body") or "")
        and lane_result_comment_trusted(comment, lane)
    ]
    if not ids:
        raise ReviewContractError("NO_CANONICAL_TRUSTED_COMMENT")
    return min(ids)


def assert_referenced_result_is_canonical(
    comments: list[dict[str, Any]],
    *,
    lane: str,
    marker: str,
    referenced_comment_id: int,
) -> int:
    canonical = canonical_trusted_comment_id(
        comments,
        lane=lane,
        marker=marker,
    )
    if referenced_comment_id != canonical:
        raise ReviewContractError(
            f"REFERENCED_RESULT_NOT_CANONICAL:{referenced_comment_id}!={canonical}"
        )
    return canonical


def assert_published_t2_is_canonical(
    comments: list[dict[str, Any]],
    *,
    marker: str,
    published_comment_id: int,
) -> int:
    canonical = canonical_trusted_comment_id(
        comments,
        lane="AUDITOR",
        marker=marker,
    )
    if published_comment_id != canonical:
        raise ReviewContractError(
            f"NONCANONICAL_DUPLICATE_T2:{published_comment_id}!={canonical}"
        )
    return canonical
