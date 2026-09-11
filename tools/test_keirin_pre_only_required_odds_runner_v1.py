#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
TARGET = HERE / "keirin_pre_only_required_odds_runner_v1.py"

spec = importlib.util.spec_from_file_location("pre_only_required_odds_v1", TARGET)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class FakeV1:
    FORBIDDEN_TOKENS = (
        "result", "payout", "refund", "finish", "winner",
        "着順", "払戻", "確定",
    )

    @staticmethod
    def reject_outcome_fields(envelope):
        if "result" in envelope:
            raise mod.FailClosed("forbidden_outcome_field:result")

    @staticmethod
    def parse_time(value, _label):
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    @staticmethod
    def canonical_bytes(obj):
        return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def sha256_bytes(b):
        return hashlib.sha256(b).hexdigest()

    @staticmethod
    def identity_tuple(obj):
        return (str(obj.get("event_date")), str(obj.get("venue", "")).strip(), int(obj.get("race_number", -1)))

    @staticmethod
    def build_frozen_ticket_probabilities(_winner):
        return {
            "3rentan": {"1-2-3": 0.30, "1-3-2": 0.20, "2-1-3": 0.10},
            "2shatan": {"1-2": 0.40, "2-1": 0.25},
        }


class FakeScore:
    value = 0.50

    @staticmethod
    def load_frozen_model(_repo_root):
        return {"frozen": True}

    @classmethod
    def produce_gate_score(cls, _pre_payload, _model):
        return {
            "value": cls.value,
            "semantic_name": "test_gate",
            "top1_agreement": True,
        }


def make_envelope():
    pre_payload = {"event_date": "2026-09-12", "venue": "TEST", "race_number": 1, "riders": []}
    pre_sha = FakeV1.sha256_bytes(FakeV1.canonical_bytes(pre_payload))
    identity = {"event_date": "2026-09-12", "venue": "TEST", "race_number": 1}
    return {
        "pre_freeze_receipt": {
            "record": "KEIRIN_PROSPECTIVE_PRE_FREEZE_RECEIPT_v1",
            "status": "PASS_PRE_FROZEN_BEFORE_OUTCOME",
            "outcome_accessed": False,
            "post_result_reconstruction": False,
            "target_identity": identity,
            "capture_time": "2026-09-12T09:00:00+09:00",
            "target_cutoff": "2026-09-12T10:00:00+09:00",
            "pre_payload_sha256": pre_sha,
            "winner_prediction": dict(identity),
        },
        "pre_payload_for_gate_score": pre_payload,
    }


