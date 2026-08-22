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

    # Regression for Lab finding: an exact ruleset must not early-return past
    # any competing tag ruleset or same-name noncompliant ruleset.
    exact_plus_other = [base_detail(), copy.deepcopy(other_tag)]
    exact_plus_other[1]["id"] = 125
    expect_denied(exact_plus_other, "OTHER_TAG_RULESET_REQUIRES_REREVIEW")

    exact_plus_same_name_bad = [base_detail(), copy.deepcopy(same_name_bad)]
    exact_plus_same_name_bad[1]["id"] = 126
    expect_denied(exact_plus_same_name_bad, "SAME_NAME_NONCOMPLIANT")

    # Generic endpoint/method/payload primitive is gone. Read-only endpoints
    # come only from a closed builder; the production mutation is argument-free
    # and reruns Fresh barriers internally before the fixed POST.
    assert not hasattr(m, "_gh_json")
    assert list(inspect.signature(m._post_exact_ruleset_after_fresh_barrier).parameters) == []
    assert m._build_get_endpoint("main") == f"/repos/{m.REPO}/branches/main"
    try:
        m._build_get_endpoint("arbitrary_endpoint")
    except m.Denied as exc:
        assert "GET_RESOURCE_NOT_ALLOWLISTED" in str(exc)
    else:
        raise AssertionError("non-allowlisted GET selector must deny")

    dry = m._result("DRY_RUN_WOULD_CREATE_EXACT_RULESET")
    assert dry["secret_material_present"] is False
    assert dry["runtime_activation_performed"] is False
    assert dry["runtime_branch_created"] is False
    assert dry["writer_key_created"] is False
    assert dry["activation_receipt_created"] is False

    print("MULTIVERSE_R1_STAGE1_RULESET_ADMIN_CHANNEL_SELFTEST_PASS")


if __name__ == "__main__":
    main()
