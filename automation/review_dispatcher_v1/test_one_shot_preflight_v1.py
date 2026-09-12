from __future__ import annotations

import io
import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

from automation.review_dispatcher_v1.one_shot_preflight_v1 import (
    FIXED_ARTIFACT_SCHEMA,
    PREFLIGHT_SCHEMA,
    _failure_class,
    _safe_extract_tar,
    _tail,
    classify_review_outcome,
)


class OneShotPreflightTests(unittest.TestCase):
    def _artifact(self, *, verdict="PASS", findings=None, test_count=10):
        return {
            "schema_version": FIXED_ARTIFACT_SCHEMA,
            "verdict": verdict,
            "findings": [] if findings is None else findings,
            "test_count": test_count,
        }

    def test_01_build63_rate_limit_signature_classifies_infra(self):
        self.assertEqual(
            _failure_class(
                "",
                "urllib.error.HTTPError: HTTP Error 403: rate limit exceeded",
            ),
            "INFRA_GITHUB_READ_RATE_LIMIT",
        )

    def test_02_429_rate_limit_signature_classifies_infra(self):
        self.assertEqual(
            _failure_class("HTTP Error 429: secondary rate limit", ""),
            "INFRA_GITHUB_READ_RATE_LIMIT",
        )

    def test_03_non_rate_limit_403_is_not_misclassified(self):
        self.assertEqual(
            _failure_class("", "urllib.error.HTTPError: HTTP Error 403: Forbidden"),
            "DISPATCHER_EXECUTION_FAILURE",
        )

    def test_04_dispatcher_contract_failure_is_distinct(self):
        self.assertEqual(
            _failure_class("DISPATCHER_FIX_REQUIRED:EXACT_OPEN_PR_COUNT:0", ""),
            "DISPATCHER_CONTRACT_FAILURE",
        )

    def test_05_pass_requires_zero_exit_pass_and_empty_findings(self):
        ready, classification, findings = classify_review_outcome(
            returncode=0,
            artifact=self._artifact(),
        )
        self.assertTrue(ready)
        self.assertEqual(classification, "PASS")
        self.assertEqual(findings, [])

    def test_06_build62_source_rule_finding_blocks_preflight(self):
        finding = (
            "source_contains:automation/multimodel_research_v1/"
            "phase_b_live_preauth.py:\"store\": False: missing"
        )
        ready, classification, findings = classify_review_outcome(
            returncode=1,
            artifact=self._artifact(
                verdict="FIX_REQUIRED", findings=[finding], test_count=556
            ),
        )
        self.assertFalse(ready)
        self.assertEqual(
            classification, "REVIEW_RECIPE_OR_CANDIDATE_FAILURE"
        )
        self.assertEqual(findings, [finding])

    def test_07_build64_per_module_count_finding_blocks_preflight(self):
        finding = (
            "unittest_count:automation.review_dispatcher_v1.test_dispatcher: "
            "52 != 132"
        )
        ready, classification, findings = classify_review_outcome(
            returncode=1,
            artifact=self._artifact(
                verdict="FIX_REQUIRED", findings=[finding], test_count=52
            ),
        )
        self.assertFalse(ready)
        self.assertEqual(
            classification, "REVIEW_RECIPE_OR_CANDIDATE_FAILURE"
        )
        self.assertEqual(findings, [finding])

    def test_08_missing_artifact_blocks_preflight(self):
        ready, classification, findings = classify_review_outcome(
            returncode=1,
            artifact=None,
        )
        self.assertFalse(ready)
        self.assertEqual(classification, "REVIEW_ARTIFACT_MISSING_OR_INVALID")
        self.assertEqual(findings, [])

    def test_09_wrong_artifact_schema_blocks_preflight(self):
        artifact = self._artifact()
        artifact["schema_version"] = "WRONG"
        ready, classification, findings = classify_review_outcome(
            returncode=1,
            artifact=artifact,
        )
        self.assertFalse(ready)
        self.assertEqual(classification, "REVIEW_ARTIFACT_SCHEMA_MISMATCH")
        self.assertTrue(findings)

    def test_10_nonpass_return_with_pass_payload_is_execution_failure(self):
        ready, classification, findings = classify_review_outcome(
            returncode=1,
            artifact=self._artifact(),
        )
        self.assertFalse(ready)
        self.assertEqual(classification, "REVIEW_EXECUTION_FAILURE")
        self.assertEqual(findings, [])

    def test_11_output_tail_is_bounded(self):
        text = "\n".join(str(i) for i in range(50))
        tail = _tail(text, lines=3)
        self.assertEqual(tail.splitlines(), ["47", "48", "49"])

    def test_12_archive_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tar_path = root / "bad.tar"
            payload = b"nope"
            with tarfile.open(tar_path, "w") as archive:
                info = tarfile.TarInfo("../escape.txt")
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
            destination = root / "out"
            destination.mkdir()
            with self.assertRaises(RuntimeError):
                _safe_extract_tar(tar_path, destination)

    def test_13_artifact_json_round_trip_shape_is_stable(self):
        artifact = self._artifact(
            verdict="FIX_REQUIRED",
            findings=["example"],
            test_count=52,
        )
        encoded = json.dumps(artifact, sort_keys=True, separators=(",", ":"))
        self.assertEqual(json.loads(encoded), artifact)

    def test_14_schema_name_is_fixed(self):
        self.assertEqual(PREFLIGHT_SCHEMA, "MULTIVERSE_ONE_SHOT_PREFLIGHT_v1")


if __name__ == "__main__":
    unittest.main()
