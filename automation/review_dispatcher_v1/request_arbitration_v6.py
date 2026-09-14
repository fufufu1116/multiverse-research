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
)


CandidateRecord = tuple[int, dict[str, Any], dict[str, Any], str | None]

_SAFE_RECIPE = {
    "subtrees": {}, "durable_comments": [], "source_rules": [],
    "unittest_modules": [], "validators": [], "secret_scan_paths": [],
    "forbidden_patterns": [], "http": None,
}


def _validate_request(request: dict[str, Any]) -> dict[str, Any]:
    # Late import avoids model <-> arbitration import cycle while ensuring the
    # active compatibility validator, not the frozen legacy validator, is used.
    from automation.review_dispatcher_v1 import model
    return model.validate_request(request)


def _recipe_only_invalid(request: dict[str, Any]) -> bool:
    probe = dict(request)
    probe["recipe"] = {
        key: (value.copy() if isinstance(value, dict) else list(value) if isinstance(value, list) else value)
        for key, value in _SAFE_RECIPE.items()
    }
    try:
        _validate_request(probe)
    except ReviewContractError:
        return False
    return True


def _exact_candidates(comments, *, repo, pr, lane, head, tree, base, main):
    candidates: list[CandidateRecord] = []
    for raw_comment in comments:
        comment = required_object(raw_comment, "COMMENT_RESPONSE_OBJECT")
        body = comment.get("body") or ""
        if REQUEST_MARKER not in body or not issue_comment_owner_trusted(comment, repo):
            continue
        request = parse_request_from_comment(body)
        if request is None:
            continue
        envelope_keys = ("lane", "repo", "pr", "head", "tree", "base", "main")
        if not all(key in request for key in envelope_keys):
            raise ReviewContractError("OWNER_REQUEST_ENVELOPE_INCOMPLETE")
        if (request["lane"] == lane and request["repo"] == repo and request["pr"] == pr
                and request["head"] == head and request["tree"] == tree
                and request["base"] == base and request["main"] == main):
            validation_error = None
            try:
                _validate_request(request)
            except ReviewContractError as exc:
                if not _recipe_only_invalid(request):
                    raise
                validation_error = str(exc)
            candidates.append((github_comment_id(comment, "OWNER_REQUEST_COMMENT_ID"), request, comment, validation_error))
    candidates.sort(key=lambda item: item[0])
    return candidates


def exact_current_owner_requests_v6(comments, *, repo, pr, lane, head, tree, base, main):
    candidates = _exact_candidates(comments, repo=repo, pr=pr, lane=lane, head=head, tree=tree, base=base, main=main)
    seen_ids = set()
    generations = {}
    for comment_id, request, comment, validation_error in candidates:
        rid = request["request_id"]
        require(rid not in seen_ids, f"DUPLICATE_EXACT_REQUEST_ID:{rid}")
        seen_ids.add(rid)
        predecessor = request["supersedes_request_sha256"]
        generations.setdefault(predecessor, []).append((comment_id, request, comment, validation_error))

    historical_bridge_hashes = set()
    for comment_id, request, _comment, validation_error in candidates:
        if validation_error is None:
            continue
        request_sha = sha256_json(request)
        direct_successors = [c for c in candidates if c[0] > comment_id and c[1]["supersedes_request_sha256"] == request_sha]
        require(len(direct_successors) == 1, f"HISTORICAL_INVALID_EXACT_SUCCESSOR_COUNT:{comment_id}:{len(direct_successors)}:{validation_error}")
        successor = direct_successors[0]
        require(successor[3] is None, f"HISTORICAL_INVALID_EXACT_SUCCESSOR_NOT_VALID:{comment_id}:{successor[0]}:{successor[3]}")
        historical_bridge_hashes.add(request_sha)

    accepted = []
    winning_predecessors = set()
    predecessor = None
    previous_comment_id = 0
    visited_predecessors = set()
    while predecessor in generations:
        require(predecessor not in visited_predecessors, "SUPERSESSION_PREDECESSOR_CYCLE")
        visited_predecessors.add(predecessor)
        winner_comment_id, winner_request, winner_comment, validation_error = generations[predecessor][0]
        require(winner_comment_id > previous_comment_id, f"SUPERSESSION_COMMENT_ORDER_INVALID:{winner_comment_id}<={previous_comment_id}")
        winner_sha = sha256_json(winner_request)
        if validation_error is None:
            accepted.append((winner_comment_id, winner_request, winner_comment))
        else:
            require(winner_sha in historical_bridge_hashes, f"CURRENT_MALFORMED_REQUEST_NOT_BRIDGEABLE:{winner_comment_id}:{validation_error}")
        winning_predecessors.add(predecessor)
        previous_comment_id = winner_comment_id
        predecessor = winner_sha

    for comment_id, request, _comment, _validation_error in candidates:
        candidate_predecessor = request["supersedes_request_sha256"]
        require(candidate_predecessor in winning_predecessors, f"ORPHANED_OR_LOSER_DERIVED_SUPERSESSION:{comment_id}:{candidate_predecessor!r}")
    accepted.reverse()
    return accepted


def latest_exact_current_owner_request_v6(comments, *, repo, pr, lane, head, tree, base, main):
    candidates = exact_current_owner_requests_v6(comments, repo=repo, pr=pr, lane=lane, head=head, tree=tree, base=base, main=main)
    require(bool(candidates), f"NO_EXACT_CURRENT_{lane}_REQUEST")
    return candidates[0]
