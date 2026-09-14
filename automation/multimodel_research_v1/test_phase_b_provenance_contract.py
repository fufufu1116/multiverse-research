from __future__ import annotations

import copy
import unittest

from automation.multimodel_research_v1.model import ResearchContractError, sha256_json
from automation.multimodel_research_v1.phase_b_provenance_contract import (
    ASSIGNMENT_SCHEMA,
    RECEIPT_SCHEMA,
    RESULT_SCHEMA_V2,
    receipt_authenticates_external_provider,
    validate_assignment,
    validate_execution_receipt,
    validate_result_v2,
)


NONAUTHORITY = {
    "adoption": False,
    "merge": False,
    "main_mutation": False,
    "ruleset_mutation": False,
    "workflow_dispatch_rerun": False,
    "runtime_activation": False,
    "provider_effect": False,
    "production": False,
    "protected_data": False,
    "live_business_effect": False,
    "spend": False,
}


def task_v2(network: str = "PUBLIC_READ_ONLY") -> dict:
    digest = "1" * 64
    return {
        "schema": "MULTIVERSE_RESEARCH_TASK_v2",
        "task_id": "task-provenance-001",
        "snapshot_id": "snapshot-provenance-001",
        "created_at": "2026-09-15T00:00:00Z",
        "domain": "MULTIMODEL_RESEARCH",
        "objective": "Synthetic provenance contract validation only.",
        "source_refs": [
            {
                "kind": "PUBLIC_DOC",
                "ref": "https://example.invalid/evidence",
                "sha256": digest,
                "observed_at": "2026-09-14T23:59:00Z",
            }
        ],
        "allowed_primitives": ["PUBLIC_EVIDENCE_REF"],
        "constraints": {
            "network_access": network,
            "max_compute_seconds": 120,
            "max_output_bytes": 100000,
            "max_findings": 8,
        },
        "requested_roles": ["RESEARCHER", "CHALLENGER"],
        "nonauthority": copy.deepcopy(NONAUTHORITY),
        "evidence_manifest": [
            {
                "primitive": "PUBLIC_EVIDENCE_REF",
                "ref": "https://example.invalid/evidence",
                "sha256": digest,
                "observed_at": "2026-09-14T23:59:00Z",
            }
        ],
    }


def assignment(task: dict, mode: str = "SYNTHETIC_OFFLINE", provider: str = "SYNTHETIC_PROVIDER", model: str = "synthetic-model-a") -> dict:
    live = mode == "LIVE_ADVISORY"
    return {
        "schema": ASSIGNMENT_SCHEMA,
        "assignment_id": "assignment-provenance-001",
        "task_id": task["task_id"],
        "task_sha256": sha256_json(task),
        "snapshot_id": task["snapshot_id"],
        "target": {"provider": provider, "model": model},
        "requested_role": "RESEARCHER",
        "adapter_sha256": "2" * 64,
        "execution_mode": mode,
        "research_network_access": "PUBLIC_READ_ONLY" if live else "NONE",
        "provider_transport": "ADVISORY_ONLY" if live else "DISABLED",
        "limits": {
            "max_compute_seconds": 60,
            "max_output_bytes": 50000,
        },
        "attestation_required": live,
        "nonauthority": copy.deepcopy(NONAUTHORITY),
    }


def result_v2(task: dict, a: dict) -> dict:
    return {
        "schema": RESULT_SCHEMA_V2,
        "task_id": task["task_id"],
        "task_sha256": sha256_json(task),
        "assignment_sha256": sha256_json(a),
        "submission_id": "submission-provenance-001",
        "snapshot_id": task["snapshot_id"],
        "produced_at": "2026-09-15T00:02:00Z",
        "model_identity": {
            "provider": a["target"]["provider"],
            "model": a["target"]["model"],
            "role": a["requested_role"],
        },
        "status": "COMPLETED",
        "findings": [
            {
                "finding_id": "finding-provenance-001",
                "claim_key": "claim-provenance-001",
                "position": "SUPPORT",
                "severity": "INFO",
                "assertion": "Synthetic contract path preserves exact assignment provenance.",
                "evidence": {
                    "primitive": "PUBLIC_EVIDENCE_REF",
                    "ref": "https://example.invalid/evidence",
                    "sha256": "1" * 64,
                },
                "confidence": 0.8,
                "uncertainty": "Synthetic-only contract evidence.",
                "recommendation": "Keep provider authority separate.",
                "validation_plan": "Run fail-closed unit tests.",
            }
        ],
        "uncertainty_factors": ["synthetic-only"],
        "nonauthority": copy.deepcopy(NONAUTHORITY),
    }


