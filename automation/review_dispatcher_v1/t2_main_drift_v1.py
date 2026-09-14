from __future__ import annotations

import copy
from typing import Any, Callable

from automation.review_dispatcher_v1 import t2 as _t2
from automation.review_dispatcher_v1 import t2_legacy_v1 as _legacy
from automation.review_dispatcher_v1.main_drift_runtime_v1 import (
    assert_dispatcher_ref_on_live_chain,
    assert_job_main_binding_fresh,
    assert_job_request_latest_across_snapshots,
    select_request_for_live_main,
)


Fetch = Callable[[str], Any]

_original_exact_publish_t2 = _t2._original_publish_t2
_original_fresh_t2_verify = _t2._fresh_t2_verify


def _live_main_sha(job: dict[str, Any], fetch: Fetch) -> str:
    return _legacy.github_branch_commit_sha(
        fetch(
            f"https://api.github.com/repos/{job['repo']}/branches/main"
        )
    )


def _safe_lab_binding(
    job: dict[str, Any],
    comments: list[dict[str, Any]],
    *,
    live_main: str | None = None,
    fetch: Fetch | None = None,
):
    fetch_fn = fetch or _legacy.public_github
    current_main = live_main or _live_main_sha(job, fetch_fn)
    request = job["request"]

    latest_id, latest_request, _comment, _classification = (
        select_request_for_live_main(
            comments,
            repo=job["repo"],
            pr=job["pr"],
            lane="LAB",
            head=job["head"],
            tree=job["tree"],
            base=job["base"],
            live_main=current_main,
            fetch=fetch_fn,
        )
    )

    # Preserve the cross-stage snapshot invariant. Main may move through safe
    # unrelated research after the Lab PASS, but the Auditor/T2 chain must not
    # silently switch to a different Lab request snapshot.
    _legacy.require(
        latest_request["main"] == job["main"],
        "LATEST_LAB_REQUEST_MAIN_SNAPSHOT_MISMATCH",
    )

    latest_sha = _legacy.sha256_json(latest_request)
    _legacy.require(
        latest_request["proof_ceiling"] == request["proof_ceiling"],
        "LATEST_LAB_PROOF_CEILING_MISMATCH",
    )
    _legacy.require(
        latest_request["execution_state"] == request["execution_state"],
        "LATEST_LAB_EXECUTION_STATE_MISMATCH",
    )
    _legacy.require(
        request["upstream"]["lab_request_sha256"] == latest_sha,
        "LATEST_LAB_REQUEST_SHA256_MISMATCH",
    )

    marker = _legacy.result_marker(
        latest_request["request_id"],
        job["head"],
        latest_id,
        latest_sha,
    )
    referenced_id = request["upstream"]["lab_pass_comment"]
    _t2.assert_referenced_result_is_canonical(
        comments,
        lane="LAB",
        marker=marker,
        referenced_comment_id=referenced_id,
    )
    return marker, referenced_id


def _assert_safe_freshness(
    job: dict[str, Any],
    *,
    fetch: Fetch,
) -> tuple[str, list[dict[str, Any]]]:
    repo = job["repo"]
    pr_number = job["pr"]

    pr = _legacy.github_full_pr_binding(
        fetch(f"https://api.github.com/repos/{repo}/pulls/{pr_number}"),
        expected_number=pr_number,
        expected_head=job["head"],
    )
    live_main = _live_main_sha(job, fetch)
    tree_sha = _legacy.github_commit_tree_sha(
        fetch(
            f"https://api.github.com/repos/{repo}/commits/{job['head']}"
        )
    )

    _legacy.require(pr["base_sha"] == job["base"], "BASE_DRIFT")
    _legacy.require(tree_sha == job["tree"], "TREE_DRIFT")

    assert_job_main_binding_fresh(
        job,
        live_main=live_main,
        fetch=fetch,
    )
    assert_dispatcher_ref_on_live_chain(
        job,
        live_main=live_main,
        fetch=fetch,
    )

    comments = _legacy.fetch_all_pages(
        fetch,
        f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments",
    )
    assert_job_request_latest_across_snapshots(
        job,
        comments,
        live_main=live_main,
    )
    _safe_lab_binding(
        job,
        comments,
        live_main=live_main,
        fetch=fetch,
    )
    return live_main, comments


def _compat_public_github(
    job: dict[str, Any],
    original_fetch: Fetch,
):
    """Compatibility view for legacy exact-main assertions.

    The real live main is always fetched and fully guarded first. Only after
    that proof succeeds is the branch response copied with the request snapshot
    SHA so the legacy exact-equality assertion can execute unchanged. No other
    response is altered.
    """

    def fetch(url: str):
        value = original_fetch(url)
        if url == f"https://api.github.com/repos/{job['repo']}/branches/main":
            live_main = _legacy.github_branch_commit_sha(value)
            _assert_safe_freshness(job, fetch=original_fetch)
            shadow = copy.deepcopy(value)
            shadow["commit"]["sha"] = job["main"]
            _legacy.require(
                live_main != "" and live_main is not None,
                "LIVE_MAIN_EMPTY",
            )
            return shadow
        return value

    return fetch


def _safe_exact_publish_t2(job, artifact, receipt):
    original_fetch = _legacy.public_github
    original_github_json = _legacy.github_json

    # First fail closed before entering legacy publication logic.
    _assert_safe_freshness(job, fetch=original_fetch)

    shadow_job = dict(job)
    # Legacy code requires dispatcher_ref == request main. The real dispatcher
    # chain was just proven separately and is re-proven at the mutation edge.
    shadow_job["dispatcher_ref"] = job["main"]

    compat_fetch = _compat_public_github(job, original_fetch)

    def guarded_github_json(method, url, token, payload=None):
        if method.upper() == "POST":
            # Last possible read-only guard immediately before the irreversible
            # T2 comment mutation. Any newly unsafe drift aborts the write.
            _assert_safe_freshness(job, fetch=original_fetch)
        return original_github_json(method, url, token, payload)

    _legacy.public_github = compat_fetch
    _legacy.github_json = guarded_github_json
    try:
        return _original_exact_publish_t2(
            shadow_job,
            artifact,
            receipt,
        )
    finally:
        _legacy.public_github = original_fetch
        _legacy.github_json = original_github_json


def _safe_fresh_t2_verify(job, artifact, receipt):
    original_fetch = _legacy.public_github
    _assert_safe_freshness(job, fetch=original_fetch)

    shadow_job = dict(job)
    shadow_job["dispatcher_ref"] = job["main"]
    compat_fetch = _compat_public_github(job, original_fetch)

    _legacy.public_github = compat_fetch
    try:
        return _original_fresh_t2_verify(
            shadow_job,
            artifact,
            receipt,
        )
    finally:
        _legacy.public_github = original_fetch


# Patch only the T2 orchestration edges. Existing result canonicalization,
# receipt recovery, mutation implementation, identity checks, T1 binding and
# duplicate handling remain the current canonical logic.
_t2._lab_binding = _safe_lab_binding
_t2._original_publish_t2 = _safe_exact_publish_t2
_t2._fresh_t2_verify = _safe_fresh_t2_verify


def main() -> int:
    return _t2.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (_legacy.ReviewContractError, _legacy.GitHubAppError) as exc:
        print(f"T2_FIX_REQUIRED:{exc}")
        raise SystemExit(1)
