from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable

CLAIM_SCHEMA = "MULTIVERSE_REVIEW_REQUEST_CLAIM_v3"
CLAIM_REF_PREFIX = "refs/tags/multiverse-review-claims/v3"
ENVELOPE_KEYS = ("repo", "pr", "lane", "head", "tree", "base", "main")


class RequestClaimError(RuntimeError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RequestClaimError(code)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def _sha40(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{40}", value))


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def normalize_envelope(value: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(value, dict), "ENVELOPE_OBJECT")
    require(set(value) == set(ENVELOPE_KEYS), "ENVELOPE_KEYS")
    require(isinstance(value["repo"], str) and value["repo"].count("/") == 1, "ENVELOPE_REPO")
    require(isinstance(value["pr"], int) and not isinstance(value["pr"], bool) and value["pr"] > 0, "ENVELOPE_PR")
    require(value["lane"] in {"LAB", "AUDITOR"}, "ENVELOPE_LANE")
    for key in ("head", "tree", "base", "main"):
        require(_sha40(value[key]), f"ENVELOPE_{key.upper()}")
    return {key: value[key] for key in ENVELOPE_KEYS}


def normalize_predecessor(value: str | None) -> str | None:
    require(value is None or _sha256(value), "CLAIM_PREDECESSOR_SHA256")
    return value


def envelope_sha256(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(normalize_envelope(value))).hexdigest()


def generation_payload(envelope: dict[str, Any], predecessor_sha256: str | None) -> dict[str, Any]:
    return {
        "envelope": normalize_envelope(envelope),
        "predecessor_sha256": normalize_predecessor(predecessor_sha256),
    }


def generation_sha256(envelope: dict[str, Any], predecessor_sha256: str | None) -> str:
    return hashlib.sha256(canonical_bytes(generation_payload(envelope, predecessor_sha256))).hexdigest()


def claim_ref(envelope: dict[str, Any], predecessor_sha256: str | None) -> str:
    return f"{CLAIM_REF_PREFIX}/{generation_sha256(envelope, predecessor_sha256)}"


def build_claim(
    *,
    envelope: dict[str, Any],
    request_id: str,
    claimant: str,
    nonce: str,
    predecessor_sha256: str | None,
) -> dict[str, Any]:
    normalized = normalize_envelope(envelope)
    predecessor = normalize_predecessor(predecessor_sha256)
    require(isinstance(request_id, str) and bool(re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,127}", request_id)), "CLAIM_REQUEST_ID")
    require(isinstance(claimant, str) and bool(re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", claimant)), "CLAIMANT")
    require(isinstance(nonce, str) and bool(re.fullmatch(r"[A-Za-z0-9_.-]{16,128}", nonce)), "CLAIM_NONCE")
    claim = {
        "schema": CLAIM_SCHEMA,
        "envelope": normalized,
        "envelope_sha256": envelope_sha256(normalized),
        "generation_sha256": generation_sha256(normalized, predecessor),
        "claim_ref": claim_ref(normalized, predecessor),
        "request_id": request_id,
        "claimant": claimant,
        "nonce": nonce,
        "predecessor_sha256": predecessor,
    }
    claim["claim_blob_sha1"] = git_blob_sha1(canonical_bytes(claim))
    return claim


def claim_payload_without_digest(claim: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in claim.items() if key != "claim_blob_sha1"}


def validate_claim(claim: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(claim, dict), "CLAIM_OBJECT")
    require(
        set(claim)
        == {
            "schema",
            "envelope",
            "envelope_sha256",
            "generation_sha256",
            "claim_ref",
            "request_id",
            "claimant",
            "nonce",
            "predecessor_sha256",
            "claim_blob_sha1",
        },
        "CLAIM_KEYS",
    )
    expected = build_claim(
        envelope=claim["envelope"],
        request_id=claim["request_id"],
        claimant=claim["claimant"],
        nonce=claim["nonce"],
        predecessor_sha256=claim["predecessor_sha256"],
    )
    require(claim == expected, "CLAIM_CANONICAL_MISMATCH")
    return claim


def acquire_claim(
    *,
    claim: dict[str, Any],
    create_blob: Callable[[bytes], str],
    create_ref: Callable[[str, str], None],
) -> dict[str, Any]:
    validate_claim(claim)
    payload = canonical_bytes(claim_payload_without_digest(claim))
    blob_sha = create_blob(payload)
    require(_sha40(blob_sha), "CLAIM_BLOB_SHA")
    require(blob_sha == claim["claim_blob_sha1"], "CLAIM_BLOB_SHA_MISMATCH")
    create_ref(claim["claim_ref"], blob_sha)
    return {
        "claim_ref": claim["claim_ref"],
        "claim_blob_sha1": blob_sha,
        "generation_sha256": claim["generation_sha256"],
        "request_id": claim["request_id"],
    }


def verify_claim_binding(
    *,
    claim: dict[str, Any],
    observed_ref_sha: str,
    request_id: str,
    predecessor_sha256: str | None,
) -> None:
    validate_claim(claim)
    require(_sha40(observed_ref_sha), "OBSERVED_CLAIM_REF_SHA")
    require(observed_ref_sha == claim["claim_blob_sha1"], "CLAIM_REF_BLOB_MISMATCH")
    require(request_id == claim["request_id"], "CLAIM_REQUEST_ID_DRIFT")
    require(predecessor_sha256 == claim["predecessor_sha256"], "CLAIM_PREDECESSOR_DRIFT")
