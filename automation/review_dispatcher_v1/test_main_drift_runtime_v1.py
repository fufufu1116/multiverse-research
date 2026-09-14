from __future__ import annotations

import unittest
from unittest.mock import patch

from automation.review_dispatcher_v1 import main_drift_runtime_v1 as runtime
from automation.review_dispatcher_v1.model import ReviewContractError, sha256_json


OLD = "a" * 40
DISPATCH = "b" * 40
LIVE = "c" * 40
BASE = "d" * 40
HEAD = "e" * 40
TREE = "f" * 40
REPO = "fufufu1116/multiverse-research"
PR = 999


def candidate_compare():
    return {
        "status": "ahead",
        "ahead_by": 1,
        "behind_by": 0,
        "total_commits": 1,
        "too_large": None,
        "merge_base_commit": {"sha": BASE},
        "files": [{"filename": "automation/review_dispatcher_v1/x.py"}],
    }


def drift_compare(base: str, files=("research/opportunity_engine_v0/note.md",)):
    return {
        "status": "ahead",
        "ahead_by": 1,
        "behind_by": 0,
        "total_commits": 1,
        "too_large": None,
        "merge_base_commit": {"sha": base},
        "files": [{"filename": path} for path in files],
    }


def fetch_for(*, unsafe_dispatch_to_live=False):
    def fetch(url: str):
        if url.endswith(f"/compare/{BASE}...{HEAD}"):
            return candidate_compare()
        if url.endswith(f"/compare/{OLD}...{DISPATCH}"):
            return drift_compare(OLD)
        if url.endswith(f"/compare/{DISPATCH}...{LIVE}"):
            files = (
                "automation/review_dispatcher_v1/model.py",
            ) if unsafe_dispatch_to_live else (
                "research/opportunity_engine_v0/later.md",
            )
            return drift_compare(DISPATCH, files=files)
        if url.endswith(f"/compare/{OLD}...{LIVE}"):
            return drift_compare(OLD)
        raise AssertionError(url)

    return fetch


def request(main: str, request_id: str = "req-1"):
    return {
        "request_id": request_id,
        "main": main,
    }


class MainDriftRuntimeTests(unittest.TestCase):
    def test_exact_live_main_is_preferred_without_fallback(self):
        exact = request(LIVE, "exact-live")
        with patch.object(
            runtime,
            "latest_exact_current_owner_request",
            return_value=(10, exact, {"body": "exact"}),
        ), patch.object(
            runtime,
            "latest_target_request_across_main_snapshots",
            side_effect=AssertionError("fallback must not run"),
        ):
            cid, selected, _comment, classification = runtime.select_request_for_live_main(
                [],
                repo=REPO,
                pr=PR,
                lane="LAB",
                head=HEAD,
                tree=TREE,
                base=BASE,
                live_main=LIVE,
                fetch=fetch_for(),
            )
        self.assertEqual(cid, 10)
        self.assertIs(selected, exact)
        self.assertEqual(classification["mode"], "EXACT_MAIN")

    def test_no_exact_live_main_falls_back_to_safe_snapshot(self):
        stale = request(OLD, "stale-safe")
        with patch.object(
            runtime,
            "latest_exact_current_owner_request",
            side_effect=ReviewContractError("NO_EXACT_CURRENT_LAB_REQUEST"),
        ), patch.object(
            runtime,
            "latest_target_request_across_main_snapshots",
            return_value=(9, stale, {"body": "stale"}),
        ):
            cid, selected, _comment, classification = runtime.select_request_for_live_main(
                [],
                repo=REPO,
                pr=PR,
                lane="LAB",
                head=HEAD,
                tree=TREE,
                base=BASE,
                live_main=LIVE,
                fetch=fetch_for(),
            )
        self.assertEqual(cid, 9)
        self.assertIs(selected, stale)
        self.assertEqual(classification["mode"], "SAFE_UNRELATED_MAIN_DRIFT")

    def test_malformed_exact_live_main_never_falls_back(self):
        with patch.object(
            runtime,
            "latest_exact_current_owner_request",
            side_effect=ReviewContractError("SAME_HEAD_SUPERSESSION_CHAIN_INVALID"),
        ), patch.object(
            runtime,
            "latest_target_request_across_main_snapshots",
            side_effect=AssertionError("fallback must not run"),
        ):
            with self.assertRaisesRegex(
                ReviewContractError,
                "SAME_HEAD_SUPERSESSION_CHAIN_INVALID",
            ):
                runtime.select_request_for_live_main(
                    [],
                    repo=REPO,
                    pr=PR,
                    lane="LAB",
                    head=HEAD,
                    tree=TREE,
                    base=BASE,
                    live_main=LIVE,
                    fetch=fetch_for(),
                )

    def test_dispatcher_ref_must_stay_on_safe_live_chain(self):
        job = {
            "repo": REPO,
            "base": BASE,
            "head": HEAD,
            "main": OLD,
            "dispatcher_ref": DISPATCH,
        }
        result = runtime.assert_dispatcher_ref_on_live_chain(
            job,
            live_main=LIVE,
            fetch=fetch_for(),
        )
        self.assertEqual(
            result["request_to_dispatcher"]["mode"],
            "SAFE_UNRELATED_MAIN_DRIFT",
        )
        self.assertEqual(
            result["dispatcher_to_live"]["mode"],
            "SAFE_UNRELATED_MAIN_DRIFT",
        )

    def test_dispatcher_to_live_control_drift_fails_closed(self):
        job = {
            "repo": REPO,
            "base": BASE,
            "head": HEAD,
            "main": OLD,
            "dispatcher_ref": DISPATCH,
        }
        with self.assertRaisesRegex(ReviewContractError, "MAIN_DRIFT_NOT_ALLOWLISTED"):
            runtime.assert_dispatcher_ref_on_live_chain(
                job,
                live_main=LIVE,
                fetch=fetch_for(unsafe_dispatch_to_live=True),
            )

    def test_exact_live_request_supersedes_stale_job_at_freshness(self):
        stale = request(OLD, "stale-job")
        exact = request(LIVE, "new-exact")
        job = {
            "repo": REPO,
            "pr": PR,
            "lane": "LAB",
            "head": HEAD,
            "tree": TREE,
            "base": BASE,
            "main": OLD,
            "request_comment": 11,
            "request_sha256": sha256_json(stale),
            "request": stale,
        }
        with patch.object(
            runtime,
            "latest_exact_current_owner_request",
            return_value=(12, exact, {}),
        ):
            with self.assertRaisesRegex(
                ReviewContractError,
                "REQUEST_SUPERSEDED_BY_EXACT_LIVE_MAIN",
            ):
                runtime.assert_job_request_latest_across_snapshots(
                    job,
                    [],
                    live_main=LIVE,
                )

    def test_no_exact_live_request_keeps_matching_latest_snapshot_job(self):
        stale = request(OLD, "stale-job")
        job = {
            "repo": REPO,
            "pr": PR,
            "lane": "LAB",
            "head": HEAD,
            "tree": TREE,
            "base": BASE,
            "main": OLD,
            "request_comment": 11,
            "request_sha256": sha256_json(stale),
            "request": stale,
        }
        with patch.object(
            runtime,
            "latest_exact_current_owner_request",
            side_effect=ReviewContractError("NO_EXACT_CURRENT_LAB_REQUEST"),
        ), patch.object(
            runtime,
            "latest_target_request_across_main_snapshots",
            return_value=(11, stale, {}),
        ):
            runtime.assert_job_request_latest_across_snapshots(
                job,
                [],
                live_main=LIVE,
            )


if __name__ == "__main__":
    unittest.main()
