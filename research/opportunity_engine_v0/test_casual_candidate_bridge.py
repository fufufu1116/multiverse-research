import unittest

from .casual_candidate_bridge import build_research_candidate_from_casual
from .casual_intake import CasualPostCandidate


class CasualCandidateBridgeTests(unittest.TestCase):
    def candidate(self, **overrides):
        values = dict(
            source_id="chat-idea-1",
            source_kind="CASUAL_CHAT_FORWARD",
            summary="A reusable value-added service pattern.",
            reusable_pattern="lawful upstream right + independent value add + recurring self-service",
            concrete_claims_present=True,
            claims_verified=False,
            contains_sensitive_personal_data=False,
            deceptive_or_evasive=False,
            commercial_relevance=4,
            novelty_or_reuse_value=4,
            evidence_strength=1,
            owner_fit=4,
            verification_refs=(),
        )
        values.update(overrides)
        return CasualPostCandidate(**values)

    def test_candidate_becomes_research_required_not_adopted(self):
        packet = build_research_candidate_from_casual(self.candidate())
        self.assertEqual(packet["research_status"], "RESEARCH_REQUIRED")
        self.assertTrue(packet["competitor_research_required"])
        self.assertTrue(packet["forecast_required_before_governed_test"])
        self.assertFalse(packet["adoption_authorized"])
        self.assertFalse(packet["live_execution_authorized"])

    def test_unverified_claims_add_verification_question(self):
        packet = build_research_candidate_from_casual(self.candidate())
        self.assertTrue(packet["requires_verification_before_use"])
        self.assertIn("verified", packet["research_questions"][0].lower())

    def test_intake_adds_zero_independent_evidence(self):
        packet = build_research_candidate_from_casual(self.candidate())
        self.assertEqual(packet["independent_evidence_count_added_by_intake"], 0)
        self.assertEqual(packet["dedupe_key"], packet["content_fingerprint"])

    def test_verified_evidence_refs_are_carried_without_execution_authority(self):
        packet = build_research_candidate_from_casual(self.candidate(
            claims_verified=True,
            verification_refs=("official-source-1",),
            evidence_strength=4,
        ))
        self.assertFalse(packet["requires_verification_before_use"])
        self.assertEqual(packet["verification_refs"], ["official-source-1"])
        self.assertFalse(packet["provider_call_authorized"])
        self.assertFalse(packet["spend_authorized"])

    def test_low_value_banter_cannot_be_promoted(self):
        with self.assertRaises(ValueError):
            build_research_candidate_from_casual(self.candidate(
                concrete_claims_present=False,
                commercial_relevance=0,
                novelty_or_reuse_value=0,
                evidence_strength=0,
                owner_fit=0,
            ))


if __name__ == "__main__":
    unittest.main()
