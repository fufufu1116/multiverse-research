from __future__ import annotations

from typing import Any

from automation.review_dispatcher_v1.model_legacy_v1 import (
    REQUEST_MARKER,
    ReviewContractError,
    github_comment_id,
    issue_comment_owner_trusted,
    parse_request_from_comment,
    require,
    required_object,
    sha256_json,
    validate_request,
)


def _exact_candidates(
    comments: list[dict[str, Any]],
    *,
    repo: str,
    pr: int,
    lane: str,
    head: str,
    tree: str,
    base: str,
    main: str,
) -> list[tuple[int, dict[str, Any], dict[str, Any]]]:
    candidates: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
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
        envelope_keys = ("lane", "repo", "pr", "head", "tree", "base", "main")
        if not all(key in request for key in envelope_keys):
            raise ReviewContractError("OWNER_REQUEST_ENVELOPE_INCOMPLETE")
        if (
            request["lane"] == lane
            and request["repo"] == repo
            and request["pr"] == pr
            and request["head"] == head
            and request["tree"] == tree
            and request["base"] == base
            and request["main"] == main
        ):
            validate_request(request)
            candidates.append(
                (
                    github_comment_id(comment, "OWNER_REQUEST_COMMENT_ID"),
                    request,
                    comment,
                )
            )
    candidates.sort(key=lambda item: item[0])
    return candidates


def exact_current_owner_requests_v6(
    comments: list[dict[str, Any]],
    *,
    repo: str,
    pr: int,
    lane: str,
    head: str,
    tree: str,
    base: str,
    main: str,
) -> list[tuple[int, dict[str, Any], dict[str, Any]]]:
    candidates = _exact_candidates(
        comments,
        repo=repo,
        pr=pr,
        lane=lane,
        head=head,
        tree=tree,
        base=base,
        main=main,
    )

    seen_ids: set[str] = set()
    generations: dict[str | None, list[tuple[int, dict[str, Any], dict[str, Any]]]] = {}
    for comment_id, request, comment in candidates:
        rid = request["request_id"]
        require(rid not in seen_ids, f"DUPLICATE_EXACT_REQUEST_ID:{rid}")
        seen_ids.add(rid)
        predecessor = request["supersedes_request_sha256"]
        generations.setdefault(predecessor, []).append((comment_id, request, comment))

    accepted: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    winning_predecessors: set[str | None] = set()
    predecessor: str | None = None
    previous_comment_id = 0
    visited_predecessors: set[str | None] = set()

    while predecessor in generations:
        require(predecessor not in visited_predecessors, "SUPERSESSION_PREDECESSOR_CYCLE")
        visited_predecessors.add(predecessor)
        generation = generations[predecessor]
        winner = generation[0]
        winner_comment_id, winner_request, _ = winner
        require(
            winner_comment_id > previous_comment_id,
            (
                "SUPERSESSION_COMMENT_ORDER_INVALID:"
                f"{winner_comment_id}<={previous_comment_id}"
            ),
        )
        accepted.append(winner)
        winning_predecessors.add(predecessor)
        previous_comment_id = winner_comment_id
        predecessor = sha256_json(winner_request)

    for comment_id, request, _ in candidates:
        candidate_predecessor = request["supersedes_request_sha256"]
        require(
            candidate_predecessor in winning_predecessors,
            (
                "ORPHANED_OR_LOSER_DERIVED_SUPERSESSION:"
                f"{comment_id}:{candidate_predecessor!r}"
            ),
        )

    accepted.reverse()
    return accepted


def latest_exact_current_owner_request_v6(
    comments: list[dict[str, Any]],
    *,
    repo: str,
    pr: int,
    lane: str,
    head: str,
    tree: str,
    base: str,
    main: str,
) -> tuple[int, dict[str, Any], dict[str, Any]]:
    candidates = exact_current_owner_requests_v6(
        comments,
        repo=repo,
        pr=pr,
        lane=lane,
        head=head,
        tree=tree,
        base=base,
        main=main,
    )
    require(bool(candidates), f"NO_EXACT_CURRENT_{lane}_REQUEST")
    return candidates[0]
