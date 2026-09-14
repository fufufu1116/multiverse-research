from __future__ import annotations

from typing import Any, Callable

from automation.review_dispatcher_v1.main_drift_guard_v1 import (
    assess_unrelated_main_drift,
)
from automation.review_dispatcher_v1.model import (
    REQUEST_MARKER,
    github_comment_id,
    issue_comment_owner_trusted,
    latest_exact_current_owner_request,
    parse_request_from_comment,
    require,
    required_object,
    sha256_json,
)


Fetch = Callable[[str], Any]


def _compare_url(repo: str, base: str, head: str) -> str:
    return f"https://api.github.com/repos/{repo}/compare/{base}...{head}"


def _request_snapshot_mains(
    comments: list[dict[str, Any]],
    *,
    repo: str,
    pr: int,
    lane: str,
    head: str,
    tree: str,
    base: str,
) -> set[str]:
    mains: set[str] = set()
    envelope_keys = ("lane", "repo", "pr", "head", "tree", "base", "main")
    for raw_comment in comments:
        comment = required_object(raw_comment, "COMMENT_RESPONSE_OBJECT")
        body = comment.get("body") or ""
        if REQUEST_MARKER not in body:
            continue
        if not issue_comment_owner_trusted(comment, repo):
            continue
        request = parse_request_from_comment(body)
        if request is None:
            continue
        require(
            all(key in request for key in envelope_keys),
            "OWNER_REQUEST_ENVELOPE_INCOMPLETE",
        )
        if (
            request["lane"] == lane
            and request["repo"] == repo
            and request["pr"] == pr
            and request["head"] == head
            and request["tree"] == tree
            and request["base"] == base
        ):
            require(isinstance(request["main"], str), "OWNER_REQUEST_MAIN_TYPE")
            mains.add(request["main"])
    return mains


def latest_target_request_across_main_snapshots(
    comments: list[dict[str, Any]],
    *,
    repo: str,
    pr: int,
    lane: str,
    head: str,
    tree: str,
    base: str,
) -> tuple[int, dict[str, Any], dict[str, Any]]:
    """Return the newest valid exact-envelope winner across request-main snapshots.

    Each snapshot delegates lineage/arbitration to the canonical v6 exact
    selector. A malformed/ambiguous matching snapshot therefore fails closed;
    this function never skips a bad newer snapshot in order to fall back to an
    older request.
    """
    mains = _request_snapshot_mains(
        comments,
        repo=repo,
        pr=pr,
        lane=lane,
        head=head,
        tree=tree,
        base=base,
    )
    require(bool(mains), f"NO_TARGET_{lane}_REQUEST")

    winners: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    for request_main in sorted(mains):
        winners.append(
            latest_exact_current_owner_request(
                comments,
                repo=repo,
                pr=pr,
                lane=lane,
                head=head,
                tree=tree,
                base=base,
                main=request_main,
            )
        )

    winners.sort(key=lambda item: item[0], reverse=True)
    return winners[0]


def assess_request_main_against_live(
    *,
    repo: str,
    base: str,
    head: str,
    request_main: str,
    live_main: str,
    fetch: Fetch,
) -> dict[str, Any]:
    candidate_compare = required_object(
        fetch(_compare_url(repo, base, head)),
        "CANDIDATE_COMPARE_RESPONSE_OBJECT",
    )
    if request_main == live_main:
        drift_compare: dict[str, Any] = {
            "status": "ahead",
            "ahead_by": 0,
            "behind_by": 0,
            "total_commits": 0,
            "too_large": None,
            "merge_base_commit": {"sha": request_main},
            "files": [],
        }
    else:
        drift_compare = required_object(
            fetch(_compare_url(repo, request_main, live_main)),
            "MAIN_DRIFT_COMPARE_RESPONSE_OBJECT",
        )

    return assess_unrelated_main_drift(
        request_main=request_main,
        live_main=live_main,
        candidate_base=base,
        candidate_compare=candidate_compare,
        drift_compare=drift_compare,
    )


def select_request_for_live_main(
    comments: list[dict[str, Any]],
    *,
    repo: str,
    pr: int,
    lane: str,
    head: str,
    tree: str,
    base: str,
    live_main: str,
    fetch: Fetch,
) -> tuple[int, dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Select the newest target request, then prove its main binding is safe.

    Exact-main is naturally preferred when the newest trusted request is bound
    to live main. If the newest request belongs to an older snapshot, no older
    request is tried: that exact request must pass the fail-closed drift guard.
    """
    comment_id, request, comment = latest_target_request_across_main_snapshots(
        comments,
        repo=repo,
        pr=pr,
        lane=lane,
        head=head,
        tree=tree,
        base=base,
    )
    classification = assess_request_main_against_live(
        repo=repo,
        base=base,
        head=head,
        request_main=request["main"],
        live_main=live_main,
        fetch=fetch,
    )
    return comment_id, request, comment, classification


def assert_job_main_binding_fresh(
    job: dict[str, Any],
    *,
    live_main: str,
    fetch: Fetch,
) -> dict[str, Any]:
    return assess_request_main_against_live(
        repo=job["repo"],
        base=job["base"],
        head=job["head"],
        request_main=job["main"],
        live_main=live_main,
        fetch=fetch,
    )


def assert_job_request_latest_across_snapshots(
    job: dict[str, Any],
    comments: list[dict[str, Any]],
) -> None:
    comment_id, request, _ = latest_target_request_across_main_snapshots(
        comments,
        repo=job["repo"],
        pr=job["pr"],
        lane=job["lane"],
        head=job["head"],
        tree=job["tree"],
        base=job["base"],
    )
    require(
        comment_id == job["request_comment"],
        f"REQUEST_NO_LONGER_LATEST_TARGET:{job['request_comment']}!={comment_id}",
    )
    require(
        sha256_json(request) == job["request_sha256"],
        "REQUEST_NO_LONGER_LATEST_TARGET_SHA256",
    )
    require(request == job["request"], "REQUEST_NO_LONGER_LATEST_TARGET_BODY")
