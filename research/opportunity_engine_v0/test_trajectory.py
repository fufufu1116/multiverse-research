import unittest

from research.opportunity_engine_v0.market_dynamics import MarketDynamics
from research.opportunity_engine_v0.model import CompetitorResearch, OpportunityCandidate
from research.opportunity_engine_v0.trajectory import Trajectory, assess_strategy


COMPLETE_RESEARCH = CompetitorResearch(True, True, True, True)


def candidate(**overrides):
    data = dict(
        name="synthetic opportunity",
        evidence_verified=True,
        buyer_clarity=4,
        attention=4,
        purchase_intent=4,
        why_now=4,
        why_not_before=4,
        competitor_pressure=2,
        incumbent_crush_risk=2,
        ai_substitutability=2,
        proprietary_edge=4,
        action_completion=4,
        reusable_asset=4,
        distribution=4,
        legal_risk=1,
        human_burden=1,
        initial_cost_yen=3000,
        build_days=2,
        demand_life_days=30,
        expected_profit_low_yen=6000,
        expected_profit_base_yen=30000,
        expected_profit_high_yen=120000,
        future_steps=("rise", "peak", "competition", "decay"),
        exit_trigger="exit when demand falls 40% from peak",
        competitor_research=COMPLETE_RESEARCH,
    )
    data.update(overrides)
    return OpportunityCandidate(**data)


def dynamics(**overrides):
    data = dict(
        transmission=4,
        host_fit=4,
        habituation_immunity=2,
        ai_substitution_immunity=2,
        incumbent_immunity=2,
        mutation_capacity=4,
        recurrence=3,
        network_effect=3,
        embeddedness=3,
        mutual_value=4,
    )
    data.update(overrides)
    return MarketDynamics(**data)


class TrajectoryTests(unittest.TestCase):
    def test_fast_short_lived_diffusion_is_harvest_and_exit(self) -> None:
        result = assess_strategy(
            candidate(build_days=1, demand_life_days=20),
            dynamics(transmission=5, network_effect=4, recurrence=2),
        )
        self.assertEqual(result.trajectory, Trajectory.HARVEST_AND_EXIT)

    def test_symbiotic_durable_candidate_can_build_durable(self) -> None:
        result = assess_strategy(
            candidate(demand_life_days=None, exit_trigger=""),
            dynamics(
                embeddedness=5,
                mutual_value=5,
                recurrence=4,
                mutation_capacity=4,
                habituation_immunity=1,
                ai_substitution_immunity=1,
                incumbent_immunity=2,
            ),
        )
        self.assertEqual(result.trajectory, Trajectory.BUILD_DURABLE)

    def test_high_immunity_low_adaptation_longer_market_is_watch(self) -> None:
        result = assess_strategy(
            candidate(demand_life_days=None, exit_trigger=""),
            dynamics(
                habituation_immunity=5,
                ai_substitution_immunity=5,
                incumbent_immunity=4,
                mutation_capacity=1,
                recurrence=1,
                host_fit=2,
            ),
        )
        self.assertEqual(result.trajectory, Trajectory.WATCH)
        self.assertIn("immunity_outpaces_adaptation", result.reasons)

    def test_harmful_dependence_is_rejected_even_if_economics_pass(self) -> None:
        result = assess_strategy(
            candidate(),
            dynamics(harmful_dependence_risk=5),
        )
        self.assertEqual(result.trajectory, Trajectory.REJECT)
        self.assertIn("market_dynamics_ineligible", result.reasons)

    def test_core_rejection_wins_over_market_attractiveness(self) -> None:
        incomplete = CompetitorResearch(True, False, True, True)
        result = assess_strategy(
            candidate(competitor_research=incomplete),
            dynamics(transmission=5, embeddedness=5, mutual_value=5, recurrence=5),
        )
        self.assertEqual(result.trajectory, Trajectory.REJECT)
        self.assertIn("core_rejected", result.reasons)


if __name__ == "__main__":
    unittest.main()
