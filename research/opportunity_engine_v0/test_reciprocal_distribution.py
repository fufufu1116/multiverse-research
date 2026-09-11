import unittest

from .reciprocal_distribution import (
    LoopVerdict,
    ReciprocalDistributionProfile,
    assess_reciprocal_distribution,
)


class ReciprocalDistributionTests(unittest.TestCase):
    def test_recipe_app_social_loop_can_be_flywheel_candidate(self):
        result = assess_reciprocal_distribution(ReciprocalDistributionProfile(5, 5, 4, 5, 5, 1, 2, 1))
        self.assertEqual(result["verdict"], LoopVerdict.FLYWHEEL_CANDIDATE.value)

    def test_strong_outbound_weak_return_is_one_way(self):
        result = assess_reciprocal_distribution(ReciprocalDistributionProfile(5, 1, 4, 4, 1, 1, 1, 1))
        self.assertEqual(result["verdict"], LoopVerdict.ONE_WAY_ACQUISITION.value)

    def test_two_way_value_without_strong_repeat_is_reciprocal(self):
        result = assess_reciprocal_distribution(ReciprocalDistributionProfile(4, 4, 3, 3, 3, 1, 2, 1))
        self.assertEqual(result["verdict"], LoopVerdict.RECIPROCAL_LOOP.value)

    def test_high_policy_risk_fails_closed(self):
        result = assess_reciprocal_distribution(ReciprocalDistributionProfile(5, 5, 5, 5, 5, 0, 0, 4))
        self.assertEqual(result["verdict"], LoopVerdict.REJECT.value)

    def test_unclear_rights_fails_closed(self):
        result = assess_reciprocal_distribution(ReciprocalDistributionProfile(5, 5, 5, 5, 5, 0, 0, 0, rights_unclear=True))
        self.assertEqual(result["verdict"], LoopVerdict.REJECT.value)

    def test_flywheel_never_authorizes_execution(self):
        result = assess_reciprocal_distribution(ReciprocalDistributionProfile(5, 5, 4, 5, 5, 1, 2, 1))
        self.assertFalse(result["automatic_execution_authorized"])


if __name__ == "__main__":
    unittest.main()
