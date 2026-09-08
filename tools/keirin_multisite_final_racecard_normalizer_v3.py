#!/usr/bin/env python3
"""Exact-integer hardening wrapper for multisite final racecard normalizer v3.

v3 preserves v2 source/consensus semantics while preventing Python int()
from silently converting bool/float/decimal-like race_no/car_no values.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping
import re

import keirin_multisite_final_racecard_normalizer_v2 as v2

RacecardNormalizerError=v2.RacecardNormalizerError
INVALID_INTEGER_SENTINEL="__INVALID_EXACT_INTEGER__"


def _exact_integer_or_poison(value: Any):
    if isinstance(value,bool):
        return INVALID_INTEGER_SENTINEL
    if isinstance(value,int):
        return value
    if isinstance(value,str) and re.fullmatch(r"[0-9]+",value):
        return int(value)
    return INVALID_INTEGER_SENTINEL


def _harden_observations(
    observations: Iterable[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    out=[]
    for raw in observations:
        if not isinstance(raw,Mapping):
            raise RacecardNormalizerError("observation_must_be_mapping")
        row=deepcopy(dict(raw))
        row["race_no"]=_exact_integer_or_poison(row.get("race_no"))
        row["car_no"]=_exact_integer_or_poison(row.get("car_no"))
        out.append(row)
    return out


def normalize(
    locked_order: Mapping[str, Any],
    observations: Iterable[Mapping[str, Any]],
) -> dict:
    hardened=_harden_observations(observations)
    out=v2.normalize(locked_order,hardened)
    out["record"]="KEIRIN_MULTISITE_FINAL_RACECARD_NORMALIZATION_OUTPUT_v3"
    out["integer_input_policy"]="RACE_NO_CAR_NO_INTEGER_OR_DIGIT_STRING_ONLY_BOOL_FLOAT_REJECTED"
    out["v2_consensus_semantics_preserved"]=True
    return out


def build_finalizer_manifest(
    shell: Mapping[str, Any],
    locked_order: Mapping[str, Any],
    observations: Iterable[Mapping[str, Any]],
) -> dict:
    result=normalize(locked_order,observations)
    out=deepcopy(dict(shell))
    by_reg={r["official_registration_number"]:r for r in result["normalized_rows"]}
    rows=[]
    for row in out.get("rows") or []:
        reg=v2._nfkc(row.get("official_registration_number"))
        rows.append(deepcopy(by_reg.get(reg,row)))
    out["rows"]=rows
    out["record"]="KEIRIN_35_FINAL_DAY1_PRE_INPUT_MANIFEST_MULTISITE_NORMALIZED_v3"
    out["multisite_normalizer"]="tools/keirin_multisite_final_racecard_normalizer_v3.py"
    out["multisite_normalization"]=result
    out["support_increment_authorized_now"]=0
    out["result_access_authorized"]=False
    out["runtime"]=False
    return out
