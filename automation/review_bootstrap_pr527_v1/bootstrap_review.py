from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from automation.review_dispatcher_v1 import review as _review

TARGET_REPO = "fufufu1116/multiverse-research"
TARGET_PR = 527
TARGET_HEAD = "4af4521dfd5daaa47d9b816874c9a65bdf526079"
TARGET_TREE = "7bb675f8ab93a7ec123e40b14f8cb5672c38efaa"
TARGET_MAIN = "e81f3d310d07d40eb6c11fe8233dade3d72a5ad2"
TARGET_REQUEST_COMMENT = 5668811178
TARGET_REQUEST_SHA256 = "024130391042f6fcae795fe1463b3b79d5b7822dcbdffbc1bf6ec8a1bbced629"
TARGET_REQUEST_ID = "pr527-cross-lane-execution-state-aliasing-repair-v1-auditor-e81f3d31-r1"
TARGET_LAB_PASS_COMMENT = 5668703439
TARGET_LAB_REQUEST_SHA256 = "cefa31fe6e5e4bd1eccf1d44009354ff9da3a8e52286fa855224318ceae62717"
TARGET_T1_COMMENT = 5668803160


def cross_lane_execution_state_valid(
    lab_execution_state: Any,
    auditor_execution_state: Any,
) -> bool:
    lab_suffix = "_REVIEW_REQUESTED"
    auditor_suffix = "_AUDIT_REQUESTED"
    if not isinstance(lab_execution_state, str):
        return False
    if not isinstance(auditor_execution_state, str):
        return False
    if not lab_execution_state.endswith(lab_suffix):
        return False
    if not auditor_execution_state.endswith(auditor_suffix):
        return False
    lab_family = lab_execution_state[: -len(lab_suffix)]
    auditor_family = auditor_execution_state[: -len(auditor_suffix)]
    return bool(lab_family) and lab_family == auditor_family


def validate_bootstrap_target(job: dict[str, Any]) -> None:
    request = job.get("request") or {}
    upstream = request.get("upstream") or {}
    exact = {
        "lane": "AUDITOR",
        "repo": TARGET_REPO,
        "pr": TARGET_PR,
        "head": TARGET_HEAD,
        "tree": TARGET_TREE,
        "base": TARGET_MAIN,
        "main": TARGET_MAIN,
        "request_comment": TARGET_REQUEST_COMMENT,
        "request_sha256": TARGET_REQUEST_SHA256,
        "request_id": TARGET_REQUEST_ID,
    }
    for key, expected in exact.items():
        _review.require(job.get(key) == expected, f"BOOTSTRAP_TARGET_{key.upper()}")
    _review.require(request.get("lane") == "AUDITOR", "BOOTSTRAP_REQUEST_LANE")
    _review.require(request.get("repo") == TARGET_REPO, "BOOTSTRAP_REQUEST_REPO")
    _review.require(request.get("pr") == TARGET_PR, "BOOTSTRAP_REQUEST_PR")
    _review.require(request.get("head") == TARGET_HEAD, "BOOTSTRAP_REQUEST_HEAD")
    _review.require(request.get("tree") == TARGET_TREE, "BOOTSTRAP_REQUEST_TREE")
    _review.require(request.get("base") == TARGET_MAIN, "BOOTSTRAP_REQUEST_BASE")
    _review.require(request.get("main") == TARGET_MAIN, "BOOTSTRAP_REQUEST_MAIN")
    _review.require(request.get("request_id") == TARGET_REQUEST_ID, "BOOTSTRAP_REQUEST_ID")
    _review.require(
        upstream.get("lab_pass_comment") == TARGET_LAB_PASS_COMMENT,
        "BOOTSTRAP_UPSTREAM_LAB_PASS",
    )
    _review.require(
        upstream.get("lab_request_sha256") == TARGET_LAB_REQUEST_SHA256,
        "BOOTSTRAP_UPSTREAM_LAB_REQUEST_SHA256",
    )
    _review.require(
        upstream.get("t1_comment") == TARGET_T1_COMMENT,
        "BOOTSTRAP_UPSTREAM_T1",
    )


