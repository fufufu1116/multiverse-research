#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
TARGET = HERE / "keirin_pre_only_required_odds_runner_v1.py"

spec = importlib.util.spec_from_file_location("pre_only_required_odds_v1", TARGET)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class RequiredOddsRunnerTests(unittest.TestCase):
    def test_rank_market_probability_desc_and_break_even(self):
        rows = mod._rank_market({"1-2": 0.25, "2-1": 0.50, "3-1": 0.125})
        self.assertEqual([r["ticket"] for r in rows], ["2-1", "1-2", "3-1"])
        self.assertEqual([r["raw_probability_rank"] for r in rows], [1, 2, 3])
        self.assertTrue(math.isclose(rows[0]["raw_break_even_decimal_odds"], 2.0))
        self.assertTrue(math.isclose(rows[1]["raw_break_even_decimal_odds"], 4.0))
        self.assertTrue(math.isclose(rows[2]["raw_break_even_decimal_odds"], 8.0))
        self.assertFalse(any(r["exact_v54_executable"] for r in rows))

    def test_rank_market_tie_breaks_by_ticket_key(self):
        rows = mod._rank_market({"2-1": 0.25, "1-2": 0.25})
        self.assertEqual([r["ticket"] for r in rows], ["1-2", "2-1"])

    def test_rank_market_rejects_nonpositive_probability(self):
        with self.assertRaises(mod.FailClosed):
            mod._rank_market({"1-2": 0.0})

    def test_rank_market_rejects_probability_above_one(self):
        with self.assertRaises(mod.FailClosed):
            mod._rank_market({"1-2": 1.01})

    def test_frozen_dependency_bindings_are_exact(self):
        self.assertEqual(mod.V1_GIT_BLOB, "417fa8947ab9b15dde305adc15085d558659d134")
        self.assertEqual(mod.SCORE_PRODUCER_GIT_BLOB, "8ffbab9d02562a3f8b617047c614a2008378932b")
        self.assertEqual(mod.COMPETITION_THRESHOLD, 0.40)
        self.assertEqual(mod.SUPPORTED_MARKETS, ("3rentan", "2shatan"))


if __name__ == "__main__":
    unittest.main()
