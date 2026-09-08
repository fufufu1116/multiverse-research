from __future__ import annotations

import copy
import json
import unittest

from automation.review_dispatcher_v1 import validator


class CurrentBaselineValidatorTests(unittest.TestCase):
    def _baseline(self):
        return json.loads(validator.BASELINE.read_text())

    def _convergence(self):
        return validator.CONVERGENCE.read_text()

    def test_01_current_request_only_baseline_positive_contract_passes(self):
        checks = {}
        findings = []
        validator._record_current_baseline(checks, findings, self._baseline())
        validator._record_current_convergence(checks, findings, self._convergence())
        self.assertEqual(findings, [])
        self.assertTrue(checks)
        self.assertTrue(all(value == "PASS" for value in checks.values()))

    def test_02_migration_era_baseline_is_rejected(self):
        stale = copy.deepcopy(self._baseline())
        stale["status"] = "CANDIDATE_NOT_YET_ADOPTED"
        stale["baseline_version"] = "2026-09-07.review-dispatcher-v1"
        stale["shared_pipeline_policy"] = {
            "before_installation": "owner_may_replace_steps",
            "after_installation": "immutable_shared_pipeline_definition",
            "per_chat_step_replacement": "deprecated_after_installation",
        }
        checks = {}
        findings = []
        validator._record_current_baseline(checks, findings, stale)
        self.assertTrue(findings)
        self.assertEqual(checks["current_baseline:status"], "FIX_REQUIRED")
        self.assertEqual(checks["current_baseline:baseline_version"], "FIX_REQUIRED")
        self.assertEqual(
            checks["current_baseline:shared_pipeline_policy:migration_state"],
            "FIX_REQUIRED",
        )

    def test_03_unsafe_shared_pipeline_policy_drift_fails_closed(self):
        drift = copy.deepcopy(self._baseline())
        drift["shared_pipeline_policy"]["research_lane_may_edit_steps"] = True
        drift["shared_pipeline_policy"]["per_chat_step_replacement"] = "ALLOWED"
        checks = {}
        findings = []
        validator._record_current_baseline(checks, findings, drift)
        self.assertTrue(findings)
        self.assertEqual(
            checks["current_baseline:shared_pipeline_policy:research_lane_may_edit_steps"],
            "FIX_REQUIRED",
        )
        self.assertEqual(
            checks["current_baseline:shared_pipeline_policy:per_chat_step_replacement"],
            "FIX_REQUIRED",
        )

    def test_04_current_convergence_drift_fails_closed(self):
        current = self._convergence()
        required = validator.CURRENT_CONVERGENCE_REQUIRED[2]
        drift = current.replace(required, "")
        checks = {}
        findings = []
        validator._record_current_convergence(checks, findings, drift)
        self.assertTrue(findings)
        key = f"current_convergence:{required[:32]}"
        self.assertEqual(checks[key], "FIX_REQUIRED")

    def test_05_only_exact_stale_legacy_keys_are_suppressed(self):
        six = [
            "baseline:status: mismatch",
            "baseline:baseline_version: mismatch",
            "baseline:pipeline_policy: mismatch",
        ] + [
            f"convergence:{token[:30]}: missing"
            for token in validator.STALE_MIGRATION_CONVERGENCE_TOKENS
        ]
        self.assertEqual(len(six), 6)
        self.assertTrue(all(validator._is_obsolete_legacy_finding(item) for item in six))
        self.assertFalse(
            validator._is_obsolete_legacy_finding(
                "baseline:runtime: expected OFF, got ON"
            )
        )
        self.assertFalse(
            validator._is_obsolete_legacy_finding(
                "convergence:Runtime remains OFF: missing"
            )
        )


if __name__ == "__main__":
    unittest.main()
