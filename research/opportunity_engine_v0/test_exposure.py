import unittest

from research.opportunity_engine_v0.exposure import (
    ExposureMode,
    ExposureProfile,
    evaluate_exposure,
)
from research.opportunity_engine_v0.scale import ScaleClass


class ExposurePolicyTests(unittest.TestCase):
    def profile(self, **overrides):
        data = dict(
            scale_class=ScaleClass.TACTICAL,
            copy_risk=2,
            strategic_leakage_risk=1,
            buyer_value=4,
            time_sensitivity=5,
            core_method_exposed=False,
            proprietary_data_exposed=False,
            creates_competitor_against_us=False,
            expires_naturally=True,
            independently_useful_without_multiverse=True,
        )
        data.update(overrides)
        return ExposureProfile(**data)

    def test_tactical_signal_can_be_sold(self):
        result = evaluate_exposure(self.profile())
        self.assertEqual(result.mode, ExposureMode.SELL_SIGNAL)

    def test_sustaining_output_can_be_playbook(self):
        result = evaluate_exposure(
            self.profile(scale_class=ScaleClass.SUSTAINING, expires_naturally=False)
        )
        self.assertEqual(result.mode, ExposureMode.SELL_PLAYBOOK)

    def test_growth_output_only_bounded_license(self):
        result = evaluate_exposure(
            self.profile(scale_class=ScaleClass.GROWTH, time_sensitivity=2, expires_naturally=False)
        )
        self.assertEqual(result.mode, ExposureMode.LIMITED_LICENSE)

    def test_platform_candidate_is_kept_internal(self):
        result = evaluate_exposure(self.profile(scale_class=ScaleClass.PLATFORM))
        self.assertEqual(result.mode, ExposureMode.KEEP_INTERNAL)
        self.assertIn("HIGH_SCALE_OPTION_VALUE_KEEP_INTERNAL", result.blockers)

    def test_core_method_is_never_sold(self):
        result = evaluate_exposure(self.profile(core_method_exposed=True))
        self.assertEqual(result.mode, ExposureMode.KEEP_INTERNAL)
        self.assertIn("CORE_METHOD_EXPOSED", result.blockers)

    def test_proprietary_data_is_never_sold(self):
        result = evaluate_exposure(self.profile(proprietary_data_exposed=True))
        self.assertEqual(result.mode, ExposureMode.KEEP_INTERNAL)
        self.assertIn("PROPRIETARY_DATA_EXPOSED", result.blockers)

    def test_dangerous_copy_risk_is_kept_internal(self):
        result = evaluate_exposure(
            self.profile(copy_risk=5, creates_competitor_against_us=True)
        )
        self.assertEqual(result.mode, ExposureMode.KEEP_INTERNAL)
        self.assertIn("SALE_CREATES_DANGEROUS_COMPETITOR", result.blockers)

    def test_output_must_have_standalone_value(self):
        result = evaluate_exposure(
            self.profile(independently_useful_without_multiverse=False)
        )
        self.assertEqual(result.mode, ExposureMode.KEEP_INTERNAL)
        self.assertIn("OUTPUT_NOT_SELLABLE_ON_ITS_OWN", result.blockers)


if __name__ == "__main__":
    unittest.main()
