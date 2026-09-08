from __future__ import annotations

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
