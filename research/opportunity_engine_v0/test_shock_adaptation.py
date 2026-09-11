import unittest

from .shock_adaptation import ShockAdaptationProfile, ShockVerdict, assess_shock_adaptation


class ShockAdaptationTests(unittest.TestCase):
    def test_compliant_forced_upgrade_can_be_constraint_inversion(self):
        result = assess_shock_adaptation(ShockAdaptationProfile(5, 5, 5, 4, 3, 3, 4, 4, 1000, 2, 1, 1, 4))
        self.assertEqual(result["verdict"], ShockVerdict.CONSTRAINT_INVERSION.value)

    def test_jurisdiction_escape_is_not_innovation(self):
        result = assess_shock_adaptation(ShockAdaptationProfile(5, 2, 5, 5, 5, 5, 5, 5, 0, 1, 0, 1, 5, evasion_or_jurisdiction_escape=True))
        self.assertEqual(result["verdict"], ShockVerdict.REJECT.value)

    def test_harmful_exploitation_fails_closed(self):
        result = assess_shock_adaptation(ShockAdaptationProfile(5, 5, 5, 5, 5, 5, 5, 5, 0, 1, 0, 1, 5, harmful_exploitation=True))
        self.assertEqual(result["verdict"], ShockVerdict.REJECT.value)

    def test_deception_fails_closed(self):
        result = assess_shock_adaptation(ShockAdaptationProfile(5, 5, 5, 5, 5, 5, 5, 5, 0, 1, 0, 1, 5, deceptive=True))
        self.assertEqual(result["verdict"], ShockVerdict.REJECT.value)

    def test_weak_replacement_stays_hold(self):
        result = assess_shock_adaptation(ShockAdaptationProfile(1, 5, 2, 1, 1, 1, 1, 1, 3000, 10, 2, 1, 1))
        self.assertEqual(result["verdict"], ShockVerdict.HOLD.value)

    def test_positive_adaptation_never_authorizes_execution(self):
        result = assess_shock_adaptation(ShockAdaptationProfile(5, 5, 5, 4, 3, 3, 4, 4, 1000, 2, 1, 1, 4))
        self.assertFalse(result["automatic_execution_authorized"])


if __name__ == "__main__":
    unittest.main()
