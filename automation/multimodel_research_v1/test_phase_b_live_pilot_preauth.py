from __future__ import annotations

import copy
import unittest

from automation.multimodel_research_v1.model import ResearchContractError
from automation.multimodel_research_v1.phase_b_live_pilot_preauth import (
    API_VERSION,
    CREDENTIAL_HANDLE_REF,
    CURRENT_MAIN,
    CURRENT_MULTIMODEL_SUBTREE,
    CURRENT_TREE,
    ENDPOINT,
    EXPECTED_CATALOG_AGE_SECONDS,
    HOST,
    MAX_ATTEMPTS,
    MAX_COST_USD_MICROS,
    MAX_INPUT_TOKENS,
    MAX_OUTPUT_TOKENS,
    MODEL_ID,
    OPERATION,
    PREDECESSOR_PACKET_SHA256,
    PROVIDER,
    build_first_live_provider_pilot_preauth,
    classify_pilot_outcome,
    first_live_provider_pilot_preauth_sha256,
    validate_first_live_provider_pilot_preauth,
)


class PhaseBFirstLiveProviderPilotPreauthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = build_first_live_provider_pilot_preauth()

    def fresh(self) -> dict:
        return copy.deepcopy(self.packet)

    def rejected(self, packet: dict) -> None:
        with self.assertRaises(ResearchContractError):
            validate_first_live_provider_pilot_preauth(packet)

    def success_evidence(self) -> dict:
        return {
            "http_status": 200,
            "observed_provider": PROVIDER,
            "observed_model_id": MODEL_ID,
            "native_status": "completed",
            "normalized_state": "COMPLETED",
            "strict_schema_valid": True,
            "semantic_refusal": False,
            "semantic_interrupted": False,
            "result_status": "COMPLETED",
            "input_tokens": MAX_INPUT_TOKENS,
            "output_tokens": MAX_OUTPUT_TOKENS,
            "actual_cost_usd_micros": MAX_COST_USD_MICROS,
            "termination_valid": True,
            "receipt_valid": True,
        }

    def test_521_preauth_validates(self) -> None:
        self.assertEqual(validate_first_live_provider_pilot_preauth(self.fresh())["schema"],
                         "MULTIVERSE_FIRST_LIVE_PROVIDER_PILOT_PREAUTH_v1")

    def test_522_current_canonical_tuple_exact(self) -> None:
        self.assertEqual(self.packet["current_canonical"], {
            "main": CURRENT_MAIN,
            "tree": CURRENT_TREE,
            "multimodel_subtree": CURRENT_MULTIMODEL_SUBTREE,
        })

    def test_523_predecessor_packet_hash_exact(self) -> None:
        self.assertEqual(self.packet["predecessor_execution_packet_sha256"], PREDECESSOR_PACKET_SHA256)

    def test_524_fresh_official_verification_le_24h(self) -> None:
        v = self.packet["official_verification"]
        self.assertEqual(v["catalog_age_seconds"], EXPECTED_CATALOG_AGE_SECONDS)
        self.assertLessEqual(v["catalog_age_seconds"], v["catalog_max_age_seconds"])

    def test_525_store_false_is_explicit(self) -> None:
        self.assertIs(self.packet["request_lock"]["store"], False)

    def test_526_missing_or_true_store_fails_closed(self) -> None:
        p = self.fresh()
        p["request_lock"]["store"] = True
        self.rejected(p)
        p = self.fresh()
        del p["request_lock"]["store"]
        self.rejected(p)

    def test_527_provider_model_host_operation_api_drift_fails(self) -> None:
        for key, value in (
            ("provider", "OTHER"),
            ("model_id", "other-model"),
            ("host", "example.invalid"),
            ("operation", "OTHER"),
            ("api_version", "v0"),
            ("endpoint", "https://example.invalid/v0"),
        ):
            p = self.fresh()
            p["request_lock"][key] = value
            self.rejected(p)

    def test_528_current_response_format_and_steps_bound(self) -> None:
        r = self.packet["request_lock"]
        self.assertEqual(r["response_schema"], "steps")
        self.assertEqual(r["response_format"], "CURRENT_POLYMORPHIC_TEXT_JSON_SCHEMA")

    def test_529_all_dynamic_capabilities_forbidden(self) -> None:
        c = self.packet["capability_lock"]
        self.assertTrue(all(v == "NONE" for v in c["canonical_capabilities"].values()))
        self.assertTrue(all(v is False for v in c["additional_forbidden"].values()))
        self.assertFalse(c["streaming"])

    def test_530_one_attempt_and_no_automatic_retry(self) -> None:
        r = self.packet["retry_policy"]
        self.assertEqual(r["max_attempts"], MAX_ATTEMPTS)
        self.assertFalse(r["automatic_retry"])
        self.assertFalse(r["retry_on_timeout"])
        self.assertFalse(r["retry_on_5xx"])
        self.assertFalse(r["retry_on_ambiguous_provider_outcome"])
        self.assertTrue(r["retry_requires_new_owner_authority"])

    def test_531_cost_ceiling_exact_and_cannot_increase(self) -> None:
        self.assertEqual(self.packet["limits"]["max_cost_usd_micros"], MAX_COST_USD_MICROS)
        self.assertEqual(self.packet["limits"]["owner_spend_ceiling_usd_micros"], MAX_COST_USD_MICROS)
        p = self.fresh()
        p["limits"]["owner_spend_ceiling_usd_micros"] += 1
        self.rejected(p)

    def test_532_token_ceilings_exact(self) -> None:
        self.assertEqual(self.packet["limits"]["max_input_tokens"], MAX_INPUT_TOKENS)
        self.assertEqual(self.packet["limits"]["max_output_tokens"], MAX_OUTPUT_TOKENS)

    def test_533_credential_handle_only_and_not_ready(self) -> None:
        c = self.packet["credential_boundary"]
        self.assertEqual(c["credential_handle_ref"], CREDENTIAL_HANDLE_REF)
        self.assertFalse(c["credential_material_present"])
        self.assertFalse(c["credential_resolution_performed"])
        self.assertFalse(c["credential_use_performed"])
        self.assertFalse(c["api_key_copy_paste_required_from_owner"])
        self.assertFalse(c["execution_ready"])

    def test_534_http_200_alone_is_not_success(self) -> None:
        e = {"http_status": 200, "receipt_valid": True}
        self.assertEqual(classify_pilot_outcome(e), "FAIL_CLOSED")

    def test_535_refusal_is_not_success(self) -> None:
        e = self.success_evidence()
        e["semantic_refusal"] = True
        e["result_status"] = "REFUSED"
        self.assertEqual(classify_pilot_outcome(e), "FAIL_CLOSED")

    def test_536_incomplete_or_interrupted_is_not_success(self) -> None:
        for key, value in (("native_status", "incomplete"), ("semantic_interrupted", True)):
            e = self.success_evidence()
            e[key] = value
            self.assertEqual(classify_pilot_outcome(e), "FAIL_CLOSED")

    def test_537_schema_invalid_or_model_mismatch_is_not_success(self) -> None:
        for key, value in (("strict_schema_valid", False), ("observed_model_id", "other")):
            e = self.success_evidence()
            e[key] = value
            self.assertEqual(classify_pilot_outcome(e), "FAIL_CLOSED")

    def test_538_token_or_cost_overflow_is_not_success(self) -> None:
        for key, value in (
            ("input_tokens", MAX_INPUT_TOKENS + 1),
            ("output_tokens", MAX_OUTPUT_TOKENS + 1),
            ("actual_cost_usd_micros", MAX_COST_USD_MICROS + 1),
        ):
            e = self.success_evidence()
            e[key] = value
            self.assertEqual(classify_pilot_outcome(e), "FAIL_CLOSED")

    def test_539_receipt_first_applies_to_success_and_failure(self) -> None:
        e = self.success_evidence()
        e["receipt_valid"] = False
        self.assertEqual(classify_pilot_outcome(e), "FAIL_CLOSED_NO_RECEIPT")
        e = self.success_evidence()
        e["native_status"] = "failed"
        e["receipt_valid"] = False
        self.assertEqual(classify_pilot_outcome(e), "FAIL_CLOSED_NO_RECEIPT")

    def test_540_only_all_success_conditions_pass_and_digest_deterministic(self) -> None:
        self.assertEqual(classify_pilot_outcome(self.success_evidence()), "PASS")
        one = build_first_live_provider_pilot_preauth()
        two = build_first_live_provider_pilot_preauth()
        self.assertEqual(first_live_provider_pilot_preauth_sha256(one),
                         first_live_provider_pilot_preauth_sha256(two))
        for key in (
            "provider_call_authorized", "credential_authorized", "spend_authorized",
            "runtime_activation", "live_execution_performed", "protected_data",
            "live_business_effect", "adoption_authority",
        ):
            self.assertFalse(one["authority"][key])
        self.assertEqual(one["authority"]["runtime"], "OFF")


if __name__ == "__main__":
    unittest.main()
