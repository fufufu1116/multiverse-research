import unittest

from target_environment_contract import (
    TargetEnvironmentEvidence,
    TargetEnvironmentGateError,
    canonical_receipt_sha256,
)

DIGEST = "a" * 64
ROLLBACK = "b" * 64

def valid(**overrides):
    data = dict(
        target_id="sealed-preprod-target-01",
        environment_class="PRE_PRODUCTION",
        artifact_sha256=DIGEST,
        rollback_artifact_sha256=ROLLBACK,
        credential_scope="least-privilege documented",
        credential_provisioning="ephemeral injection documented",
        credential_rotation="rotation drill evidence pending target execution",
        credential_revocation="revocation drill evidence pending target execution",
        provider_idempotency="bounded no-effect adapter contract",
        duplicate_request_control="duplicate negative control specified",
        state_store_binding="exact target state-store identity required",
        backup_restore="backup/restore drill required",
        crash_restart_recovery="restart recovery drill required",
        host_model="explicit single-host proof ceiling until demonstrated otherwise",
        lease_fencing="lease owner/fencing evidence required",
        health_readiness="health/readiness receipt required",
        logs_metrics_alerts="operator-visible telemetry required",
        kill_switch="engaged by default",
        rollback_execution="rollback drill required",
    )
    data.update(overrides)
    return TargetEnvironmentEvidence(**data)

class ContractTests(unittest.TestCase):
    def test_valid_no_effect_receipt(self):
        receipt = valid().receipt()
        self.assertEqual(receipt["runtime"], "OFF")
        self.assertFalse(receipt["ready_for_activation"])
        self.assertEqual(len(canonical_receipt_sha256(receipt)), 64)

    def test_target_identity_required(self):
        with self.assertRaises(TargetEnvironmentGateError):
            valid(target_id=" ").validate()

    def test_environment_class_fail_closed(self):
        with self.assertRaises(TargetEnvironmentGateError):
            valid(environment_class="PRODUCTION_LIVE").validate()

    def test_digest_format_fail_closed(self):
        with self.assertRaises(TargetEnvironmentGateError):
            valid(artifact_sha256="bad").validate()

    def test_missing_evidence_fail_closed(self):
        with self.assertRaises(TargetEnvironmentGateError):
            valid(backup_restore="").validate()

    def test_runtime_activation_forbidden(self):
        with self.assertRaises(TargetEnvironmentGateError):
            valid(runtime_activation=True).validate()

    def test_network_forbidden(self):
        with self.assertRaises(TargetEnvironmentGateError):
            valid(network_enabled=True).validate()

    def test_external_effect_forbidden(self):
        with self.assertRaises(TargetEnvironmentGateError):
            valid(external_effect_enabled=True).validate()

    def test_spend_forbidden(self):
        with self.assertRaises(TargetEnvironmentGateError):
            valid(spend_enabled=True).validate()

    def test_protected_keirin_data_forbidden(self):
        with self.assertRaises(TargetEnvironmentGateError):
            valid(protected_keirin_data_enabled=True).validate()

    def test_production_credentials_forbidden(self):
        with self.assertRaises(TargetEnvironmentGateError):
            valid(production_credentials_enabled=True).validate()

    def test_bool_subclass_trick_rejected(self):
        with self.assertRaises(TargetEnvironmentGateError):
            valid(runtime_activation=0).validate()

if __name__ == "__main__":
    unittest.main()
