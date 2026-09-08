from __future__ import annotations

from line_relation_features_v1 import validate_line_states
from c1_n1_line_logit_adapter_v1 import build_c1_n1_distributions


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
    base = {1:1.1, 2:0.9, 3:0.2, 4:1.0, 5:0.4, 6:0.1, 7:-0.2}

    zero = build_c1_n1_distributions(
        base,
        states,
        own_coefficients={},
        rank2_coefficients={},
        rank3_coefficients={},
    )
    assert set(zero["C1"]) == set(zero["N1"])
    assert max(abs(zero["C1"][k] - zero["N1"][k]) for k in zero["C1"]) < 1e-12
    assert abs(sum(zero["C1"].values()) - 1.0) < 1e-12
    assert abs(sum(zero["N1"].values()) - 1.0) < 1e-12

    nonzero = build_c1_n1_distributions(
        base,
        states,
        own_coefficients={"is_bante":0.1},
        rank2_coefficients={"same_line":0.2},
        rank3_coefficients={"first_second_same_line":-0.1},
    )
    assert abs(sum(nonzero["C1"].values()) - 1.0) < 1e-12
    assert abs(sum(nonzero["N1"].values()) - 1.0) < 1e-12
    assert any(abs(nonzero["C1"][k] - nonzero["N1"][k]) > 1e-12 for k in nonzero["C1"])

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
