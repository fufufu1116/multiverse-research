from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from automation.review_dispatcher_v1 import dispatcher, review
from automation.review_dispatcher_v1.github_app import app_jwt, github_json
from automation.review_dispatcher_v1.github_read_resilience_v1 import (
    github_json_read,
)
from automation.review_dispatcher_v1.model import (
    AUDITOR_APP_ID,
    LAB_APP_ID,
    ReviewContractError,
)

BOOTSTRAP_SCHEMA = "MULTIVERSE_AUTHENTICATED_REVIEW_BOOTSTRAP_v2"
READ_PERMISSIONS = {
    "contents": "read",
    "issues": "read",
    "pull_requests": "read",
}
LANE_PRIVATE_KEY_ENV = {
    "LAB": "MULTIVERSE_INDEPENDENT_LAB_PRIVATE_KEY",
    "AUDITOR": "MULTIVERSE_INDEPENDENT_AUDITOR_PRIVATE_KEY",
}
LANE_APP_ID = {
    "LAB": LAB_APP_ID,
    "AUDITOR": AUDITOR_APP_ID,
}


class BootstrapAuthError(RuntimeError):
    pass


def _bootstrap_require(condition: bool, code: str) -> None:
    if not condition:
        raise BootstrapAuthError(code)


def _lane_identity(lane: str) -> tuple[int, str]:
    _bootstrap_require(lane in LANE_PRIVATE_KEY_ENV, "LANE")
    app_id = LANE_APP_ID[lane]
    private_key_env = LANE_PRIVATE_KEY_ENV[lane]
    _bootstrap_require(
        isinstance(app_id, int)
        and not isinstance(app_id, bool)
        and app_id > 0,
        "APP_ID",
    )
    return app_id, private_key_env


def _strict_token(value: Any) -> str:
    _bootstrap_require(isinstance(value, str) and bool(value), "READ_TOKEN")
    _bootstrap_require(len(value) <= 4096, "READ_TOKEN_LENGTH")
    _bootstrap_require(
        not any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value),
        "READ_TOKEN_CONTROL_CHAR",
    )
    return value


def mint_downscoped_read_token(
    *,
    repo: str,
    lane: str,
    private_key: str,
    github_call: Callable[..., Any] = github_json,
    jwt_factory: Callable[[int, str], str] = app_jwt,
) -> str:
    app_id, _ = _lane_identity(lane)
    _bootstrap_require(isinstance(repo, str) and "/" in repo, "REPO")
    _bootstrap_require(
        isinstance(private_key, str) and bool(private_key.strip()),
        "PRIVATE_KEY_REQUIRED",
    )

    jwt = jwt_factory(app_id, private_key)
    installation = github_call(
        "GET",
        f"https://api.github.com/repos/{repo}/installation",
        jwt,
    )
    _bootstrap_require(isinstance(installation, dict), "INSTALLATION_OBJECT")
    installation_id = installation.get("id")
    _bootstrap_require(
        isinstance(installation_id, int)
        and not isinstance(installation_id, bool)
        and installation_id > 0,
        "INSTALLATION_ID",
    )

    token_result = github_call(
        "POST",
        (
            "https://api.github.com/app/installations/"
            f"{installation_id}/access_tokens"
        ),
        jwt,
        {"permissions": dict(READ_PERMISSIONS)},
    )
    _bootstrap_require(isinstance(token_result, dict), "TOKEN_OBJECT")
    return _strict_token(token_result.get("token"))


def _assert_github_api_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    _bootstrap_require(parsed.scheme == "https", "READ_URL_SCHEME")
    _bootstrap_require(parsed.hostname == "api.github.com", "READ_URL_HOST")
    _bootstrap_require(parsed.username is None, "READ_URL_USERINFO")
    _bootstrap_require(parsed.password is None, "READ_URL_USERINFO")


