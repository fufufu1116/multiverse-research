import unittest

from research.opportunity_engine_v0.advisor_learning import (
    SettledAdvisorOutcome,
    compile_advisor_track_records,
)


class AdvisorLearningTests(unittest.TestCase):
    def outcome(self, **overrides):
        values = {
            "outcome_id": "outcome-1",
            "review_id": "review-1",
            "provider": "OPENAI",
            "model": "gpt-example",
            "domain": "competition",
            "settlement_basis": "MEASURED_OUTCOME",
            "settled": True,
            "confirmed_material_challenge": True,
            "false_alarm_challenge": False,
            "missed_material_blocker": False,
            "calibration_error": 0.2,
            "actual_cost_yen": 50.0,
        }
        values.update(overrides)
        return SettledAdvisorOutcome(**values)

    def test_unsettled_outcome_is_not_counted(self):
        records = compile_advisor_track_records((self.outcome(settled=False),))
        self.assertEqual(records, ())

    def test_untrusted_self_report_style_basis_is_not_counted(self):
        records = compile_advisor_track_records((self.outcome(settlement_basis="MODEL_SELF_REPORT"),))
        self.assertEqual(records, ())

    def test_measured_outcomes_build_track_record(self):
        records = compile_advisor_track_records((
            self.outcome(),
            self.outcome(
                outcome_id="outcome-2",
                review_id="review-2",
                confirmed_material_challenge=False,
                false_alarm_challenge=True,
                calibration_error=0.4,
                actual_cost_yen=150.0,
            ),
        ))
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.completed_reviews, 2)
        self.assertEqual(record.confirmed_material_challenges, 1)
        self.assertEqual(record.false_alarm_challenges, 1)
        self.assertAlmostEqual(record.calibration_error, 0.3)
        self.assertAlmostEqual(record.average_cost_yen, 100.0)

    def test_missed_blocker_is_preserved_for_later_penalty(self):
        records = compile_advisor_track_records((
            self.outcome(confirmed_material_challenge=False, missed_material_blocker=True),
        ))
        self.assertEqual(records[0].missed_material_blockers, 1)

    def test_duplicate_outcome_id_fails_closed(self):
        with self.assertRaises(ValueError):
            compile_advisor_track_records((self.outcome(), self.outcome()))

    def test_duplicate_provider_model_review_settlement_fails_closed(self):
        with self.assertRaises(ValueError):
            compile_advisor_track_records((
                self.outcome(),
                self.outcome(outcome_id="outcome-2"),
            ))

    def test_domains_are_kept_separate(self):
        records = compile_advisor_track_records((
            self.outcome(),
            self.outcome(
                outcome_id="outcome-2",
                review_id="review-2",
                domain="forecasting",
            ),
        ))
        self.assertEqual(len(records), 2)
        self.assertEqual({record.domain for record in records}, {"competition", "forecasting"})


if __name__ == "__main__":
    unittest.main()
