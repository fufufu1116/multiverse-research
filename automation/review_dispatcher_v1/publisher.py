from __future__ import annotations

import argparse
import json
import os
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
    AUDITOR_LOGIN,
    LAB_APP_ID,
    LAB_LOGIN,
    ReviewContractError,
    extract_request_from_comment,
    fetch_all_pages,
    issue_comment_owner_trusted,
    lane_result_comment_trusted,
    result_marker,
    validate_request,
)

RECEIPT_SCHEMA = "MULTIVERSE_FIXED_REVIEW_PUBLISH_RECEIPT_v1"


def public_github(url: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "multiverse-fixed-review-publisher-v1",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ReviewContractError(code)


def _lane_identity(lane: str) -> tuple[str, int, str]:
    if lane == "LAB":
        return (
            LAB_LOGIN,
            LAB_APP_ID,
            "MULTIVERSE_INDEPENDENT_LAB_PRIVATE_KEY",
        )
    if lane == "AUDITOR":
        return (
            AUDITOR_LOGIN,
            AUDITOR_APP_ID,
            "MULTIVERSE_INDEPENDENT_AUDITOR_PRIVATE_KEY",
        )
    raise ReviewContractError("LANE_UNKNOWN")


def _fresh_verify(job: dict[str, Any]) -> list[dict[str, Any]]:
    repo = job["repo"]
    pr_number = job["pr"]

    pr = public_github(
        f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    )
    main = public_github(
        f"https://api.github.com/repos/{repo}/branches/main"
    )
    commit = public_github(
        f"https://api.github.com/repos/{repo}/commits/{job['head']}"
    )
    request_comment = public_github(
        (
            f"https://api.github.com/repos/{repo}/issues/comments/"
            f"{job['request_comment']}"
        )
    )

    require(pr["state"] == "open", "PR_NOT_OPEN")
    require(pr["draft"] is True, "PR_NOT_DRAFT")
    require(pr["merged"] is False, "PR_MERGED")
    require(pr["head"]["sha"] == job["head"], "HEAD_DRIFT")
    require(pr["base"]["sha"] == job["base"], "BASE_DRIFT")
    require(
        commit["commit"]["tree"]["sha"] == job["tree"],
        "TREE_DRIFT",
    )
    require(main["commit"]["sha"] == job["main"], "MAIN_DRIFT")

    parsed = extract_request_from_comment(
        request_comment.get("body") or ""
    )
    require(parsed is not None, "REQUEST_COMMENT_NOT_PARSEABLE")
    validate_request(parsed)
    require(parsed == job["request"], "REQUEST_COMMENT_DRIFT")
    require(
        issue_comment_owner_trusted(request_comment, repo),
        "REQUEST_COMMENT_PRODUCER_NOT_OWNER",
    )

    comments = fetch_all_pages(
        public_github,
        f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments",
    )
    return comments


def publish(
    job: dict[str, Any],
    artifact: dict[str, Any],
) -> dict[str, Any]:
    lane = job["lane"]
    expected_login, app_id, secret_name = _lane_identity(lane)

    require(
        artifact.get("schema_version")
        == "MULTIVERSE_FIXED_REVIEW_ARTIFACT_v1",
        "ARTIFACT_SCHEMA",
    )
    require(artifact.get("lane") == lane, "ARTIFACT_LANE")
    require(
        artifact.get("request_id") == job["request_id"],
        "ARTIFACT_REQUEST_ID",
    )
    require(
        artifact.get("request_comment") == job["request_comment"],
        "ARTIFACT_REQUEST_COMMENT",
    )
    require(
        artifact.get("reviewed_repo") == job["repo"],
        "ARTIFACT_REPO",
    )
    require(
        artifact.get("reviewed_pr") == job["pr"],
        "ARTIFACT_PR",
    )
    require(
        artifact.get("reviewed_head") == job["head"],
        "ARTIFACT_HEAD",
    )
    require(
        artifact.get("reviewed_tree") == job["tree"],
        "ARTIFACT_TREE",
    )
    require(
        artifact.get("reviewed_base") == job["base"],
        "ARTIFACT_BASE",
    )
    require(
        artifact.get("reviewed_main") == job["main"],
        "ARTIFACT_MAIN",
    )
    require(artifact.get("verdict") == "PASS", "ARTIFACT_NOT_PASS")
    require(artifact.get("findings") == [], "ARTIFACT_FINDINGS")

    producer = artifact.get("producer") or {}
    require(
        producer.get("github_login") == expected_login,
        "ARTIFACT_PRODUCER_LOGIN",
    )
    require(
        producer.get("github_app_id") == app_id,
        "ARTIFACT_PRODUCER_APP_ID",
    )

    comments = _fresh_verify(job)
    marker = result_marker(
        job["request_id"],
        job["head"],
        job["request_comment"],
    )
    for comment in comments:
        if (
            marker in (comment.get("body") or "")
            and lane_result_comment_trusted(comment, lane)
        ):
            raise ReviewContractError(
                f"CURRENT_REQUEST_RESULT_ALREADY_EXISTS:{comment['id']}"
            )

    private_key = os.environ.get(secret_name)
    require(bool(private_key), f"{secret_name}_MISSING")

    token = installation_token(
        repo=job["repo"],
        app_id=app_id,
        private_key=private_key,
    )

    fence = chr(96) * 3
    body = "\n".join(
        [
            (
                marker
                + (os.environ.get("BUILDKITE_BUILD_ID") or "UNKNOWN")
                + " -->"
            ),
            "",
            (
                "MULTIVERSE FIXED REVIEW DISPATCHER v1 — "
                f"{lane} RESULT"
            ),
            "",
            fence + "json",
            json.dumps(
                artifact,
                indent=2,
                sort_keys=True,
            ),
            fence,
            "",
            (
                "FIXED_REVIEW_DISPATCH_VERDICT: "
                + artifact["verdict"]
            ),
            f"REQUEST_ID: {job['request_id']}",
            f"REQUEST_COMMENT: {job['request_comment']}",
            f"REVIEWED_HEAD: {job['head']}",
            f"REVIEWED_TREE: {job['tree']}",
            f"REVIEWED_BASE: {job['base']}",
            f"REVIEWED_MAIN: {job['main']}",
            f"PROOF_CEILING: {job['request']['proof_ceiling']}",
            f"EXECUTION_STATE: {job['request']['execution_state']}",
            "",
            (
                "This result grants no authority beyond the "
                "request's explicit nonauthority boundary."
            ),
        ]
    )

    result = github_json(
        "POST",
        (
            f"https://api.github.com/repos/{job['repo']}/issues/"
            f"{job['pr']}/comments"
        ),
        token,
        {"body": body},
    )

    return {
        "schema": RECEIPT_SCHEMA,
        "lane": lane,
        "request_id": job["request_id"],
        "request_comment": job["request_comment"],
        "reviewed_head": job["head"],
        "reviewed_tree": job["tree"],
        "reviewed_main": job["main"],
        "published_comment_id": result["id"],
        "published_by": expected_login,
        "github_app_id": app_id,
        "verdict": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", default="review_job.json")
    parser.add_argument("--artifact", default="review_artifact.json")
    parser.add_argument("--receipt", default="review_publish_receipt.json")
    args = parser.parse_args()

    job = json.loads(Path(args.job).read_text())
    artifact = json.loads(Path(args.artifact).read_text())
    receipt = publish(job, artifact)

    Path(args.receipt).write_text(
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ReviewContractError, GitHubAppError) as exc:
        print(f"PUBLISH_FIX_REQUIRED:{exc}")
        raise SystemExit(1)
