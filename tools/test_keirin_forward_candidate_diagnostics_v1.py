#!/usr/bin/env python3
import unittest

from keirin_forward_candidate_diagnostics_v1 import (
    CandidateDiagnosticError,
    core_feasibility_floor,
    minimum_core_odds,
    paired_value_thresholds_are_redundant,
    fallback_pairwise_score_equivalent,
    equal_stake_uniform_minimum_odds,
    lower_probability_addition_dilutes_uniform_screen,
)


class CandidateDiagnosticsV1Test(unittest.TestCase):
    def test_core_feasibility_floor(self):
        self.assertAlmostEqual(core_feasibility_floor(), 0.055, places=12)

    def test_r5_exact_threshold(self):
        result = minimum_core_odds(0.179212765529)
        self.assertTrue(result["core_possible"])
        self.assertAlmostEqual(
            result["minimum_odds"], 6.137955612442124, places=12
        )

    def test_below_floor_is_core_impossible(self):
        self.assertFalse(minimum_core_odds(0.05)["core_possible"])

    def test_exact_floor_reaches_core_ceiling(self):
        result = minimum_core_odds(0.055)
        self.assertTrue(result["core_possible"])
        self.assertAlmostEqual(result["minimum_odds"], 20.0, places=12)

    def test_all_current_band_pairs_are_redundant(self):
        for multiple, ev in (
            (1.10, 0.10),
            (1.35, 0.35),
            (1.75, 0.75),
            (2.50, 1.50),
        ):
            self.assertTrue(
                paired_value_thresholds_are_redundant(multiple, ev)
            )

    def test_nonmatching_pair_is_not_redundant(self):
        self.assertFalse(
            paired_value_thresholds_are_redundant(1.20, 0.10)
        )

    def test_fallback_style_spread_equivalent(self):
        result = fallback_pairwise_score_equivalent(
            [-0.020537046719, 0.038120995374, 0.0024804485],
            0.22260435254784533,
        )
        self.assertAlmostEqual(
            result["max_pairwise_logit_spread"], 0.058658042093, places=12
        )
        self.assertAlmostEqual(
            result["equivalent_score_points"], 0.26350806451725767, places=12
        )

    def test_lower_probability_ticket_dilutes_uniform_screen(self):
        result = lower_probability_addition_dilutes_uniform_screen(0.18, 0.10)
        self.assertTrue(result["added_probability_lower_than_best"])
        self.assertTrue(result["dilutes"])

    def test_equal_probability_ticket_does_not_dilute(self):
        result = lower_probability_addition_dilutes_uniform_screen(0.18, 0.18)
        self.assertFalse(result["added_probability_lower_than_best"])
        self.assertFalse(result["dilutes"])

    def test_equal_stake_formula(self):
        self.assertAlmostEqual(
            equal_stake_uniform_minimum_odds([0.18, 0.10]),
            2 * 1.10 / 0.28,
            places=12,
        )

    def test_invalid_probability_fails_closed(self):
        with self.assertRaises(CandidateDiagnosticError):
            minimum_core_odds(0.0)


if __name__ == "__main__":
    unittest.main()
