import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RECEIPT = json.loads((ROOT / "REMOTE_EVIDENCE_RECEIPT_v2.json").read_text())
OBS = json.loads((ROOT / "PROVIDER_OBSERVABILITY_v2.json").read_text())
SEAL = json.loads((ROOT / "CANDIDATE_SEAL_v2.json").read_text())
APP = (ROOT / "app.py").read_text()


class FinalEvidenceV2Tests(unittest.TestCase):
    def test_exact_lineage_and_scope(self):
        self.assertEqual(
            RECEIPT["canonical_main"],
            "a6f56facc80709f2e7b8218d927484d522bfa356",
        )
        self.assertEqual(
            RECEIPT["deployed_head"],
            "5d9b06e0e04495c3d3a3fe7dc5a1971f31fd3474",
        )
        self.assertEqual(
            RECEIPT["deployed_tree"],
            "7b96eabbe5717593069fa358fbb9151a3719c629",
        )
        self.assertEqual(
            RECEIPT["proof_ceiling"],
            "REMOTE_MULTI_HOST_PREPRODUCTION_RENDER_NO_EFFECT_EVIDENCE_ONLY",
        )
        self.assertEqual(RECEIPT["runtime"], "OFF")

    def test_real_two_worker_provider_binding(self):
        workers = RECEIPT["workers"]
        self.assertEqual(
            workers["worker-a"]["service_id"],
            "srv-dae4cs8n74is73cbj7vg",
        )
        self.assertEqual(
            workers["worker-b"]["service_id"],
            "srv-dae4cugn74is73cbjfu0",
        )
        self.assertNotEqual(
            workers["worker-a"]["service_id"],
            workers["worker-b"]["service_id"],
        )
        self.assertEqual(workers["worker-a"]["plan"], "free")
        self.assertEqual(workers["worker-b"]["plan"], "free")
        self.assertEqual(
            RECEIPT["shared_postgres"]["id"],
            "dpg-dadou0on74is73b09570-a",
        )
        self.assertEqual(RECEIPT["shared_postgres"]["plan"], "free")

    def test_final_distributed_safety_receipt(self):
        drill = RECEIPT["drill"]
        self.assertEqual(drill["phase"], "COMPLETE")
        self.assertEqual(drill["current_owner"], "worker-a")
        self.assertEqual(drill["current_fence_token"], 3)
        self.assertEqual(drill["operation_count"], 1)
        self.assertEqual(drill["simulated_effect_count"], 1)
        self.assertIs(drill["duplicate_external_effect"], False)
        self.assertIs(drill["fatal_error_present"], False)

        expected = {
            "worker_a_token_1_acquired",
            "worker_b_early_acquire_rejected_lease_held",
            "worker_b_token_2_acquired",
            "stale_fence_token_1_rejected",
            "same_key_same_payload_duplicate_suppressed",
            "same_key_different_payload_rejected",
            "stale_worker_a_rejected",
            "split_brain_reacquire_rejected",
            "worker_a_restart_observed",
            "worker_a_token_3_acquired",
            "restart_duplicate_suppressed",
            "restart_failover_complete",
            "final_phase_complete",
        }
        self.assertEqual(set(drill["events"]), expected)
        self.assertTrue(all(drill["events"].values()))

    def test_restart_persistence(self):
        a = RECEIPT["workers"]["worker-a"]
        b = RECEIPT["workers"]["worker-b"]
        self.assertEqual(a["boot_count"], 2)
        self.assertEqual(b["boot_count"], 1)
        self.assertEqual(
            a["restart_deploy_id"],
            "dep-dae6gilbedkc73bh778g",
        )
        self.assertTrue(
            a["final_instance_id"].endswith("b2c7q")
        )

    def test_provider_observability_without_http_slo_claim(self):
        self.assertTrue(OBS["worker_a"]["cpu_timeseries_present"])
        self.assertTrue(OBS["worker_a"]["memory_timeseries_present"])
        self.assertTrue(OBS["worker_b"]["cpu_timeseries_present"])
        self.assertTrue(OBS["worker_b"]["memory_timeseries_present"])
        self.assertTrue(
            OBS["worker_a"]["restart_instance_transition_observed"]
        )
        self.assertTrue(OBS["worker_a"]["final_evidence_get_http_200_at"])
        self.assertIs(OBS["claims"]["http_slo"], False)
        self.assertIs(OBS["claims"]["network_partition_timing"], False)

    def test_real_postgres_locking_source(self):
        self.assertIn("FOR UPDATE", APP)
        self.assertIn("mv_mh1_control", APP)
        self.assertIn("mv_mh1_operations", APP)
        self.assertIn("clock_timestamp()", APP)

    def test_authority_is_exact_false(self):
        for artifact in (RECEIPT, SEAL):
            for key, value in artifact["authority"].items():
                self.assertIs(type(value), bool)
                self.assertIs(value, False)
        self.assertEqual(RECEIPT["incremental_spend_ceiling_usd"], 0)
        self.assertEqual(SEAL["runtime"], "OFF")

    def test_no_raw_connection_secret_in_durable_artifacts(self):
        durable = (
            "REMOTE_TARGET_BINDING_v1.json",
            "REMOTE_EVIDENCE_RECEIPT_v2.json",
            "PROVIDER_OBSERVABILITY_v2.json",
            "CANDIDATE_SEAL_v2.json",
            "RECOVERY_DRILL_v2.md",
            "README.md",
        )
        for name in durable:
            raw = (ROOT / name).read_text(errors="ignore")
            self.assertNotIn("postgresql://", raw)
            self.assertNotIn("postgres://", raw)
            self.assertNotIn("DATABASE_URL=", raw)


if __name__ == "__main__":
    unittest.main()
