from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from automation.runtime_convergence_v1.runtime_convergence_validator import (
    build_convergence_receipt,
)


ROOT = Path(__file__).resolve().parent
AUTOMATION = ROOT.parent
CONTRACT = json.loads((ROOT / "CONVERGENCE_CONTRACT_v1.json").read_text())
LEDGER = json.loads((ROOT / "PROVENANCE_LEDGER_v1.json").read_text())


class RuntimeConvergenceTests(unittest.TestCase):
    def test_exact_materialized_subtrees(self):
        expected = {
            "automation/shared_engine":
                "36208a51847b01f6185efd690649694e94645bda",
        }

        for item in CONTRACT["materialized_subtrees"].values():
            expected[item["path"]] = item["subtree"]

        for path, sha in expected.items():
            actual = subprocess.check_output(
                ["git", "rev-parse", f"HEAD:{path}"],
                text=True,
            ).strip()
            self.assertEqual(actual, sha, path)

    def test_convergence_receipt(self):
        receipt = build_convergence_receipt()
        self.assertEqual(receipt["status"], "READY_FOR_INDEPENDENT_REVIEW")
        self.assertEqual(
            receipt["proof_ceiling"],
            "RUNTIME_CONVERGENCE_REPOSITORY_PREPARATION_ONLY",
        )
        self.assertEqual(receipt["runtime"], "OFF")
        self.assertEqual(receipt["distributed_safety"]["fence_sequence"], [1, 2, 3])
        self.assertEqual(receipt["distributed_safety"]["operation_count"], 1)
        self.assertIs(
            receipt["distributed_safety"]["duplicate_external_effect"],
            False,
        )

    def test_all_convergence_authority_false(self):
        for key, value in CONTRACT["authority"].items():
            self.assertIs(type(value), bool, key)
            self.assertIs(value, False, key)

    def test_runtime_supervisor_is_sealed_and_kill_switch_default_on(self):
        source = (
            AUTOMATION / "runtime_v1" / "runtime_supervisor.py"
        ).read_text()
        self.assertIn('MODE = "SEALED_DRY_RUN"', source)
        self.assertIn('self._set_default(c, "kill_switch", "1")', source)
        self.assertNotIn('self._set_default(c, "kill_switch", "0")', source)

    def test_deployment_contract_default_deny(self):
        source = (
            AUTOMATION / "deployment_v1" / "deployment_contract.py"
        ).read_text()
        self.assertIn('RUNTIME = "OFF"', source)
        self.assertIn('"runtime_activation": False', source)
        self.assertIn('"external_effect": False', source)
        self.assertIn('"spend": False', source)
        self.assertIn('"protected_keirin_data": False', source)
        self.assertIn('"secret_persistence": False', source)

    def test_remote_multi_host_exact_state(self):
        receipt = json.loads(
            (
                AUTOMATION
                / "remote_multihost_render_v1"
                / "REMOTE_EVIDENCE_RECEIPT_v2.json"
            ).read_text()
        )
        self.assertEqual(receipt["drill"]["phase"], "COMPLETE")
        self.assertEqual(receipt["drill"]["current_fence_token"], 3)
        self.assertEqual(receipt["drill"]["operation_count"], 1)
        self.assertEqual(receipt["workers"]["worker-a"]["boot_count"], 2)
        self.assertEqual(receipt["workers"]["worker-b"]["boot_count"], 1)
        self.assertIs(receipt["drill"]["duplicate_external_effect"], False)

    def test_adopted_single_host_lineage_excludes_later_pr123_head(self):
        item = CONTRACT["materialized_subtrees"]["remote_preprod_render_v1"]
        self.assertEqual(
            item["source_commit"],
            "f673d5eb53d5831ce345ff3262970cad6bcd0f9a",
        )
        self.assertEqual(
            item["explicitly_excludes_later_pr123_head"],
            "f5cdc340a1e80281d4805e0f7701cb92a63e8402",
        )
        self.assertNotEqual(
            item["source_commit"],
            item["explicitly_excludes_later_pr123_head"],
        )

    def test_superseded_failures_cannot_be_current_pass(self):
        self.assertEqual(
            LEDGER["rule"],
            "Superseded FIX_REQUIRED or FALSE artifacts are provenance only and can never satisfy a current PASS gate.",
        )
        real = LEDGER["real_multi_host"]
        self.assertNotEqual(
            real["historical_lab_fix_required"],
            real["final_lab_pass"],
        )
        self.assertNotEqual(
            real["historical_auditor_fix_required"],
            real["final_auditor_pass"],
        )
        self.assertEqual(real["final_t2_pass"], 5554935885)

    def test_no_raw_connection_secret_in_durable_evidence(self):
        durable = [
            ROOT / "CONVERGENCE_CONTRACT_v1.json",
            ROOT / "PROVENANCE_LEDGER_v1.json",
            ROOT / "README.md",
            AUTOMATION
            / "remote_preprod_render_v1"
            / "REMOTE_EVIDENCE_RECEIPT_v1.json",
            AUTOMATION
            / "remote_multihost_render_v1"
            / "REMOTE_EVIDENCE_RECEIPT_v2.json",
            AUTOMATION
            / "remote_multihost_render_v1"
            / "PROVIDER_OBSERVABILITY_v2.json",
        ]
        for path in durable:
            raw = path.read_text(errors="ignore")
            self.assertNotIn("postgresql://", raw, str(path))
            self.assertNotIn("postgres://", raw, str(path))
            self.assertNotIn("DATABASE_URL=", raw, str(path))


if __name__ == "__main__":
    unittest.main()