def fake_load_pinned(_repo_root, rel, _expected_blob, _module_name):
    if rel == mod.V1_REL:
        return FakeV1
    if rel == mod.SCORE_PRODUCER_REL:
        return FakeScore
    raise AssertionError(rel)


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

    def test_rank_market_rejects_empty_market(self):
        with self.assertRaisesRegex(mod.FailClosed, "empty_ticket_probability_market"):
            mod._rank_market({})

    def test_frozen_dependency_bindings_are_exact(self):
        self.assertEqual(mod.V1_GIT_BLOB, "417fa8947ab9b15dde305adc15085d558659d134")
        self.assertEqual(mod.SCORE_PRODUCER_GIT_BLOB, "8ffbab9d02562a3f8b617047c614a2008378932b")
        self.assertEqual(mod.COMPETITION_THRESHOLD, 0.40)
        self.assertEqual(mod.SUPPORTED_MARKETS, ("3rentan", "2shatan"))

    def test_scoped_outcome_filter_allows_exact_required_control_paths(self):
        env = make_envelope()
        mod._reject_outcome_fields_scoped(env, FakeV1.FORBIDDEN_TOKENS)

    def test_scoped_outcome_filter_rejects_nested_result_inside_winner_prediction(self):
        env = make_envelope()
        env["pre_freeze_receipt"]["winner_prediction"]["result"] = {"car_no": 1}
        with self.assertRaisesRegex(mod.FailClosed, "outcome_or_settlement_field_forbidden"):
            mod._reject_outcome_fields_scoped(env, FakeV1.FORBIDDEN_TOKENS)

    def test_scoped_outcome_filter_rejects_misplaced_winner_control_name(self):
        env = make_envelope()
        env["shadow"] = {"winner_prediction": {}}
        with self.assertRaisesRegex(mod.FailClosed, "outcome_or_settlement_field_forbidden"):
            mod._reject_outcome_fields_scoped(env, FakeV1.FORBIDDEN_TOKENS)

    def test_load_pinned_fails_closed_on_missing_file(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(mod.FailClosed, "missing_pinned_module"):
                mod._load_pinned(Path(td), "missing.py", "0" * 40, "missing")

    def test_load_pinned_fails_closed_on_blob_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.py"
            p.write_text("X = 1\n", encoding="utf-8")
            with self.assertRaisesRegex(mod.FailClosed, "pinned_module_blob_mismatch"):
                mod._load_pinned(Path(td), "x.py", "0" * 40, "x")

    def test_run_gate_pass_emits_ranked_candidates_and_required_odds(self):
        FakeScore.value = 0.50
        with mock.patch.object(mod, "_load_pinned", side_effect=fake_load_pinned):
            out = mod.run(make_envelope(), Path("."), top_n=2)
        self.assertEqual(out["status"], "PASS_PRE_ONLY_CANDIDATES")
        self.assertTrue(out["competition_gate"]["pass"])
        self.assertEqual(out["markets"]["3rentan"]["prediction_only_candidate"]["ticket"], "1-2-3")
        self.assertEqual(len(out["markets"]["3rentan"]["top_ranked_raw_candidates"]), 2)
        self.assertTrue(math.isclose(out["markets"]["2shatan"]["prediction_only_candidate"]["raw_break_even_decimal_odds"], 2.5))
        self.assertFalse(out["exact_v54_executable"])
        self.assertFalse(out["result_accessed"])
        self.assertFalse(out["payout_accessed"])
        self.assertFalse(out["network_access"])
        self.assertFalse(out["automatic_betting"])
        self.assertEqual(out["runtime"], "OFF")

    def test_run_gate_fail_emits_no_candidates(self):
        FakeScore.value = 0.39
        with mock.patch.object(mod, "_load_pinned", side_effect=fake_load_pinned):
            out = mod.run(make_envelope(), Path("."))
        self.assertEqual(out["status"], "PASS_PRE_ONLY_GATE_NO_CANDIDATE")
        for market in mod.SUPPORTED_MARKETS:
            self.assertIsNone(out["markets"][market]["prediction_only_candidate"])
            self.assertEqual(out["markets"][market]["top_ranked_raw_candidates"], [])

    def test_run_rejects_nonpositive_top_n(self):
        with self.assertRaisesRegex(mod.FailClosed, "top_n_must_be_positive"):
            mod.run(make_envelope(), Path("."), top_n=0)

    def test_run_rejects_capture_after_cutoff(self):
        env = make_envelope()
        env["pre_freeze_receipt"]["capture_time"] = "2026-09-12T10:00:01+09:00"
        with mock.patch.object(mod, "_load_pinned", side_effect=fake_load_pinned):
            with self.assertRaisesRegex(mod.FailClosed, "pre_capture_after_cutoff"):
                mod.run(env, Path("."))

    def test_run_rejects_pre_payload_sha_mismatch(self):
        env = make_envelope()
        env["pre_freeze_receipt"]["pre_payload_sha256"] = "0" * 64
        with mock.patch.object(mod, "_load_pinned", side_effect=fake_load_pinned):
            with self.assertRaisesRegex(mod.FailClosed, "pre_payload_sha256_mismatch"):
                mod.run(env, Path("."))

    def test_run_rejects_outcome_contamination(self):
        env = make_envelope()
        env["result"] = {"winner": 1}
        with mock.patch.object(mod, "_load_pinned", side_effect=fake_load_pinned):
            with self.assertRaisesRegex(mod.FailClosed, "outcome_or_settlement_field_forbidden"):
                mod.run(env, Path("."))

    def test_run_fails_closed_when_supported_market_missing(self):
        original = FakeV1.build_frozen_ticket_probabilities
        FakeV1.build_frozen_ticket_probabilities = staticmethod(lambda _winner: {"3rentan": {"1-2-3": 0.3}})
        try:
            with mock.patch.object(mod, "_load_pinned", side_effect=fake_load_pinned):
                with self.assertRaisesRegex(mod.FailClosed, "ticket_probabilities.2shatan_not_object"):
                    mod.run(make_envelope(), Path("."))
        finally:
            FakeV1.build_frozen_ticket_probabilities = original

    def test_run_fails_closed_when_supported_market_empty(self):
        original = FakeV1.build_frozen_ticket_probabilities
        FakeV1.build_frozen_ticket_probabilities = staticmethod(lambda _winner: {"3rentan": {}, "2shatan": {"1-2": 0.4}})
        try:
            with mock.patch.object(mod, "_load_pinned", side_effect=fake_load_pinned):
                with self.assertRaisesRegex(mod.FailClosed, "empty_ticket_probability_market"):
                    mod.run(make_envelope(), Path("."))
        finally:
            FakeV1.build_frozen_ticket_probabilities = original


if __name__ == "__main__":
    unittest.main()
