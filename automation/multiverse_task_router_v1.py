#!/usr/bin/env python3
"""Deterministic task-state/router core for the MULTIVERSE automation candidate lane.

No network calls. No production authority. It validates task manifests, parses exact
review result fields, enforces retry/risk ceilings, and emits the next-role envelope.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import tempfile
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "multiverse-task-router-v1"
MAX_REMEDIATION_RETRIES = 3

STATES = {
    "NEW", "CORE_WORKING", "MECHANICAL_GATE", "LAB_REVIEW", "LAB_FIX_REQUIRED",
    "AUDIT_REVIEW", "AUDIT_FIX_REQUIRED", "OWNER_GATE", "DONE", "FAILED_CLOSED",
}
EVENTS = {
    "CORE_READY", "MECHANICAL_PASS", "MECHANICAL_FAIL", "LAB_PASS",
    "LAB_FIX_REQUIRED", "AUDITOR_PASS", "AUDITOR_FIX_REQUIRED",
    "OWNER_APPROVED", "OWNER_REJECTED", "FATAL",
}
BASE_TRANSITIONS = {
    ("NEW", "CORE_READY"): "CORE_WORKING",
    ("CORE_WORKING", "CORE_READY"): "MECHANICAL_GATE",
    ("MECHANICAL_GATE", "MECHANICAL_PASS"): "LAB_REVIEW",
    ("MECHANICAL_GATE", "MECHANICAL_FAIL"): "CORE_WORKING",
    ("LAB_REVIEW", "LAB_PASS"): "AUDIT_REVIEW",
    ("LAB_REVIEW", "LAB_FIX_REQUIRED"): "LAB_FIX_REQUIRED",
    ("LAB_FIX_REQUIRED", "CORE_READY"): "CORE_WORKING",
    ("AUDIT_REVIEW", "AUDITOR_PASS"): "DONE",
    ("AUDIT_REVIEW", "AUDITOR_FIX_REQUIRED"): "AUDIT_FIX_REQUIRED",
    ("AUDIT_FIX_REQUIRED", "CORE_READY"): "CORE_WORKING",
    ("OWNER_GATE", "OWNER_APPROVED"): "CORE_WORKING",
    ("OWNER_GATE", "OWNER_REJECTED"): "DONE",
}
OWNER_FREE_REMEDIATION_KEYS = (
    "candidate_scope_only",
    "no_production_or_stable_effect",
    "no_external_send",
    "no_spending",
    "no_secrets_or_writer_key",
    "no_protected_data_access",
    "no_irreversible_operation",
    "no_authority_expansion",
    "deterministic_testable",
)
SHA40 = re.compile(r"^[0-9a-f]{40}$")
FIELD_NAME = re.compile(r"^[A-Z0-9_]+$")


class RouterError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RouterError(code)


def _string_list(task: dict[str, Any], key: str) -> None:
    require(isinstance(task[key], list) and all(isinstance(x, str) and x for x in task[key]), f"{key.upper()}")


def validate_manifest(task: dict[str, Any]) -> None:
    required = (
        "schema_version", "task_id", "objective", "canonical_repo", "target_branch",
        "target_head", "artifact_ref", "role_owner", "state", "previous_state",
        "retry_count", "risk_class", "created_at", "updated_at", "evidence_refs",
        "allowed_read", "forbidden_read", "allowed_actions", "forbidden_actions",
        "pass_criteria", "fail_criteria", "authority", "routing_contract",
    )
    for key in required:
        require(key in task, f"MISSING:{key}")
    require(task["schema_version"] == SCHEMA_VERSION, "SCHEMA_VERSION")
    for key in ("task_id", "objective", "target_branch", "artifact_ref", "role_owner", "risk_class", "created_at", "updated_at"):
        require(isinstance(task[key], str) and task[key], key.upper())
    require(
        isinstance(task["canonical_repo"], str)
        and task["canonical_repo"].count("/") == 1
        and not task["canonical_repo"].startswith("/")
        and not task["canonical_repo"].endswith("/"),
        "CANONICAL_REPO",
    )
    require(isinstance(task["target_head"], str) and SHA40.fullmatch(task["target_head"]) is not None, "TARGET_HEAD")
    require(task["state"] in STATES, "STATE")
    require(task["previous_state"] is None or task["previous_state"] in STATES, "PREVIOUS_STATE")
    require(isinstance(task["retry_count"], int) and 0 <= task["retry_count"] <= MAX_REMEDIATION_RETRIES, "RETRY_COUNT")
    for key in ("evidence_refs", "allowed_read", "forbidden_read", "allowed_actions", "forbidden_actions", "pass_criteria", "fail_criteria"):
        _string_list(task, key)
    require(isinstance(task["authority"], dict), "AUTHORITY")
    require(isinstance(task["routing_contract"], dict), "ROUTING_CONTRACT")
    rc = task["routing_contract"]
    for key in ("lab_verdict_field", "lab_head_field", "auditor_verdict_field", "auditor_head_field"):
        require(isinstance(rc.get(key), str) and FIELD_NAME.fullmatch(rc[key]) is not None, f"ROUTING_CONTRACT:{key}")


def owner_free_remediation_allowed(authority: dict[str, Any]) -> bool:
    return all(authority.get(key) is True for key in OWNER_FREE_REMEDIATION_KEYS)


def next_role_for_state(state: str) -> str:
    return {
        "NEW": "CORE",
        "CORE_WORKING": "CORE",
        "MECHANICAL_GATE": "MECHANICAL_GATE",
        "LAB_REVIEW": "LAB",
        "LAB_FIX_REQUIRED": "CORE",
        "AUDIT_REVIEW": "AUDITOR",
        "AUDIT_FIX_REQUIRED": "CORE",
        "OWNER_GATE": "OWNER",
        "DONE": "NONE",
        "FAILED_CLOSED": "OWNER",
    }[state]


def routing_envelope(task: dict[str, Any]) -> dict[str, Any]:
    validate_manifest(task)
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": task["task_id"],
        "role": next_role_for_state(task["state"]),
        "objective": task["objective"],
        "canonical_repo": task["canonical_repo"],
        "target_branch": task["target_branch"],
        "target_head": task["target_head"],
        "artifact_ref": task["artifact_ref"],
        "risk_class": task["risk_class"],
        "retry_count": task["retry_count"],
        "allowed_read": task["allowed_read"],
        "forbidden_read": task["forbidden_read"],
        "allowed_actions": task["allowed_actions"],
        "forbidden_actions": task["forbidden_actions"],
        "pass_criteria": task["pass_criteria"],
        "fail_criteria": task["fail_criteria"],
        "evidence_refs": task["evidence_refs"],
    }


def transition(task: dict[str, Any], event: str, evidence_ref: str | None = None) -> dict[str, Any]:
    validate_manifest(task)
    require(event in EVENTS, "EVENT")
    current = task["state"]
    if current in {"DONE", "FAILED_CLOSED"}:
        raise RouterError(f"TERMINAL_STATE:{current}")

    if event == "FATAL":
        target = "FAILED_CLOSED"
    elif event in {"LAB_FIX_REQUIRED", "AUDITOR_FIX_REQUIRED", "MECHANICAL_FAIL"}:
        if not owner_free_remediation_allowed(task["authority"]):
            target = "OWNER_GATE"
        elif task["retry_count"] >= MAX_REMEDIATION_RETRIES:
            target = "FAILED_CLOSED"
        else:
            target = {
                "LAB_FIX_REQUIRED": "LAB_FIX_REQUIRED",
                "AUDITOR_FIX_REQUIRED": "AUDIT_FIX_REQUIRED",
                "MECHANICAL_FAIL": "CORE_WORKING",
            }[event]
    else:
        target = BASE_TRANSITIONS.get((current, event))
        if target is None:
            raise RouterError(f"INVALID_TRANSITION:{current}:{event}")

    out = json.loads(json.dumps(task))
    out["previous_state"] = current
    out["state"] = target
    if event in {"LAB_FIX_REQUIRED", "AUDITOR_FIX_REQUIRED", "MECHANICAL_FAIL"} and target not in {"OWNER_GATE", "FAILED_CLOSED"}:
        out["retry_count"] += 1
    out["updated_at"] = utc_now()
    if evidence_ref:
        require(isinstance(evidence_ref, str) and evidence_ref, "EVIDENCE_REF")
        out["evidence_refs"].append(evidence_ref)
    out["next_role"] = next_role_for_state(target)
    out["fail_closed"] = target == "FAILED_CLOSED"
    out["next_state"] = target
    validate_manifest(out)
    return out


def _field_values(body: str, field: str) -> list[str]:
    values: list[str] = []
    prefix = field + ":"
    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("`") and line.endswith("`") and len(line) >= 2:
            line = line[1:-1].strip()
        if line.startswith(prefix):
            values.append(line[len(prefix):].strip())
    return values


def event_from_review(task: dict[str, Any], role: str, body: str) -> str:
    validate_manifest(task)
    role = role.upper()
    require(role in {"LAB", "AUDITOR"}, "ROLE")
    rc = task["routing_contract"]
    verdict_field = rc["lab_verdict_field"] if role == "LAB" else rc["auditor_verdict_field"]
    head_field = rc["lab_head_field"] if role == "LAB" else rc["auditor_head_field"]
    verdicts = _field_values(body, verdict_field)
    heads = _field_values(body, head_field)
    require(len(verdicts) == 1, f"VERDICT_FIELD_COUNT:{len(verdicts)}")
    require(len(heads) == 1, f"HEAD_FIELD_COUNT:{len(heads)}")
    require(heads[0] == task["target_head"], "REVIEWED_HEAD_MISMATCH")
    verdict = verdicts[0]
    if role == "LAB":
        mapping = {"PASS": "LAB_PASS", "FIX_REQUIRED": "LAB_FIX_REQUIRED", "MATERIAL_BLOCK": "FATAL"}
    else:
        mapping = {"PASS": "AUDITOR_PASS", "FIX_REQUIRED": "AUDITOR_FIX_REQUIRED", "MATERIAL_BLOCK": "FATAL"}
    require(verdict in mapping, f"VERDICT_VALUE:{verdict}")
    return mapping[verdict]


def new_task(
    task_id: str,
    canonical_repo: str,
    target_branch: str,
    target_head: str,
    risk_class: str,
    authority: dict[str, Any],
    *,
    objective: str,
    artifact_ref: str,
    role_owner: str,
    allowed_read: list[str],
    forbidden_read: list[str],
    allowed_actions: list[str],
    forbidden_actions: list[str],
    pass_criteria: list[str],
    fail_criteria: list[str],
    routing_contract: dict[str, str],
) -> dict[str, Any]:
    now = utc_now()
    task = {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "objective": objective,
        "canonical_repo": canonical_repo,
        "target_branch": target_branch,
        "target_head": target_head,
        "artifact_ref": artifact_ref,
        "role_owner": role_owner,
        "state": "NEW",
        "previous_state": None,
        "retry_count": 0,
        "risk_class": risk_class,
        "created_at": now,
        "updated_at": now,
        "evidence_refs": [],
        "allowed_read": allowed_read,
        "forbidden_read": forbidden_read,
        "allowed_actions": allowed_actions,
        "forbidden_actions": forbidden_actions,
        "pass_criteria": pass_criteria,
        "fail_criteria": fail_criteria,
        "authority": authority,
        "routing_contract": routing_contract,
        "next_role": "CORE",
        "fail_closed": False,
        "next_state": "NEW",
    }
    validate_manifest(task)
    return task


def atomic_write_json(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = pathlib.Path(tmp_name)
    try:
        with os.fdopen(fd, "wb", closefd=True) as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def read_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    require(isinstance(value, dict), "TASK_OBJECT")
    return value


def cmd_transition(args: argparse.Namespace) -> int:
    task = read_json(pathlib.Path(args.task))
    out = transition(task, args.event, args.evidence)
    if args.write:
        atomic_write_json(pathlib.Path(args.task), out)
    print(json.dumps(out, sort_keys=True, separators=(",", ":")))
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    task = read_json(pathlib.Path(args.task))
    body = pathlib.Path(args.review).read_text()
    event = event_from_review(task, args.role, body)
    out = transition(task, event, args.evidence)
    if args.write:
        atomic_write_json(pathlib.Path(args.task), out)
    print(json.dumps({"event": event, "task": out, "route": routing_envelope(out)}, sort_keys=True, separators=(",", ":")))
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("transition")
    t.add_argument("--task", required=True)
    t.add_argument("--event", required=True, choices=sorted(EVENTS))
    t.add_argument("--evidence")
    t.add_argument("--write", action="store_true")
    t.set_defaults(func=cmd_transition)
    r = sub.add_parser("review")
    r.add_argument("--task", required=True)
    r.add_argument("--role", required=True, choices=("LAB", "AUDITOR"))
    r.add_argument("--review", required=True)
    r.add_argument("--evidence")
    r.add_argument("--write", action="store_true")
    r.set_defaults(func=cmd_review)
    args = p.parse_args()
    try:
        return args.func(args)
    except RouterError as exc:
        print(f"MULTIVERSE_ROUTER_DENIED:{exc}", file=os.sys.stderr)
        return 92


if __name__ == "__main__":
    raise SystemExit(main())
