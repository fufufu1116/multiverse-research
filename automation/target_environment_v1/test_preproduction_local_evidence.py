import unittest

from preproduction_local_evidence import run_local_drill
from target_environment_contract import REQUIRED_EVIDENCE_DOMAINS, TargetEnvironmentEvidence


class PreproductionLocalEvidenceTests(unittest.TestCase):
    def test_local_drill_binds_to_contract_and_stays_no_effect(self):
        result = run_local_drill()
        self.assertEqual(result["environment_class"], "PRE_PRODUCTION")
        self.assertEqual(set(result["evidence_refs"]), REQUIRED_EVIDENCE_DOMAINS)
        evidence = TargetEnvironmentEvidence(
            target_id=result["target_id"],
            environment_class=result["environment_class"],
            artifact_sha256=result["artifact_sha256"],
            rollback_artifact_sha256=result["rollback_artifact_sha256"],
            evidence_refs=result["evidence_refs"],
            network_enabled=result["network_enabled"],
            external_effect_enabled=result["external_effect_enabled"],
            spend_enabled=result["spend_enabled"],
            protected_keirin_data_enabled=result["protected_keirin_data_enabled"],
            production_credentials_enabled=result["production_credentials_enabled"],
            runtime_activation=result["runtime_activation"],
        )
        receipt = evidence.receipt()
        self.assertEqual(receipt["runtime"], "OFF")
        self.assertFalse(receipt["ready_for_activation"])
        self.assertTrue(result["evidence_payloads"]["backup_restore"]["pass"])
        self.assertTrue(result["evidence_payloads"]["crash_restart_recovery"]["pass"])
        self.assertTrue(result["evidence_payloads"]["lease_fencing"]["pass"])
        self.assertFalse(result["evidence_payloads"]["host_model"]["multi_host_proven"])
        self.assertFalse(result["evidence_payloads"]["logs_metrics_alerts"]["production_alerting_proven"])


if __name__ == "__main__":
    unittest.main()
