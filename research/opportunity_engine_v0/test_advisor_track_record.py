import unittest

from research.opportunity_engine_v0.advisor_track_record import (
    AdvisorTrackRecord,
    rank_advisors,
    score_advisor,
)


class AdvisorTrackRecordTests(unittest.TestCase):
    def record(self, **overrides):
        values = {
            "provider": "OPENAI",
            "model": "gpt-example",
            "domain": "competition",
            "completed_reviews": 20,
            "confirmed_material_challenges": 5,
            "false_alarm_challenges": 1,
            "missed_material_blockers": 0,
            "calibration_error": 0.15,
            "average_cost_yen": 100.0,
        }
        values.update(overrides)
        return AdvisorTrackRecord(**values)

    def test_no_history_stays_neutral_and_unproven(self):
        score = score_advisor(self.record(completed_reviews=0, confirmed_material_challenges=0, false_alarm_challenges=0))
        self.assertEqual(score.score, 50.0)
        self.assertEqual(score.status, "UNPROVEN")

    def test_sparse_history_is_shrunk_toward_neutral(self):
        score = score_advisor(self.record(completed_reviews=2, confirmed_material_challenges=2, false_alarm_challenges=0))
        self.assertLess(score.score, 60.0)
        self.assertEqual(score.status, "LIMITED_HISTORY")

    def test_missed_material_blocker_is_heavily_penalized(self):
        clean = score_advisor(self.record())
        missed = score_advisor(self.record(missed_material_blockers=4))
        self.assertLess(missed.score, clean.score)
        self.assertIn("MISSED_BLOCKER_PENALTY", missed.reasons)

    def test_cross_provider_is_preferred_for_second_slot_when_available(self):
        records = (
            self.record(provider="OPENAI", model="gpt-a", average_cost_yen=50),
            self.record(provider="OPENAI", model="gpt-b", average_cost_yen=40, confirmed_material_challenges=6),
            self.record(provider="GOOGLE", model="gemini-a", average_cost_yen=50, confirmed_material_challenges=4),
        )
        selected = rank_advisors(records, domain="competition", max_advisors=2, max_total_expected_cost_yen=200)
        self.assertEqual(len({item.provider for item in selected}), 2)

    def test_budget_can_block_second_provider(self):
        records = (
            self.record(provider="OPENAI", model="gpt-a", average_cost_yen=10),
            self.record(provider="GOOGLE", model="gemini-a", average_cost_yen=200),
        )
        selected = rank_advisors(records, domain="competition", max_advisors=2, max_total_expected_cost_yen=50)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].provider, "OPENAI")

    def test_domain_history_is_not_silently_transferred(self):
        records = (
            self.record(domain="competition"),
            self.record(provider="GOOGLE", model="gemini-a", domain="forecasting"),
        )
        selected = rank_advisors(records, domain="competition")
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].provider, "OPENAI")


if __name__ == "__main__":
    unittest.main()
