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

PR318_HEAD = "c3e5bbd340b6da75c8fc80fa921becf01b0bc907"
PR318_TREE = "867ec216722155c7ab97400b6891e64af1dde896"
PR318_MAIN = "d1edc2eabb847c10a4faa59a039b480e85dfb0e4"
PR318_V2_SHA256 = "35011c99d39be40fa80d4ca0abb41c7c57beee40c13a31486f44c045faf03917"
PR318_V3_REQUEST_ID = "pr318-current-main-preflight-read-resilience-lab-v3-main-d1edc2ea"


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


def pr318_v3_request_shape() -> dict:
    value = request(PR318_V3_REQUEST_ID, PR318_V2_SHA256)
    value.update({
        "pr": 318,
        "head": PR318_HEAD,
        "tree": PR318_TREE,
        "base": PR318_MAIN,
        "main": PR318_MAIN,
        "proof_ceiling": "ONE_SHOT_PREFLIGHT_AND_GITHUB_READ_RESILIENCE_REPOSITORY_ONLY",
        "execution_state": "FIXED_REQUEST_ONLY_BASELINE_ONE_SHOT_PREFLIGHT_REVIEW_REQUESTED",
    })
    return value


def malformed_recipe_request(
    request_id: str,
    predecessor: str | None = None,
) -> dict:
    value = request(request_id, predecessor)
    value["recipe"]["source_rules"] = [
        {"path": "x.py", "contains": ["x"]}
    ]
    return value


def comment(
    comment_id: int,
    req: dict,
    login: str = "fufufu1116",
    prefix: str = "",
) -> dict:
    fence = "```"
    parts = []
    if prefix:
        parts.append(prefix)
    parts.extend((REQUEST_MARKER, fence + "json", json.dumps(req, sort_keys=True), fence))
    body = "\n".join(parts)
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


