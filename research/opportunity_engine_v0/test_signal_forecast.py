import unittest

from research.opportunity_engine_v0.signals import (
    EvidenceRef,
    SignalObservation,
    SignalType,
    evidence_quality,
)


class SignalTests(unittest.TestCase):
    def test_signal_requires_evidence(self):
        with self.assertRaises(ValueError):
            SignalObservation(
                signal_id="s1",
                title="candidate",
                signal_type=SignalType.SEARCH,
                market="JP",
                observed_at="2026-09-11T00:00:00+09:00",
                strength=4,
                purchase_intent_hint=3,
                evidence=(),
            )

    def test_multi_source_with_primary_scores_high(self):
        signal = SignalObservation(
            signal_id="s2",
            title="candidate",
            signal_type=SignalType.RULE_CHANGE,
            market="JP",
            observed_at="2026-09-11T00:00:00+09:00",
            strength=4,
            purchase_intent_hint=4,
            evidence=(
                EvidenceRef("official", "official://notice", "2026-09-11", True),
                EvidenceRef("search", "search://trend", "2026-09-11"),
                EvidenceRef("news", "news://coverage", "2026-09-11"),
            ),
        )
        self.assertEqual(evidence_quality(signal), 5)


if __name__ == "__main__":
    unittest.main()
