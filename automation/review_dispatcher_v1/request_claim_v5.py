from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable

from automation.review_dispatcher_v1.model import (
    canonical_json,
    require,
    sha256_json,
    validate_request,
)

CLAIM_SCHEMA = "MULTIVERSE_REVIEW_REQUEST_CLAIM_v5"
CLAIM_REF_PREFIX = "refs/heads/multiverse-review-claims/v5"
CLAIM_MESSAGE_MARKER = "MULTIVERSE_REVIEW_REQUEST_CLAIM_V5"
ENVELOPE_KEYS = ("repo", "pr", "lane", "head", "tree", "base", "main")


def _sha40(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{40}", value))


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def canonical_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def request_envelope(request: dict[str, Any]) -> dict[str, Any]:
    validate_request(request)
    return {key: request[key] for key in ENVELOPE_KEYS}


def generation_payload(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "envelope": request_envelope(request),
        "predecessor_sha256": request["supersedes_request_sha256"],
    }


def generation_sha256(request: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(generation_payload(request))).hexdigest()


def claim_ref(request: dict[str, Any]) -> str:
    return f"{CLAIM_REF_PREFIX}/{generation_sha256(request)}"


def build_claim(*, request: dict[str, Any], claimant: str, nonce: str) -> dict[str, Any]:
    validate_request(request)
    require(
        isinstance(claimant, str)
        and bool(re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", claimant)),
        "CLAIMANT",
    )
    require(
        isinstance(nonce, str)
        and bool(re.fullmatch(r"[A-Za-z0-9_.-]{16,128}", nonce)),
        "CLAIM_NONCE",
    )
    return {
        "schema": CLAIM_SCHEMA,
        "envelope": request_envelope(request),
        "generation_sha256": generation_sha256(request),
        "claim_ref": claim_ref(request),
        "request_id": request["request_id"],
        "request_sha256": sha256_json(request),
        "claimant": claimant,
        "nonce": nonce,
        "predecessor_sha256": request["supersedes_request_sha256"],
    }


def claim_commit_message(claim: dict[str, Any]) -> str:
    return CLAIM_MESSAGE_MARKER + "\n" + canonical_json(claim)


def parse_claim_commit_message(message: Any) -> dict[str, Any]:
    require(isinstance(message, str), "CLAIM_COMMIT_MESSAGE")
    marker = CLAIM_MESSAGE_MARKER + "\n"
    require(message.startswith(marker), "CLAIM_COMMIT_MARKER")
    raw = message[len(marker):]
    try:
        claim = json.loads(raw)
    except json.JSONDecodeError as exc:
        from automation.review_dispatcher_v1.model import ReviewContractError
        raise ReviewContractError("CLAIM_COMMIT_JSON_INVALID") from exc
    return validate_claim(claim)


def validate_claim(claim: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(claim, dict), "CLAIM_OBJECT")
    require(
        set(claim)
        == {
            "schema",
            "envelope",
            "generation_sha256",
            "claim_ref",
            "request_id",
            "request_sha256",
            "claimant",
            "nonce",
            "predecessor_sha256",
        },
        "CLAIM_KEYS",
    )
    require(claim["schema"] == CLAIM_SCHEMA, "CLAIM_SCHEMA")
    require(_sha256(claim["generation_sha256"]), "CLAIM_GENERATION_SHA256")
    require(_sha256(claim["request_sha256"]), "CLAIM_REQUEST_SHA256")
    require(isinstance(claim["claim_ref"], str) and claim["claim_ref"].startswith(CLAIM_REF_PREFIX + "/"), "CLAIM_REF")
    require(isinstance(claim["request_id"], str) and bool(claim["request_id"]), "CLAIM_REQUEST_ID")
    require(
        isinstance(claim["claimant"], str)
        and bool(re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", claim["claimant"])),
        "CLAIMANT",
    )
    require(
        isinstance(claim["nonce"], str)
        and bool(re.fullmatch(r"[A-Za-z0-9_.-]{16,128}", claim["nonce"])),
        "CLAIM_NONCE",
    )
    predecessor = claim["predecessor_sha256"]
    require(predecessor is None or _sha256(predecessor), "CLAIM_PREDECESSOR_SHA256")
    return claim


def acquire_claim(
    *,
    request: dict[str, Any],
    claimant: str,
    nonce: str,
    create_commit: Callable[[str, str], str],
    create_branch: Callable[[str, str], None],
) -> dict[str, Any]:
    claim = build_claim(request=request, claimant=claimant, nonce=nonce)
    commit_sha = create_commit(claim_commit_message(claim), request["main"])
    require(_sha40(commit_sha), "CLAIM_COMMIT_SHA")
    branch_name = claim["claim_ref"].removeprefix("refs/heads/")
    create_branch(branch_name, commit_sha)
    return {**claim, "claim_commit_sha": commit_sha}


def verify_request_claim(
    *,
    request: dict[str, Any],
    fetch: Callable[[str], Any],
) -> dict[str, Any]:
    validate_request(request)
    repo = request["repo"]
    expected_ref = claim_ref(request)
    ref_suffix = expected_ref.removeprefix("refs/")
    ref_raw = fetch(f"https://api.github.com/repos/{repo}/git/ref/{ref_suffix}")
    require(isinstance(ref_raw, dict), "CLAIM_REF_RESPONSE_OBJECT")
    require(ref_raw.get("ref") == expected_ref, "CLAIM_REF_NAME_MISMATCH")
    obj = ref_raw.get("object")
    require(isinstance(obj, dict), "CLAIM_REF_OBJECT")
    require(obj.get("type") == "commit", "CLAIM_REF_OBJECT_TYPE")
    commit_sha = obj.get("sha")
    require(_sha40(commit_sha), "CLAIM_REF_COMMIT_SHA")

    commit_raw = fetch(f"https://api.github.com/repos/{repo}/git/commits/{commit_sha}")
    require(isinstance(commit_raw, dict), "CLAIM_COMMIT_RESPONSE_OBJECT")
    require(commit_raw.get("sha") == commit_sha, "CLAIM_COMMIT_SHA_MISMATCH")
    parents = commit_raw.get("parents")
    require(isinstance(parents, list) and len(parents) == 1, "CLAIM_COMMIT_PARENT_COUNT")
    parent = parents[0]
    require(isinstance(parent, dict) and parent.get("sha") == request["main"], "CLAIM_COMMIT_PARENT_MAIN_MISMATCH")

    main_raw = fetch(f"https://api.github.com/repos/{repo}/git/commits/{request['main']}")
    require(isinstance(main_raw, dict), "CLAIM_MAIN_COMMIT_OBJECT")
    main_tree = main_raw.get("tree")
    claim_tree = commit_raw.get("tree")
    require(isinstance(main_tree, dict) and isinstance(claim_tree, dict), "CLAIM_COMMIT_TREE_OBJECT")
    require(main_tree.get("sha") == claim_tree.get("sha"), "CLAIM_COMMIT_NOT_EMPTY")

    claim = parse_claim_commit_message(commit_raw.get("message"))
    require(claim["claim_ref"] == expected_ref, "CLAIM_REF_BINDING_MISMATCH")
    require(claim["envelope"] == request_envelope(request), "CLAIM_ENVELOPE_MISMATCH")
    require(claim["generation_sha256"] == generation_sha256(request), "CLAIM_GENERATION_MISMATCH")
    require(claim["request_id"] == request["request_id"], "CLAIM_REQUEST_ID_MISMATCH")
    require(claim["request_sha256"] == sha256_json(request), "CLAIM_REQUEST_SHA256_MISMATCH")
    require(claim["predecessor_sha256"] == request["supersedes_request_sha256"], "CLAIM_PREDECESSOR_MISMATCH")
    return {**claim, "claim_commit_sha": commit_sha}
