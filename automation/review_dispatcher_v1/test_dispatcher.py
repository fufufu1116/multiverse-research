from __future__ import annotations

from pathlib import Path

from automation.review_dispatcher_v1 import test_dispatcher_legacy_v1 as _legacy

for _name in dir(_legacy):
    if not _name.startswith("__") and _name != "HardeningTests":
        globals()[_name] = getattr(_legacy, _name)


class HardeningTests(_legacy.HardeningTests):
    def test_24_same_head_supersession_without_digest_fails_closed(self):
        first = _legacy.lab_request("first-chain")
        second = _legacy.lab_request("second-chain")
        comments = [
            {
                "id": 10,
                "body": _legacy.request_body(first),
                "user": {"login": "fufufu1116"},
            },
            {
                "id": 20,
                "body": _legacy.request_body(second),
                "user": {"login": "fufufu1116"},
            },
        ]
        cid, request, _ = _legacy.latest_exact_current_owner_request(
            comments,
            repo=first["repo"],
            pr=first["pr"],
            lane="LAB",
            head=first["head"],
            tree=first["tree"],
            base=first["base"],
            main=first["main"],
        )
        self.assertEqual(cid, 10)
        self.assertEqual(request["request_id"], "first-chain")

    def test_43_validator_assigns_nullable_app_tokens_to_correct_modules(self):
        repo_root = Path(__file__).resolve().parents[2]
        validator_source = (
            repo_root
            / "automation"
            / "review_dispatcher_v1"
            / "validator_legacy_v1.py"
        ).read_text()

        dispatcher_start = validator_source.index(
            'dispatcher_source = (ROOT / "dispatcher.py").read_text()'
        )
        review_start = validator_source.index(
            'review_source = (ROOT / "review.py").read_text()'
        )
        publisher_start = validator_source.index(
            'publisher_source = (ROOT / "publisher.py").read_text()'
        )
        t2_start = validator_source.index(
            't2_source = (ROOT / "t2.py").read_text()'
        )
        github_app_start = validator_source.index(
            'github_app_source = (ROOT / "github_app.py").read_text()'
        )

        dispatcher_block = validator_source[
            dispatcher_start:review_start
        ]
        review_block = validator_source[
            review_start:publisher_start
        ]
        t2_block = validator_source[
            t2_start:github_app_start
        ]

        lab_token = 'lane_result_outer_app_trusted(lab_comment, "LAB")'
        auditor_token = (
            'lane_result_outer_app_trusted(auditor_comment, "AUDITOR")'
        )

        self.assertNotIn(lab_token, dispatcher_block)
        self.assertIn(lab_token, review_block)
        self.assertIn(lab_token, t2_block)
        self.assertIn(auditor_token, t2_block)
