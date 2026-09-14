from __future__ import annotations

from typing import Any, Callable

from automation.review_dispatcher_v1.main_drift_guard_v1 import (
    assess_unrelated_main_drift,
)
from automation.review_dispatcher_v1.model import (
    REQUEST_MARKER,
    ReviewContractError,
    issue_comment_owner_trusted,
    latest_exact_current_owner_request,
    parse_request_from_comment,
    require,
    required_object,
    sha256_json,
    sha40,
)


Fetch = Callable[[str], Any]


def _compare_url(repo: str, base: str, head: str) -> str:
    return f"https://api.github.com/repos/{repo}/compare/{base}...{head}"


def _fetch_compare(fetch: Fetch, url: str, code: str) -> dict[str, Any]:
    try:
        raw = fetch(url)
    except Exception as exc:
        raise ReviewContractError(f"{code}_FETCH_FAILED:{type(exc).__name__}") from exc
    return required_object(raw, f"{code}_RESPONSE_OBJECT")


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
            require(sha40(request["main"]), "OWNER_REQUEST_MAIN_SHA")
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
    """Return the newest valid winner across request-main snapshots.

    Every snapshot still delegates lineage/arbitration to the canonical exact
    selector. A malformed or ambiguous matching snapshot therefore fails
    closed; this function never skips a bad snapshot to resurrect older
    authority.
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
    # Preserve the legacy exact-main fast path: exact authority needs no
    # compare API evidence and therefore does not add a new failure mode to
    # already-valid exact requests.
    if request_main == live_main:
        return {
            "mode": "EXACT_MAIN",
            "request_main": request_main,
            "live_main": live_main,
            "candidate_files": [],
            "drift_files": [],
        }

    candidate_compare = _fetch_compare(
        fetch,
        _compare_url(repo, base, head),
        "CANDIDATE_COMPARE",
    )
    drift_compare = _fetch_compare(
        fetch,
        _compare_url(repo, request_main, live_main),
        "MAIN_DRIFT_COMPARE",
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
    """Prefer exact-live-main authority; use stale snapshot only if absent.

    If an exact-live-main request exists, it wins even when an older-main
    request has a later comment id. If exact-live-main arbitration is malformed
    or ambiguous, fail closed rather than falling back. Only the specific
    `NO_EXACT_CURRENT_<LANE>_REQUEST` condition enables stale-snapshot
    consideration, and that selected snapshot must then pass the drift guard.
    """
    try:
        comment_id, request, comment = latest_exact_current_owner_request(
            comments,
            repo=repo,
            pr=pr,
            lane=lane,
            head=head,
            tree=tree,
            base=base,
            main=live_main,
        )
    except ReviewContractError as exc:
        if str(exc) != f"NO_EXACT_CURRENT_{lane}_REQUEST":
            raise
    else:
        classification = assess_request_main_against_live(
            repo=repo,
            base=base,
            head=head,
            request_main=live_main,
            live_main=live_main,
            fetch=fetch,
        )
        return comment_id, request, comment, classification

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


def assert_dispatcher_ref_on_live_chain(
    job: dict[str, Any],
    *,
    live_main: str,
    fetch: Fetch,
) -> dict[str, Any]:
    """Prove dispatcher ref is on the same safe descendant main chain.

    This replaces the old `dispatcher_ref == live_main` assumption without
    allowing an arbitrary historical or divergent dispatcher snapshot.
    """
    dispatcher_ref = job.get("dispatcher_ref")
    require(sha40(dispatcher_ref), "DISPATCHER_REF_SHA")

    request_to_dispatcher = assess_request_main_against_live(
        repo=job["repo"],
        base=job["base"],
        head=job["head"],
        request_main=job["main"],
        live_main=dispatcher_ref,
        fetch=fetch,
    )
    dispatcher_to_live = assess_request_main_against_live(
        repo=job["repo"],
        base=job["base"],
        head=job["head"],
        request_main=dispatcher_ref,
        live_main=live_main,
        fetch=fetch,
    )
    return {
        "request_to_dispatcher": request_to_dispatcher,
        "dispatcher_to_live": dispatcher_to_live,
    }


def assert_job_request_latest_across_snapshots(
    job: dict[str, Any],
    comments: list[dict[str, Any]],
    *,
    live_main: str | None = None,
) -> None:
    if live_main is not None:
        try:
            comment_id, request, _ = latest_exact_current_owner_request(
                comments,
                repo=job["repo"],
                pr=job["pr"],
                lane=job["lane"],
                head=job["head"],
                tree=job["tree"],
                base=job["base"],
                main=live_main,
            )
        except ReviewContractError as exc:
            if str(exc) != f"NO_EXACT_CURRENT_{job['lane']}_REQUEST":
                raise
        else:
            require(
                comment_id == job["request_comment"],
                f"REQUEST_SUPERSEDED_BY_EXACT_LIVE_MAIN:{job['request_comment']}!={comment_id}",
            )
            require(
                sha256_json(request) == job["request_sha256"],
                "REQUEST_SUPERSEDED_BY_EXACT_LIVE_MAIN_SHA256",
            )
            require(request == job["request"], "REQUEST_SUPERSEDED_BY_EXACT_LIVE_MAIN_BODY")
            return

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
