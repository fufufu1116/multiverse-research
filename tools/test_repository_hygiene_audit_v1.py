from __future__ import annotations

import unittest

from tools.repository_hygiene_audit_v1 import audit, classify_name


class RepositoryHygieneAuditTests(unittest.TestCase):
    def test_protected_precedes_other_name_hints(self):
        self.assertEqual(
            classify_name("v3/ECON_HOLDOUT1000_CURRENT_STATE_v1.json"),
            "PROTECTED_SEALED",
        )

    def test_receipt_is_evidence(self):
        self.assertEqual(
            classify_name("governance/OWNER_ADOPTION_RECEIPT_20260912_v1.json"),
            "EVIDENCE_IMMUTABLE",
        )

    def test_current_name_is_only_candidate_not_authority(self):
        self.assertEqual(
            classify_name("governance/CORE_CURRENT_STATE_v2.json"),
            "CURRENT_POINTER_CANDIDATE",
        )

    def test_nested_workflow_tree_detected(self):
        result = audit([
            ".github/workflows/a.yml",
            ".github/workflows/.github/workflows/remote-proof.yml",
        ])
        self.assertTrue(any(f["code"] == "NESTED_WORKFLOW_TREE" for f in result["findings"]))
        self.assertFalse(result["deletion_authority"])

    def test_multiple_current_like_same_directory_detected(self):
        result = audit([
            "governance/MULTIVERSE_CORE_CURRENT_STATE_20260902_v1.json",
            "governance/MULTIVERSE_CORE_CURRENT_STATE_20260902_v2.json",
        ])
        codes = [f["code"] for f in result["findings"]]
        self.assertIn("MULTIPLE_CURRENT_LIKE_FILES_SAME_DIRECTORY", codes)

    def test_version_siblings_require_index_not_delete(self):
        result = audit([
            "automation/orchestrator_role_relay_v3.py",
            "automation/orchestrator_role_relay_v4.py",
        ])
        hit = [f for f in result["findings"] if f["code"] == "VERSION_SIBLINGS_REQUIRE_LIFECYCLE_INDEX"]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["decision"], "CONSOLIDATION_CANDIDATE")
        self.assertFalse(result["deletion_authority"])

    def test_read_only_runtime_off(self):
        result = audit(["MULTIVERSE_BOOTSTRAP.md"])
        self.assertEqual(result["mode"], "READ_ONLY")
        self.assertEqual(result["runtime"], "OFF")
        self.assertFalse(result["deletion_authority"])


if __name__ == "__main__":
    unittest.main()
