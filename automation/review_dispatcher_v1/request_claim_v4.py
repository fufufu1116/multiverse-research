from __future__ import annotations

import base64
import hashlib
import json
import re
from typing import Any, Callable

from automation.review_dispatcher_v1.model import (
    ReviewContractError,
    canonical_json,
    require,
    sha256_json,
    validate_request,
)

CLAIM_SCHEMA = "MULTIVERSE_REVIEW_REQUEST_CLAIM_v4"
CLAIM_REF_PREFIX = "refs/tags/multiverse-review-claims/v4"
ENVELOPE_KEYS = ("repo", "pr", "lane", "head", "tree", "base", "main")


def _sha40(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{40}", value))


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def canonical_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


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


def build_claim(
    *,
    request: dict[str, Any],
    claimant: str,
    nonce: str,
) -> dict[str, Any]:
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
    claim = {
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
            "generation_sha256",
            "claim_ref",
            "request_id",
            "request_sha256",
            "claimant",
            "nonce",
            "predecessor_sha256",
            "claim_blob_sha1",
        },
        "CLAIM_KEYS",
    )
    require(claim["schema"] == CLAIM_SCHEMA, "CLAIM_SCHEMA")
    require(_sha256(claim["generation_sha256"]), "CLAIM_GENERATION_SHA256")
    require(_sha256(claim["request_sha256"]), "CLAIM_REQUEST_SHA256")
    require(_sha40(claim["claim_blob_sha1"]), "CLAIM_BLOB_SHA1")
    require(
        isinstance(claim["request_id"], str) and bool(claim["request_id"]),
        "CLAIM_REQUEST_ID",
    )
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
    payload = claim_payload_without_digest(claim)
    require(
        git_blob_sha1(canonical_bytes(payload)) == claim["claim_blob_sha1"],
        "CLAIM_BLOB_DIGEST_MISMATCH",
    )
    return claim


def acquire_claim(
    *,
    request: dict[str, Any],
    claimant: str,
    nonce: str,
    create_blob: Callable[[bytes], str],
    create_ref: Callable[[str, str], None],
) -> dict[str, Any]:
    claim = build_claim(request=request, claimant=claimant, nonce=nonce)
    payload = canonical_bytes(claim_payload_without_digest(claim))
    blob_sha = create_blob(payload)
    require(_sha40(blob_sha), "CLAIM_PROVIDER_BLOB_SHA")
    require(blob_sha == claim["claim_blob_sha1"], "CLAIM_PROVIDER_BLOB_MISMATCH")
    create_ref(claim["claim_ref"], blob_sha)
    return claim


def _decode_blob_payload(raw: Any, expected_sha: str) -> dict[str, Any]:
    require(isinstance(raw, dict), "CLAIM_BLOB_RESPONSE_OBJECT")
    require(raw.get("sha") == expected_sha, "CLAIM_BLOB_RESPONSE_SHA_MISMATCH")
    require(raw.get("encoding") == "base64", "CLAIM_BLOB_ENCODING")
    content = raw.get("content")
    require(isinstance(content, str), "CLAIM_BLOB_CONTENT")
    try:
        decoded = base64.b64decode(content, validate=False)
    except Exception as exc:
        raise ReviewContractError("CLAIM_BLOB_BASE64_INVALID") from exc
    require(git_blob_sha1(decoded) == expected_sha, "CLAIM_BLOB_OBJECT_DIGEST_MISMATCH")
    try:
        claim = json.loads(decoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReviewContractError("CLAIM_BLOB_JSON_INVALID") from exc
    return validate_claim(claim)


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
    require(obj.get("type") == "blob", "CLAIM_REF_OBJECT_TYPE")
    blob_sha = obj.get("sha")
    require(_sha40(blob_sha), "CLAIM_REF_BLOB_SHA")

    blob_raw = fetch(f"https://api.github.com/repos/{repo}/git/blobs/{blob_sha}")
    claim = _decode_blob_payload(blob_raw, blob_sha)

    require(claim["claim_ref"] == expected_ref, "CLAIM_REF_BINDING_MISMATCH")
    require(claim["claim_blob_sha1"] == blob_sha, "CLAIM_BLOB_BINDING_MISMATCH")
    require(claim["envelope"] == request_envelope(request), "CLAIM_ENVELOPE_MISMATCH")
    require(claim["generation_sha256"] == generation_sha256(request), "CLAIM_GENERATION_MISMATCH")
    require(claim["request_id"] == request["request_id"], "CLAIM_REQUEST_ID_MISMATCH")
    require(claim["request_sha256"] == sha256_json(request), "CLAIM_REQUEST_SHA256_MISMATCH")
    require(
        claim["predecessor_sha256"] == request["supersedes_request_sha256"],
        "CLAIM_PREDECESSOR_MISMATCH",
    )
    return claim
