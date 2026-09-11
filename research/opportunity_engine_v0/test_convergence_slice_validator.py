import unittest

from research.opportunity_engine_v0.convergence_slice_validator import (
    slice_a_authority_ceiling,
    slice_authority_ceiling,
    validate_adoption_slice_paths,
)


class ConvergenceSliceValidatorTests(unittest.TestCase):
    def test_slice_a_pure_domain_paths_are_allowed(self):
        result = validate_adoption_slice_paths([
            "research/opportunity_engine_v0/model.py",
            "research/opportunity_engine_v0/engine.py",
            "research/opportunity_engine_v0/market_discovery.py",
        ])
        self.assertTrue(result.valid)
        self.assertEqual(result.findings, ())

    def test_slice_b_forecast_paths_are_allowed(self):
        result = validate_adoption_slice_paths([
            "research/opportunity_engine_v0/forecast_ledger.py",
            "research/opportunity_engine_v0/forecast_revision.py",
            "research/opportunity_engine_v0/trend_forecast.py",
            "research/opportunity_engine_v0/trend_retrospective.py",
        ], profile="B_FORECAST_INTEGRITY")
        self.assertTrue(result.valid)

    def test_slice_c_customer_paths_are_allowed(self):
        result = validate_adoption_slice_paths([
            "research/opportunity_engine_v0/customer_value_loop.py",
            "research/opportunity_engine_v0/customer_contribution.py",
            "research/opportunity_engine_v0/hundred_user_general.py",
            "research/opportunity_engine_v0/growth_loop.py",
        ], profile="C_CUSTOMER_VALUE_HUNDRED_USER")
        self.assertTrue(result.valid)

    def test_slice_a_rejects_forecast_path(self):
        result = validate_adoption_slice_paths([
            "research/opportunity_engine_v0/forecast_revision.py",
        ], profile="A_CORE_DOMAIN")
        self.assertFalse(result.valid)

    def test_slice_b_rejects_customer_path(self):
        result = validate_adoption_slice_paths([
            "research/opportunity_engine_v0/hundred_user_general.py",
        ], profile="B_FORECAST_INTEGRITY")
        self.assertFalse(result.valid)

    def test_slice_c_rejects_forecast_path(self):
        result = validate_adoption_slice_paths([
            "research/opportunity_engine_v0/trend_forecast.py",
        ], profile="C_CUSTOMER_VALUE_HUNDRED_USER")
        self.assertFalse(result.valid)

    def test_bridge_path_is_rejected_in_all_profiles(self):
        for profile in ("A_CORE_DOMAIN", "B_FORECAST_INTEGRITY", "C_CUSTOMER_VALUE_HUNDRED_USER"):
            result = validate_adoption_slice_paths([
                "research/opportunity_engine_v0/multiverse_bridge.py",
            ], profile=profile)
            self.assertFalse(result.valid)

    def test_provider_path_is_rejected(self):
        result = validate_adoption_slice_paths([
            "research/opportunity_engine_v0/provider_escalation.py",
        ])
        self.assertFalse(result.valid)

    def test_path_outside_module_is_rejected(self):
        result = validate_adoption_slice_paths(["README.md"])
        self.assertFalse(result.valid)
        self.assertIn("OUTSIDE_OPPORTUNITY_ENGINE:README.md", result.findings)

    def test_parent_escape_is_rejected(self):
        result = validate_adoption_slice_paths([
            "research/opportunity_engine_v0/../automation/review_dispatcher_v1/dispatcher.py",
        ])
        self.assertFalse(result.valid)
        self.assertTrue(any(x.startswith("UNSAFE_PATH:") for x in result.findings))

    def test_duplicates_are_rejected(self):
        result = validate_adoption_slice_paths([
            "research/opportunity_engine_v0/model.py",
            "research/opportunity_engine_v0/model.py",
        ])
        self.assertFalse(result.valid)
        self.assertIn("DUPLICATE_PATH", result.findings)

    def test_unknown_profile_fails_closed(self):
        result = validate_adoption_slice_paths([
            "research/opportunity_engine_v0/model.py",
        ], profile="UNKNOWN")
        self.assertFalse(result.valid)
        self.assertIn("UNKNOWN_PROFILE:UNKNOWN", result.findings)

    def test_all_slices_grant_no_authority(self):
        for ceiling in (slice_a_authority_ceiling(), slice_authority_ceiling()):
            self.assertTrue(ceiling)
            self.assertTrue(all(value is False for value in ceiling.values()))


if __name__ == "__main__":
    unittest.main()
