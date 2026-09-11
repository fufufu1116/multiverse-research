import unittest

from research.opportunity_engine_v0.growth_loop import (
    GrowthChannel,
    LoopDecision,
    LoopEdge,
    assess_growth_loop,
)


class GrowthLoopTests(unittest.TestCase):
    def channels(self):
        return (
            GrowthChannel("owned_app", True, 1),
            GrowthChannel("social_video", False, 4),
        )

    def edge(self, source, destination, **overrides):
        values = dict(
            source=source,
            destination=destination,
            mechanism="deep-link/share",
            verified_available=True,
            evidence_count=2,
            user_value=4,
            friction=1,
            intent_strength=4,
            attribution_quality=4,
            reusable_asset_gain=3,
            platform_policy_risk=1,
            legal_risk=1,
            deceptive_tactic_required=False,
        )
        values.update(overrides)
        return LoopEdge(**values)

    def test_bidirectional_owned_loop_can_be_ready(self):
        result = assess_growth_loop(
            channels=self.channels(),
            edges=(
                self.edge("owned_app", "social_video"),
                self.edge("social_video", "owned_app"),
            ),
        )
        self.assertEqual(result.decision, LoopDecision.LOOP_READY)
        self.assertIn("BIDIRECTIONAL_USER_FLOW", result.reasons)
        self.assertIn("OWNED_CAPTURE_POINT", result.reasons)

    def test_one_way_distribution_is_not_called_a_loop(self):
        result = assess_growth_loop(
            channels=self.channels(),
            edges=(self.edge("owned_app", "social_video"),),
        )
        self.assertEqual(result.decision, LoopDecision.ONE_WAY_AMPLIFIER)
        self.assertEqual(result.closed_pairs, ())

    def test_no_owned_capture_is_fragile(self):
        channels = (
            GrowthChannel("platform_a", False, 3),
            GrowthChannel("platform_b", False, 3),
        )
        result = assess_growth_loop(
            channels=channels,
            edges=(
                self.edge("platform_a", "platform_b"),
                self.edge("platform_b", "platform_a"),
            ),
        )
        self.assertEqual(result.decision, LoopDecision.FRAGILE_LOOP)
        self.assertIn("NO_OWNED_CAPTURE_POINT", result.reasons)

    def test_high_policy_risk_edge_is_rejected(self):
        result = assess_growth_loop(
            channels=self.channels(),
            edges=(
                self.edge("owned_app", "social_video", platform_policy_risk=5),
                self.edge("social_video", "owned_app", platform_policy_risk=5),
            ),
        )
        self.assertEqual(result.decision, LoopDecision.UNSAFE_OR_POLICY_FRAGILE)
        self.assertIn("PLATFORM_POLICY_RISK_TOO_HIGH", result.blockers)

    def test_deceptive_loop_fails_closed(self):
        result = assess_growth_loop(
            channels=self.channels(),
            edges=(
                self.edge("owned_app", "social_video", deceptive_tactic_required=True),
                self.edge("social_video", "owned_app", deceptive_tactic_required=True),
            ),
        )
        self.assertEqual(result.decision, LoopDecision.UNSAFE_OR_POLICY_FRAGILE)
        self.assertIn("DECEPTIVE_TACTIC_REQUIRED", result.blockers)

    def test_high_friction_reduces_strength(self):
        low = assess_growth_loop(
            channels=self.channels(),
            edges=(
                self.edge("owned_app", "social_video", friction=1),
                self.edge("social_video", "owned_app", friction=1),
            ),
        )
        high = assess_growth_loop(
            channels=self.channels(),
            edges=(
                self.edge("owned_app", "social_video", friction=4),
                self.edge("social_video", "owned_app", friction=4),
            ),
        )
        self.assertGreater(low.score, high.score)
        self.assertGreater(low.estimated_loop_multiplier, high.estimated_loop_multiplier)

    def test_unverified_edges_do_not_count(self):
        result = assess_growth_loop(
            channels=self.channels(),
            edges=(
                self.edge("owned_app", "social_video", verified_available=False),
                self.edge("social_video", "owned_app", evidence_count=0),
            ),
        )
        self.assertEqual(result.decision, LoopDecision.UNSAFE_OR_POLICY_FRAGILE)
        self.assertIn("UNVERIFIED_EDGE", result.blockers)


if __name__ == "__main__":
    unittest.main()
