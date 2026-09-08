from __future__ import annotations

from copy import deepcopy
import math

from line_relation_features_v2 import RunnerLineState, validate_line_states
from c1_n1_line_logit_adapter_v2 import (
    LineLogitAdapterV2Error,
    build_c1_n1_distributions,
    build_c1_n1_distributions_from_pre_rows,
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


BASE = {1:1.1, 2:0.9, 3:0.2, 4:1.0, 5:0.4, 6:0.1, 7:-0.2}


def must_fail(callable_, contains=None):
    try:
        callable_()
    except (LineLogitAdapterV2Error, ValueError) as exc:
        if contains is not None:
            assert contains in str(exc), (contains, str(exc))
        return
    raise AssertionError("expected fail-closed error")


def assert_distribution(dist):
    assert len(dist) == 7 * 6 * 5 == 210
    assert abs(sum(dist.values()) - 1.0) < 1e-12
    assert all(len(k) == 3 and len(set(k)) == 3 for k in dist)
    assert all(set(k) <= set(BASE) for k in dist)
    assert all(math.isfinite(p) and 0.0 <= p <= 1.0 for p in dist.values())


def main() -> int:
    states = validate_line_states(fixture())

    # Zero line coefficients must collapse exactly to the PL control.
    zero = build_c1_n1_distributions(BASE, states, {}, {}, {})
    assert_distribution(zero["C1"])
    assert_distribution(zero["N1"])
    assert set(zero["C1"]) == set(zero["N1"])
    assert max(abs(zero["C1"][k] - zero["N1"][k]) for k in zero["C1"]) < 1e-12

    # Same PRE input must be deterministic.
    repeat = build_c1_n1_distributions(BASE, states, {}, {}, {})
    assert zero == repeat

    # Nonzero conditional line terms must be able to distinguish N1 from C1
    # while preserving a valid full distribution.
    nonzero = build_c1_n1_distributions(
        BASE,
        states,
        {"is_bante":0.1},
        {"same_line":0.2},
        {"first_second_same_line":-0.1},
    )
    assert_distribution(nonzero["C1"])
    assert_distribution(nonzero["N1"])
    assert any(abs(nonzero["C1"][k] - nonzero["N1"][k]) > 1e-12 for k in nonzero["C1"])

    # Preferred raw-row entry point must give the same zero-coefficient object.
    raw = build_c1_n1_distributions_from_pre_rows(BASE, fixture(), {}, {}, {})
    assert raw == zero

    # Fresh post-decision fields must fail at the raw PRE boundary.
    leaked = fixture()
    leaked[0] = dict(leaked[0], result_rank=1)
    must_fail(
        lambda: build_c1_n1_distributions_from_pre_rows(BASE, leaked, {}, {}, {}),
        "forbidden_post_decision_field",
    )

    # A caller cannot bypass topology validation by fabricating a state map.
    bad_topology = dict(states)
    bad_topology[2] = RunnerLineState(
        car_no=2, line_group_id="A", line_position=2, line_size=3, is_singleton=False
    )
    must_fail(
        lambda: build_c1_n1_distributions(BASE, bad_topology, {}, {}, {}),
        "invalid_line_state_topology",
    )

    # Mapping key and embedded car number must agree.
    bad_key = dict(states)
    bad_key[8] = bad_key.pop(7)
    must_fail(
        lambda: build_c1_n1_distributions(BASE, bad_key, {}, {}, {}),
        "state_mapping_key_car_no_mismatch",
    )

    # Base utility domain and numeric values are fail-closed.
    missing = dict(BASE)
    missing.pop(7)
    must_fail(
        lambda: build_c1_n1_distributions(missing, states, {}, {}, {}),
        "base_utility_and_line_state_car_set_mismatch",
    )
    nonfinite = dict(BASE)
    nonfinite[7] = float("inf")
    must_fail(
        lambda: build_c1_n1_distributions(nonfinite, states, {}, {}, {}),
        "nonfinite_base_utility",
    )

    # Coefficients must be finite and refer only to admitted features.
    must_fail(
        lambda: build_c1_n1_distributions(
            BASE, states, {"is_bante":float("nan")}, {}, {}
        ),
        "nonfinite_coefficient",
    )
    must_fail(
        lambda: build_c1_n1_distributions(
            BASE, states, {"not_a_feature":1.0}, {}, {}
        ),
        "missing_feature",
    )

    print("PASS 12/12")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
