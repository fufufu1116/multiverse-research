#!/usr/bin/env python3
from __future__ import annotations

import copy
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
    try:
        m._classify_existing([same_name_bad])
    except m.Denied as exc:
        assert "SAME_NAME_NONCOMPLIANT" in str(exc)
    else:
        raise AssertionError("same-name noncompliant ruleset must deny")

    other_tag = base_detail()
    other_tag["name"] = "other-tag-ruleset"
    try:
        m._classify_existing([other_tag])
    except m.Denied as exc:
        assert "OTHER_TAG_RULESET_REQUIRES_REREVIEW" in str(exc)
    else:
        raise AssertionError("other tag ruleset must deny")

    duplicate = [base_detail(), copy.deepcopy(base_detail())]
    duplicate[1]["id"] = 124
    try:
        m._classify_existing(duplicate)
    except m.Denied as exc:
        assert "DUPLICATE_EXACT" in str(exc)
    else:
        raise AssertionError("duplicate exact rulesets must deny")

    dry = m._result("DRY_RUN_WOULD_CREATE_EXACT_RULESET")
    assert dry["secret_material_present"] is False
    assert dry["runtime_activation_performed"] is False
    assert dry["runtime_branch_created"] is False
    assert dry["writer_key_created"] is False
    assert dry["activation_receipt_created"] is False

    print("MULTIVERSE_R1_STAGE1_RULESET_ADMIN_CHANNEL_SELFTEST_PASS")


if __name__ == "__main__":
    main()
