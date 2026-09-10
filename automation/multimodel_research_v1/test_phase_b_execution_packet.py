from __future__ import annotations

import copy
import json
import unittest

from automation.multimodel_research_v1.catalog_freshness import (
    build_catalog_freshness_receipt,
)
from automation.multimodel_research_v1.model import ResearchContractError, sha256_json
from automation.multimodel_research_v1.phase_b_execution_packet import (
    CATALOG_CHECKED_AT,
    CANONICAL_MAIN,
    CANONICAL_MULTIMODEL_SUBTREE,
    CANONICAL_TREE,
    FIRST_SMOKE_MAX_INPUT_TOKENS,
    FIRST_SMOKE_MAX_OUTPUT_TOKENS,
    REPOSITORY_MAX_COST_USD_MICROS,
    WIRE_SCHEMA_STRIPPED_KEYS,
    build_first_provider_execution_packet,
    catalog_snapshot,
    first_provider_execution_packet_sha256,
    official_verification,
    packet_summary,
    validate_first_provider_execution_packet,
)


class PhaseBFirstProviderExecutionPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = build_first_provider_execution_packet()

    def fresh(self) -> dict:
        return copy.deepcopy(self.packet)

    def assert_rejected(self, packet: dict) -> None:
        with self.assertRaises(ResearchContractError):
            validate_first_provider_execution_packet(packet)

    def test_497_execution_packet_validates(self) -> None:
        validated = validate_first_provider_execution_packet(self.fresh())
        self.assertEqual(validated["schema"], "MULTIVERSE_PHASE_B_FIRST_PROVIDER_EXECUTION_PACKET_v1")

    def test_498_mechanical_selection_is_gemini(self) -> None:
        selection = self.packet["mechanical_selection"]
        self.assertEqual(selection["selected_provider"], "GOOGLE_GEMINI")
        self.assertEqual(selection["selected_model_id"], "gemini-3.8-flash")

    def test_499_mechanical_costs_are_exact(self) -> None:
        rows = {row["provider"]: row for row in self.packet["eligible_provider_comparison"]}
        self.assertEqual(rows["GOOGLE_GEMINI"]["estimated_max_cost_usd_micros"], 39936)
        self.assertEqual(rows["ANTHROPIC_CLAUDE"]["estimated_max_cost_usd_micros"], 53248)

    def test_500_catalog_freshness_is_within_24h(self) -> None:
        receipt = self.packet["catalog"]["freshness_receipt"]
        self.assertEqual(receipt["checked_at"], CATALOG_CHECKED_AT)
        self.assertEqual(receipt["age_seconds"], 11520)
        self.assertLessEqual(receipt["age_seconds"], 86400)

    def test_501_stale_catalog_fails_closed(self) -> None:
        with self.assertRaises(ResearchContractError) as ctx:
            build_catalog_freshness_receipt(
                catalog_snapshot(),
                checked_at="2026-09-11T12:00:01Z",
            )
        self.assertEqual(str(ctx.exception), "CATALOG_SNAPSHOT_STALE")

    def test_502_provider_or_model_drift_fails_closed(self) -> None:
        packet = self.fresh()
        packet["mechanical_selection"]["selected_model_id"] = "drifted-model"
        self.assert_rejected(packet)

    def test_503_task_drift_fails_closed(self) -> None:
        packet = self.fresh()
        packet["synthetic_task"]["objective"] += " drift"
        self.assert_rejected(packet)

    def test_504_prompt_drift_fails_closed(self) -> None:
        packet = self.fresh()
        packet["pilot_matrix"]["prompt"]["objective"] += " drift"
        self.assert_rejected(packet)

    def test_505_rendered_body_drift_fails_closed(self) -> None:
        packet = self.fresh()
        packet["pilot_matrix"]["render"]["body"]["model"] = "drifted-model"
        self.assert_rejected(packet)

    def test_506_credential_material_leak_fails_closed(self) -> None:
        packet = self.fresh()
        packet["pilot_matrix"]["execution_prep"]["credential_material_in_repository"] = True
        self.assert_rejected(packet)

    def test_507_second_attempt_fails_closed(self) -> None:
        packet = self.fresh()
        packet["pilot_matrix"]["execution_prep"]["max_attempts"] = 2
        self.assert_rejected(packet)

    def test_508_excess_token_or_cost_ceiling_fails_closed(self) -> None:
        for key, value in (
            ("max_input_tokens", FIRST_SMOKE_MAX_INPUT_TOKENS + 1),
            ("max_output_tokens", FIRST_SMOKE_MAX_OUTPUT_TOKENS + 1),
            ("proposed_max_cost_usd_micros", REPOSITORY_MAX_COST_USD_MICROS + 1),
        ):
            packet = self.fresh()
            packet["pilot_matrix"]["execution_prep"][key] = value
            self.assert_rejected(packet)

    def test_509_non_synthetic_data_fails_closed(self) -> None:
        packet = self.fresh()
        packet["pilot_matrix"]["smoke_profile"]["data_ceiling"] = "PUBLIC"
        self.assert_rejected(packet)

    def test_510_capability_escalation_fails_closed(self) -> None:
        for key in (
            "tools",
            "provider_retrieval_search",
            "code_execution",
            "file_access",
            "provider_memory",
            "function_calling",
        ):
            packet = self.fresh()
            packet["pilot_matrix"]["capability_policy"][key] = "ENABLED"
            self.assert_rejected(packet)

    def test_511_host_or_operation_drift_fails_closed(self) -> None:
        for key, value in (
            ("allowed_host", "example.invalid"),
            ("allowed_operation", "UNEXPECTED_OPERATION"),
        ):
            packet = self.fresh()
            packet["pilot_matrix"]["execution_prep"][key] = value
            self.assert_rejected(packet)

    def test_512_provider_wire_schema_drift_fails_closed(self) -> None:
        packet = self.fresh()
        packet["provider_wire_response_schema"]["properties"]["submission_id"]["minLength"] = 1
        self.assert_rejected(packet)

    def test_513_result_termination_receipt_binding_drift_fails_closed(self) -> None:
        packet = self.fresh()
        packet["termination_receipt_requirements"]["result_sha256_required"] = False
        self.assert_rejected(packet)

    def test_514_canonical_tuple_drift_fails_closed(self) -> None:
        for key, value in (
            ("main", "0" * 40),
            ("tree", "1" * 40),
            ("multimodel_subtree", "2" * 40),
        ):
            packet = self.fresh()
            packet["canonical"][key] = value
            self.assert_rejected(packet)
        self.assertEqual(self.packet["canonical"]["main"], CANONICAL_MAIN)
        self.assertEqual(self.packet["canonical"]["tree"], CANONICAL_TREE)
        self.assertEqual(
            self.packet["canonical"]["multimodel_subtree"],
            CANONICAL_MULTIMODEL_SUBTREE,
        )

    def test_515_wire_schema_uses_common_supported_subset(self) -> None:
        wire_text = json.dumps(self.packet["provider_wire_response_schema"], sort_keys=True)
        for key in WIRE_SCHEMA_STRIPPED_KEYS:
            self.assertNotIn(f'"{key}"', wire_text)

    def test_516_strict_local_schema_is_distinct_and_ingestion_bound(self) -> None:
        strict_schema = self.packet["strict_local_result_schema"]
        wire_schema = self.packet["provider_wire_response_schema"]
        self.assertNotEqual(strict_schema, wire_schema)
        req = self.packet["result_ingestion_requirements"]
        self.assertEqual(req["strict_local_result_schema_sha256"], sha256_json(strict_schema))
        self.assertEqual(req["provider_wire_response_schema_sha256"], sha256_json(wire_schema))
        self.assertTrue(req["local_result_v2_validation_required"])

    def test_517_all_live_authorities_are_false_and_runtime_off(self) -> None:
        authority = self.packet["authority"]
        for key in (
            "provider_call_authorized",
            "credential_authorized",
            "spend_authorized",
            "runtime_activation",
            "live_execution_performed",
            "protected_data",
            "live_business_effect",
            "adoption_authority",
        ):
            self.assertFalse(authority[key])
        self.assertEqual(authority["runtime"], "OFF")

    def test_518_packet_digest_is_deterministic(self) -> None:
        one = build_first_provider_execution_packet()
        two = build_first_provider_execution_packet()
        self.assertEqual(
            first_provider_execution_packet_sha256(one),
            first_provider_execution_packet_sha256(two),
        )
        self.assertEqual(packet_summary()["packet_sha256"], first_provider_execution_packet_sha256(one))

    def test_519_official_verification_covers_catalog_provider_set(self) -> None:
        snapshot = catalog_snapshot()
        verification = official_verification()
        catalog_providers = {row["provider"] for row in snapshot["entries"]}
        verified_providers = {row["provider"] for row in verification["providers"]}
        self.assertEqual(catalog_providers, verified_providers)
        self.assertEqual(catalog_providers, {"GOOGLE_GEMINI", "ANTHROPIC_CLAUDE"})

    def test_520_selection_grants_no_spend_and_respects_repo_ceiling(self) -> None:
        selection = self.packet["mechanical_selection"]
        self.assertFalse(selection["spend_authorized"])
        self.assertLessEqual(
            selection["selected_estimated_max_cost_usd_micros"],
            REPOSITORY_MAX_COST_USD_MICROS,
        )
        self.assertEqual(
            self.packet["limits"]["proposed_max_cost_usd_micros"],
            selection["selected_estimated_max_cost_usd_micros"],
        )


if __name__ == "__main__":
    unittest.main()
