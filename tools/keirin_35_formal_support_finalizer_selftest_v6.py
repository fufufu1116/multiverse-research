#!/usr/bin/env python3
from copy import deepcopy
import importlib
import pathlib
import sys

HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))

v6=importlib.import_module("keirin_35_formal_support_finalizer_v6")
v5test=importlib.import_module("keirin_35_formal_support_finalizer_selftest_v5")


def must_fail(fn,contains=None):
    try:
        fn()
    except Exception as exc:
        if contains is not None:
            assert contains in str(exc),(contains,str(exc))
        return
    raise AssertionError("expected fail-closed error")


def decision(out,priority):
    return next(x for x in out["decisions"] if x.get("priority")==priority)


def main():
    order,matrix,registry,manifest=v5test.fixture()

    out=v6.finalize(order,matrix,registry,manifest)
    assert out["record"]=="KEIRIN_35_FORMAL_SUPPORT_FINALIZATION_OUTPUT_v6"
    assert out["new_pass_riders"]==29
    assert out["stopped_after_29_new_pass"] is True
    assert out["integrity_hardening"]["baseline_row_count"]==2

    # Digit strings remain compatible with upstream JSON normalization.
    strings=deepcopy(manifest)
    strings["rows"][0]["race_no"]="1"
    strings["rows"][0]["car_no"]="2"
    string_out=v6.finalize(order,matrix,registry,strings)
    assert decision(string_out,1)["status"]=="PASS_FORMAL_SUPPORT"

    # Floats/bools cannot be silently coerced by int().
    bad_float=deepcopy(manifest)
    bad_float["rows"][0]["race_no"]=1.9
    float_out=v6.finalize(order,matrix,registry,bad_float)
    d=decision(float_out,1)
    assert d["status"]=="FAIL_CLOSED"
    assert "INVALID_PRE_ROW" in d["reason"]

    bad_bool=deepcopy(manifest)
    bad_bool["rows"][0]["car_no"]=True
    bool_out=v6.finalize(order,matrix,registry,bad_bool)
    d=decision(bool_out,1)
    assert d["status"]=="FAIL_CLOSED"
    assert "INVALID_PRE_ROW" in d["reason"]

    bad_decimal_string=deepcopy(manifest)
    bad_decimal_string["rows"][0]["race_no"]="1.0"
    decimal_out=v6.finalize(order,matrix,registry,bad_decimal_string)
    assert decision(decimal_out,1)["status"]=="FAIL_CLOSED"

    # Fixed baseline is immutable and order-insensitive.
    reversed_baseline=deepcopy(manifest)
    reversed_baseline["baseline_supported_rows"].reverse()
    assert v6.finalize(order,matrix,registry,reversed_baseline)["new_pass_riders"]==29

    wrong_reg=deepcopy(manifest)
    wrong_reg["baseline_supported_rows"][0]["registration_number"]="999999"
    must_fail(
        lambda:v6.finalize(order,matrix,registry,wrong_reg),
        "baseline_binding_mismatch",
    )

    wrong_venue=deepcopy(manifest)
    wrong_venue["baseline_supported_rows"][0]["venue"]="別府"
    must_fail(
        lambda:v6.finalize(order,matrix,registry,wrong_venue),
        "baseline_binding_mismatch",
    )

    duplicate=deepcopy(manifest)
    duplicate["baseline_supported_rows"][1]=deepcopy(duplicate["baseline_supported_rows"][0])
    must_fail(
        lambda:v6.finalize(order,matrix,registry,duplicate),
        "duplicate_baseline_supported_row",
    )

    extra=deepcopy(manifest)
    extra["baseline_supported_rows"].append(deepcopy(extra["baseline_supported_rows"][0]))
    must_fail(
        lambda:v6.finalize(order,matrix,registry,extra),
        "baseline_supported_rows_count_mismatch",
    )

    missing=deepcopy(manifest)
    missing["baseline_supported_rows"]=[]
    must_fail(
        lambda:v6.finalize(order,matrix,registry,missing),
        "baseline_supported_rows_count_mismatch",
    )

    # Existing six-failure margin and seven-failure fail-closed behavior survive.
    six=deepcopy(manifest)
    six["rows"]=six["rows"][6:]
    assert v6.finalize(order,matrix,registry,six)["new_pass_riders"]==29

    seven=deepcopy(manifest)
    seven["rows"]=seven["rows"][7:]
    seven_out=v6.finalize(order,matrix,registry,seven)
    assert seven_out["new_pass_riders"]==28
    assert seven_out["status"]=="TARGET_NOT_REACHED_FAIL_CLOSED"

    print("PASS 15/15")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
