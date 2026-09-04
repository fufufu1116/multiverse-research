#!/usr/bin/env python3
"""Read-only GitHub Fresh-Read manifest builder for MULTIVERSE candidate routing.

GET-only, api.github.com only, no token handling, no writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

RC = 92
SHA40 = re.compile(r"^[0-9a-f]{40}$")


class FreshReadError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise FreshReadError(code)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def api_get(url: str) -> Any:
    parsed = urllib.parse.urlparse(url)
    require(parsed.scheme == "https" and parsed.hostname == "api.github.com", "HOST")
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "multiverse-fresh-manifest-v1",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            require(resp.status == 200, f"HTTP:{resp.status}")
            return json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise FreshReadError(f"FETCH:{type(exc).__name__}") from exc


def repo_parts(full: str) -> tuple[str, str]:
    require(isinstance(full, str) and full.count("/") == 1, "REPO")
    owner, repo = full.split("/")
    require(owner and repo, "REPO")
    return owner, repo


def url(base: str, path: str) -> str:
    return f"{base}/{path}"


def build_snapshot(
    task: dict[str, Any],
    pr_number: int | None = None,
    comment_ids: list[int] | None = None,
    fetch: Callable[[str], Any] = api_get,
) -> dict[str, Any]:
    require(isinstance(task, dict), "TASK")
    for key in ("canonical_repo", "target_branch", "target_head"):
        require(isinstance(task.get(key), str) and task[key], f"TASK:{key}")
    require(SHA40.fullmatch(task["target_head"]) is not None, "TASK:target_head")
    owner, repo = repo_parts(task["canonical_repo"])
    base = f"https://api.github.com/repos/{urllib.parse.quote(owner, safe='')}/{urllib.parse.quote(repo, safe='')}"
    branch_q = urllib.parse.quote(task["target_branch"], safe="")

    main_ref = fetch(url(base, "git/ref/heads/main"))
    target_ref = fetch(url(base, f"git/ref/heads/{branch_q}"))
    main_sha = main_ref["object"]["sha"]
    target_sha = target_ref["object"]["sha"]
    require(SHA40.fullmatch(main_sha) is not None, "MAIN_SHA")
    require(SHA40.fullmatch(target_sha) is not None, "TARGET_SHA")
    require(target_sha == task["target_head"], "TARGET_HEAD_DRIFT")

    main_commit = fetch(url(base, f"git/commits/{main_sha}"))
    target_commit = fetch(url(base, f"git/commits/{target_sha}"))
    main_tree = main_commit["tree"]["sha"]
    target_tree = target_commit["tree"]["sha"]
    require(SHA40.fullmatch(main_tree) is not None, "MAIN_TREE")
    require(SHA40.fullmatch(target_tree) is not None, "TARGET_TREE")

    snapshot: dict[str, Any] = {
        "snapshot_version": "multiverse-fresh-snapshot-v1",
        "fetched_at": utc_now(),
        "canonical_repo": task["canonical_repo"],
        "canonical_main": main_sha,
        "canonical_main_tree": main_tree,
        "target_branch": task["target_branch"],
        "target_head": target_sha,
        "target_tree": target_tree,
        "pr": None,
        "comments": [],
        "authority": task.get("authority", {}),
    }

    if pr_number is not None:
        require(isinstance(pr_number, int) and pr_number > 0, "PR_NUMBER")
        pr = fetch(url(base, f"pulls/{pr_number}"))
        snapshot["pr"] = {
            "number": pr["number"],
            "state": pr["state"],
            "draft": bool(pr.get("draft")),
            "merged": bool(pr.get("merged", pr.get("merged_at") is not None)),
            "base_ref": pr["base"]["ref"],
            "base_sha": pr["base"]["sha"],
            "head_ref": pr["head"]["ref"],
            "head_sha": pr["head"]["sha"],
            "updated_at": pr["updated_at"],
        }

    for comment_id in comment_ids or []:
        require(isinstance(comment_id, int) and comment_id > 0, "COMMENT_ID")
        c = fetch(url(base, f"issues/comments/{comment_id}"))
        body = c.get("body") or ""
        app = c.get("performed_via_github_app") or {}
        snapshot["comments"].append(
            {
                "id": c["id"],
                "created_at": c["created_at"],
                "updated_at": c["updated_at"],
                "author_login": (c.get("user") or {}).get("login"),
                "author_association": c.get("author_association"),
                "github_app_slug": app.get("slug"),
                "body_sha256": hashlib.sha256(body.encode()).hexdigest(),
            }
        )
    return snapshot


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--task", required=True)
    p.add_argument("--pr", type=int)
    p.add_argument("--comment", action="append", type=int, default=[])
    args = p.parse_args()
    try:
        task = json.loads(pathlib.Path(args.task).read_text())
        print(json.dumps(build_snapshot(task, args.pr, args.comment), sort_keys=True, separators=(",", ":")))
        return 0
    except (FreshReadError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"MULTIVERSE_FRESH_READ_DENIED:{exc}", file=__import__("sys").stderr)
        return RC


if __name__ == "__main__":
    raise SystemExit(main())
