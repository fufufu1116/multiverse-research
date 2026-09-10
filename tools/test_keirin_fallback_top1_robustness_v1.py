import math
import unittest

from keirin_fallback_top1_robustness_v1 import (
    FallbackTop1RobustnessError,
    evaluate_top1_robustness,
    required_score_gap,
)

BETA = 0.22260435254784533
DELTA_MIN = -0.020537046719
DELTA_MAX = 0.038120995374


class TestFallbackTop1Robustness(unittest.TestCase):
    def test_required_gap_exact_reference(self):
        self.assertAlmostEqual(
            required_score_gap(BETA, DELTA_MIN, DELTA_MAX),
            0.26350806451725767,
            places=15,
        )

    def test_takeo_r5_is_robust(self):
        scores = {1:79.875, 2:72.37, 3:74.0, 4:72.19, 5:71.454, 6:67.111}
        out = evaluate_top1_robustness(
            scores, beta=BETA, delta_min=DELTA_MIN, delta_max=DELTA_MAX
        )
        self.assertEqual(out["top_car"], 1)
        self.assertEqual(out["second_car"], 3)
        self.assertAlmostEqual(out["score_gap"], 5.875, places=12)
        self.assertTrue(out["robust_top1_under_supported_fallback"])
        self.assertGreater(out["worst_case_logit_margin"], 1.24)

    def test_exact_boundary_is_not_strictly_robust(self):
        threshold = required_score_gap(BETA, DELTA_MIN, DELTA_MAX)
        out = evaluate_top1_robustness(
            {1:100.0 + threshold, 2:100.0},
            beta=BETA, delta_min=DELTA_MIN, delta_max=DELTA_MAX,
        )
        self.assertFalse(out["robust_top1_under_supported_fallback"])

    def test_above_boundary_is_robust(self):
        threshold = required_score_gap(BETA, DELTA_MIN, DELTA_MAX)
        out = evaluate_top1_robustness(
            {1:100.0 + threshold + 1e-6, 2:100.0},
            beta=BETA, delta_min=DELTA_MIN, delta_max=DELTA_MAX,
        )
        self.assertTrue(out["robust_top1_under_supported_fallback"])

    def test_tie_is_not_robust(self):
        out = evaluate_top1_robustness(
            {2:100.0, 1:100.0}, beta=BETA,
            delta_min=DELTA_MIN, delta_max=DELTA_MAX,
        )
        self.assertFalse(out["robust_top1_under_supported_fallback"])
        self.assertEqual(out["top_car"], 1)

    def test_zero_q_bound_makes_positive_gap_robust(self):
        out = evaluate_top1_robustness(
            {1:100.000001, 2:100.0}, beta=BETA,
            delta_min=DELTA_MIN, delta_max=DELTA_MAX, abs_q_bound=0.0,
        )
        self.assertTrue(out["robust_top1_under_supported_fallback"])
        self.assertEqual(out["required_score_gap"], 0.0)

    def test_invalid_beta_rejected(self):
        with self.assertRaises(FallbackTop1RobustnessError):
            required_score_gap(0.0, DELTA_MIN, DELTA_MAX)

    def test_reversed_delta_range_rejected(self):
        with self.assertRaises(FallbackTop1RobustnessError):
            required_score_gap(BETA, DELTA_MAX, DELTA_MIN)

    def test_negative_q_bound_rejected(self):
        with self.assertRaises(FallbackTop1RobustnessError):
            required_score_gap(BETA, DELTA_MIN, DELTA_MAX, -1.0)

    def test_nonfinite_score_rejected(self):
        with self.assertRaises(FallbackTop1RobustnessError):
            evaluate_top1_robustness(
                {1: math.inf, 2: 1.0}, beta=BETA,
                delta_min=DELTA_MIN, delta_max=DELTA_MAX,
            )

    def test_too_few_scores_rejected(self):
        with self.assertRaises(FallbackTop1RobustnessError):
            evaluate_top1_robustness(
                {1: 100.0}, beta=BETA,
                delta_min=DELTA_MIN, delta_max=DELTA_MAX,
            )

    def test_input_order_does_not_change_result(self):
        a = evaluate_top1_robustness(
            {1:101.0, 2:100.0, 3:90.0}, beta=BETA,
            delta_min=DELTA_MIN, delta_max=DELTA_MAX,
        )
        b = evaluate_top1_robustness(
            {3:90.0, 2:100.0, 1:101.0}, beta=BETA,
            delta_min=DELTA_MIN, delta_max=DELTA_MAX,
        )
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