def receipt(task: dict, a: dict, result: dict, state: str = "SYNTHETIC_OFFLINE") -> dict:
    live = a["execution_mode"] == "LIVE_ADVISORY"
    return {
        "schema": RECEIPT_SCHEMA,
        "task_id": task["task_id"],
        "task_sha256": sha256_json(task),
        "assignment_sha256": sha256_json(a),
        "submission_id": result["submission_id"],
        "adapter_sha256": a["adapter_sha256"],
        "execution_mode": a["execution_mode"],
        "request_started_at": "2026-09-15T00:01:00Z",
        "response_received_at": "2026-09-15T00:02:00Z",
        "provider_reference_id": "provider-ref-001" if live and state == "LIVE_ATTESTED" else None,
        "observed_provider": a["target"]["provider"],
        "observed_model": a["target"]["model"],
        "provider_response_sha256": "3" * 64,
        "result_sha256": sha256_json(result),
        "attestation_state": state,
        "nonauthority": copy.deepcopy(NONAUTHORITY),
    }


class ProvenanceContractTests(unittest.TestCase):
    def test_565_valid_synthetic_assignment(self):
        t = task_v2()
        a = assignment(t)
        self.assertIs(validate_assignment(t, a), a)

    def test_566_same_task_can_bind_two_provider_assignments(self):
        t = task_v2()
        a1 = assignment(t, provider="SYNTHETIC_A", model="model-a")
        a2 = assignment(t, provider="SYNTHETIC_B", model="model-b")
        a2["assignment_id"] = "assignment-provenance-002"
        self.assertEqual(a1["task_sha256"], a2["task_sha256"])
        self.assertNotEqual(sha256_json(a1), sha256_json(a2))
        validate_assignment(t, a1)
        validate_assignment(t, a2)

    def test_567_assignment_role_must_be_requested(self):
        t = task_v2()
        a = assignment(t)
        a["requested_role"] = "UNREQUESTED_ROLE"
        with self.assertRaisesRegex(ResearchContractError, "ASSIGNMENT_ROLE_NOT_REQUESTED"):
            validate_assignment(t, a)

    def test_568_assignment_cannot_widen_compute(self):
        t = task_v2()
        a = assignment(t)
        a["limits"]["max_compute_seconds"] = 121
        with self.assertRaisesRegex(ResearchContractError, "ASSIGNMENT_COMPUTE_WIDENING"):
            validate_assignment(t, a)

    def test_569_assignment_cannot_widen_output(self):
        t = task_v2()
        a = assignment(t)
        a["limits"]["max_output_bytes"] = 100001
        with self.assertRaisesRegex(ResearchContractError, "ASSIGNMENT_OUTPUT_WIDENING"):
            validate_assignment(t, a)

    def test_570_synthetic_transport_forbidden(self):
        t = task_v2()
        a = assignment(t)
        a["provider_transport"] = "ADVISORY_ONLY"
        with self.assertRaisesRegex(ResearchContractError, "SYNTHETIC_PROVIDER_TRANSPORT_FORBIDDEN"):
            validate_assignment(t, a)

    def test_571_synthetic_network_must_be_none(self):
        t = task_v2()
        a = assignment(t)
        a["research_network_access"] = "PUBLIC_READ_ONLY"
        with self.assertRaisesRegex(ResearchContractError, "SYNTHETIC_NETWORK_MUST_BE_NONE"):
            validate_assignment(t, a)

    def test_572_live_assignment_requires_attestation(self):
        t = task_v2()
        a = assignment(t, mode="LIVE_ADVISORY", provider="EXAMPLE_PROVIDER", model="example-model")
        a["attestation_required"] = False
        with self.assertRaisesRegex(ResearchContractError, "LIVE_ADVISORY_ATTESTATION_REQUIRED"):
            validate_assignment(t, a)

    def test_573_task_network_none_blocks_live_assignment(self):
        t = task_v2(network="NONE")
        a = assignment(t, mode="LIVE_ADVISORY", provider="EXAMPLE_PROVIDER", model="example-model")
        with self.assertRaisesRegex(ResearchContractError, "ASSIGNMENT_NETWORK_WIDENING"):
            validate_assignment(t, a)

    def test_574_result_v2_binds_exact_assignment(self):
        t = task_v2()
        a = assignment(t)
        r = result_v2(t, a)
        self.assertIs(validate_result_v2(t, a, r), r)

    def test_575_result_v2_rejects_wrong_assignment_digest(self):
        t = task_v2()
        a = assignment(t)
        r = result_v2(t, a)
        r["assignment_sha256"] = "f" * 64
        with self.assertRaisesRegex(ResearchContractError, "RESULT_V2_ASSIGNMENT_SHA256_MISMATCH"):
            validate_result_v2(t, a, r)

    def test_576_result_v2_rejects_provider_mismatch(self):
        t = task_v2()
        a = assignment(t)
        r = result_v2(t, a)
        r["model_identity"]["provider"] = "OTHER_PROVIDER"
        with self.assertRaisesRegex(ResearchContractError, "RESULT_V2_PROVIDER_MISMATCH"):
            validate_result_v2(t, a, r)

    def test_577_result_v2_rejects_model_mismatch(self):
        t = task_v2()
        a = assignment(t)
        r = result_v2(t, a)
        r["model_identity"]["model"] = "other-model"
        with self.assertRaisesRegex(ResearchContractError, "RESULT_V2_MODEL_MISMATCH"):
            validate_result_v2(t, a, r)

    def test_578_synthetic_receipt_exact_binding(self):
        t = task_v2()
        a = assignment(t)
        r = result_v2(t, a)
        x = receipt(t, a, r)
        self.assertIs(validate_execution_receipt(t, a, r, x), x)
        self.assertFalse(receipt_authenticates_external_provider(x))

    def test_579_receipt_rejects_adapter_drift(self):
        t = task_v2()
        a = assignment(t)
        r = result_v2(t, a)
        x = receipt(t, a, r)
        x["adapter_sha256"] = "9" * 64
        with self.assertRaisesRegex(ResearchContractError, "RECEIPT_ADAPTER_SHA256_MISMATCH"):
            validate_execution_receipt(t, a, r, x)

    def test_580_receipt_rejects_result_substitution(self):
        t = task_v2()
        a = assignment(t)
        r = result_v2(t, a)
        x = receipt(t, a, r)
        x["result_sha256"] = "8" * 64
        with self.assertRaisesRegex(ResearchContractError, "RECEIPT_RESULT_SHA256_MISMATCH"):
            validate_execution_receipt(t, a, r, x)

    def test_581_receipt_cannot_start_before_task(self):
        t = task_v2()
        a = assignment(t)
        r = result_v2(t, a)
        x = receipt(t, a, r)
        x["request_started_at"] = "2026-09-14T23:59:59Z"
        with self.assertRaisesRegex(ResearchContractError, "RECEIPT_STARTED_BEFORE_TASK"):
            validate_execution_receipt(t, a, r, x)

    def test_582_live_attested_receipt_requires_exact_provider_model(self):
        t = task_v2()
        a = assignment(t, mode="LIVE_ADVISORY", provider="EXAMPLE_PROVIDER", model="example-model")
        r = result_v2(t, a)
        x = receipt(t, a, r, state="LIVE_ATTESTED")
        x["observed_model"] = "wrong-model"
        with self.assertRaisesRegex(ResearchContractError, "LIVE_ATTESTED_MODEL_MISMATCH"):
            validate_execution_receipt(t, a, r, x)

    def test_583_unverified_live_receipt_is_not_authenticated_diversity(self):
        t = task_v2()
        a = assignment(t, mode="LIVE_ADVISORY", provider="EXAMPLE_PROVIDER", model="example-model")
        r = result_v2(t, a)
        x = receipt(t, a, r, state="LIVE_PROVIDER_ID_UNVERIFIED")
        validate_execution_receipt(t, a, r, x)
        self.assertFalse(receipt_authenticates_external_provider(x))

    def test_584_live_attested_receipt_authenticates_external_provider(self):
        t = task_v2()
        a = assignment(t, mode="LIVE_ADVISORY", provider="EXAMPLE_PROVIDER", model="example-model")
        r = result_v2(t, a)
        x = receipt(t, a, r, state="LIVE_ATTESTED")
        validate_execution_receipt(t, a, r, x)
        self.assertTrue(receipt_authenticates_external_provider(x))

    def test_585_nonauthority_cannot_become_true(self):
        t = task_v2()
        a = assignment(t)
        a["nonauthority"]["provider_effect"] = True
        with self.assertRaisesRegex(ResearchContractError, "PROVENANCE_NONAUTHORITY_NOT_FALSE:provider_effect"):
            validate_assignment(t, a)

    def test_586_credential_like_key_rejected(self):
        t = task_v2()
        a = assignment(t)
        a["target"]["credential_hint"] = "forbidden"
        with self.assertRaises(ResearchContractError):
            validate_assignment(t, a)


if __name__ == "__main__":
    unittest.main()
