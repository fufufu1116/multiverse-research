#!/usr/bin/env python3
import unittest

from keirin_forward_price_value_gate_v2 import (
    ForwardPriceValueGateError,
    evaluate,
)


P_R5 = 0.179212765529


class ForwardPriceValueGateV2Test(unittest.TestCase):
    def test_core_6_1_no_bet(self):
        self.assertEqual(evaluate(P_R5, P_R5, 6.1)["decision"], "NO_BET")

    def test_core_6_2_buy_candidate(self):
        out = evaluate(P_R5, P_R5, 6.2)
        self.assertEqual(out["decision"], "BUY_CANDIDATE_100YEN")
        self.assertEqual(out["stake_yen_if_buy_candidate"], 100)

    def test_core_boundary_20_can_buy(self):
        self.assertEqual(
            evaluate(P_R5, P_R5, 20.0)["decision"],
            "BUY_CANDIDATE_100YEN",
        )

    def test_over_20_never_buy(self):
        self.assertEqual(
            evaluate(P_R5, P_R5, 20.1)["decision"],
            "SHADOW_ONLY",
        )

    def test_mid_hole_80_shadow(self):
        self.assertEqual(
            evaluate(P_R5, P_R5, 80.0)["decision"],
            "SHADOW_ONLY",
        )

    def test_longshot_requires_second_source(self):
        self.assertEqual(
            evaluate(P_R5, P_R5, 80.1)["decision"],
            "NO_BET_UNVERIFIED",
        )
        self.assertEqual(
            evaluate(P_R5, P_R5, 80.1, second_source_verified=True)["decision"],
            "SHADOW_ONLY",
        )

    def test_extreme_requires_anomaly_check(self):
        self.assertEqual(
            evaluate(
                P_R5,
                P_R5,
                300.1,
                second_source_verified=True,
            )["decision"],
            "NO_BET_UNVERIFIED",
        )
        self.assertEqual(
            evaluate(
                P_R5,
                P_R5,
                300.1,
                second_source_verified=True,
                anomaly_check_passed=True,
            )["decision"],
            "SHADOW_ONLY",
        )

    def test_9999_9_placeholder_fails_closed(self):
        self.assertEqual(
            evaluate(
                P_R5,
                P_R5,
                9999.9,
                second_source_verified=True,
                anomaly_check_passed=True,
            )["decision"],
            "NO_BET_UNVERIFIED",
        )

    def test_9999_9_explicitly_verified_still_shadow_only(self):
        self.assertEqual(
            evaluate(
                P_R5,
                P_R5,
                9999.9,
                second_source_verified=True,
                anomaly_check_passed=True,
                explicit_9999_9_verified=True,
            )["decision"],
            "SHADOW_ONLY",
        )

    def test_stale_price_fails_closed(self):
        self.assertEqual(
            evaluate(
                P_R5,
                P_R5,
                6.2,
                odds_quality_state="STALE",
            )["decision"],
            "NO_BET_UNVERIFIED",
        )

    def test_conservative_probability_is_min(self):
        out = evaluate(0.20, 0.18, 6.2)
        self.assertAlmostEqual(out["conservative_probability"], 0.18)

    def test_invalid_odds_rejected(self):
        with self.assertRaises(ForwardPriceValueGateError):
            evaluate(P_R5, P_R5, 0.9)

    def test_automatic_execution_off(self):
        out = evaluate(P_R5, P_R5, 6.2)
        self.assertFalse(out["automatic_execution"])
        self.assertEqual(out["runtime"], "OFF")


if __name__ == "__main__":
    unittest.main()
