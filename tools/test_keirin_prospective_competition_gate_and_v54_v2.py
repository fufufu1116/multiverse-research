#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def load(rel: str, name: str):
    p = REPO_ROOT / rel
    spec = importlib.util.spec_from_file_location(name, p)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {rel}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


score = load("tools/keirin_prospective_competition_gate_score_v1.py", "gate_score")
v2 = load("tools/keirin_prospective_v54_decision_freeze_runner_v2.py", "decision_v2")


def canonical_sha(obj) -> str:
    b = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def base_pre():
    return {
        "event_date": "2026-09-12",
        "venue": "松山",
        "race_number": 1,
        "circumference_bucket": "400",
        "entrants": [
            {"car_no": 1, "score": 100.0, "style": "追", "registration_number": "X001"},
            {"car_no": 2, "score": 95.0, "style": "逃", "registration_number": "X002"},
            {"car_no": 3, "score": 90.0, "style": "両", "registration_number": "X003"},
        ],
    }


class GateScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = score.load_frozen_model(REPO_ROOT)

    def test_valid_pre_only_score_is_bounded_and_pinned(self):
        out = score.produce_gate_score(base_pre(), self.model)
        self.assertGreaterEqual(out["value"], 0.0)
        self.assertLessEqual(out["value"], 1.0)
        self.assertEqual(out["threshold"], 0.40)
        self.assertEqual(out["frozen_model_git_blob"], score.MODEL_FREEZE_GIT_BLOB)
        self.assertFalse(out["result_accessed"])
        self.assertFalse(out["payout_accessed"])
        self.assertFalse(out["odds_accessed"])
        self.assertFalse(out["retune"])

    def test_rider_score_alias_mismatch_fails_closed(self):
        pre = base_pre()
        pre["entrants"][0]["competition_score"] = 99.0
        with self.assertRaisesRegex(score.FailClosed, "rider_score_alias_mismatch"):
            score.produce_gate_score(pre, self.model)

    def test_outcome_field_fails_closed(self):
        pre = base_pre()
        pre["result"] = {"winner": 1}
        with self.assertRaisesRegex(score.FailClosed, "forbidden_outcome_key"):
            score.produce_gate_score(pre, self.model)

    def test_unsupported_circumference_fails_closed(self):
        pre = base_pre()
        pre["circumference_bucket"] = "500"
        with self.assertRaisesRegex(score.FailClosed, "unsupported_circumference_bucket"):
            score.produce_gate_score(pre, self.model)

    def test_duplicate_car_fails_closed(self):
        pre = base_pre()
        pre["entrants"][1]["car_no"] = 1
        with self.assertRaisesRegex(score.FailClosed, "invalid_or_duplicate_car"):
            score.produce_gate_score(pre, self.model)

    def test_unknown_support_uses_s0_fallback_not_invention(self):
        pre = base_pre()
        pre["entrants"][0]["style"] = "UNKNOWN"
        pre["entrants"][0]["registration_number"] = "NOT_IN_FROZEN_MODEL"
        out = score.produce_gate_score(pre, self.model)
        self.assertEqual(out["support_mode_by_car"]["1"], "S0_FALLBACK")


class DecisionV2HardeningTests(unittest.TestCase):
    def test_caller_supplied_competition_score_is_forbidden(self):
        with self.assertRaisesRegex(v2.FailClosed, "caller_supplied_competition_score_forbidden_in_v2"):
            v2.run_v2({"competition_score": {"value": 1.0}}, REPO_ROOT)

    def test_missing_pre_receipt_fails_closed(self):
        with self.assertRaisesRegex(v2.FailClosed, "pre_freeze_receipt_missing"):
            v2.run_v2({}, REPO_ROOT)

    def test_pre_payload_sha_mismatch_fails_closed_before_decision(self):
        pre = base_pre()
        env = {
            "pre_freeze_receipt": {
                "pre_payload_sha256": "0" * 64,
                "target_identity": {"event_date": "2026-09-12", "venue": "松山", "race_number": 1},
                "capture_time": "2026-09-11T12:00:00+09:00",
            },
            "pre_payload_for_gate_score": pre,
        }
        self.assertNotEqual(canonical_sha(pre), "0" * 64)
        with self.assertRaisesRegex(v2.FailClosed, "pre_payload_for_gate_score_sha256_mismatch"):
            v2.run_v2(env, REPO_ROOT)

    def test_target_identity_mismatch_fails_closed(self):
        pre = base_pre()
        env = {
            "pre_freeze_receipt": {
                "pre_payload_sha256": canonical_sha(pre),
                "target_identity": {"event_date": "2026-09-12", "venue": "松山", "race_number": 2},
                "capture_time": "2026-09-11T12:00:00+09:00",
            },
            "pre_payload_for_gate_score": pre,
        }
        with self.assertRaisesRegex(v2.FailClosed, "target_identity_mismatch"):
            v2.run_v2(env, REPO_ROOT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
