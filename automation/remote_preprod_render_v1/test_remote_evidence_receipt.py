import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent

EXPECTED_MAIN = "a6f56facc80709f2e7b8218d927484d522bfa356"
EXPECTED_CODE_COMMIT = "9da766ac53a3f99b8f4d3eaa21b5aec00fec63e9"
EXPECTED_SERVICE = "srv-dadou8pt0dsc73fg73cg"
EXPECTED_POSTGRES = "dpg-dadou0on74is73b09570-a"
EXPECTED_TARGET = "RENDER_REMOTE_PREPRODUCTION_SINGLE_SERVICE_NO_EFFECT_v1"
EXPECTED_PROOF = "REMOTE_PREPRODUCTION_SINGLE_RENDER_NO_EFFECT_EVIDENCE_ONLY"


def load(name):
    return json.loads((ROOT / name).read_text())


class RemoteTargetBindingTests(unittest.TestCase):
    def test_exact_target_binding_and_zero_spend(self):
        binding = load("REMOTE_TARGET_BINDING_v1.json")

        self.assertEqual(binding["canonical_main"], EXPECTED_MAIN)
        self.assertEqual(binding["provider"], "RENDER")
        self.assertEqual(binding["provider_target_class"], EXPECTED_TARGET)
        self.assertEqual(binding["environment_class"], "PRE_PRODUCTION")

        service = binding["service"]
        self.assertEqual(service["id"], EXPECTED_SERVICE)
        self.assertEqual(service["plan"], "free")
        self.assertEqual(service["region"], "singapore")
        self.assertEqual(service["deployed_code_commit"], EXPECTED_CODE_COMMIT)
        self.assertIs(service["auto_deploy"], False)

        state = binding["state_store"]
        self.assertEqual(state["id"], EXPECTED_POSTGRES)
        self.assertEqual(state["plan"], "free")
        self.assertEqual(state["region"], "singapore")
        self.assertIs(state["high_availability"], False)

        spend = binding["spend_boundary"]
        self.assertEqual(spend["incremental_monetary_spend_ceiling_usd"], 0)
        self.assertIs(spend["paid_upgrade_authorized"], False)
        self.assertIs(spend["paid_external_service_authorized"], False)

        self.assertEqual(binding["runtime"], "OFF")
        self.assertIs(binding["runtime_activation"], False)
        self.assertEqual(binding["proof_ceiling"], EXPECTED_PROOF)

    def test_no_secret_or_production_authority_is_persisted(self):
        binding = load("REMOTE_TARGET_BINDING_v1.json")

        credential = binding["credential_boundary"]
        self.assertIs(credential["database_url_stored_in_github"], False)
        self.assertIs(credential["production_credentials_enabled"], False)

        boundary = binding["network_effect_boundary"]
        for key, value in boundary.items():
            with self.subTest(key=key):
                self.assertIs(type(value), bool)
                self.assertIs(value, False)

        raw = (ROOT / "REMOTE_TARGET_BINDING_v1.json").read_text()
        self.assertNotIn("postgresql://", raw)
        self.assertNotIn("postgres://", raw)
        self.assertNotIn("DATABASE_URL=", raw)


class RemoteEvidenceReceiptTests(unittest.TestCase):
    def test_database_bound_pass_receipt(self):
        receipt = load("REMOTE_EVIDENCE_RECEIPT_v1.json")

        self.assertEqual(receipt["target_class"], EXPECTED_TARGET)
        self.assertEqual(receipt["environment_class"], "PRE_PRODUCTION")
        self.assertEqual(receipt["service_id"], EXPECTED_SERVICE)
        self.assertEqual(receipt["postgres_id"], EXPECTED_POSTGRES)
        self.assertEqual(receipt["deployed_code_commit"], EXPECTED_CODE_COMMIT)

        first = receipt["first_database_bound_deploy"]
        self.assertEqual(first["provider_status"], "live")
        self.assertIs(first["database_bound"], True)
        self.assertIs(first["execution_authorized"], True)
        self.assertIs(first["ready"], True)
        self.assertEqual(first["previous_boot_count"], 0)
        self.assertEqual(first["current_boot_count"], 1)
        self.assertIs(first["backup_restore_match"], True)
        self.assertEqual(
            first["backup_snapshot_sha256"],
            first["restore_snapshot_sha256"],
        )
        self.assertEqual(len(first["backup_snapshot_sha256"]), 64)
        self.assertIs(first["lease_fencing_pass"], True)
        self.assertEqual(first["lease_owner"], "worker-b")
        self.assertEqual(first["fence_token"], 2)
        self.assertIs(first["idempotency_pass"], True)
        self.assertEqual(first["idempotency_first_count"], 1)
        self.assertEqual(first["idempotency_second_count"], 1)
        self.assertIs(first["duplicate_external_effect"], False)
        self.assertEqual(first["findings"], [])

    def test_restart_persistence_is_observed_on_new_instance(self):
        receipt = load("REMOTE_EVIDENCE_RECEIPT_v1.json")
        first = receipt["first_database_bound_deploy"]
        restart = receipt["restart_persistence_deploy"]

        self.assertNotEqual(first["instance_id"], restart["instance_id"])
        self.assertIs(restart["database_bound"], True)
        self.assertIs(restart["ready"], True)
        self.assertEqual(restart["previous_boot_count"], 1)
        self.assertEqual(restart["current_boot_count"], 2)
        self.assertIs(restart["restart_persistence_observable"], True)
        self.assertIs(restart["backup_restore_match"], True)
        self.assertEqual(
            restart["backup_snapshot_sha256"],
            restart["restore_snapshot_sha256"],
        )
        self.assertEqual(len(restart["backup_snapshot_sha256"]), 64)
        self.assertIs(restart["lease_fencing_pass"], True)
        self.assertIs(restart["idempotency_pass"], True)
        self.assertIs(restart["duplicate_external_effect"], False)
        self.assertEqual(restart["findings"], [])

    def test_authority_remains_fail_closed(self):
        receipt = load("REMOTE_EVIDENCE_RECEIPT_v1.json")

        for key, value in receipt["authority"].items():
            with self.subTest(key=key):
                self.assertIs(type(value), bool)
                self.assertIs(value, False)

        spend = receipt["spend"]
        self.assertEqual(spend["service_plan"], "free")
        self.assertEqual(spend["database_plan"], "free")
        self.assertEqual(spend["incremental_monetary_spend_ceiling_usd"], 0)

        self.assertEqual(receipt["runtime"], "OFF")
        self.assertEqual(receipt["proof_ceiling"], EXPECTED_PROOF)

    def test_provider_observability_is_bound(self):
        receipt = load("REMOTE_EVIDENCE_RECEIPT_v1.json")
        obs = receipt["provider_observability"]

        self.assertIs(obs["render_logs_observed"], True)
        self.assertIs(obs["render_cpu_metrics_observed"], True)
        self.assertIs(obs["render_memory_metrics_observed"], True)
        self.assertIs(obs["restart_instance_metrics_observed"], True)
        self.assertEqual(
            obs["restart_instance_id"],
            receipt["restart_persistence_deploy"]["instance_id"],
        )

    def test_receipt_contains_no_secret_connection_string(self):
        raw = (ROOT / "REMOTE_EVIDENCE_RECEIPT_v1.json").read_text()
        self.assertNotIn("postgresql://", raw)
        self.assertNotIn("postgres://", raw)
        self.assertNotIn("DATABASE_URL=", raw)


if __name__ == "__main__":
    unittest.main()