def authenticated_fetcher(
    token: str,
    *,
    user_agent: str,
) -> Callable[[str], Any]:
    token = _strict_token(token)

    def fetch(url: str) -> Any:
        _assert_github_api_url(url)

        def authenticated_opener(
            req: urllib.request.Request,
            *,
            timeout: int,
        ) -> Any:
            req.add_header("Authorization", f"Bearer {token}")
            return urllib.request.urlopen(req, timeout=timeout)

        # The existing same-build cache is intentionally bypassed here so
        # every bootstrap authority read is mechanically authenticated. The
        # authenticated installation-token quota is the read-admission fix;
        # bounded rate-limit retry behavior remains delegated to the shared
        # canonical helper.
        build_id = os.environ.pop("BUILDKITE_BUILD_ID", None)
        try:
            return github_json_read(
                url,
                user_agent=user_agent,
                opener=authenticated_opener,
            )
        finally:
            if build_id is not None:
                os.environ["BUILDKITE_BUILD_ID"] = build_id

    return fetch


def _write_artifact(artifact: dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n"
    )


def run_authenticated_review(
    *,
    lane: str,
    repo: str,
    head: str,
    job_output: str | Path,
    artifact_output: str | Path,
    repo_root: Path,
    mint: Callable[..., str] = mint_downscoped_read_token,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _, private_key_env = _lane_identity(lane)
    other_lane = "AUDITOR" if lane == "LAB" else "LAB"
    other_private_key_env = LANE_PRIVATE_KEY_ENV[other_lane]

    private_key = os.environ.get(private_key_env, "")
    _bootstrap_require(bool(private_key.strip()), "PRIVATE_KEY_REQUIRED")
    _bootstrap_require(
        not os.environ.get(other_private_key_env),
        "CROSS_LANE_PRIVATE_KEY_PRESENT",
    )

    token = mint(repo=repo, lane=lane, private_key=private_key)

    # Destroy the long-lived key reference and remove it from the process
    # environment before dispatcher/reviewer code or candidate-controlled
    # subprocesses are entered. Only the downscoped read token remains in a
    # trusted closure; it is never exported or persisted.
    private_key = ""
    os.environ.pop(private_key_env, None)

    fetch = authenticated_fetcher(
        token,
        user_agent=f"multiverse-authenticated-review-bootstrap-v2-{lane.lower()}",
    )
    try:
        job = dispatcher.discover_request(
            repo=repo,
            lane=lane,
            head=head,
            fetch=fetch,
        )
        dispatcher.write_job(job, job_output)

        artifact = review.run_review(
            job,
            repo_root=repo_root.resolve(),
            fetch=fetch,
        )
        _write_artifact(artifact, artifact_output)
        return job, artifact
    finally:
        # Drop the only token reference owned by this bootstrap frame. The
        # token is never exported to the environment or written to disk.
        token = ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", required=True, choices=("LAB", "AUDITOR"))
    parser.add_argument(
        "--repo",
        default="fufufu1116/multiverse-research",
    )
    parser.add_argument("--head", default=None)
    parser.add_argument("--job-output", default="review_job.json")
    parser.add_argument("--artifact-output", default="review_artifact.json")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    head = args.head or os.environ.get("BUILDKITE_COMMIT") or ""
    _bootstrap_require(bool(head), "BUILD_COMMIT_REQUIRED")

    job, artifact = run_authenticated_review(
        lane=args.lane,
        repo=args.repo,
        head=head,
        job_output=args.job_output,
        artifact_output=args.artifact_output,
        repo_root=Path(args.repo_root),
    )

    print(
        json.dumps(
            {
                "schema": BOOTSTRAP_SCHEMA,
                "lane": job["lane"],
                "pr": job["pr"],
                "head": job["head"],
                "request_comment": job["request_comment"],
                "request_sha256": job["request_sha256"],
                "verdict": artifact["verdict"],
                "authenticated_read": True,
                "private_key_present_after_mint": bool(
                    os.environ.get(LANE_PRIVATE_KEY_ENV[args.lane])
                ),
            },
            sort_keys=True,
        )
    )

    if artifact["verdict"] != "PASS":
        print("FIX_REQUIRED")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ReviewContractError, BootstrapAuthError) as exc:
        print(f"AUTHENTICATED_BOOTSTRAP_FIX_REQUIRED:{exc}")
        raise SystemExit(1)
