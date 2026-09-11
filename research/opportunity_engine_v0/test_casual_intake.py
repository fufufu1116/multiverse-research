import unittest

from .casual_intake import CasualPostCandidate, IntakeDecision, assess_casual_post


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
        )
        values.update(overrides)
        return CasualPostCandidate(**values)

    def test_useful_unverified_post_is_stored_as_candidate_not_fact(self):
        result = assess_casual_post(self.candidate())
        self.assertEqual(result["decision"], IntakeDecision.STORE_OPPORTUNITY_CANDIDATE.value)
        self.assertTrue(result["requires_verification_before_use"])
        self.assertIn("UNVERIFIED_CLAIMS_QUARANTINED", result["reasons"])

    def test_verified_claims_remove_verification_hold(self):
        result = assess_casual_post(self.candidate(claims_verified=True, evidence_strength=4))
        self.assertFalse(result["requires_verification_before_use"])

    def test_sensitive_personal_data_is_not_stored(self):
        result = assess_casual_post(self.candidate(contains_sensitive_personal_data=True))
        self.assertEqual(result["decision"], IntakeDecision.REJECT.value)

    def test_deceptive_or_evasive_pattern_is_rejected(self):
        result = assess_casual_post(self.candidate(deceptive_or_evasive=True))
        self.assertEqual(result["decision"], IntakeDecision.REJECT.value)

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


if __name__ == "__main__":
    unittest.main()
