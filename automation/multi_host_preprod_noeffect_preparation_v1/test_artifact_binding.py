import json
import unittest
from pathlib import Path

from automation.multi_host_preprod_noeffect_preparation_v1.multi_host_contract import (
    AUTHORITY,
    ENVIRONMENT_CLASS,
    PROOF_CEILING,
    RUNTIME,
    TOPOLOGY_CLASS,
    build_preparation_contract,
    run_synthetic_failover_drill,
)


ROOT = Path(__file__).resolve().parent


class ArtifactBindingTests(unittest.TestCase):
    def load(self, name):
        return json.loads((ROOT / name).read_text())

    def test_static_preparation_contract_matches_executable_core(self):
        static = self.load("PREPARATION_CONTRACT_v1.json")
        dynamic = build_preparation_contract()

        for key in (
            "topology_class",
            "environment_class",
            "provider_family",
            "planned_topology",
            "lease_contract",
            "idempotency_contract",
            "future_remote_evidence_requirements",
            "authority",
            "runtime",
            "proof_ceiling",
        ):
            with self.subTest(key=key):
                self.assertEqual(static[key], dynamic[key])

        self.assertEqual(static["authority_comment"], 5549695338)
        self.assertEqual(static["issue"], 126)
        self.assertEqual(static["authority_issue"], 125)
        self.assertEqual(
            static["adopted_single_host_head"],
            "f673d5eb53d5831ce345ff3262970cad6bcd0f9a",
        )
        self.assertEqual(
            static["excluded_later_pr123_head"],
            "f5cdc340a1e80281d4805e0f7701cb92a63e8402",
        )

    def test_static_synthetic_receipt_exactly_matches_executable_drill(self):
        static = self.load("SYNTHETIC_EVIDENCE_RECEIPT_v1.json")
        dynamic = run_synthetic_failover_drill()
        self.assertEqual(static, dynamic)

    def test_all_persisted_authority_is_exact_false(self):
        for filename in (
            "PREPARATION_CONTRACT_v1.json",
            "SYNTHETIC_EVIDENCE_RECEIPT_v1.json",
        ):
            artifact = self.load(filename)
            self.assertEqual(set(artifact["authority"]), set(AUTHORITY))
            for key, value in artifact["authority"].items():
                with self.subTest(filename=filename, key=key):
                    self.assertIs(type(value), bool)
                    self.assertIs(value, False)

    def test_exact_boundary_constants(self):
        self.assertEqual(
            TOPOLOGY_CLASS,
            "RENDER_PREPRODUCTION_TWO_SERVICE_SHARED_POSTGRES_NO_EFFECT_v1",
        )
        self.assertEqual(ENVIRONMENT_CLASS, "PRE_PRODUCTION")
        self.assertEqual(
            PROOF_CEILING,
            "MULTI_HOST_PREPRODUCTION_SYNTHETIC_NO_EFFECT_PREPARATION_ONLY",
        )
        self.assertEqual(RUNTIME, "OFF")

    def test_no_real_resource_identity_is_manufactured(self):
        contract = self.load("PREPARATION_CONTRACT_v1.json")
        topology = contract["planned_topology"]

        self.assertEqual(
            [item["service_identity"] for item in topology["workers"]],
            ["UNPROVISIONED_WORKER_A", "UNPROVISIONED_WORKER_B"],
        )
        self.assertEqual(
            topology["shared_state"]["identity"],
            "UNPROVISIONED_SHARED_POSTGRES",
        )
        self.assertTrue(
            all(item["provisioned"] is False for item in topology["workers"])
        )
        self.assertIs(topology["shared_state"]["provisioned"], False)
        self.assertIs(
            topology["actual_remote_execution_performed"],
            False,
        )


if __name__ == "__main__":
    unittest.main()
