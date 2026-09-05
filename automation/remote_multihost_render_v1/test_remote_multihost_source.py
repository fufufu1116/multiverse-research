import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
APP = (ROOT / "app.py").read_text()
BINDING = json.loads((ROOT / "REMOTE_TARGET_BINDING_v1.json").read_text())


class RemoteMultiHostSourceTests(unittest.TestCase):
    def test_exact_target_binding(self):
        self.assertEqual(
            BINDING["target_class"],
            "RENDER_PREPRODUCTION_TWO_SERVICE_SHARED_POSTGRES_NO_EFFECT_v1",
        )
        self.assertEqual(BINDING["environment_class"], "PRE_PRODUCTION")
        self.assertEqual(BINDING["provider"], "RENDER")
        self.assertEqual(BINDING["region"], "singapore")
        self.assertIs(BINDING["auto_deploy"], False)
        self.assertEqual(
            BINDING["deployed_workload_source_commit"],
            "3b9748cee8d4a9e4769ea8b58d496580617a79e5",
        )

    def test_two_exact_free_worker_services(self):
        workers = BINDING["workers"]
        self.assertEqual(len(workers), 2)
        self.assertEqual(
            [item["worker_id"] for item in workers],
            ["worker-a", "worker-b"],
        )
        self.assertNotEqual(workers[0]["service_id"], workers[1]["service_id"])
        for worker in workers:
            self.assertEqual(worker["plan"], "free")
            self.assertEqual(worker["region"], "singapore")

    def test_shared_postgres_binding(self):
        state = BINDING["shared_state"]
        self.assertEqual(state["postgres_id"], "dpg-dadou0on74is73b09570-a")
        self.assertEqual(state["plan"], "free")
        self.assertEqual(state["region"], "singapore")
        self.assertEqual(state["version"], 18)
        self.assertIs(state["high_availability"], False)
        self.assertEqual(state["table_namespace"], "mv_mh1_")
        self.assertIs(state["database_url_stored_in_github"], False)

    def test_zero_spend_and_runtime_off(self):
        spend = BINDING["spend_boundary"]
        self.assertEqual(spend["incremental_monetary_spend_ceiling_usd"], 0)
        self.assertIs(spend["paid_upgrade_authorized"], False)
        self.assertIs(spend["paid_external_service_authorized"], False)
        self.assertEqual(BINDING["runtime"], "OFF")
        self.assertIs(BINDING["runtime_activation"], False)

    def test_real_postgres_row_lock_mechanism_is_present(self):
        self.assertIn("FOR UPDATE", APP)
        self.assertIn("mv_mh1_control", APP)
        self.assertIn("mv_mh1_operations", APP)
        self.assertIn("clock_timestamp()", APP)

    def test_http_state_changes_are_denied(self):
        self.assertIn("def do_POST", APP)
        self.assertIn("def do_PUT", APP)
        self.assertIn("def do_PATCH", APP)
        self.assertIn("def do_DELETE", APP)
        self.assertIn("state_changes_disabled_over_http", APP)
        self.assertIn("403", APP)

    def test_exact_runtime_and_authority_gates_are_present(self):
        for token in (
            'RUNTIME = "OFF"',
            "MULTIVERSE_MULTIHOST_EXECUTION_AUTHORIZED",
            "MULTIVERSE_LIVE_BUSINESS_EFFECT",
            "MULTIVERSE_PROTECTED_KEIRIN_DATA",
            "MULTIVERSE_PRODUCTION_CREDENTIALS",
            "MULTIVERSE_INCREMENTAL_SPEND_USD",
            "MULTIVERSE_POSTGRES_ID",
            "MULTIVERSE_RENDER_SERVICE_ID",
        ):
            self.assertIn(token, APP)

    def test_github_artifacts_contain_no_connection_secret(self):
        for path in ROOT.iterdir():
            if not path.is_file():
                continue
            raw = path.read_text(errors="ignore")
            self.assertNotIn("postgresql://", raw)
            self.assertNotIn("postgres://", raw)
            self.assertNotIn("DATABASE_URL=", raw)


if __name__ == "__main__":
    unittest.main()
