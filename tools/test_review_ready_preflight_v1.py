import unittest

from automation.review_dispatcher_v1.review_ready_preflight_v1 import (
    AMBIGUOUS,
    CARRIER,
    READY,
    preflight,
)

HEAD = "1" * 40
TREE = "2" * 40
MAIN = "3" * 40
BASE = "4" * 40


def commit(sha, tree):
    return {"sha": sha, "commit": {"tree": {"sha": tree}}}


def branch(sha):
    return {"commit": {"sha": sha}}


def pr_summary(number):
    return {"number": number, "state": "open", "head": {"sha": HEAD}}


def full_pr(number):
    return {
        "number": number,
        "state": "open",
        "draft": True,
        "merged": False,
        "head": {"sha": HEAD, "ref": "candidate"},
        "base": {"sha": BASE, "ref": "main"},
    }


def fake_fetch(prs):
    def fetch(url):
        if url.endswith(f"/commits/{HEAD}"):
            return commit(HEAD, TREE)
        if url.endswith("/branches/main"):
            return branch(MAIN)
        if f"/commits/{HEAD}/pulls" in url:
            return prs if "page=1" in url else []
        if url.endswith("/pulls/7"):
            return full_pr(7)
        raise AssertionError(url)
    return fetch


class ReviewReadyPreflightTests(unittest.TestCase):
    def test_no_pr(self):
        out = preflight(repo="o/r", head=HEAD, fetch=fake_fetch([]))
        self.assertEqual(out["state"], CARRIER)
        self.assertFalse(out["authority_created"])

    def test_one_pr(self):
        out = preflight(repo="o/r", head=HEAD, fetch=fake_fetch([pr_summary(7)]))
        self.assertEqual(out["state"], READY)
        self.assertEqual(out["pr"], 7)
        self.assertFalse(out["owner_marker_created"])

    def test_ambiguous(self):
        out = preflight(repo="o/r", head=HEAD, fetch=fake_fetch([pr_summary(7), pr_summary(8)]))
        self.assertEqual(out["state"], AMBIGUOUS)
        self.assertEqual(out["exact_open_pr_count"], 2)


if __name__ == "__main__":
    unittest.main()
