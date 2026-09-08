#!/usr/bin/env python3
"""Integrity-hardened PRE-only finalizer v6 for the locked 35-rider front.

v6 preserves v5 support/accounting semantics and adds two fail-closed bindings:
1) the fixed existing baseline must be exactly Takahashi Rika (015018),
   Kawasaki 400m + Hofu 333/333.33m, with no duplicate/extra rows;
2) race_no/car_no may be integer JSON values or digit-only strings only.
   bool/float/decimal-like values are poisoned before v5 validation so they
   cannot be silently truncated by int().

No RESULT/PAYOUT/ODDS/PREDICTION/HUMAN COMMENT access is added.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Mapping
import re

import keirin_35_formal_support_finalizer_v1 as base
import keirin_35_formal_support_finalizer_v5 as v5

EXPECTED_BASELINE = frozenset({
    ("015018", "川崎", "400"),
    ("015018", "防府", "333_OR_333_33"),
})
INVALID_INTEGER_SENTINEL="__INVALID_EXACT_INTEGER__"


def _validate_fixed_baseline(future_pre: dict) -> None:
    rows=future_pre.get("baseline_supported_rows")
    if not isinstance(rows,list):
        raise base.FinalizerError("baseline_supported_rows_must_be_list")
    if len(rows)!=2:
        raise base.FinalizerError(f"baseline_supported_rows_count_mismatch:{len(rows)}")

    observed=[]
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            raise base.FinalizerError(f"baseline_row_must_be_mapping:{i}")
        reg=str(row.get("registration_number") or "")
        venue=str(row.get("venue") or "")
        try:
            bucket=base.circumference_bucket(row.get("circumference_m"))
        except Exception as exc:
            raise base.FinalizerError(f"invalid_baseline_circumference:{i}") from exc
        observed.append((reg,venue,bucket))

    if len(set(observed))!=2:
        raise base.FinalizerError("duplicate_baseline_supported_row")
    if frozenset(observed)!=EXPECTED_BASELINE:
        raise base.FinalizerError(
            "baseline_binding_mismatch_expected_015018_kawasaki400_hofu333"
        )


def _exact_integer_or_poison(value):
    if isinstance(value,bool):
        return INVALID_INTEGER_SENTINEL
    if isinstance(value,int):
        return value
    if isinstance(value,str) and re.fullmatch(r"[0-9]+",value):
        return int(value)
    return INVALID_INTEGER_SENTINEL


def _harden_future_rows(future_pre: dict) -> dict:
    out=deepcopy(future_pre)
    rows=out.get("rows")
    if rows is None:
        rows=[]
    if not isinstance(rows,list):
        raise base.FinalizerError("future_pre_rows_must_be_list")
    for row in rows:
        if not isinstance(row,dict):
            raise base.FinalizerError("future_pre_row_must_be_mapping")
        row["race_no"]=_exact_integer_or_poison(row.get("race_no"))
        row["car_no"]=_exact_integer_or_poison(row.get("car_no"))
    return out


def finalize(order: dict, matrix: dict, registry: dict, future_pre: dict) -> dict:
    if not isinstance(future_pre,dict):
        raise base.FinalizerError("future_pre_must_be_mapping")

    _validate_fixed_baseline(future_pre)
    hardened=_harden_future_rows(future_pre)
    out=v5.finalize(order,matrix,registry,hardened)

    out["record"]="KEIRIN_35_FORMAL_SUPPORT_FINALIZATION_OUTPUT_v6"
    out["integrity_hardening"]={
        "baseline_binding":"EXACT_015018_KAWASAKI400_HOFU333_TWO_ROWS",
        "baseline_row_count":2,
        "future_race_no_input":"INTEGER_OR_DIGIT_STRING_ONLY_BOOL_FLOAT_REJECTED",
        "future_car_no_input":"INTEGER_OR_DIGIT_STRING_ONLY_BOOL_FLOAT_REJECTED",
        "v5_gate_semantics_preserved":True,
        "calendar_block_gate":"UNKNOWN_PENDING_ADOPTED_PR177_DEFINITION",
    }
    return out


def main():
    raise SystemExit(
        "Library finalizer v6: invoke finalize() with locked order/matrix/registry/manifest."
    )


if __name__=="__main__":
    main()
