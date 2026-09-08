from __future__ import annotations

from copy import deepcopy

from line_relation_features_v2 import (
    LineRelationError,
    encode_race_line_relations,
    pair_line_features,
    rank3_context_features,
    validate_line_states,
)


def fixture():
    return [
        {"car_no":1,"line_group_id":"A","line_position":0,"line_size":3,"is_singleton":False},
        {"car_no":2,"line_group_id":"A","line_position":1,"line_size":3,"is_singleton":False},
        {"car_no":3,"line_group_id":"A","line_position":2,"line_size":3,"is_singleton":False},
        {"car_no":4,"line_group_id":"B","line_position":0,"line_size":2,"is_singleton":False},
        {"car_no":5,"line_group_id":"B","line_position":1,"line_size":2,"is_singleton":False},
        {"car_no":6,"line_group_id":"C","line_position":0,"line_size":1,"is_singleton":True},
        {"car_no":7,"line_group_id":"D","line_position":0,"line_size":1,"is_singleton":True},
    ]


def must_fail(rows, contains=None):
    try:
        validate_line_states(rows)
    except LineRelationError as exc:
        if contains is not None:
            assert contains in str(exc), (contains, str(exc))
        return
    raise AssertionError("expected LineRelationError")


def main() -> int:
    states = validate_line_states(fixture())

    # Direct-ahead / direct-behind relationships must be reciprocal.
    a = pair_line_features(states, 1, 2)
    b = pair_line_features(states, 2, 1)
    assert a["candidate_directly_ahead_of_context"] is True
    assert b["candidate_directly_behind_context"] is True
    assert a["same_line"] == b["same_line"] is True
    assert a["position_delta_candidate_minus_context"] == -b["position_delta_candidate_minus_context"]

    # Cross-line relationships must stay neutral rather than inventing order.
    cross = pair_line_features(states, 1, 4)
    assert cross["same_line"] is False
    assert cross["within_line_position_relation_known"] is False
    assert cross["position_delta_candidate_minus_context"] == 0

    # Rank-3 context must preserve distinct-car semantics.
    r3 = rank3_context_features(states, 3, 1, 2)
    assert r3["first_second_same_line"] is True
    assert r3["to_second_candidate_directly_behind_context"] is True
    try:
        rank3_context_features(states, 3, 1, 1)
    except LineRelationError:
        pass
    else:
        raise AssertionError("duplicate rank3 cars must fail")

    # Deterministic encoding, including generator input.
    one = encode_race_line_relations(fixture())
    two = encode_race_line_relations((row for row in fixture()))
    assert one == two
    assert one["cars"] == (1,2,3,4,5,6,7)
    assert one["own"][6]["is_singleton"] is True
    assert one["result_fields_included"] is False
    assert one["payout_fields_included"] is False
    assert one["odds_fields_included"] is False
    assert one["prediction_fields_included"] is False
    assert one["human_comment_fields_included"] is False

    # Existing structural fail-closed checks.
    duplicate = fixture() + [deepcopy(fixture()[0])]
    must_fail(duplicate, "duplicate_car_no")

    bad_size = fixture()
    bad_size[0] = dict(bad_size[0], line_size=2)
    must_fail(bad_size, "line_size_group_mismatch")

    bad_position = fixture()
    bad_position[1] = dict(bad_position[1], line_position=2)
    must_fail(bad_position, "line_positions_not_contiguous")

    bad_singleton = fixture()
    bad_singleton[5] = dict(bad_singleton[5], is_singleton=False)
    must_fail(bad_singleton, "singleton_semantics_mismatch")

    bad_car = fixture()
    bad_car[6] = dict(bad_car[6], car_no=10)
    must_fail(bad_car, "car_no_exceeds_keirin_domain")

    # PRE-only firewall: ignored post-decision columns are no longer allowed.
    for forbidden_key in (
        "result_rank",
        "payout_yen",
        "odds",
        "prediction_score",
        "human_comments",
        "着順",
        "払戻金",
        "オッズ",
        "予想印",
        "コメント",
    ):
        bad = fixture()
        bad[0] = dict(bad[0], **{forbidden_key: "blocked"})
        must_fail(bad, "forbidden_post_decision_field")

    print("PASS 18/18")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
