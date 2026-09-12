from __future__ import annotations

import unittest
from unittest import mock

from automation.review_dispatcher_v1 import prelaunch_guard_v1 as guard

B = dict(repo="fufufu1116/multiverse-research", pr=346, lane="AUDITOR", request_id="req-v2", request_sha256="a"*64, head="b"*40, main="c"*40)


def result_comment(cid=9):
    marker = guard.result_marker(B["request_id"], B["head"], 123, B["request_sha256"])
    return {"id": cid, "body": marker, "user": {"login": "multiverse-independent-auditor[bot]"}, "performed_via_github_app": {"id": 4821179, "slug": "multiverse-independent-auditor"}}


class PrelaunchGuardTests(unittest.TestCase):
    def decision(self, comments=None, **kw):
        args = dict(comments=comments or [], lane=B["lane"], request_id=B["request_id"], head=B["head"], request_comment=123, request_sha256=B["request_sha256"], gate_request_sha256=B["request_sha256"], current_request_sha256=B["request_sha256"], lease_exists=False)
        args.update(kw)
        return guard.prelaunch_decision(**args)

    def test_01_fresh_request_requires_lease_before_launch(self):
        self.assertEqual(self.decision()["decision"], "LEASE_THEN_LAUNCH")

    def test_02_late_visible_exact_result_prevents_build(self):
        with mock.patch.object(guard, "lane_result_comment_trusted", return_value=True):
            out = self.decision([result_comment(5641130370)])
        self.assertEqual(out, {"decision": "COMPLETE", "reason": "EXACT_RESULT_ALREADY_EXISTS", "result_ids": [5641130370]})

    def test_03_untrusted_lookalike_result_does_not_complete(self):
        with mock.patch.object(guard, "lane_result_comment_trusted", return_value=False):
            self.assertEqual(self.decision([result_comment()])["decision"], "LEASE_THEN_LAUNCH")

    def test_04_stale_gate_fails_closed(self):
        self.assertEqual(self.decision(current_request_sha256="d"*64), {"decision": "BLOCK", "reason": "STALE_GATE"})

    def test_05_existing_exact_lease_prevents_duplicate_build(self):
        self.assertEqual(self.decision(lease_exists=True), {"decision": "BLOCK", "reason": "EXACT_REQUEST_LAUNCH_ALREADY_LEASED"})

    def test_06_result_wins_over_existing_lease(self):
        with mock.patch.object(guard, "lane_result_comment_trusted", return_value=True):
            self.assertEqual(self.decision([result_comment()], lease_exists=True)["decision"], "COMPLETE")

    def test_07_same_request_key_is_deterministic(self):
        self.assertEqual(guard.launch_key(**B), guard.launch_key(**dict(reversed(list(B.items())))))

    def test_08_lane_isolated(self):
        lab = dict(B); lab["lane"] = "LAB"
        self.assertNotEqual(guard.launch_lease_ref(**B), guard.launch_lease_ref(**lab))

    def test_09_request_isolated_within_lane(self):
        other = dict(B); other["request_sha256"] = "e"*64
        self.assertNotEqual(guard.launch_lease_ref(**B), guard.launch_lease_ref(**other))

    def test_10_pr_isolated_across_lanes_and_candidates(self):
        other = dict(B); other["pr"] = 999
        self.assertNotEqual(guard.launch_lease_ref(**B), guard.launch_lease_ref(**other))

    def test_11_lease_payload_binds_exact_launch_key(self):
        payload = guard.lease_payload(**B)
        self.assertEqual(payload["schema"], guard.LEASE_SCHEMA)
        self.assertEqual(payload["launch_key"], guard.launch_key(**B))
        self.assertEqual(payload["binding"], B)

    def test_12_ref_namespace_is_not_branch_namespace(self):
        self.assertTrue(guard.launch_lease_ref(**B).startswith("refs/tags/multiverse-build-launch-leases/v1/auditor/"))


if __name__ == "__main__":
    unittest.main()
