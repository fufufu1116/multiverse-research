from __future__ import annotations

import time

from automation.review_dispatcher_v1 import t2_legacy_v1 as _legacy
from automation.review_dispatcher_v1.publisher_freshness_v1 import (
    assert_job_request_still_canonical,
)
from automation.review_dispatcher_v1.t2_idempotence_v1 import (
    assert_published_t2_is_canonical,
    assert_referenced_result_is_canonical,
    canonical_trusted_comment_id,
)
from automation.review_dispatcher_v1.t2_receipt_recovery_v1 import (
    recover_t2_receipt,
)

_original_publish_t2 = _legacy.publish_t2
_original_fetch_all_pages = _legacy.fetch_all_pages

T2_POST_WRITE_VISIBILITY_MAX_READS = 4
T2_POST_WRITE_VISIBILITY_DELAY_SECONDS = 1.0


def _all_comments(job):
    return _original_fetch_all_pages(
        _legacy.public_github,
        f"https://api.github.com/repos/{job['repo']}/issues/{job['pr']}/comments",
    )


def _lab_binding(job, comments):
    request = job["request"]
    latest_id, latest_request, _ = _legacy.latest_exact_current_owner_request(
        comments,
        repo=job["repo"],
        pr=job["pr"],
        lane="LAB",
        head=job["head"],
        tree=job["tree"],
        base=job["base"],
        main=job["main"],
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
    assert_referenced_result_is_canonical(
        comments,
        lane="LAB",
        marker=marker,
        referenced_comment_id=referenced_id,
    )
    return marker, referenced_id


def _filter_noncanonical_lab_duplicates(job, comments):
    marker, canonical_id = _lab_binding(job, comments)
    filtered = []
    for comment in comments:
        if (
            marker in (comment.get("body") or "")
            and _legacy.lane_result_comment_trusted(comment, "LAB")
            and _legacy.github_comment_id(comment, "LAB_RESULT_COMMENT_ID") != canonical_id
        ):
            continue
        filtered.append(comment)
    return filtered


def _t2_marker_for_job(job, receipt):
    auditor_comment_id = _legacy.required_positive_int(
        receipt.get("published_comment_id"),
        "AUDITOR_RECEIPT_COMMENT_ID",
    )
    return auditor_comment_id, _legacy.t2_marker(
        job["request_id"],
        job["head"],
        auditor_comment_id,
        job["request_sha256"],
    )


def _canonical_t2_comment_or_none(comments, marker):
    try:
        cid = canonical_trusted_comment_id(
            comments,
            lane="AUDITOR",
            marker=marker,
        )
    except _legacy.ReviewContractError as exc:
        if str(exc) == "NO_CANONICAL_TRUSTED_COMMENT":
            return None
        raise
    for comment in comments:
        if _legacy.github_comment_id(comment, "T2_COMMENT_ID") == cid:
            return comment
    raise _legacy.ReviewContractError("CANONICAL_T2_COMMENT_NOT_FOUND")


def _validate_recovery_t2_artifact(job, artifact, auditor_comment_id):
    exact = {
        "schema_version": _legacy.T2_SCHEMA,
        "gate": "T2",
        "verdict": "PASS",
        "request_id": job["request_id"],
        "request_comment": job["request_comment"],
        "request_sha256": job["request_sha256"],
        "reviewed_repo": job["repo"],
        "reviewed_pr": job["pr"],
        "reviewed_head": job["head"],
        "reviewed_tree": job["tree"],
        "reviewed_base": job["base"],
        "reviewed_main": job["main"],
        "auditor_pass_comment": auditor_comment_id,
        "auditor_producer": _legacy.AUDITOR_LOGIN,
        "auditor_app_id": _legacy.AUDITOR_APP_ID,
        "proof_ceiling": job["request"]["proof_ceiling"],
        "execution_state": job["request"]["execution_state"],
        "nonauthority": job["request"]["nonauthority"],
    }
    for key, expected in exact.items():
        _legacy.require(
            artifact.get(key) == expected,
            f"T2_RECOVERY_LEGACY_BINDING_{key.upper()}",
        )


def _recover_existing_t2(job, receipt, comments, marker):
    canonical = _canonical_t2_comment_or_none(comments, marker)
    if canonical is None:
        return None
    auditor_comment_id = receipt["published_comment_id"]
    artifact = _legacy.json_block(canonical.get("body") or "")
    _validate_recovery_t2_artifact(job, artifact, auditor_comment_id)
    return recover_t2_receipt(
        job=job,
        auditor_comment_id=auditor_comment_id,
        expected_t2_artifact=artifact,
        canonical_t2_comment=canonical,
    )


def _fresh_t2_verify(job, artifact, receipt):
    repo = job["repo"]
    pr_number = job["pr"]

    pr = _legacy.github_full_pr_binding(
        _legacy.public_github(
            f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
        ),
        expected_number=pr_number,
        expected_head=job["head"],
    )
    main_sha = _legacy.github_branch_commit_sha(
        _legacy.public_github(
            f"https://api.github.com/repos/{repo}/branches/main"
        )
    )
    tree_sha = _legacy.github_commit_tree_sha(
        _legacy.public_github(
            f"https://api.github.com/repos/{repo}/commits/{job['head']}"
        )
    )

    _legacy.require(pr["base_sha"] == job["base"], "BASE_DRIFT")
    _legacy.require(tree_sha == job["tree"], "TREE_DRIFT")
    _legacy.require(main_sha == job["main"], "MAIN_DRIFT")
    _legacy.require(
        job.get("dispatcher_ref") == main_sha,
        "DISPATCHER_REF_DRIFT",
    )

    comments = _all_comments(job)
    assert_job_request_still_canonical(job, comments)
    _lab_binding(job, comments)

    auditor_comment_id = _legacy.required_positive_int(
        receipt.get("published_comment_id"),
        "AUDITOR_RECEIPT_COMMENT_ID",
    )
    _legacy.require(
        receipt.get("published_by") == _legacy.AUDITOR_LOGIN,
        "AUDITOR_RECEIPT_PRODUCER",
    )
    _legacy.require(
        receipt.get("github_app_id") == _legacy.AUDITOR_APP_ID,
        "AUDITOR_RECEIPT_APP",
    )
    _legacy.require(
        receipt.get("request_sha256") == job["request_sha256"],
        "AUDITOR_RECEIPT_REQUEST_SHA256",
    )

    auditor_comment = _legacy.required_object(
        _legacy.public_github(
            (
                f"https://api.github.com/repos/{repo}/issues/comments/"
                f"{auditor_comment_id}"
            )
        ),
        "AUDITOR_COMMENT_RESPONSE_OBJECT",
    )
    _legacy.require(
        (auditor_comment.get("user") or {}).get("login")
        == _legacy.AUDITOR_LOGIN,
        "AUDITOR_COMMENT_LOGIN",
    )
    _legacy.require(
        _legacy.lane_result_outer_app_trusted(
            auditor_comment,
            "AUDITOR",
        ),
        "AUDITOR_COMMENT_APP",
    )
    _legacy.require(
        _legacy.json_block(auditor_comment.get("body") or "") == artifact,
        "PUBLISHED_AUDITOR_ARTIFACT_DRIFT",
    )

    upstream = job["request"]["upstream"]
    t1_comment = _legacy.required_object(
        _legacy.public_github(
            (
                f"https://api.github.com/repos/{repo}/issues/comments/"
                f"{upstream['t1_comment']}"
            )
        ),
        "T1_COMMENT_RESPONSE_OBJECT",
    )
    _legacy.require(
        _legacy.issue_comment_owner_trusted(t1_comment, repo),
        "T1_PRODUCER_NOT_OWNER",
    )
    t1_body = t1_comment.get("body") or ""
    for token, code in (
        (str(upstream["lab_pass_comment"]), "T1_LAB_BINDING_MISSING"),
        (upstream["lab_request_sha256"], "T1_LAB_REQUEST_SHA256_MISSING"),
        (job["head"], "T1_HEAD_BINDING_MISSING"),
        (job["tree"], "T1_TREE_BINDING_MISSING"),
        (job["base"], "T1_BASE_BINDING_MISSING"),
        (job["main"], "T1_MAIN_BINDING_MISSING"),
        ("PASS", "T1_PASS_MARKER_MISSING"),
    ):
        _legacy.require(token in t1_body, code)

    return comments


def _await_published_t2_canonical(
    job,
    artifact,
    receipt,
    *,
    marker,
    result,
):
    published_comment_id = result["t2_comment_id"]
    missed_visibility = False

    for read_index in range(T2_POST_WRITE_VISIBILITY_MAX_READS):
        comments = _fresh_t2_verify(job, artifact, receipt)
        try:
            assert_published_t2_is_canonical(
                comments,
                marker=marker,
                published_comment_id=published_comment_id,
            )
        except _legacy.ReviewContractError as exc:
            if str(exc) != "NO_CANONICAL_TRUSTED_COMMENT":
                raise
            missed_visibility = True
        else:
            if not missed_visibility:
                return result
            recovered = _recover_existing_t2(
                job,
                receipt,
                comments,
                marker,
            )
            if recovered is None:
                raise _legacy.ReviewContractError(
                    "T2_POST_WRITE_CANONICAL_RESULT_DISAPPEARED"
                )
            _legacy.require(
                recovered["t2_comment_id"] == published_comment_id,
                "T2_POST_WRITE_RECEIPT_COMMENT_ID_DRIFT",
            )
            return recovered

        if read_index + 1 < T2_POST_WRITE_VISIBILITY_MAX_READS:
            time.sleep(T2_POST_WRITE_VISIBILITY_DELAY_SECONDS)

    raise _legacy.ReviewContractError(
        "T2_POST_WRITE_VISIBILITY_DEADLINE_EXHAUSTED"
    )


def publish_t2(job, artifact, receipt):
    comments = _all_comments(job)
    _lab_binding(job, comments)
    auditor_comment_id, marker = _t2_marker_for_job(job, receipt)

    recovered = _recover_existing_t2(job, receipt, comments, marker)
    if recovered is not None:
        return recovered

    def filtered_fetch(fetch, url, *, max_pages=100):
        raw = _original_fetch_all_pages(fetch, url, max_pages=max_pages)
        if f"/issues/{job['pr']}/comments" in url:
            return _filter_noncanonical_lab_duplicates(job, raw)
        return raw

    previous_fetch = _legacy.fetch_all_pages
    _legacy.fetch_all_pages = filtered_fetch
    try:
        try:
            result = _original_publish_t2(job, artifact, receipt)
        except _legacy.ReviewContractError as exc:
            if not str(exc).startswith("CURRENT_T2_ALREADY_EXISTS:"):
                raise
            comments = _all_comments(job)
            recovered = _recover_existing_t2(job, receipt, comments, marker)
            if recovered is None:
                raise _legacy.ReviewContractError(
                    "EXISTING_T2_RACE_WITHOUT_CANONICAL_RECOVERY"
                ) from exc
            return recovered
    finally:
        _legacy.fetch_all_pages = previous_fetch

    return _await_published_t2_canonical(
        job,
        artifact,
        receipt,
        marker=marker,
        result=result,
    )


_legacy.publish_t2 = publish_t2

for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)


def main() -> int:
    return _legacy.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (_legacy.ReviewContractError, _legacy.GitHubAppError) as exc:
        print(f"T2_FIX_REQUIRED:{exc}")
        raise SystemExit(1)
