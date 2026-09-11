import unittest

from research.opportunity_engine_v0.tactics import (
    TacticDecision,
    TacticPolicy,
    TacticStage,
    TacticStep,
    assess_tactic_plan,
)


def step(name, stage, **overrides):
    data = dict(
        name=name,
        stage=stage,
        verified_method=True,
        measurable=True,
        reversible=True,
        spend_yen=500,
        owner_hours=0.5,
        learning_value=4,
    )
    data.update(overrides)
    return TacticStep(**data)


POLICY = TacticPolicy(max_preproof_spend_yen=3000, max_total_owner_hours=5)


class TacticTests(unittest.TestCase):
    def test_validate_prove_automate_scale_exit_is_ready(self):
        plan = (
            step("validate demand", TacticStage.VALIDATE),
            step("prove one conversion", TacticStage.PROVE_CONVERSION),
            step("automate fulfillment", TacticStage.AUTOMATE),
            step("add distribution", TacticStage.ACQUIRE),
            step("scale proven route", TacticStage.SCALE),
            step("settle and learn", TacticStage.EXIT_AND_LEARN),
        )
        result = assess_tactic_plan(plan, POLICY)
        self.assertEqual(result.decision, TacticDecision.READY)
        self.assertIn("CONVERSION_PROVEN_BEFORE_SCALE", result.reasons)
        self.assertIn("AUTOMATE_AFTER_VALUE_PROOF", result.reasons)

    def test_scale_before_conversion_is_rejected(self):
        plan = (
            step("validate", TacticStage.VALIDATE),
            step("scale", TacticStage.SCALE),
            step("prove", TacticStage.PROVE_CONVERSION),
            step("exit", TacticStage.EXIT_AND_LEARN),
        )
        result = assess_tactic_plan(plan, POLICY)
        self.assertEqual(result.decision, TacticDecision.REJECT)
        self.assertIn("SCALE_BEFORE_CONVERSION_PROOF", result.hard_failures)

    def test_automation_before_value_proof_is_rejected(self):
        plan = (
            step("validate", TacticStage.VALIDATE),
            step("automate", TacticStage.AUTOMATE),
            step("prove", TacticStage.PROVE_CONVERSION),
            step("exit", TacticStage.EXIT_AND_LEARN),
        )
        result = assess_tactic_plan(plan, POLICY)
        self.assertEqual(result.decision, TacticDecision.REJECT)
        self.assertIn("AUTOMATION_BEFORE_VALUE_PROOF", result.hard_failures)

    def test_large_spend_before_proof_is_rejected(self):
        plan = (
            step("validate", TacticStage.VALIDATE, spend_yen=2500),
            step("prove", TacticStage.PROVE_CONVERSION, spend_yen=2500),
            step("exit", TacticStage.EXIT_AND_LEARN),
        )
        result = assess_tactic_plan(plan, POLICY)
        self.assertEqual(result.decision, TacticDecision.REJECT)
        self.assertIn("PREPROOF_SPEND_TOO_HIGH", result.hard_failures)

    def test_short_demand_rejects_slow_tactic(self):
        plan = (
            step("validate", TacticStage.VALIDATE),
            step("prove", TacticStage.PROVE_CONVERSION),
            step("exit", TacticStage.EXIT_AND_LEARN),
        )
        policy = TacticPolicy(
            max_preproof_spend_yen=3000,
            max_total_owner_hours=5,
            demand_life_days=10,
            total_setup_days=5,
        )
        result = assess_tactic_plan(plan, policy)
        self.assertEqual(result.decision, TacticDecision.REJECT)
        self.assertIn("TACTIC_TOO_SLOW_FOR_DEMAND_WINDOW", result.hard_failures)

    def test_exit_and_learning_is_required_at_end(self):
        plan = (
            step("validate", TacticStage.VALIDATE),
            step("prove", TacticStage.PROVE_CONVERSION),
            step("acquire", TacticStage.ACQUIRE),
        )
        result = assess_tactic_plan(plan, POLICY)
        self.assertEqual(result.decision, TacticDecision.REJECT)
        self.assertIn("EXIT_AND_LEARNING_MUST_BE_LAST", result.hard_failures)


if __name__ == "__main__":
    unittest.main()