def latest_pr318(comments: list[dict]):
    return latest_exact_current_owner_request_v6(
        comments,
        repo=REPO,
        pr=318,
        lane="LAB",
        head=PR318_HEAD,
        tree=PR318_TREE,
        base=PR318_MAIN,
        main=PR318_MAIN,
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

    def test_09_recipe_invalid_historical_request_can_be_explicitly_superseded(self):
        broken = malformed_recipe_request("request-broken")
        successor = request("request-successor", sha256_json(broken))
        cid, selected, _ = latest([
            comment(10, broken),
            comment(20, successor),
        ])
        self.assertEqual(cid, 20)
        self.assertEqual(selected["request_id"], "request-successor")

    def test_10_recipe_invalid_latest_request_still_fails_closed(self):
        broken = malformed_recipe_request("request-broken")
        with self.assertRaisesRegex(
            ReviewContractError,
            "HISTORICAL_INVALID_EXACT_SUCCESSOR_COUNT:10:0:SOURCE_RULE_SCHEMA",
        ):
            latest([comment(10, broken)])

    def test_11_ambiguous_multiple_successors_of_invalid_request_fail_closed(self):
        broken = malformed_recipe_request("request-broken")
        first = request("request-first-successor", sha256_json(broken))
        second = request("request-second-successor", sha256_json(broken))
        with self.assertRaisesRegex(
            ReviewContractError,
            "HISTORICAL_INVALID_EXACT_SUCCESSOR_COUNT:10:2:SOURCE_RULE_SCHEMA",
        ):
            latest([
                comment(10, broken),
                comment(20, first),
                comment(30, second),
            ])

    def test_12_invalid_collision_loser_child_remains_orphaned(self):
        winner = request("request-winner")
        broken_loser = malformed_recipe_request("request-broken-loser")
        loser_child = request(
            "request-loser-child",
            sha256_json(broken_loser),
        )
        with self.assertRaisesRegex(
            ReviewContractError,
            "ORPHANED_OR_LOSER_DERIVED_SUPERSESSION",
        ):
            latest([
                comment(10, winner),
                comment(20, broken_loser),
                comment(30, loser_child),
            ])

    def test_13_duplicate_id_with_historical_invalid_request_still_fails(self):
        broken = malformed_recipe_request("request-duplicate")
        successor = request("request-duplicate", sha256_json(broken))
        with self.assertRaisesRegex(
            ReviewContractError,
            "DUPLICATE_EXACT_REQUEST_ID:request-duplicate",
        ):
            latest([comment(10, broken), comment(20, successor)])

    def test_14_authority_defect_cannot_be_historically_bridged(self):
        broken = request("request-authority-broken")
        broken["nonauthority"]["merge"] = True
        successor = request("request-successor", sha256_json(broken))
        with self.assertRaisesRegex(
            ReviewContractError,
            "NONAUTHORITY_NOT_FALSE:merge",
        ):
            latest([comment(10, broken), comment(20, successor)])

    def test_15_prepublished_successor_cannot_bridge_invalid_request(self):
        broken = malformed_recipe_request("request-broken")
        successor = request("request-successor", sha256_json(broken))
        with self.assertRaisesRegex(
            ReviewContractError,
            "HISTORICAL_INVALID_EXACT_SUCCESSOR_COUNT:10:0:SOURCE_RULE_SCHEMA",
        ):
            latest([comment(5, successor), comment(10, broken)])

    def test_16_invalid_successor_cannot_bridge_invalid_request(self):
        broken = malformed_recipe_request("request-broken")
        successor = malformed_recipe_request(
            "request-invalid-successor",
            sha256_json(broken),
        )
        with self.assertRaisesRegex(
            ReviewContractError,
            "HISTORICAL_INVALID_EXACT_SUCCESSOR_NOT_VALID:10:20:SOURCE_RULE_SCHEMA",
        ):
            latest([comment(10, broken), comment(20, successor)])

    def test_17_identical_valid_duplicate_echo_collapses_to_earliest(self):
        first = request("request-echo")
        echo = copy.deepcopy(first)
        cid, selected, selected_comment = latest([
            comment(20, echo, prefix="later prose may differ"),
            comment(10, first, prefix="earlier prose"),
        ])
        self.assertEqual(cid, 10)
        self.assertEqual(selected, first)
        self.assertEqual(selected_comment["id"], 10)

    def test_18_multiple_identical_valid_echoes_remain_one_logical_request(self):
        first = request("request-echo")
        cid, selected, _ = latest([
            comment(30, copy.deepcopy(first)),
            comment(10, first),
            comment(20, copy.deepcopy(first)),
        ])
        self.assertEqual(cid, 10)
        self.assertEqual(selected["request_id"], "request-echo")

    def test_19_successor_after_identical_echo_chain_still_wins(self):
        first = request("request-first")
        successor = request("request-successor", sha256_json(first))
        cid, selected, _ = latest([
            comment(10, first),
            comment(15, copy.deepcopy(first)),
            comment(20, successor),
        ])
        self.assertEqual(cid, 20)
        self.assertEqual(selected["request_id"], "request-successor")

    def test_20_identical_historical_invalid_duplicate_never_collapses(self):
        broken = malformed_recipe_request("request-broken-echo")
        with self.assertRaisesRegex(
            ReviewContractError,
            "DUPLICATE_EXACT_REQUEST_ID:request-broken-echo",
        ):
            latest([
                comment(10, broken),
                comment(20, copy.deepcopy(broken)),
            ])

    def test_21_untrusted_same_id_echo_cannot_influence_trusted_winner(self):
        trusted = request("request-trusted-echo")
        cid, selected, _ = latest([
            comment(5, copy.deepcopy(trusted), login="attacker"),
            comment(10, trusted),
            comment(20, copy.deepcopy(trusted)),
        ])
        self.assertEqual(cid, 10)
        self.assertEqual(selected["request_id"], "request-trusted-echo")

    def test_22_pr318_duplicate_v3_envelope_shape_collapses_when_lineage_is_present(self):
        v3 = pr318_v3_request_shape()
        self.assertEqual(v3["supersedes_request_sha256"], PR318_V2_SHA256)

        # This focused unit isolates the duplicate-publication behavior. The
        # separate repository-only proof replays the complete live PR #318
        # v1/v2/v3 durable history and verifies the real v2 predecessor SHA.
        isolated = copy.deepcopy(v3)
        isolated["supersedes_request_sha256"] = None
        cid, selected, selected_comment = latest_pr318([
            comment(
                5628512577,
                isolated,
                prefix="SOLE CONTROL first durable v3 publication",
            ),
            comment(
                5628564802,
                copy.deepcopy(isolated),
                prefix="SOLE CONTROL repeated durable v3 publication",
            ),
        ])
        self.assertEqual(cid, 5628512577)
        self.assertEqual(selected_comment["id"], 5628512577)
        self.assertEqual(selected["request_id"], PR318_V3_REQUEST_ID)
        self.assertEqual(selected["head"], PR318_HEAD)
        self.assertEqual(selected["tree"], PR318_TREE)
        self.assertEqual(selected["base"], PR318_MAIN)
        self.assertEqual(selected["main"], PR318_MAIN)


if __name__ == "__main__":
    unittest.main()
