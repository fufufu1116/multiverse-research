from __future__ import annotations

import copy
import json
import unittest

from automation.review_dispatcher_v1 import model
from automation.review_dispatcher_v1.model_legacy_v1 import (
    REQUEST_MARKER,
    ReviewContractError,
    sha256_json,
)
from automation.review_dispatcher_v1.request_arbitration_v6 import (
    latest_exact_current_owner_request_v6,
)

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40
REPO = "fufufu1116/multiverse-research"


def nonauthority() -> dict:
    return {key: False for key in (
        "provider_resource_mutation", "deploy", "database_mutation",
        "provider_effect_enablement", "runtime_activation_bridge_enablement",
        "runtime_activation", "production_credentials", "production_deployment",
        "protected_data", "live_business_effect", "additional_spend", "merge",
        "main_mutation", "ruleset_mutation", "workflow_dispatch_rerun",
    )}


def request(request_id: str, predecessor: str | None = None) -> dict:
    return {
        "schema": "MULTIVERSE_REVIEW_REQUEST_v1",
        "request_id": request_id,
        "lane": "LAB",
        "mode": "REPOSITORY_ONLY",
        "repo": REPO,
        "pr": 999,
        "head": SHA_A,
        "tree": SHA_B,
        "base": SHA_C,
        "main": SHA_D,
        "proof_ceiling": "TEST_ONLY",
        "execution_state": "TEST_REQUESTED",
        "supersedes_request_sha256": predecessor,
        "recipe": {
            "subtrees": {}, "durable_comments": [], "source_rules": [],
            "unittest_modules": [], "validators": [], "secret_scan_paths": [],
            "forbidden_patterns": [], "http": None,
        },
        "upstream": {},
        "nonauthority": nonauthority(),
    }


def comment(comment_id: int, req: dict, login: str = "fufufu1116") -> dict:
    fence = "```"
    body = "\n".join((REQUEST_MARKER, fence + "json", json.dumps(req, sort_keys=True), fence))
    return {"id": comment_id, "body": body, "user": {"login": login}}


def latest(comments: list[dict]):
    return latest_exact_current_owner_request_v6(
        comments,
        repo=REPO,
        pr=999,
        lane="LAB",
        head=SHA_A,
        tree=SHA_B,
        base=SHA_C,
        main=SHA_D,
    )


class RequestArbitrationV6Tests(unittest.TestCase):
    def test_01_single_linear_chain_preserved(self):
        first = request("request-first")
        second = request("request-second", sha256_json(first))
        cid, selected, _ = latest([comment(10, first), comment(20, second)])
        self.assertEqual(cid, 20)
        self.assertEqual(selected["request_id"], "request-second")

    def test_02_parallel_same_generation_earliest_comment_wins(self):
        first = request("request-first")
        sibling = request("request-sibling")
        next_req = request("request-next", sha256_json(first))
        cid, selected, _ = latest([
            comment(20, sibling),
            comment(30, next_req),
            comment(10, first),
        ])
        self.assertEqual(cid, 30)
        self.assertEqual(selected["request_id"], "request-next")

    def test_03_late_sibling_does_not_change_generation_winner(self):
        first = request("request-first")
        next_req = request("request-next", sha256_json(first))
        late_sibling = request("request-late-sibling")
        cid, selected, _ = latest([
            comment(10, first),
            comment(20, next_req),
            comment(30, late_sibling),
        ])
        self.assertEqual(cid, 20)
        self.assertEqual(selected["request_id"], "request-next")

    def test_04_child_of_collision_loser_fails_closed(self):
        first = request("request-first")
        loser = request("request-loser")
        loser_child = request("request-loser-child", sha256_json(loser))
        with self.assertRaisesRegex(ReviewContractError, "ORPHANED_OR_LOSER_DERIVED_SUPERSESSION"):
            latest([comment(10, first), comment(20, loser), comment(30, loser_child)])

    def test_05_prepublished_successor_order_fails_closed(self):
        first = request("request-first")
        successor = request("request-successor", sha256_json(first))
        with self.assertRaisesRegex(ReviewContractError, "SUPERSESSION_COMMENT_ORDER_INVALID"):
            latest([comment(5, successor), comment(10, first)])

    def test_06_duplicate_request_id_still_fails_closed(self):
        first = request("request-duplicate")
        sibling = copy.deepcopy(first)
        sibling["proof_ceiling"] = "OTHER"
        with self.assertRaisesRegex(ReviewContractError, "DUPLICATE_EXACT_REQUEST_ID"):
            latest([comment(10, first), comment(20, sibling)])

    def test_07_untrusted_owner_request_is_ignored(self):
        trusted = request("request-trusted")
        untrusted = request("request-untrusted")
        cid, selected, _ = latest([
            comment(10, trusted),
            comment(5, untrusted, login="attacker"),
        ])
        self.assertEqual(cid, 10)
        self.assertEqual(selected["request_id"], "request-trusted")

    def test_08_model_wrapper_exports_v6_selection(self):
        first = request("request-first")
        sibling = request("request-sibling")
        selected = model.latest_exact_current_owner_request(
            [comment(10, first), comment(20, sibling)],
            repo=REPO,
            pr=999,
            lane="LAB",
            head=SHA_A,
            tree=SHA_B,
            base=SHA_C,
            main=SHA_D,
        )
        self.assertEqual(selected[0], 10)
        self.assertEqual(selected[1]["request_id"], "request-first")


if __name__ == "__main__":
    unittest.main()
