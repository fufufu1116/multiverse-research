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


def test_no_pr():
    out = preflight(repo="o/r", head=HEAD, fetch=fake_fetch([]))
    assert out["state"] == CARRIER
    assert out["authority_created"] is False


def test_one_pr():
    out = preflight(repo="o/r", head=HEAD, fetch=fake_fetch([pr_summary(7)]))
    assert out["state"] == READY
    assert out["pr"] == 7
    assert out["owner_marker_created"] is False


def test_ambiguous():
    out = preflight(repo="o/r", head=HEAD, fetch=fake_fetch([pr_summary(7), pr_summary(8)]))
    assert out["state"] == AMBIGUOUS
    assert out["exact_open_pr_count"] == 2


if __name__ == "__main__":
    test_no_pr()
    test_one_pr()
    test_ambiguous()
    print("REVIEW_READY_PREFLIGHT_V1_TESTS_PASS:3")
