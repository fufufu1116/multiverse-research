import unittest

from research.opportunity_engine_v0.convergence_slice_validator import (
    slice_a_authority_ceiling,
    validate_adoption_slice_paths,
)


class ConvergenceSliceValidatorTests(unittest.TestCase):
    def test_pure_domain_paths_are_allowed(self):
        result = validate_adoption_slice_paths([
            "research/opportunity_engine_v0/model.py",
            "research/opportunity_engine_v0/engine.py",
            "research/opportunity_engine_v0/market_discovery.py",
        ])
        self.assertTrue(result.valid)
        self.assertEqual(result.findings, ())

    def test_bridge_path_is_rejected(self):
        result = validate_adoption_slice_paths([
            "research/opportunity_engine_v0/multiverse_bridge.py",
        ])
        self.assertFalse(result.valid)
        self.assertTrue(any("HIGH_COUPLING_PATH_FORBIDDEN" in x for x in result.findings))

    def test_provider_path_is_rejected(self):
        result = validate_adoption_slice_paths([
            "research/opportunity_engine_v0/provider_escalation.py",
        ])
        self.assertFalse(result.valid)

    def test_customer_stage_path_is_rejected(self):
        result = validate_adoption_slice_paths([
            "research/opportunity_engine_v0/hundred_user_general.py",
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

    def test_slice_a_grants_no_authority(self):
        ceiling = slice_a_authority_ceiling()
        self.assertTrue(ceiling)
        self.assertTrue(all(value is False for value in ceiling.values()))


if __name__ == "__main__":
    unittest.main()
