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


CandidateRecord = tuple[
    int,
    dict[str, Any],
    dict[str, Any],
    str | None,
]


_SAFE_RECIPE = {
    "subtrees": {},
    "durable_comments": [],
    "source_rules": [],
    "unittest_modules": [],
    "validators": [],
    "secret_scan_paths": [],
    "forbidden_patterns": [],
    "http": None,
}


def _recipe_only_invalid(request: dict[str, Any]) -> bool:
    """True only when replacing recipe makes the whole request valid.

    This is the safety boundary for historical bridging. Authority,
    identity, envelope, upstream, supersession and nonauthority fields must
    already satisfy the current canonical request contract. Only a malformed
    historical recipe may be bridged by an explicit later valid successor.
    """
    probe = dict(request)
    probe["recipe"] = {
        key: (value.copy() if isinstance(value, dict) else list(value) if isinstance(value, list) else value)
        for key, value in _SAFE_RECIPE.items()
    }
    try:
        validate_request(probe)
    except ReviewContractError:
        return False
    return True


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
) -> list[CandidateRecord]:
    candidates: list[CandidateRecord] = []
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
            validation_error: str | None = None
            try:
                validate_request(request)
            except ReviewContractError as exc:
                # Never bridge authority/identity/upstream/envelope defects.
                # A later successor may bridge only a recipe-local historical
                # defect, and only after exact SHA/order/ambiguity checks below.
                if not _recipe_only_invalid(request):
                    raise
                validation_error = str(exc)
            candidates.append(
                (
                    github_comment_id(comment, "OWNER_REQUEST_COMMENT_ID"),
                    request,
                    comment,
                    validation_error,
                )
            )
    candidates.sort(key=lambda item: item[0])
    return candidates


def _collapse_identical_valid_duplicate_echoes(
    candidates: list[CandidateRecord],
) -> list[CandidateRecord]:
    """Collapse only exact idempotent re-publications of a valid request.

    The earliest trusted durable comment remains the single logical request.
    A later same-request-id comment is ignored only when both requests are
    independently valid and their parsed request objects and canonical SHA256
    are identical. Historical-invalid requests are never collapsed, and any
    same-id near-duplicate remains a hard fail-close.
    """
    collapsed: list[CandidateRecord] = []
    first_by_request_id: dict[str, CandidateRecord] = {}

    for candidate in candidates:
        _comment_id, request, _comment, validation_error = candidate
        request_id = request["request_id"]
        previous = first_by_request_id.get(request_id)
        if previous is None:
            first_by_request_id[request_id] = candidate
            collapsed.append(candidate)
            continue

        _previous_comment_id, previous_request, _previous_comment, previous_error = previous
        identical_valid_echo = (
            previous_error is None
            and validation_error is None
            and request == previous_request
            and sha256_json(request) == sha256_json(previous_request)
        )
        require(
            identical_valid_echo,
            f"DUPLICATE_EXACT_REQUEST_ID:{request_id}",
        )
        # Exact valid duplicate echo: preserve durable history externally but
        # do not create another logical generation candidate. Because input is
        # sorted by comment id, the first/earliest trusted durable comment is
        # deterministic and remains authoritative for this exact request.

    return collapsed


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
    candidates = _collapse_identical_valid_duplicate_echoes(
        _exact_candidates(
            comments,
            repo=repo,
            pr=pr,
            lane=lane,
            head=head,
            tree=tree,
            base=base,
            main=main,
        )
    )

    generations: dict[str | None, list[CandidateRecord]] = {}
    for comment_id, request, comment, validation_error in candidates:
        # Recipe-only historical candidates already passed a full validation
        # probe with a safe empty recipe, so these arbitration fields are
        # canonical and authority-safe even when their original recipe is not.
        predecessor = request["supersedes_request_sha256"]
        generations.setdefault(predecessor, []).append(
            (comment_id, request, comment, validation_error)
        )

    # A malformed exact request is tolerated only as durable historical
    # lineage when exactly one later exact trusted *valid* request binds to
    # its raw canonical SHA. No successor, an invalid successor, or multiple
    # non-identical successors remains fail-closed. Exact valid duplicate
    # publication echoes were already collapsed above and therefore cannot
    # create false successor ambiguity.
    historical_bridge_hashes: set[str] = set()
    for comment_id, request, _comment, validation_error in candidates:
        if validation_error is None:
            continue
        request_sha = sha256_json(request)
        direct_successors = [
            candidate
            for candidate in candidates
            if candidate[0] > comment_id
            and candidate[1]["supersedes_request_sha256"] == request_sha
        ]
        require(
            len(direct_successors) == 1,
            (
                "HISTORICAL_INVALID_EXACT_SUCCESSOR_COUNT:"
                f"{comment_id}:{len(direct_successors)}:{validation_error}"
            ),
        )
        successor = direct_successors[0]
        require(
            successor[3] is None,
            (
                "HISTORICAL_INVALID_EXACT_SUCCESSOR_NOT_VALID:"
                f"{comment_id}:{successor[0]}:{successor[3]}"
            ),
        )
        historical_bridge_hashes.add(request_sha)

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
        winner_comment_id, winner_request, winner_comment, validation_error = winner
        require(
            winner_comment_id > previous_comment_id,
            (
                "SUPERSESSION_COMMENT_ORDER_INVALID:"
                f"{winner_comment_id}<={previous_comment_id}"
            ),
        )
        winner_sha = sha256_json(winner_request)
        if validation_error is None:
            accepted.append((winner_comment_id, winner_request, winner_comment))
        else:
            require(
                winner_sha in historical_bridge_hashes,
                (
                    "CURRENT_MALFORMED_REQUEST_NOT_BRIDGEABLE:"
                    f"{winner_comment_id}:{validation_error}"
                ),
            )
        winning_predecessors.add(predecessor)
        previous_comment_id = winner_comment_id
        predecessor = winner_sha

    for comment_id, request, _comment, _validation_error in candidates:
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
