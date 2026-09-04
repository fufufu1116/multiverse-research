import unittest

from target_environment_contract import (
    REQUIRED_EVIDENCE_DOMAINS,
    TargetEnvironmentEvidence,
    TargetEnvironmentGateError,
    canonical_receipt_sha256,
)

DIGEST = "a" * 64
ROLLBACK = "b" * 64

def refs():
    return {
        domain: f"EVIDENCE_REF:test/{domain}/001"
        for domain in REQUIRED_EVIDENCE_DOMAINS
    }

def valid(**overrides):
    data = dict(
        target_id="sealed-preprod-target-01",
        environment_class="PRE_PRODUCTION",
        artifact_sha256=DIGEST,
        rollback_artifact_sha256=ROLLBACK,
        evidence_refs=refs(),
    )
    data.update(overrides)
    return TargetEnvironmentEvidence(**data)

class EqualToPreprod:
    def __eq__(self, other):
        return other == "PRE_PRODUCTION"
    def __hash__(self):
        return hash("PRE_PRODUCTION")

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

    def test_environment_class_custom_equality_rejected(self):
        with self.assertRaises(TargetEnvironmentGateError):
            valid(environment_class=EqualToPreprod()).validate()

    def test_environment_class_str_subclass_rejected(self):
        class S(str):
            pass
        with self.assertRaises(TargetEnvironmentGateError):
            valid(environment_class=S("PRE_PRODUCTION")).validate()

    def test_digest_format_fail_closed(self):
        with self.assertRaises(TargetEnvironmentGateError):
            valid(artifact_sha256="bad").validate()

    def test_evidence_ref_domain_set_exact(self):
        bad = refs()
        bad.pop("backup_restore")
        with self.assertRaises(TargetEnvironmentGateError):
            valid(evidence_refs=bad).validate()

    def test_extra_evidence_ref_rejected(self):
        bad = refs()
        bad["extra"] = "EVIDENCE_REF:test/extra/001"
        with self.assertRaises(TargetEnvironmentGateError):
            valid(evidence_refs=bad).validate()

    def test_evidence_refs_must_be_exact_dict(self):
        class D(dict):
            pass
        with self.assertRaises(TargetEnvironmentGateError):
            valid(evidence_refs=D(refs())).validate()

    def test_evidence_ref_prefix_required(self):
        bad = refs()
        bad["backup_restore"] = "pending"
        with self.assertRaises(TargetEnvironmentGateError):
            valid(evidence_refs=bad).validate()

    def test_evidence_ref_str_subclass_rejected(self):
        class S(str):
            pass
        bad = refs()
        bad["backup_restore"] = S("EVIDENCE_REF:test/backup/001")
        with self.assertRaises(TargetEnvironmentGateError):
            valid(evidence_refs=bad).validate()

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

    def test_bool_type_confusion_rejected(self):
        for value in (0, 0.0, None, "false"):
            with self.subTest(value=value):
                with self.assertRaises(TargetEnvironmentGateError):
                    valid(runtime_activation=value).validate()

    def test_receipt_hash_rejects_non_dict(self):
        with self.assertRaises(TargetEnvironmentGateError):
            canonical_receipt_sha256([])

if __name__ == "__main__":
    unittest.main()