def _check_auditor_upstream_bootstrap(
    job: dict[str, Any],
    fetch: Callable[[str], Any],
    checks: dict[str, str],
    findings: list[str],
) -> None:
    if job["lane"] != "AUDITOR":
        return

    validate_bootstrap_target(job)

    def check(name: str, condition: bool, detail: str) -> None:
        if condition:
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: {detail}")

    upstream = job["request"]["upstream"]
    lab_comment_id = upstream["lab_pass_comment"]
    t1_comment_id = upstream["t1_comment"]

    comments = _review.fetch_all_pages(
        fetch,
        f"https://api.github.com/repos/{job['repo']}/issues/{job['pr']}/comments",
    )
    try:
        latest_lab_request_id, latest_lab_request, _ = (
            _review.latest_exact_current_owner_request(
                comments,
                repo=job["repo"],
                pr=job["pr"],
                lane="LAB",
                head=job["head"],
                tree=job["tree"],
                base=job["base"],
                main=job["main"],
            )
        )
        check(
            "upstream_lab_result_bound_to_latest_request",
            latest_lab_request_id > 0,
            repr(latest_lab_request_id),
        )
        check(
            "upstream_lab_request_proof_ceiling",
            latest_lab_request["proof_ceiling"]
            == job["request"]["proof_ceiling"],
            repr(latest_lab_request["proof_ceiling"]),
        )
        lab_execution_state = latest_lab_request["execution_state"]
        auditor_execution_state = job["request"]["execution_state"]
        check(
            "upstream_lab_request_execution_state",
            cross_lane_execution_state_valid(
                lab_execution_state,
                auditor_execution_state,
            ),
            f"lab={lab_execution_state!r} auditor={auditor_execution_state!r}",
        )
        latest_lab_request_sha256 = _review.sha256_json(latest_lab_request)
        check(
            "upstream_lab_request_sha256",
            upstream["lab_request_sha256"] == latest_lab_request_sha256,
            (
                f"{upstream['lab_request_sha256']!r} "
                f"!= {latest_lab_request_sha256!r}"
            ),
        )
    except Exception as exc:
        checks["upstream_latest_lab_request"] = "FIX_REQUIRED"
        findings.append(f"upstream_latest_lab_request: {exc}")
        latest_lab_request_id = -1
        latest_lab_request = {}
        latest_lab_request_sha256 = ""

    lab_comment = _review.required_object(
        fetch(
            f"https://api.github.com/repos/{job['repo']}/issues/comments/{lab_comment_id}"
        ),
        "LAB_COMMENT_RESPONSE_OBJECT",
    )
    lab_login = (lab_comment.get("user") or {}).get("login")
    lab_app = lab_comment.get("performed_via_github_app")
    check("upstream_lab_login", lab_login == _review.LAB_LOGIN, repr(lab_login))
    check(
        "upstream_lab_app",
        _review.lane_result_outer_app_trusted(lab_comment, "LAB"),
        repr(lab_app),
    )

    try:
        lab_artifact = _review._comment_json_block(lab_comment.get("body") or "")
    except Exception as exc:
        checks["upstream_lab_artifact"] = "FIX_REQUIRED"
        findings.append(f"upstream_lab_artifact: {exc!r}")
        lab_artifact = None

    if lab_artifact is not None:
        exact_fields = {
            "schema_version": _review.ARTIFACT_SCHEMA,
            "result_schema": _review.RESULT_SCHEMA,
            "lane": "LAB",
            "request_id": latest_lab_request.get("request_id"),
            "request_comment": latest_lab_request_id,
            "request_sha256": latest_lab_request_sha256,
            "mode": latest_lab_request.get("mode"),
            "verdict": "PASS",
            "findings": [],
            "reviewed_repo": job["repo"],
            "reviewed_pr": job["pr"],
            "reviewed_head": job["head"],
            "reviewed_tree": job["tree"],
            "reviewed_base": job["base"],
            "reviewed_main": job["main"],
            "proof_ceiling": job["request"]["proof_ceiling"],
            "execution_state": latest_lab_request.get("execution_state"),
        }
        for key, expected in exact_fields.items():
            actual = lab_artifact.get(key)
            check(
                f"upstream_lab_artifact:{key}",
                actual == expected,
                f"{actual!r} != {expected!r}",
            )
        producer = lab_artifact.get("producer") or {}
        check(
            "upstream_lab_artifact:producer_login",
            producer.get("github_login") == _review.LAB_LOGIN,
            repr(producer.get("github_login")),
        )
        check(
            "upstream_lab_artifact:producer_app_id",
            producer.get("github_app_id") == _review.LAB_APP_ID,
            repr(producer.get("github_app_id")),
        )

        marker = _review.result_marker(
            latest_lab_request.get("request_id", ""),
            job["head"],
            latest_lab_request_id,
            latest_lab_request_sha256,
        )
        authentic_result_ids: list[int] = []
        for item in comments:
            if (
                marker in (item.get("body") or "")
                and _review.lane_result_comment_trusted(item, "LAB")
            ):
                try:
                    authentic_result_ids.append(
                        _review.github_comment_id(item, "LAB_RESULT_COMMENT_ID")
                    )
                except _review.ReviewContractError as exc:
                    findings.append(f"upstream_lab_result_comment_id: {exc}")
        check(
            "upstream_lab_single_authentic_latest_result",
            authentic_result_ids == [lab_comment_id],
            repr(authentic_result_ids),
        )

    t1_comment = _review.required_object(
        fetch(
            f"https://api.github.com/repos/{job['repo']}/issues/comments/{t1_comment_id}"
        ),
        "T1_COMMENT_RESPONSE_OBJECT",
    )
    check(
        "upstream_t1_owner",
        _review.issue_comment_owner_trusted(t1_comment, job["repo"]),
        repr((t1_comment.get("user") or {}).get("login")),
    )
    t1_body = t1_comment.get("body") or ""
    for label, token in (
        ("lab_comment", str(lab_comment_id)),
        ("lab_request_sha256", latest_lab_request_sha256),
        ("head", job["head"]),
        ("tree", job["tree"]),
        ("base", job["base"]),
        ("main", job["main"]),
        ("pass", "PASS"),
    ):
        check(
            f"upstream_t1_binding:{label}",
            token in t1_body,
            f"missing {token!r}",
        )


def run_bootstrap_review(
    job: dict[str, Any],
    *,
    repo_root: Path,
    fetch: Callable[[str], Any] = _review.github_get,
    endpoint_fn: Callable[..., tuple[int, Any]] = _review.endpoint,
) -> dict[str, Any]:
    validate_bootstrap_target(job)
    original = _review._check_auditor_upstream
    _review._check_auditor_upstream = _check_auditor_upstream_bootstrap
    try:
        return _review.run_review(
            job,
            repo_root=repo_root,
            fetch=fetch,
            endpoint_fn=endpoint_fn,
        )
    finally:
        _review._check_auditor_upstream = original


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", default="review_job.json")
    parser.add_argument("--output", default="review_artifact.json")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    job = json.loads(Path(args.job).read_text())
    artifact = run_bootstrap_review(
        job,
        repo_root=Path(args.repo_root).resolve(),
    )
    Path(args.output).write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    print(json.dumps(artifact, indent=2, sort_keys=True))
    if artifact["verdict"] != "PASS":
        print("FIX_REQUIRED")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except _review.ReviewContractError as exc:
        print(f"BOOTSTRAP_REVIEW_FIX_REQUIRED:{exc}")
        raise SystemExit(1)
