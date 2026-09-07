from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

from automation.review_dispatcher_v1.github_app import (
    GitHubAppError,
    github_json,
    installation_token,
)
from automation.review_dispatcher_v1.model import (
    AUDITOR_APP_ID,
    AUDITOR_APP_SLUG,
    AUDITOR_LOGIN,
    LAB_APP_ID,
    LAB_APP_SLUG,
    LAB_LOGIN,
    RESULT_SCHEMA,
    T2_SCHEMA,
    ReviewContractError,
    fetch_all_pages,
    github_branch_commit_sha,
    github_comment_id,
    github_commit_tree_sha,
    github_full_pr_binding,
    issue_comment_owner_trusted,
    lane_result_comment_trusted,
    latest_exact_current_owner_request,
    required_positive_int,
    result_marker,
    sha256_json,
    t2_marker,
    validate_request,
)

T2_RECEIPT_SCHEMA = "MULTIVERSE_FIXED_T2_PUBLISH_RECEIPT_v1"


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ReviewContractError(code)


def public_github(url: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "multiverse-fixed-t2-v1",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def json_block(body: str) -> dict[str, Any]:
    fence = r"\x60\x60\x60"
    match = re.search(
        fence + r"json\s*(\{.*?\})\s*" + fence,
        body,
        re.S,
    )
    require(match is not None, "JSON_BLOCK_MISSING")
    return json.loads(match.group(1))


def publish_t2(
    job: dict[str, Any],
    artifact: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    request = job["request"]
    validate_request(request)

    require(job["lane"] == "AUDITOR", "T2_REQUIRES_AUDITOR_LANE")
    require(
        job.get("request_sha256") == sha256_json(request),
        "AUDITOR_REQUEST_SHA256_MISMATCH",
    )
    require(
        artifact.get("request_sha256") == job["request_sha256"],
        "AUDITOR_ARTIFACT_REQUEST_SHA256",
    )
    require(artifact.get("verdict") == "PASS", "AUDITOR_NOT_PASS")
    require(artifact.get("findings") == [], "AUDITOR_FINDINGS")
    require(
        artifact.get("reviewed_head") == job["head"],
        "AUDITOR_HEAD_MISMATCH",
    )
    require(
        artifact.get("reviewed_tree") == job["tree"],
        "AUDITOR_TREE_MISMATCH",
    )
    require(
        artifact.get("reviewed_main") == job["main"],
        "AUDITOR_MAIN_MISMATCH",
    )

    auditor_comment_id = required_positive_int(
        receipt.get("published_comment_id"),
        "AUDITOR_RECEIPT_COMMENT_ID",
    )
    require(
        receipt.get("published_by") == AUDITOR_LOGIN,
        "AUDITOR_RECEIPT_PRODUCER",
    )
    require(
        receipt.get("github_app_id") == AUDITOR_APP_ID,
        "AUDITOR_RECEIPT_APP",
    )
    require(
        receipt.get("request_sha256") == job["request_sha256"],
        "AUDITOR_RECEIPT_REQUEST_SHA256",
    )

    repo = job["repo"]
    pr_number = job["pr"]

    pr_raw = public_github(
        f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    )
    main_raw = public_github(
        f"https://api.github.com/repos/{repo}/branches/main"
    )
    commit_raw = public_github(
        f"https://api.github.com/repos/{repo}/commits/{job['head']}"
    )

    pr = github_full_pr_binding(
        pr_raw,
        expected_number=pr_number,
        expected_head=job["head"],
    )
    tree_sha = github_commit_tree_sha(commit_raw)
    main_sha = github_branch_commit_sha(main_raw)

    require(pr["base_sha"] == job["base"], "BASE_DRIFT")
    require(tree_sha == job["tree"], "TREE_DRIFT")
    require(main_sha == job["main"], "MAIN_DRIFT")
    require(
        job.get("dispatcher_ref") == main_sha,
        "DISPATCHER_REF_DRIFT",
    )

    auditor_comment = required_object(
        public_github(
            (
                f"https://api.github.com/repos/{repo}/issues/comments/"
                f"{auditor_comment_id}"
            )
        ),
        "AUDITOR_COMMENT_RESPONSE_OBJECT",
    )
    require(
        (auditor_comment.get("user") or {}).get("login")
        == AUDITOR_LOGIN,
        "AUDITOR_COMMENT_LOGIN",
    )
    outer_app = (
        (auditor_comment.get("performed_via_github_app") or {}).get("slug")
    )
    require(
        outer_app == AUDITOR_APP_SLUG,
        "AUDITOR_COMMENT_APP",
    )

    published_artifact = json_block(
        auditor_comment.get("body") or ""
    )
    require(
        published_artifact == artifact,
        "PUBLISHED_AUDITOR_ARTIFACT_DRIFT",
    )

    upstream = request["upstream"]
    lab_comment_id = upstream["lab_pass_comment"]
    t1_comment_id = upstream["t1_comment"]

    comments = fetch_all_pages(
        public_github,
        f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments",
    )
    latest_lab_request_id, latest_lab_request, _ = (
        latest_exact_current_owner_request(
            comments,
            repo=repo,
            pr=pr_number,
            lane="LAB",
            head=job["head"],
            tree=job["tree"],
            base=job["base"],
            main=job["main"],
        )
    )
    require(
        latest_lab_request["proof_ceiling"] == request["proof_ceiling"],
        "LATEST_LAB_PROOF_CEILING_MISMATCH",
    )
    require(
        latest_lab_request["execution_state"] == request["execution_state"],
        "LATEST_LAB_EXECUTION_STATE_MISMATCH",
    )
    latest_lab_request_sha256 = sha256_json(latest_lab_request)
    require(
        request["upstream"]["lab_request_sha256"]
        == latest_lab_request_sha256,
        "LATEST_LAB_REQUEST_SHA256_MISMATCH",
    )

    lab_comment = required_object(
        public_github(
            (
                f"https://api.github.com/repos/{repo}/issues/comments/"
                f"{lab_comment_id}"
            )
        ),
        "LAB_COMMENT_RESPONSE_OBJECT",
    )
    require(
        (lab_comment.get("user") or {}).get("login") == LAB_LOGIN,
        "LAB_UPSTREAM_LOGIN",
    )
    lab_app = (
        (lab_comment.get("performed_via_github_app") or {}).get("slug")
    )
    require(lab_app == LAB_APP_SLUG, "LAB_UPSTREAM_APP")

    lab_artifact = json_block(lab_comment.get("body") or "")
    require(
        lab_artifact.get("schema_version")
        == "MULTIVERSE_FIXED_REVIEW_ARTIFACT_v1",
        "LAB_UPSTREAM_SCHEMA",
    )
    require(
        lab_artifact.get("result_schema") == RESULT_SCHEMA,
        "LAB_UPSTREAM_RESULT_SCHEMA",
    )
    require(lab_artifact.get("lane") == "LAB", "LAB_UPSTREAM_LANE")
    require(
        lab_artifact.get("request_id") == latest_lab_request["request_id"],
        "LAB_UPSTREAM_REQUEST_ID",
    )
    require(
        lab_artifact.get("request_comment") == latest_lab_request_id,
        "LAB_UPSTREAM_REQUEST_COMMENT",
    )
    require(
        lab_artifact.get("request_sha256") == latest_lab_request_sha256,
        "LAB_UPSTREAM_REQUEST_SHA256",
    )
    require(
        lab_artifact.get("mode") == latest_lab_request["mode"],
        "LAB_UPSTREAM_MODE",
    )
    require(lab_artifact.get("verdict") == "PASS", "LAB_UPSTREAM_VERDICT")
    require(lab_artifact.get("findings") == [], "LAB_UPSTREAM_FINDINGS")
    require(
        lab_artifact.get("reviewed_repo") == repo,
        "LAB_UPSTREAM_REPO",
    )
    require(
        lab_artifact.get("reviewed_pr") == pr_number,
        "LAB_UPSTREAM_PR",
    )
    require(
        lab_artifact.get("reviewed_head") == job["head"],
        "LAB_UPSTREAM_HEAD",
    )
    require(
        lab_artifact.get("reviewed_tree") == job["tree"],
        "LAB_UPSTREAM_TREE",
    )
    require(
        lab_artifact.get("reviewed_base") == job["base"],
        "LAB_UPSTREAM_BASE",
    )
    require(
        lab_artifact.get("reviewed_main") == job["main"],
        "LAB_UPSTREAM_MAIN",
    )
    require(
        lab_artifact.get("proof_ceiling") == request["proof_ceiling"],
        "LAB_UPSTREAM_PROOF_CEILING",
    )
    require(
        lab_artifact.get("execution_state") == request["execution_state"],
        "LAB_UPSTREAM_EXECUTION_STATE",
    )
    lab_producer = lab_artifact.get("producer") or {}
    require(
        lab_producer.get("github_login") == LAB_LOGIN,
        "LAB_UPSTREAM_ARTIFACT_LOGIN",
    )
    require(
        lab_producer.get("github_app_id") == LAB_APP_ID,
        "LAB_UPSTREAM_ARTIFACT_APP",
    )
    lab_marker = result_marker(
        latest_lab_request["request_id"],
        job["head"],
        latest_lab_request_id,
        latest_lab_request_sha256,
    )
    authentic_lab_results = [
        github_comment_id(item, "LAB_RESULT_COMMENT_ID")
        for item in comments
        if lab_marker in (item.get("body") or "")
        and lane_result_comment_trusted(item, "LAB")
    ]
    require(
        authentic_lab_results == [lab_comment_id],
        "LAB_UPSTREAM_NOT_SINGLE_LATEST_RESULT",
    )

    t1_comment = required_object(
        public_github(
            (
                f"https://api.github.com/repos/{repo}/issues/comments/"
                f"{t1_comment_id}"
            )
        ),
        "T1_COMMENT_RESPONSE_OBJECT",
    )
    require(
        issue_comment_owner_trusted(t1_comment, repo),
        "T1_PRODUCER_NOT_OWNER",
    )
    t1_body = t1_comment.get("body") or ""
    require(
        str(lab_comment_id) in t1_body,
        "T1_LAB_BINDING_MISSING",
    )
    require(
        latest_lab_request_sha256 in t1_body,
        "T1_LAB_REQUEST_SHA256_MISSING",
    )
    require(
        job["head"] in t1_body,
        "T1_HEAD_BINDING_MISSING",
    )
    require(
        job["tree"] in t1_body,
        "T1_TREE_BINDING_MISSING",
    )
    require(
        job["base"] in t1_body,
        "T1_BASE_BINDING_MISSING",
    )
    require(
        job["main"] in t1_body,
        "T1_MAIN_BINDING_MISSING",
    )
    require("PASS" in t1_body, "T1_PASS_MARKER_MISSING")

    marker = t2_marker(
        job["request_id"],
        job["head"],
        auditor_comment_id,
        job["request_sha256"],
    )
    for comment in comments:
        if (
            marker in (comment.get("body") or "")
            and lane_result_comment_trusted(comment, "AUDITOR")
        ):
            raise ReviewContractError(
                "CURRENT_T2_ALREADY_EXISTS:"
                + str(
                    github_comment_id(
                        comment,
                        "T2_COMMENT_ID",
                    )
                )
            )

    private_key = os.environ.get(
        "MULTIVERSE_INDEPENDENT_AUDITOR_PRIVATE_KEY"
    )
    require(bool(private_key), "AUDITOR_PRIVATE_KEY_MISSING")
    token = installation_token(
        repo=repo,
        app_id=AUDITOR_APP_ID,
        private_key=private_key,
    )

    t2_artifact = {
        "schema_version": T2_SCHEMA,
        "gate": "T2",
        "verdict": "PASS",
        "request_id": job["request_id"],
        "request_comment": job["request_comment"],
        "request_sha256": job["request_sha256"],
        "lab_request_sha256": latest_lab_request_sha256,
        "reviewed_repo": repo,
        "reviewed_pr": pr_number,
        "reviewed_head": job["head"],
        "reviewed_tree": job["tree"],
        "reviewed_base": job["base"],
        "reviewed_main": job["main"],
        "lab_pass_comment": lab_comment_id,
        "t1_comment": t1_comment_id,
        "auditor_pass_comment": auditor_comment_id,
        "auditor_producer": AUDITOR_LOGIN,
        "auditor_app_id": AUDITOR_APP_ID,
        "proof_ceiling": request["proof_ceiling"],
        "execution_state": request["execution_state"],
        "nonauthority": request["nonauthority"],
    }

    fence = chr(96) * 3
    body = "\n".join(
        [
            (
                marker
                + (os.environ.get("BUILDKITE_BUILD_ID") or "UNKNOWN")
                + " -->"
            ),
            "",
            "MULTIVERSE FIXED REVIEW DISPATCHER v1 — T2 RESULT",
            "",
            fence + "json",
            json.dumps(
                t2_artifact,
                indent=2,
                sort_keys=True,
            ),
            fence,
            "",
            "FIXED_REVIEW_T2_VERDICT: PASS",
            f"REQUEST_ID: {job['request_id']}",
            f"REQUEST_SHA256: {job['request_sha256']}",
            f"LAB_REQUEST_SHA256: {latest_lab_request_sha256}",
            f"BOUND_TO_LAB_PASS: {lab_comment_id}",
            f"BOUND_TO_T1: {t1_comment_id}",
            f"BOUND_TO_AUDITOR_PASS: {auditor_comment_id}",
            f"T2_REVIEWED_HEAD: {job['head']}",
            f"T2_REVIEWED_TREE: {job['tree']}",
            f"T2_REVIEWED_MAIN: {job['main']}",
            f"PROOF_CEILING: {request['proof_ceiling']}",
            f"EXECUTION_STATE: {request['execution_state']}",
            "",
            (
                "T2 grants no authority beyond the request's explicit "
                "nonauthority boundary."
            ),
        ]
    )

    result = github_json(
        "POST",
        (
            f"https://api.github.com/repos/{repo}/issues/"
            f"{pr_number}/comments"
        ),
        token,
        {"body": body},
    )

    return {
        "schema": T2_RECEIPT_SCHEMA,
        "request_id": job["request_id"],
        "request_sha256": job["request_sha256"],
        "auditor_comment_id": auditor_comment_id,
        "t2_comment_id": github_comment_id(
            result,
            "PUBLISHED_T2_COMMENT_ID",
        ),
        "reviewed_head": job["head"],
        "reviewed_tree": job["tree"],
        "reviewed_main": job["main"],
        "verdict": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", default="review_job.json")
    parser.add_argument("--artifact", default="review_artifact.json")
    parser.add_argument("--receipt", default="review_publish_receipt.json")
    parser.add_argument("--output", default="t2_publish_receipt.json")
    args = parser.parse_args()

    job = json.loads(Path(args.job).read_text())
    artifact = json.loads(Path(args.artifact).read_text())
    receipt = json.loads(Path(args.receipt).read_text())

    result = publish_t2(job, artifact, receipt)
    Path(args.output).write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ReviewContractError, GitHubAppError) as exc:
        print(f"T2_FIX_REQUIRED:{exc}")
        raise SystemExit(1)
