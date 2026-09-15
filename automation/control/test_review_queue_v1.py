from __future__ import annotations

import copy
import unittest

from automation.control.review_queue_v1 import (
    QueueContractError,
    authorize,
    consume_on_build_create,
    queue_id_for,
    record_result,
    select_next,
    validate_queue,
)


def item(*, review_type="LAB", request="r1", sha="a" * 64, priority=100, seq=1, state="WAITING", consumed=False, deps=None):
    x = {
        "schema": "MULTIVERSE_REVIEW_QUEUE_ITEM_v1",
        "lane": "KEIRIN",
        "review_type": review_type,
        "pr": 10 + seq,
        "branch": f"b{seq}",
        "head": f"h{seq}",
        "tree": f"t{seq}",
        "base": "base",
        "main": "main",
        "request_id": request,
        "request_sha256": sha,
        "gate_ref": f"#{100 + seq}",
        "priority": priority,
        "created_seq": seq,
        "depends_on": deps or [],
        "state": state,
        "one_shot_consumed": consumed,
    }
    x["queue_id"] = queue_id_for(x)
    return x


def queue(items):
    return {
        "schema": "MULTIVERSE_REVIEW_QUEUE_v1",
        "runtime": "OFF",
        "exclusive_review_resources": True,
        "items": items,
    }


class ReviewQueueV1Tests(unittest.TestCase):
    def test_priority_then_sequence_deterministic(self):
        a = item(request="a", sha="1" * 64, priority=100, seq=1)
        b = item(request="b", sha="2" * 64, priority=200, seq=2)
        c = item(request="c", sha="3" * 64, priority=200, seq=3)
        self.assertEqual(select_next(queue([a, c, b]), "LAB")["queue_id"], b["queue_id"])

    def test_dependency_blocks_until_pass(self):
        dep = item(request="dep", sha="4" * 64, seq=1, state="CONSUMED", consumed=True)
        child = item(request="child", sha="5" * 64, seq=2, deps=[dep["queue_id"]])
        self.assertIsNone(select_next(queue([dep, child]), "LAB"))
        dep["state"] = "PASS"
        dep["result"] = {"request_id": dep["request_id"], "request_sha256": dep["request_sha256"], "head": dep["head"], "tree": dep["tree"], "review_type": "LAB", "verdict": "PASS"}
        self.assertEqual(select_next(queue([dep, child]), "LAB")["queue_id"], child["queue_id"])

    def test_active_resource_excludes_second_item(self):
        active = item(request="active", sha="6" * 64, seq=1, state="AUTHORIZED")
        waiting = item(request="waiting", sha="7" * 64, seq=2)
        self.assertIsNone(select_next(queue([active, waiting]), "LAB"))

    def test_resource_collision_fail_closed(self):
        a = item(request="a", sha="8" * 64, seq=1, state="AUTHORIZED")
        b = item(request="b", sha="9" * 64, seq=2, state="AUTHORIZED")
        with self.assertRaisesRegex(QueueContractError, "RESOURCE_COLLISION"):
            validate_queue(queue([a, b]))

    def test_duplicate_review_envelope_rejected(self):
        a = item(request="a", sha="a" * 64, seq=1)
        b = item(request="b", sha="a" * 64, seq=2)
        with self.assertRaisesRegex(QueueContractError, "DUPLICATE_REVIEW_ENVELOPE"):
            validate_queue(queue([a, b]))

    def test_queue_id_binds_exact_envelope(self):
        a = item(request="a", sha="b" * 64, seq=1)
        a["head"] = "drift"
        with self.assertRaisesRegex(QueueContractError, "QUEUE_ID_BINDING_MISMATCH"):
            validate_queue(queue([a]))

    def test_authorize_only_arbitration_winner(self):
        low = item(request="low", sha="c" * 64, priority=1, seq=1)
        high = item(request="high", sha="d" * 64, priority=10, seq=2)
        q = queue([low, high])
        with self.assertRaisesRegex(QueueContractError, "ITEM_NOT_ARBITRATION_WINNER"):
            authorize(q, low["queue_id"])
        authorize(q, high["queue_id"])
        self.assertEqual(high["state"], "AUTHORIZED")

    def test_build_create_consumes_one_shot_once(self):
        a = item(request="a", sha="e" * 64, seq=1)
        q = queue([a])
        authorize(q, a["queue_id"])
        consume_on_build_create(q, a["queue_id"], "build#1")
        self.assertTrue(a["one_shot_consumed"])
        self.assertEqual(a["state"], "CONSUMED")
        with self.assertRaises(QueueContractError):
            consume_on_build_create(q, a["queue_id"], "build#2")

    def test_result_binding_cannot_cross_request(self):
        a = item(request="a", sha="f" * 64, seq=1)
        q = queue([a])
        authorize(q, a["queue_id"])
        consume_on_build_create(q, a["queue_id"], "build#1")
        result = {"request_id": "other", "request_sha256": a["request_sha256"], "head": a["head"], "tree": a["tree"], "review_type": "LAB", "verdict": "PASS"}
        with self.assertRaisesRegex(QueueContractError, "RESULT_REQUEST_ID_MISMATCH"):
            record_result(q, a["queue_id"], result)

    def test_lab_and_auditor_are_distinct_resources(self):
        lab = item(review_type="LAB", request="lab", sha="0" * 64, seq=1, state="AUTHORIZED")
        aud = item(review_type="AUDITOR", request="aud", sha="1" * 64, seq=2)
        self.assertEqual(select_next(queue([lab, aud]), "AUDITOR")["queue_id"], aud["queue_id"])

    def test_runtime_on_rejected(self):
        q = queue([])
        q["runtime"] = "ON"
        with self.assertRaisesRegex(QueueContractError, "RUNTIME_MUST_BE_OFF"):
            validate_queue(q)

    def test_parallel_mode_not_implicitly_enabled(self):
        q = queue([])
        q["exclusive_review_resources"] = False
        with self.assertRaisesRegex(QueueContractError, "EXCLUSIVE_RESOURCES_REQUIRED"):
            validate_queue(q)


if __name__ == "__main__":
    unittest.main()
