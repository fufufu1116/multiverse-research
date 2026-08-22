#!/usr/bin/env python3
from __future__ import annotations

import copy
import inspect
import json

import multiverse_r1_stage1_ruleset_admin_channel_v1 as m


def base_detail() -> dict:
    return {
        "id": 123,
        "name": m.RULESET_NAME,
        "target": "tag",
        "source_type": "Repository",
        "source": m.REPO,
        "enforcement": "active",
        "bypass_actors": [],
        "conditions": {
            "ref_name": {
                "include": [m.JOURNAL_INCLUDE, m.ACTIVATION_INCLUDE],
                "exclude": [],
            }
        },
        "rules": [
            {"type": "deletion"},
            {"type": "update"},
            {"type": "non_fast_forward"},
        ],
        "updated_at": "2026-08-22T00:00:00Z",
    }


def must_fail(mutator) -> None:
    value = base_detail()
    mutator(value)
    assert not m._strict_ruleset_detail(value), json.dumps(value, sort_keys=True)


def expect_denied(details: list[dict], needle: str) -> None:
    try:
        m._classify_existing(details)
    except m.Denied as exc:
        assert needle in str(exc), str(exc)
    else:
        raise AssertionError(f"expected denial containing {needle}")


def assert_tamper_denied_without_transport(target, tamper, restore) -> None:
    calls: list[tuple] = []
    original_run = m.subprocess.run

    def forbidden_run(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("mutation tamper must deny before transport")

    tamper()
    m.subprocess.run = forbidden_run
    try:
        try:
            target()
        except m.Denied as exc:
            assert "MUTATION_BINDING_TAMPERED" in str(exc), str(exc)
        else:
            raise AssertionError("mutation binding tamper must deny")
    finally:
        m.subprocess.run = original_run
        restore()
    assert calls == [], calls


def global_tamper(name: str, bad_value):
    original = getattr(m, name)

    def tamper() -> None:
        setattr(m, name, bad_value)

    def restore() -> None:
        setattr(m, name, original)

    return tamper, restore


def payload_tamper():
    def tamper() -> None:
        m.RULESET_PAYLOAD = {
            "name": m.RULESET_NAME,
            "target": "tag",
            "enforcement": "active",
            "bypass_actors": [{"actor_id": 999}],
            "conditions": {"ref_name": {"include": [], "exclude": []}},
            "rules": [],
        }

    def restore() -> None:
        if hasattr(m, "RULESET_PAYLOAD"):
            delattr(m, "RULESET_PAYLOAD")

    return tamper, restore


def main() -> None:
    good = base_detail()
    assert m._strict_ruleset_detail(good)
    assert m._classify_existing([good])[0] == "EXISTING_EXACT"
    assert m._classify_existing([])[0] == "ABSENT_UNAMBIGUOUS"

    must_fail(lambda x: x.__setitem__("bypass_actors", [{"actor_id": 1}]))
    must_fail(lambda x: x["conditions"]["ref_name"]["exclude"].append("refs/tags/x"))
    must_fail(lambda x: x["conditions"]["ref_name"]["include"].append("refs/tags/extra"))
    must_fail(lambda x: x["rules"].append({"type": "creation"}))
    must_fail(lambda x: x.__setitem__("enforcement", "evaluate"))
    must_fail(lambda x: x.__setitem__("target", "branch"))
    must_fail(lambda x: x["rules"][1].__setitem__("parameters", {"unexpected": True}))

    same_name_bad = base_detail()
    same_name_bad["bypass_actors"] = [{"actor_id": 1}]
    expect_denied([same_name_bad], "SAME_NAME_NONCOMPLIANT")

    other_tag = base_detail()
    other_tag["name"] = "other-tag-ruleset"
    expect_denied([other_tag], "OTHER_TAG_RULESET_REQUIRES_REREVIEW")

    duplicate = [base_detail(), copy.deepcopy(base_detail())]
    duplicate[1]["id"] = 124
    expect_denied(duplicate, "DUPLICATE_EXACT")

    # Regression for the first Lab finding: exact reuse cannot early-return past
    # any competing tag ruleset or same-name noncompliant ruleset.
    exact_plus_other = [base_detail(), copy.deepcopy(other_tag)]
    exact_plus_other[1]["id"] = 125
    expect_denied(exact_plus_other, "OTHER_TAG_RULESET_REQUIRES_REREVIEW")

    exact_plus_same_name_bad = [base_detail(), copy.deepcopy(same_name_bad)]
    exact_plus_same_name_bad[1]["id"] = 126
    expect_denied(exact_plus_same_name_bad, "SAME_NAME_NONCOMPLIANT")

    # Generic endpoint/method/payload primitive remains absent. Read-only
    # endpoints come only from a closed builder and production mutation has no
    # caller parameters.
    assert not hasattr(m, "_gh_json")
    assert not hasattr(m, "RULESET_PAYLOAD")
    assert list(inspect.signature(m._post_exact_ruleset_after_fresh_barrier).parameters) == []
    assert list(inspect.signature(m._assert_mutation_bindings_untampered).parameters) == []
    assert m._build_get_endpoint("main") == f"/repos/{m.REPO}/branches/main"
    try:
        m._build_get_endpoint("arbitrary_endpoint")
    except m.Denied as exc:
        assert "GET_RESOURCE_NOT_ALLOWLISTED" in str(exc)
    else:
        raise AssertionError("non-allowlisted GET selector must deny")

    # Direct zero-argument mutation primitive remains fail-closed before
    # transport if a mutable payload is reintroduced or repo identity is rebound.
    for tamper, restore in (
        payload_tamper(),
        global_tamper("REPO", "attacker/alternate-repository"),
    ):
        assert_tamper_denied_without_transport(
            m._post_exact_ruleset_after_fresh_barrier,
            tamper,
            restore,
        )

    # Auditor regression: the *actual CLI --apply entrypoint* must run the same
    # mutation-binding guard before its first Fresh Read / gh transport. Attack
    # every mutation-bound global named in the final Auditor request plus an
    # injected mutable payload and require zero subprocess calls.
    entrypoint_tampers = [
        global_tamper("REPO", "attacker/alternate-repository"),
        global_tamper("EXPECTED_MAIN", "0" * 40),
        global_tamper("PHASE_B_PR", 999),
        global_tamper("PHASE_B_HEAD", "1" * 40),
        global_tamper("PHASE_B_LAB_COMMENT", 9999999999),
        global_tamper("PHASE_B_AUDITOR_REVIEW", 9999999999),
        global_tamper("RUNTIME_BRANCH", "runtime/attacker"),
        global_tamper("RULESET_NAME", "attacker-ruleset"),
        global_tamper("JOURNAL_INCLUDE", "refs/tags/attacker-*"),
        global_tamper("ACTIVATION_INCLUDE", "refs/tags/attacker-activation"),
        global_tamper("API_VERSION", "2099-01-01"),
        global_tamper("_CANONICAL_BLOBS", {"attacker": ("x", "y")}),
        payload_tamper(),
    ]
    for tamper, restore in entrypoint_tampers:
        assert_tamper_denied_without_transport(
            lambda: m.main(["--apply"]),
            tamper,
            restore,
        )

    dry = m._result("DRY_RUN_WOULD_CREATE_EXACT_RULESET")
    assert dry["secret_material_present"] is False
    assert dry["runtime_activation_performed"] is False
    assert dry["runtime_branch_created"] is False
    assert dry["writer_key_created"] is False
    assert dry["activation_receipt_created"] is False

    print("MULTIVERSE_R1_STAGE1_RULESET_ADMIN_CHANNEL_SELFTEST_PASS")


if __name__ == "__main__":
    main()
