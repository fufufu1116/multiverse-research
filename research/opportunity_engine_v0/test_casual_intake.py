import unittest

from .casual_intake import CasualPostCandidate, IntakeDecision, assess_casual_post, casual_content_fingerprint


class CasualPostIntakeTests(unittest.TestCase):
    def candidate(self, **overrides):
        values = dict(
            source_id="casual-post-20260911-reseller",
            source_kind="CASUAL_CHAT_FORWARD",
            summary="Value-added resale of an existing subscription service.",
            reusable_pattern="lawful resale/agency/OEM + value add + self-service recurring revenue",
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

    def test_useful_unverified_post_is_stored_as_candidate_not_fact(self):
        result = assess_casual_post(self.candidate())
        self.assertEqual(result["decision"], IntakeDecision.STORE_OPPORTUNITY_CANDIDATE.value)
        self.assertTrue(result["requires_verification_before_use"])
        self.assertIn("UNVERIFIED_CLAIMS_QUARANTINED", result["reasons"])

    def test_verified_flag_without_refs_does_not_remove_hold(self):
        result = assess_casual_post(self.candidate(claims_verified=True, evidence_strength=4))
        self.assertTrue(result["requires_verification_before_use"])
        self.assertIn("VERIFIED_FLAG_WITHOUT_EVIDENCE_REFS_IGNORED", result["reasons"])

    def test_verified_claims_require_bound_evidence_refs(self):
        result = assess_casual_post(self.candidate(
            claims_verified=True,
            evidence_strength=4,
            verification_refs=("official-provider-terms-20260911",),
        ))
        self.assertFalse(result["requires_verification_before_use"])
        self.assertIn("CLAIMS_BOUND_TO_VERIFICATION_REFS", result["reasons"])

    def test_sensitive_personal_data_is_not_stored(self):
        result = assess_casual_post(self.candidate(contains_sensitive_personal_data=True))
        self.assertEqual(result["decision"], IntakeDecision.REJECT.value)
        self.assertFalse(result["adoption_authorized"])
        self.assertFalse(result["publication_authorized"])

    def test_deceptive_or_evasive_pattern_is_rejected(self):
        result = assess_casual_post(self.candidate(deceptive_or_evasive=True))
        self.assertEqual(result["decision"], IntakeDecision.REJECT.value)
        self.assertFalse(result["spend_authorized"])

    def test_low_value_banter_is_rejected(self):
        result = assess_casual_post(self.candidate(
            commercial_relevance=0,
            novelty_or_reuse_value=0,
            evidence_strength=0,
            owner_fit=0,
            concrete_claims_present=False,
        ))
        self.assertEqual(result["decision"], IntakeDecision.REJECT.value)

    def test_intake_never_authorizes_execution_or_adoption(self):
        result = assess_casual_post(self.candidate())
        self.assertFalse(result["automatic_execution_authorized"])
        self.assertFalse(result["adoption_authorized"])
        self.assertFalse(result["provider_call_authorized"])
        self.assertFalse(result["spend_authorized"])
        self.assertFalse(result["publication_authorized"])

    def test_same_content_from_different_source_ids_has_same_fingerprint(self):
        first = self.candidate(source_id="chat-a")
        second = self.candidate(source_id="chat-b")
        self.assertEqual(casual_content_fingerprint(first), casual_content_fingerprint(second))

    def test_content_change_changes_fingerprint(self):
        first = self.candidate()
        second = self.candidate(summary="Different reusable business pattern.")
        self.assertNotEqual(casual_content_fingerprint(first), casual_content_fingerprint(second))


if __name__ == "__main__":
    unittest.main()
