import unittest
from unittest.mock import patch

from research.opportunity_engine_v0.current_main_contract_binding import (
    assess_current_main_contract_binding,
    binding_authority_ceiling,
)


class CurrentMainContractBindingTests(unittest.TestCase):
    def test_current_contract_is_compatible_with_bridge_assumptions(self):
        result = assess_current_main_contract_binding()
        self.assertTrue(result.compatible)
        self.assertEqual(result.findings, ())
        self.assertEqual(result.task_schema, "MULTIVERSE_RESEARCH_TASK_v2")
        self.assertEqual(result.result_schema, "MULTIVERSE_RESEARCH_RESULT_v1")

    def test_task_schema_drift_fails_closed(self):
        with patch(
            "research.opportunity_engine_v0.current_main_contract_binding.canonical_model.TASK_SCHEMA_V2",
            "MULTIVERSE_RESEARCH_TASK_v3",
        ):
            result = assess_current_main_contract_binding()
        self.assertFalse(result.compatible)
        self.assertIn("TASK_V2_SCHEMA_DRIFT", result.findings)

    def test_result_schema_drift_fails_closed(self):
        with patch(
            "research.opportunity_engine_v0.current_main_contract_binding.canonical_model.RESULT_SCHEMA",
            "MULTIVERSE_RESEARCH_RESULT_v2",
        ):
            result = assess_current_main_contract_binding()
        self.assertFalse(result.compatible)
        self.assertIn("RESULT_SCHEMA_DRIFT", result.findings)

    def test_missing_source_ref_primitive_fails_closed(self):
        with patch(
            "research.opportunity_engine_v0.current_main_contract_binding.canonical_model.ALLOWED_PRIMITIVES",
            {"SUBTREE_HASH"},
        ):
            result = assess_current_main_contract_binding()
        self.assertFalse(result.compatible)
        self.assertIn("SOURCE_REF_PRIMITIVE_MISSING", result.findings)

    def test_weakened_nonauthority_boundary_fails_closed(self):
        with patch(
            "research.opportunity_engine_v0.current_main_contract_binding.canonical_model.NONAUTHORITY_KEYS",
            {"adoption", "merge"},
        ):
            result = assess_current_main_contract_binding()
        self.assertFalse(result.compatible)
        self.assertIn("NONAUTHORITY_BOUNDARY_WEAKENED", result.findings)

    def test_missing_evidence_manifest_fails_closed(self):
        with patch(
            "research.opportunity_engine_v0.current_main_contract_binding.canonical_model.TASK_V2_KEYS",
            {"schema", "task_id"},
        ):
            result = assess_current_main_contract_binding()
        self.assertFalse(result.compatible)
        self.assertIn("EVIDENCE_MANIFEST_MISSING", result.findings)

    def test_binding_never_grants_authority(self):
        ceiling = binding_authority_ceiling()
        self.assertTrue(ceiling)
        self.assertTrue(all(value is False for value in ceiling.values()))


if __name__ == "__main__":
    unittest.main()
