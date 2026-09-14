from __future__ import annotations

from typing import Any

from automation.review_dispatcher_v1.model import require, sha40


# v1 is deliberately conservative. The only tolerated live-main movement is
# repository research material. Review/control/runtime paths are not inferred
# safe by exclusion; they are rejected because they are outside this allowlist.
SAFE_MAIN_DRIFT_PREFIXES = ("research/",)
MAX_SAFE_DRIFT_COMMITS = 64
MAX_COMPARE_FILES = 128


def _path_allowed(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in SAFE_MAIN_DRIFT_PREFIXES)


def _compare_files(payload: Any, code: str) -> set[str]:
    require(isinstance(payload, dict), f"{code}_OBJECT")
    require(payload.get("too_large") in (None, False), f"{code}_TOO_LARGE")
    files = payload.get("files")
    require(isinstance(files, list), f"{code}_FILES_LIST")
    require(len(files) <= MAX_COMPARE_FILES, f"{code}_FILE_BUDGET")

    names: set[str] = set()
    for item in files:
        require(isinstance(item, dict), f"{code}_FILE_OBJECT")
        name = item.get("filename")
        require(isinstance(name, str) and bool(name), f"{code}_FILENAME")
        names.add(name)

        previous = item.get("previous_filename")
        require(previous is None or (isinstance(previous, str) and bool(previous)), f"{code}_PREVIOUS_FILENAME")
        if previous:
            names.add(previous)
    return names


def _merge_base_sha(payload: dict[str, Any], code: str) -> str:
    merge_base = payload.get("merge_base_commit")
    require(isinstance(merge_base, dict), f"{code}_MERGE_BASE_OBJECT")
    sha = merge_base.get("sha")
    require(sha40(sha), f"{code}_MERGE_BASE_SHA")
    return sha


def _nonnegative_int(value: Any, code: str) -> int:
    require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, code)
    return value


def _validate_candidate_compare(
    payload: dict[str, Any],
    *,
    candidate_base: str,
) -> set[str]:
    require(payload.get("status") == "ahead", "CANDIDATE_COMPARE_NOT_AHEAD")
    require(_merge_base_sha(payload, "CANDIDATE_COMPARE") == candidate_base, "CANDIDATE_COMPARE_MERGE_BASE_MISMATCH")
    require(_nonnegative_int(payload.get("behind_by"), "CANDIDATE_COMPARE_BEHIND_BY") == 0, "CANDIDATE_COMPARE_BEHIND")
    require(_nonnegative_int(payload.get("ahead_by"), "CANDIDATE_COMPARE_AHEAD_BY") > 0, "CANDIDATE_COMPARE_EMPTY")
    return _compare_files(payload, "CANDIDATE_COMPARE")


def _validate_drift_compare(
    payload: dict[str, Any],
    *,
    request_main: str,
) -> set[str]:
    require(payload.get("status") == "ahead", "MAIN_DRIFT_NOT_DESCENDANT")
    require(_merge_base_sha(payload, "MAIN_DRIFT_COMPARE") == request_main, "MAIN_DRIFT_MERGE_BASE_MISMATCH")
    require(_nonnegative_int(payload.get("behind_by"), "MAIN_DRIFT_BEHIND_BY") == 0, "MAIN_DRIFT_BEHIND")

    ahead = _nonnegative_int(payload.get("ahead_by"), "MAIN_DRIFT_AHEAD_BY")
    total = _nonnegative_int(payload.get("total_commits"), "MAIN_DRIFT_TOTAL_COMMITS")
    require(0 < ahead <= MAX_SAFE_DRIFT_COMMITS, "MAIN_DRIFT_COMMIT_BUDGET")
    require(total == ahead, "MAIN_DRIFT_COMMIT_COUNT_AMBIGUOUS")

    files = _compare_files(payload, "MAIN_DRIFT_COMPARE")
    unsafe = sorted(path for path in files if not _path_allowed(path))
    require(not unsafe, "MAIN_DRIFT_NOT_ALLOWLISTED:" + ",".join(unsafe))
    return files


def assess_unrelated_main_drift(
    *,
    request_main: str,
    live_main: str,
    candidate_base: str,
    candidate_compare: dict[str, Any],
    drift_compare: dict[str, Any],
) -> dict[str, Any]:
    """Classify only provably unrelated descendant research drift as safe.

    This is a pure candidate primitive. It does not select stale review
    requests, change dispatcher/reviewer/publisher behavior, or grant review
    authority. Current exact-main semantics remain authoritative until a
    separate integration is independently reviewed and adopted.
    """
    require(sha40(request_main), "DRIFT_REQUEST_MAIN_SHA")
    require(sha40(live_main), "DRIFT_LIVE_MAIN_SHA")
    require(sha40(candidate_base), "DRIFT_CANDIDATE_BASE_SHA")

    candidate_files = _validate_candidate_compare(
        candidate_compare,
        candidate_base=candidate_base,
    )

    if request_main == live_main:
        return {
            "mode": "EXACT_MAIN",
            "candidate_files": sorted(candidate_files),
            "drift_files": [],
        }

    drift_files = _validate_drift_compare(
        drift_compare,
        request_main=request_main,
    )

    overlap = sorted(candidate_files & drift_files)
    require(not overlap, "MAIN_DRIFT_TARGET_OVERLAP:" + ",".join(overlap))

    return {
        "mode": "SAFE_UNRELATED_MAIN_DRIFT",
        "candidate_files": sorted(candidate_files),
        "drift_files": sorted(drift_files),
        "request_main": request_main,
        "live_main": live_main,
    }
