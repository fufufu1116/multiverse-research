from __future__ import annotations

from typing import Any

from automation.review_dispatcher_v1.model import ReviewContractError, require, sha40


CRITICAL_MAIN_DRIFT_PREFIXES = (
    "automation/review_dispatcher_v1/",
    ".github/",
    "docs/control/",
    "multiverse_vnext/",
    "MULTIVERSE_BOOTSTRAP.md",
)


def _compare_files(payload: Any, code: str) -> set[str]:
    require(isinstance(payload, dict), f"{code}_OBJECT")
    require(payload.get("too_large") in (None, False), f"{code}_TOO_LARGE")
    files = payload.get("files")
    require(isinstance(files, list), f"{code}_FILES_LIST")
    names: set[str] = set()
    for item in files:
        require(isinstance(item, dict), f"{code}_FILE_OBJECT")
        name = item.get("filename")
        require(isinstance(name, str) and bool(name), f"{code}_FILENAME")
        names.add(name)
    return names


def _merge_base_sha(payload: dict[str, Any], code: str) -> str:
    merge_base = payload.get("merge_base_commit")
    require(isinstance(merge_base, dict), f"{code}_MERGE_BASE_OBJECT")
    sha = merge_base.get("sha")
    require(sha40(sha), f"{code}_MERGE_BASE_SHA")
    return sha


def _critical(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in CRITICAL_MAIN_DRIFT_PREFIXES)


def assess_unrelated_main_drift(
    *,
    request_main: str,
    live_main: str,
    candidate_compare: dict[str, Any],
    drift_compare: dict[str, Any],
) -> dict[str, Any]:
    """Fail closed unless live-main movement is provably unrelated to the review target.

    This primitive does not select a request and does not grant review authority. It is
    intended for a future dispatcher/reviewer integration candidate after independent
    review. The current strict binding remains authoritative until that integration is
    separately adopted.
    """
    require(sha40(request_main), "DRIFT_REQUEST_MAIN_SHA")
    require(sha40(live_main), "DRIFT_LIVE_MAIN_SHA")

    if request_main == live_main:
        return {
            "mode": "EXACT_MAIN",
            "candidate_files": sorted(_compare_files(candidate_compare, "CANDIDATE_COMPARE")),
            "drift_files": [],
        }

    require(
        drift_compare.get("status") == "ahead",
        "MAIN_DRIFT_NOT_DESCENDANT",
    )
    require(
        _merge_base_sha(drift_compare, "MAIN_DRIFT_COMPARE") == request_main,
        "MAIN_DRIFT_MERGE_BASE_MISMATCH",
    )

    candidate_files = _compare_files(candidate_compare, "CANDIDATE_COMPARE")
    drift_files = _compare_files(drift_compare, "MAIN_DRIFT_COMPARE")

    critical = sorted(path for path in drift_files if _critical(path))
    require(not critical, "MAIN_DRIFT_CRITICAL_PATH:" + ",".join(critical))

    overlap = sorted(candidate_files & drift_files)
    require(not overlap, "MAIN_DRIFT_TARGET_OVERLAP:" + ",".join(overlap))

    return {
        "mode": "SAFE_UNRELATED_MAIN_DRIFT",
        "candidate_files": sorted(candidate_files),
        "drift_files": sorted(drift_files),
    }
