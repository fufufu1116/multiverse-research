#!/usr/bin/env python3
"""Governed R1 Stage1 repository-ruleset provision-or-verify operator.

DRAFT / preactivation candidate. Default mode is read-only dry-run. Actual
mutation requires --apply and a locally authenticated GitHub CLI credential
with repository Administration:write. No credential or secret value is read,
printed, accepted as an argument, or written by this tool.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import Any, Mapping

REPO = "fufufu1116/multiverse-research"
EXPECTED_MAIN = "66e342fced4bfbd3b1124a49e185b175db359e86"
PHASE_B_PR = 68
PHASE_B_HEAD = "ccdc66c3c877c4a9fb598cf5da7ecb3ff9208b26"
PHASE_B_LAB_COMMENT = 5378314532
PHASE_B_AUDITOR_REVIEW = 4999306904
RUNTIME_BRANCH = "runtime/r1-source-audit-stage1-v1"
AUTHORITY_PATH = "governance/MULTIVERSE_R1_STAGE1_PRODUCTION_AUTHORITY_ROOT_20260822_v1.json"
AUTHORITY_BLOB = "fed643f0ec5e2146dc0ea1031371fd1caf121fc6"
RUNTIME_CAS_PATH = "tools/multiverse_r1_stage1_github_runtime_cas_v1.py"
RUNTIME_CAS_BLOB = "57164a9c6a42a89af9ea45366bc93bfed88b0244"
LOADER_PATH = "tools/multiverse_r1_stage1_verified_activation_receipt_loader_v1.py"
LOADER_BLOB = "b1ae9e525f68db7bf5a321c8e90000497980e67e"
RULESET_NAME = "multiverse-r1-stage1-journal-activation-protection-v1"
JOURNAL_INCLUDE = "refs/tags/multiverse-r1-stage1-ledger-v1-*"
ACTIVATION_INCLUDE = "refs/tags/multiverse-r1-stage1-activation-v1"
API_VERSION = "2022-11-28"

_CANONICAL_BLOBS = {
    "authority": (AUTHORITY_PATH, AUTHORITY_BLOB),
    "runtime_cas": (RUNTIME_CAS_PATH, RUNTIME_CAS_BLOB),
    "loader": (LOADER_PATH, LOADER_BLOB),
}


class Denied(RuntimeError):
    pass


def _deny(code: str) -> None:
    raise Denied(code)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _validate_transport() -> None:
    if shutil.which("gh") is None:
        _deny("RULESET_ADMIN_GH_CLI_REQUIRED")
    if os.environ.get("GH_HOST") not in (None, "", "github.com"):
        _deny("RULESET_ADMIN_GH_HOST_OVERRIDE_PROHIBITED")
    for key in (
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
        "http_proxy", "https_proxy", "all_proxy",
        "SSL_CERT_FILE", "SSL_CERT_DIR",
    ):
        if os.environ.get(key):
            _deny("RULESET_ADMIN_PROXY_OR_CUSTOM_CA_PROHIBITED")
    proc = subprocess.run(
        ["gh", "config", "list", "--host", "github.com"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy(),
    )
    if proc.returncode != 0:
        _deny("RULESET_ADMIN_GH_CONFIG_QUERY_FAILED")
    sockets = [
        row.split("=", 1)[1]
        for row in proc.stdout.splitlines()
        if row.startswith("http_unix_socket=") and "=" in row
    ]
    if len(sockets) != 1 or sockets[0].strip():
        _deny("RULESET_ADMIN_GH_HTTP_UNIX_SOCKET_PROHIBITED_OR_AMBIGUOUS")


def _build_get_endpoint(resource: str, *, value: int | str | None = None, page: int | None = None) -> str:
    """Build only allowlisted read-only GitHub API endpoints."""
    if resource == "main":
        if value is not None or page is not None:
            _deny("RULESET_ADMIN_GET_ARGUMENTS_INVALID")
        return f"/repos/{REPO}/branches/main"
    if resource == "phase_b_pr":
        if value is not None or page is not None:
            _deny("RULESET_ADMIN_GET_ARGUMENTS_INVALID")
        return f"/repos/{REPO}/pulls/{PHASE_B_PR}"
    if resource == "phase_b_lab":
        if value is not None or page is not None:
            _deny("RULESET_ADMIN_GET_ARGUMENTS_INVALID")
        return f"/repos/{REPO}/issues/comments/{PHASE_B_LAB_COMMENT}"
    if resource == "phase_b_auditor":
        if value is not None or page is not None:
            _deny("RULESET_ADMIN_GET_ARGUMENTS_INVALID")
        return f"/repos/{REPO}/pulls/{PHASE_B_PR}/reviews/{PHASE_B_AUDITOR_REVIEW}"
    if resource == "canonical_blob":
        if not isinstance(value, str) or value not in _CANONICAL_BLOBS or page is not None:
            _deny("RULESET_ADMIN_CANONICAL_BLOB_SELECTOR_INVALID")
        path = _CANONICAL_BLOBS[value][0]
        return f"/repos/{REPO}/contents/{path}?ref={EXPECTED_MAIN}"
    if resource == "branches_page":
        if value is not None or not isinstance(page, int) or isinstance(page, bool) or not (1 <= page <= 100):
            _deny("RULESET_ADMIN_BRANCH_PAGE_INVALID")
        return f"/repos/{REPO}/branches?per_page=100&page={page}"
    if resource == "rulesets_page":
        if value is not None or not isinstance(page, int) or isinstance(page, bool) or not (1 <= page <= 100):
            _deny("RULESET_ADMIN_RULESET_PAGE_INVALID")
        return f"/repos/{REPO}/rulesets?includes_parents=false&per_page=100&page={page}"
    if resource == "ruleset_detail":
        if page is not None or not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            _deny("RULESET_ADMIN_RULESET_ID_INVALID")
        return f"/repos/{REPO}/rulesets/{value}?includes_parents=false"
    _deny("RULESET_ADMIN_GET_RESOURCE_NOT_ALLOWLISTED")
    raise AssertionError("unreachable")


def _gh_get_json(resource: str, *, value: int | str | None = None, page: int | None = None) -> Any:
    """Read-only GitHub API through the closed endpoint builder."""
    endpoint = _build_get_endpoint(resource, value=value, page=page)
    _validate_transport()
    cmd = [
        "gh", "api", "--hostname", "github.com",
        "-H", "Accept: application/vnd.github+json",
        "-H", f"X-GitHub-Api-Version: {API_VERSION}",
        endpoint,
    ]
    proc = subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy(),
    )
    if proc.returncode != 0:
        _deny("RULESET_ADMIN_GITHUB_API_GET_FAILED:" + proc.stderr.strip()[:240])
    try:
        return json.loads(proc.stdout)
    except Exception as exc:
        raise Denied("RULESET_ADMIN_GITHUB_API_JSON_INVALID") from exc


def _fresh_main() -> str:
    payload = _gh_get_json("main")
    sha = payload.get("commit", {}).get("sha") if isinstance(payload, dict) else None
    if sha != EXPECTED_MAIN:
        _deny("RULESET_ADMIN_CANONICAL_MAIN_DRIFT")
    return sha


def _verify_pr_and_reviews() -> None:
    pr = _gh_get_json("phase_b_pr")
    if not isinstance(pr, dict):
        _deny("RULESET_ADMIN_PHASE_B_PR_INVALID")
    if pr.get("state") != "open" or pr.get("draft") is not True or pr.get("merged_at") is not None:
        _deny("RULESET_ADMIN_PHASE_B_PR_STATE_DRIFT")
    if pr.get("head", {}).get("sha") != PHASE_B_HEAD:
        _deny("RULESET_ADMIN_PHASE_B_HEAD_DRIFT")
    if pr.get("base", {}).get("ref") != "main" or pr.get("base", {}).get("sha") != EXPECTED_MAIN:
        _deny("RULESET_ADMIN_PHASE_B_BASE_DRIFT")

    lab = _gh_get_json("phase_b_lab")
    body = lab.get("body") if isinstance(lab, dict) else None
    if not isinstance(body, str) or (
        f"LAB_PHASE_B_REVIEWED_HEAD: {PHASE_B_HEAD}" not in body
        or "LAB_PHASE_B_RULESET_SPEC_VERDICT: PASS" not in body
    ):
        _deny("RULESET_ADMIN_PHASE_B_LAB_PASS_MISSING")

    auditor = _gh_get_json("phase_b_auditor")
    body = auditor.get("body") if isinstance(auditor, dict) else None
    if not isinstance(auditor, dict) or auditor.get("commit_id") != PHASE_B_HEAD or not isinstance(body, str) or (
        f"AUDITOR_PHASE_B_REVIEWED_HEAD: {PHASE_B_HEAD}" not in body
        or "AUDITOR_PHASE_B_RULESET_SPEC_VERDICT: PASS" not in body
        or "CAN_EXECUTE_GOVERNED_ACTUAL_RULESET_PROVISIONING_AFTER_THIS_VERDICT_IF_APPROVED_ADMIN_CHANNEL_EXISTS: YES" not in body
    ):
        _deny("RULESET_ADMIN_PHASE_B_AUDITOR_PASS_MISSING")


def _verify_canonical_blob(selector: str) -> None:
    expected = _CANONICAL_BLOBS.get(selector)
    if expected is None:
        _deny("RULESET_ADMIN_CANONICAL_BLOB_SELECTOR_INVALID")
    path, expected_blob = expected
    payload = _gh_get_json("canonical_blob", value=selector)
    if not isinstance(payload, dict) or payload.get("type") != "file" or payload.get("sha") != expected_blob:
        _deny("RULESET_ADMIN_CANONICAL_BLOB_DRIFT:" + path)


def _verify_runtime_branch_absent() -> None:
    page = 1
    while True:
        rows = _gh_get_json("branches_page", page=page)
        if not isinstance(rows, list):
            _deny("RULESET_ADMIN_BRANCH_LIST_INVALID")
        if any(isinstance(row, dict) and row.get("name") == RUNTIME_BRANCH for row in rows):
            _deny("RULESET_ADMIN_RUNTIME_BRANCH_ALREADY_EXISTS")
        if len(rows) < 100:
            break
        page += 1
        if page > 100:
            _deny("RULESET_ADMIN_BRANCH_LIST_UNBOUNDED")


def _preconditions() -> None:
    _fresh_main()
    _verify_pr_and_reviews()
    _verify_canonical_blob("authority")
    _verify_canonical_blob("runtime_cas")
    _verify_canonical_blob("loader")
    _verify_runtime_branch_absent()
    _fresh_main()


def _strict_ruleset_detail(detail: Mapping[str, Any]) -> bool:
    if detail.get("name") != RULESET_NAME:
        return False
    if detail.get("target") != "tag" or detail.get("enforcement") != "active":
        return False
    if detail.get("bypass_actors") != []:
        return False
    if detail.get("source_type") not in (None, "Repository"):
        return False
    if detail.get("source") not in (None, REPO):
        return False
    conditions = detail.get("conditions")
    if not isinstance(conditions, dict) or set(conditions) != {"ref_name"}:
        return False
    ref_name = conditions.get("ref_name")
    if not isinstance(ref_name, dict) or set(ref_name) != {"include", "exclude"}:
        return False
    includes = ref_name.get("include")
    excludes = ref_name.get("exclude")
    if not isinstance(includes, list) or len(includes) != 2 or set(includes) != {JOURNAL_INCLUDE, ACTIVATION_INCLUDE}:
        return False
    if excludes != []:
        return False
    rules = detail.get("rules")
    if not isinstance(rules, list) or len(rules) != 3:
        return False
    types = []
    for rule in rules:
        if not isinstance(rule, dict) or rule.get("type") not in {"deletion", "update", "non_fast_forward"}:
            return False
        extras = set(rule) - {"type"}
        if extras and any(rule.get(key) not in (None, {}, False) for key in extras):
            return False
        types.append(rule["type"])
    return set(types) == {"deletion", "update", "non_fast_forward"}


def _repository_ruleset_details() -> list[dict]:
    out: list[dict] = []
    page = 1
    while True:
        rows = _gh_get_json("rulesets_page", page=page)
        if not isinstance(rows, list):
            _deny("RULESET_ADMIN_RULESET_LIST_INVALID")
        for row in rows:
            rid = row.get("id") if isinstance(row, dict) else None
            if not isinstance(rid, int) or isinstance(rid, bool) or rid <= 0:
                _deny("RULESET_ADMIN_RULESET_ID_INVALID")
            detail = _gh_get_json("ruleset_detail", value=rid)
            if not isinstance(detail, dict):
                _deny("RULESET_ADMIN_RULESET_DETAIL_INVALID")
            out.append(detail)
        if len(rows) < 100:
            break
        page += 1
        if page > 100:
            _deny("RULESET_ADMIN_RULESET_LIST_UNBOUNDED")
    return out


def _classify_existing(details: list[dict]) -> tuple[str, dict | None]:
    # Evaluate the full ruleset set before reuse. The exact reviewed ruleset is
    # reusable only when it is the sole repository-level tag ruleset.
    exact = [d for d in details if _strict_ruleset_detail(d)]
    if len(exact) > 1:
        _deny("RULESET_ADMIN_DUPLICATE_EXACT_RULESETS_AMBIGUOUS")

    same_name_noncompliant = [
        d for d in details
        if d.get("name") == RULESET_NAME and not _strict_ruleset_detail(d)
    ]
    if same_name_noncompliant:
        _deny("RULESET_ADMIN_SAME_NAME_NONCOMPLIANT_RULESET")

    tag_rulesets = [d for d in details if d.get("target") == "tag"]
    if len(exact) == 1:
        if len(tag_rulesets) != 1 or tag_rulesets[0] is not exact[0]:
            _deny("RULESET_ADMIN_OTHER_TAG_RULESET_REQUIRES_REREVIEW")
        return "EXISTING_EXACT", exact[0]

    if tag_rulesets:
        _deny("RULESET_ADMIN_OTHER_TAG_RULESET_REQUIRES_REREVIEW")
    return "ABSENT_UNAMBIGUOUS", None


def _assert_mutation_bindings_untampered() -> None:
    """Reject mutation-bound identity drift before any transport is possible."""
    expected_canonical_blobs = {
        "authority": (
            "governance/MULTIVERSE_R1_STAGE1_PRODUCTION_AUTHORITY_ROOT_20260822_v1.json",
            "fed643f0ec5e2146dc0ea1031371fd1caf121fc6",
        ),
        "runtime_cas": (
            "tools/multiverse_r1_stage1_github_runtime_cas_v1.py",
            "57164a9c6a42a89af9ea45366bc93bfed88b0244",
        ),
        "loader": (
            "tools/multiverse_r1_stage1_verified_activation_receipt_loader_v1.py",
            "b1ae9e525f68db7bf5a321c8e90000497980e67e",
        ),
    }
    if (
        REPO != "fufufu1116/multiverse-research"
        or EXPECTED_MAIN != "66e342fced4bfbd3b1124a49e185b175db359e86"
        or PHASE_B_PR != 68
        or PHASE_B_HEAD != "ccdc66c3c877c4a9fb598cf5da7ecb3ff9208b26"
        or PHASE_B_LAB_COMMENT != 5378314532
        or PHASE_B_AUDITOR_REVIEW != 4999306904
        or RUNTIME_BRANCH != "runtime/r1-source-audit-stage1-v1"
        or RULESET_NAME != "multiverse-r1-stage1-journal-activation-protection-v1"
        or JOURNAL_INCLUDE != "refs/tags/multiverse-r1-stage1-ledger-v1-*"
        or ACTIVATION_INCLUDE != "refs/tags/multiverse-r1-stage1-activation-v1"
        or API_VERSION != "2022-11-28"
        or _CANONICAL_BLOBS != expected_canonical_blobs
        or "RULESET_PAYLOAD" in globals()
    ):
        _deny("RULESET_ADMIN_MUTATION_BINDING_TAMPERED")


def _post_exact_ruleset_after_fresh_barrier() -> tuple[str, dict]:
    """Perform the only production mutation, with no caller-supplied inputs.

    Mutation-bound identity is checked against inline reviewed literals before
    any transport. The POST endpoint and body are then rebuilt locally from
    literals, never from a module-level mutable payload object.
    """
    _assert_mutation_bindings_untampered()

    _preconditions()
    state, detail = _classify_existing(_repository_ruleset_details())
    if state == "EXISTING_EXACT" and detail is not None:
        return "EXISTING_EXACT_VERIFIED_AFTER_REFRESH", detail

    reviewed_payload = {
        "name": "multiverse-r1-stage1-journal-activation-protection-v1",
        "target": "tag",
        "enforcement": "active",
        "bypass_actors": [],
        "conditions": {
            "ref_name": {
                "include": [
                    "refs/tags/multiverse-r1-stage1-ledger-v1-*",
                    "refs/tags/multiverse-r1-stage1-activation-v1",
                ],
                "exclude": [],
            }
        },
        "rules": [
            {"type": "deletion"},
            {"type": "update"},
            {"type": "non_fast_forward"},
        ],
    }
    reviewed_body = json.dumps(
        reviewed_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    _validate_transport()
    cmd = [
        "gh", "api", "--hostname", "github.com",
        "-H", "Accept: application/vnd.github+json",
        "-H", "X-GitHub-Api-Version: 2022-11-28",
        "--method", "POST",
        "--input", "-",
        "/repos/fufufu1116/multiverse-research/rulesets",
    ]
    proc = subprocess.run(
        cmd,
        input=reviewed_body,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy(),
    )
    if proc.returncode != 0:
        _deny("RULESET_ADMIN_GITHUB_API_POST_FAILED:" + proc.stderr.strip()[:240])
    try:
        created = json.loads(proc.stdout)
    except Exception as exc:
        raise Denied("RULESET_ADMIN_GITHUB_API_JSON_INVALID") from exc
    if not isinstance(created, dict) or not _strict_ruleset_detail(created):
        _deny("RULESET_ADMIN_CREATED_RULESET_NOT_EXACT")

    # Fresh post-create verification detects any concurrent/unexpected tag
    # ruleset and fails closed rather than silently accepting the created one.
    _fresh_main()
    state, detail = _classify_existing(_repository_ruleset_details())
    if state != "EXISTING_EXACT" or detail is None:
        _deny("RULESET_ADMIN_POST_CREATE_FRESH_VERIFY_FAILED")
    if detail.get("id") != created.get("id") or detail.get("updated_at") != created.get("updated_at"):
        _deny("RULESET_ADMIN_POST_CREATE_ID_OR_UPDATED_AT_DRIFT")
    return "CREATED_AND_FRESH_VERIFIED", detail


def _result(status: str, detail: Mapping[str, Any] | None = None) -> dict:
    result = {
        "schema_version": "MULTIVERSE_R1_STAGE1_RULESET_ADMIN_RESULT_v1",
        "status": status,
        "canonical_main": EXPECTED_MAIN,
        "phase_b_head": PHASE_B_HEAD,
        "ruleset_name": RULESET_NAME,
        "ruleset_id": None,
        "ruleset_updated_at": None,
        "secret_material_present": False,
        "runtime_activation_performed": False,
        "runtime_branch_created": False,
        "writer_key_created": False,
        "activation_receipt_created": False,
    }
    if detail is not None:
        result["ruleset_id"] = detail.get("id")
        result["ruleset_updated_at"] = detail.get("updated_at")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="create the exact ruleset if unambiguously absent")
    args = parser.parse_args(argv)

    # On the mutating CLI path, reject binding tamper before the first Fresh
    # Read or any other operation that can invoke gh/transport.
    if args.apply:
        _assert_mutation_bindings_untampered()

    _preconditions()
    state, detail = _classify_existing(_repository_ruleset_details())
    if state == "EXISTING_EXACT":
        print(_canonical_json(_result("EXISTING_EXACT_VERIFIED", detail)))
        return 0
    if not args.apply:
        print(_canonical_json(_result("DRY_RUN_WOULD_CREATE_EXACT_RULESET")))
        return 0

    status, detail = _post_exact_ruleset_after_fresh_barrier()
    print(_canonical_json(_result(status, detail)))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Denied as exc:
        print(_canonical_json({"status": "DENIED_FAIL_CLOSED", "reason": str(exc)}), file=sys.stderr)
        raise SystemExit(2)
