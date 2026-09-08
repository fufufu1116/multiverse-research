from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable

CLAIM_SCHEMA = "MULTIVERSE_REVIEW_REQUEST_CLAIM_v1"
CLAIM_REF_PREFIX = "refs/heads/multiverse-review-claims/v1"
ENVELOPE_KEYS = ("repo", "pr", "lane", "head", "tree", "base", "main")


class RequestClaimError(RuntimeError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RequestClaimError(code)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _sha40(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{40}", value))


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def normalize_envelope(value: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(value, dict), "ENVELOPE_OBJECT")
    require(set(value) == set(ENVELOPE_KEYS), "ENVELOPE_KEYS")
    require(isinstance(value["repo"], str) and value["repo"].count("/") == 1, "ENVELOPE_REPO")
    require(isinstance(value["pr"], int) and not isinstance(value["pr"], bool) and value["pr"] > 0, "ENVELOPE_PR")
    require(value["lane"] in {"LAB", "AUDITOR"}, "ENVELOPE_LANE")
    for key in ("head", "tree", "base", "main"):
        require(_sha40(value[key]), f"ENVELOPE_{key.upper()}")
    return {key: value[key] for key in ENVELOPE_KEYS}


def envelope_sha256(value: dict[str, Any]) -> str:
    return sha256_json(normalize_envelope(value))


def claim_ref(value: dict[str, Any]) -> str:
    digest = envelope_sha256(value)
    return f"{CLAIM_REF_PREFIX}/{digest}"


def build_claim(
    *,
    envelope: dict[str, Any],
    request_id: str,
    claimant: str,
    nonce: str,
    predecessor_sha256: str | None,
) -> dict[str, Any]:
    normalized = normalize_envelope(envelope)
    require(isinstance(request_id, str) and bool(re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,127}", request_id)), "CLAIM_REQUEST_ID")
    require(isinstance(claimant, str) and bool(re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", claimant)), "CLAIMANT")
    require(isinstance(nonce, str) and bool(re.fullmatch(r"[A-Za-z0-9_.-]{16,128}", nonce)), "CLAIM_NONCE")
    require(predecessor_sha256 is None or _sha256(predecessor_sha256), "CLAIM_PREDECESSOR_SHA256")
    return {
        "schema": CLAIM_SCHEMA,
        "envelope": normalized,
        "envelope_sha256": envelope_sha256(normalized),
        "claim_ref": claim_ref(normalized),
        "request_id": request_id,
        "claimant": claimant,
        "nonce": nonce,
        "predecessor_sha256": predecessor_sha256,
    }


def validate_claim(claim: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(claim, dict), "CLAIM_OBJECT")
    require(
        set(claim)
        == {
            "schema",
            "envelope",
            "envelope_sha256",
            "claim_ref",
            "request_id",
            "claimant",
            "nonce",
            "predecessor_sha256",
        },
        "CLAIM_KEYS",
    )
    require(claim["schema"] == CLAIM_SCHEMA, "CLAIM_SCHEMA")
    rebuilt = build_claim(
        envelope=claim["envelope"],
        request_id=claim["request_id"],
        claimant=claim["claimant"],
        nonce=claim["nonce"],
        predecessor_sha256=claim["predecessor_sha256"],
    )
    require(claim == rebuilt, "CLAIM_CANONICAL_MISMATCH")
    return claim


def acquire_claim(
    *,
    claim: dict[str, Any],
    claim_commit_sha: str,
    create_ref: Callable[[str, str], None],
) -> dict[str, Any]:
    validate_claim(claim)
    require(_sha40(claim_commit_sha), "CLAIM_COMMIT_SHA")
    create_ref(claim["claim_ref"], claim_commit_sha)
    return {
        "claim_ref": claim["claim_ref"],
        "claim_commit_sha": claim_commit_sha,
        "envelope_sha256": claim["envelope_sha256"],
        "request_id": claim["request_id"],
    }


def verify_claim_binding(
    *,
    claim: dict[str, Any],
    claim_commit_sha: str,
    observed_ref_sha: str,
    request_id: str,
    predecessor_sha256: str | None,
) -> None:
    validate_claim(claim)
    require(_sha40(claim_commit_sha), "CLAIM_COMMIT_SHA")
    require(_sha40(observed_ref_sha), "OBSERVED_CLAIM_REF_SHA")
    require(observed_ref_sha == claim_commit_sha, "CLAIM_REF_OWNERSHIP_LOST")
    require(request_id == claim["request_id"], "CLAIM_REQUEST_ID_DRIFT")
    require(predecessor_sha256 == claim["predecessor_sha256"], "CLAIM_PREDECESSOR_DRIFT")
