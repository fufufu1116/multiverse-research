from __future__ import annotations

from line_relation_features_v1 import (
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


def main() -> int:
    states = validate_line_states(fixture())
    r21 = pair_line_features(states, 2, 1)
    assert r21["same_line"] is True
    assert r21["candidate_directly_behind_context"] is True
    assert r21["context_is_line_head_of_candidate"] is True
    assert r21["position_delta_candidate_minus_context"] == 1

    r14 = pair_line_features(states, 1, 4)
    assert r14["same_line"] is False
    assert r14["within_line_position_relation_known"] is False
    assert r14["position_delta_candidate_minus_context"] == 0

    r6 = encode_race_line_relations(fixture())
    assert r6["own"][6]["is_singleton"] is True
    assert r6["own"][2]["is_bante"] is True
    assert r6["own"][3]["is_third"] is True
    assert r6["result_fields_included"] is False
    assert r6["odds_fields_included"] is False

    r3 = rank3_context_features(states, 3, 1, 2)
    assert r3["first_second_same_line"] is True
    assert r3["to_first_same_line"] is True
    assert r3["to_second_candidate_directly_behind_context"] is True

    bad = fixture()
    bad[1] = dict(bad[1], line_position=2)
    try:
        validate_line_states(bad)
    except LineRelationError:
        pass
    else:
        raise AssertionError("invalid non-contiguous topology must fail closed")

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
