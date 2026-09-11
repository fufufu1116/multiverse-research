from __future__ import annotations

import copy
import unittest

from automation.multimodel_research_v1.phase_b_live_preauth_fresh_main import (
    CANONICAL_MAIN,
    CANONICAL_MULTIMODEL_SUBTREE,
    CANONICAL_TREE,
    MAX_ATTEMPTS,
    MAX_COST_USD_MICROS,
    PR305_FROZEN_HEAD,
    PR313_REQUEST_ARBITRATION_BLOB,
    build_first_live_provider_preauth,
    classify_pilot_outcome,
    valid_success_fixture,
    validate_first_live_provider_preauth,
)


class FreshMainPreauthSuccessorTests(unittest.TestCase):
    def test_557_fresh_main_binding(self):
        p = build_first_live_provider_preauth()
        self.assertEqual(p["canonical"]["main"], CANONICAL_MAIN)
        self.assertEqual(p["canonical"]["tree"], CANONICAL_TREE)

    def test_558_multimodel_subtree_preserved(self):
        self.assertEqual(build_first_live_provider_preauth()["canonical"]["multimodel_subtree"], CANONICAL_MULTIMODEL_SUBTREE)

    def test_559_pr305_remains_predecessor_history(self):
        self.assertEqual(PR305_FROZEN_HEAD, "9662b62107ea29ebc10936ceba172925c3bb7aae")
        self.assertIs(validate_first_live_provider_preauth(build_first_live_provider_preauth()), build_first_live_provider_preauth())

    def test_560_post_pr313_control_binding_present(self):
        self.assertEqual(PR313_REQUEST_ARBITRATION_BLOB, "ccf53e79155a79cda4f24a1c03badf3b4d003c97")

    def test_561_live_authority_false(self):
        a = build_first_live_provider_preauth()["authority"]
        self.assertEqual(a["runtime"], "OFF")
        self.assertTrue(all(v is False for k, v in a.items() if k != "runtime"))

    def test_562_request_and_retry_boundaries(self):
        p = build_first_live_provider_preauth()
        self.assertIs(p["exact_request_body"]["store"], False)
        self.assertEqual(p["limits"]["max_attempts"], MAX_ATTEMPTS)
        self.assertFalse(p["retry_policy"]["automatic_retry"])

    def test_563_cost_boundary_preserved(self):
        self.assertEqual(build_first_live_provider_preauth()["limits"]["proposed_owner_spend_ceiling_usd_micros"], MAX_COST_USD_MICROS)

    def test_564_fail_closed_outcome_preserved(self):
        bad = copy.deepcopy(valid_success_fixture())
        bad["receipt_valid"] = False
        result = classify_pilot_outcome(bad)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["classification"], "FAIL_CLOSED")
        self.assertFalse(result["grants_authority"])
        self.assertEqual(result["runtime"], "OFF")


if __name__ == "__main__":
    unittest.main()
