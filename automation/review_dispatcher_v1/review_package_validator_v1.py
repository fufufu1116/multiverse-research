from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable

PACKAGE_SCHEMA = "MULTIVERSE_REVIEW_READY_v1"
PACKAGE_STATE = "REVIEW_READY_NONAUTHORITY"
PASS = "PACKAGE_READY_NONAUTHORITY"
FAIL = "PACKAGE_INVALID_FAIL_CLOSED"
FORBIDDEN_QUESTION = re.compile(r"OWNER[-_ ]?(MARKER|APPROV)|MULTIVERSE_REVIEW_REQUEST_V1|credential|token|password|private endpoint|```|#!/|\b(exec|eval|curl|wget|bash|powershell)\b", re.I)
PROOF_ESCALATION = re.compile(r"real[- ]world validated|economic value proven|promoted|production authorized", re.I)
CR1_REQUIRED = (
    "synthetic-only", "no real predictive superiority", "no economic value", "no promotion",
    "no R0_T2 substitution", "DEV2000_C unopened", "ECON_HOLDOUT1000 sealed",
    "Gate487 no-rerun", "A+B not fresh", "no prospective result/outcome/payout/odds/price/economics",
    "Runtime OFF", "automatic betting OFF", "independent Lab/Auditor",
)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _fail(reason: str) -> dict[str, Any]:
    return {"schema": "MULTIVERSE_PACKAGE_VALIDATION_v1", "state": FAIL, "reason": reason,
            "authority_created": False, "owner_marker_created": False, "runtime_authority": False}


def validate(envelope: dict[str, Any], *, read: Callable[[str, str], dict[str, Any]]) -> dict[str, Any]:
    """Pure validator. read(kind, identity) must Fresh-read repository evidence and return exact identities/bytes."""
    try:
        if envelope.get("schema") != PACKAGE_SCHEMA or envelope.get("state") != PACKAGE_STATE:
            return _fail("SCHEMA_OR_STATE")
        required = ("lane_id","candidate_id","repo","candidate_ref","candidate_head","candidate_tree","package_path",
                    "package_blob_sha","package_sha256","evidence_manifest_sha256","candidate_history_pointer",
                    "review_questions","proof_ceiling","contamination_declarations","prohibited_authority",
                    "created_from_lane_state","ready_sha256")
        if any(not envelope.get(k) for k in required): return _fail("REQUIRED_FIELD")
        head = read("ref", envelope["candidate_ref"])
        if head.get("head") != envelope["candidate_head"] or head.get("tree") != envelope["candidate_tree"]:
            return _fail("STALE_HEAD_OR_TREE")
        path = envelope["package_path"]
        if path.startswith("/") or ".." in path.split("/"): return _fail("PACKAGE_PATH")
        package = read("package", path)
        if package.get("blob_sha") != envelope["package_blob_sha"]: return _fail("PACKAGE_BLOB_MISMATCH")
        raw = package.get("bytes")
        if not isinstance(raw, (bytes, bytearray)): return _fail("PACKAGE_BYTES")
        if hashlib.sha256(raw).hexdigest() != envelope["package_sha256"]: return _fail("PACKAGE_SHA256")
        evidence = read("evidence_manifest", envelope["evidence_manifest_sha256"])
        eraw = evidence.get("bytes")
        if not isinstance(eraw, (bytes, bytearray)) or hashlib.sha256(eraw).hexdigest() != envelope["evidence_manifest_sha256"]:
            return _fail("EVIDENCE_MANIFEST_SHA256")
        history = read("history", envelope["candidate_history_pointer"])
        if not history.get("resolved") or not history.get("immutable_enough"): return _fail("CANDIDATE_HISTORY")
        lane_state = read("lane_state", envelope["created_from_lane_state"])
        if not lane_state.get("exact"): return _fail("SOURCE_LANE_STATE")
        questions = envelope["review_questions"]
        if not isinstance(questions, list) or not questions or any(not isinstance(q,str) or not q.strip() or FORBIDDEN_QUESTION.search(q) for q in questions):
            return _fail("REVIEW_QUESTIONS")
        if PROOF_ESCALATION.search(str(envelope["proof_ceiling"])): return _fail("PROOF_CEILING_ESCALATION")
        if not isinstance(envelope["prohibited_authority"], list) or not envelope["prohibited_authority"]: return _fail("PROHIBITED_AUTHORITY")
        declarations = envelope["contamination_declarations"]
        if not isinstance(declarations, list) or not declarations: return _fail("CONTAMINATION_DECLARATIONS")
        if envelope["candidate_id"] == "CR1_E05":
            text = " | ".join(map(str, declarations + envelope["prohibited_authority"]))
            if any(term.lower() not in text.lower() for term in CR1_REQUIRED): return _fail("CR1_FIREWALL")
        unsigned = dict(envelope); unsigned.pop("ready_sha256", None)
        if canonical_sha256(unsigned) != envelope["ready_sha256"]: return _fail("READY_SHA256")
        identity = [envelope[k] for k in ("lane_id","candidate_id","candidate_head","package_blob_sha","ready_sha256")]
        return {"schema":"MULTIVERSE_PACKAGE_VALIDATION_v1","state":PASS,"idempotency_key":identity,
                "authority_created":False,"owner_marker_created":False,"runtime_authority":False}
    except Exception as exc:
        return _fail(f"VALIDATION_EXCEPTION:{type(exc).__name__}")
