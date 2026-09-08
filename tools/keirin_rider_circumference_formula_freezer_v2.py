#!/usr/bin/env python3
"""Recursive PRE-only firewall wrapper for exact formula freezer v2.

v2 preserves the v1 frozen formula, parent Blob bindings, support/calendar
authorization gates, membership role checks, and output schema semantics.

New v2 hardening:
- recursively reject RESULT/PAYOUT/ODDS/PREDICTION/COMMENT/WINNER/RANK-like
  fields anywhere inside fit/evaluation membership payloads;
- governance access flags are allowed only when explicitly False;
- formula_fit_authorized/result_join_authorized/model_promotion_authorized may
  not already be True before formula freeze;
- no new model-fit or result authority is added.

No RESULT/PAYOUT/ODDS/PREDICTION/HUMAN COMMENT access is performed.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping

import keirin_rider_circumference_formula_freezer_v1 as v1

FormulaFreezeError=v1.FormulaFreezeError
FORMULA_ID=v1.FORMULA_ID
CALENDAR_DEF=v1.CALENDAR_DEF
S0_BETA=v1.S0_BETA
LAMBDA_GRID=v1.LAMBDA_GRID

# Exact governance/access flags may legitimately appear in PRE artifacts as
# explicit False safeguards. True is always rejected pre-freeze.
_TRUE_GOVERNANCE_KEYS={
    "result_still_closed",
}

_FALSE_ONLY_KEYS={
    "result_accessed",
    "target_result_accessed",
    "payout_accessed",
    "odds_accessed",
    "prediction_accessed",
    "human_comments_accessed",
    "human_forecast_accessed",
    "result_join_authorized",
    "formula_fit_authorized",
    "model_promotion_authorized",
}

_FORBIDDEN_ASCII_TOKENS={
    "result","results","outcome","outcomes",
    "payout","payouts","payoff","payoffs","dividend","dividends",
    "odds",
    "prediction","predictions","forecast","forecasts",
    "comment","comments",
    "winner","winners",
    "finish","finishing",
    "rank","ranking",
}

_FORBIDDEN_JP_FRAGMENTS=(
    "結果","払戻","オッズ","予想","コメント","着順","勝者",
)


def _tokens(key:Any)->set[str]:
    return {x for x in re.split(r"[^a-z0-9]+",str(key).lower()) if x}


def _recursive_pre_only_firewall(obj:Any,label:str,path:str="root")->None:
    """Reject outcome-bearing namespaces anywhere in a PRE membership object."""
    if isinstance(obj,Mapping):
        for raw_key,value in obj.items():
            key=str(raw_key)
            child=f"{path}.{key}"

            if key in _TRUE_GOVERNANCE_KEYS:
                if value is not True:
                    raise FormulaFreezeError(
                        f"pre_freeze_governance_flag_must_be_true:{label}:{child}"
                    )
                continue

            if key in _FALSE_ONLY_KEYS:
                if value is not False:
                    raise FormulaFreezeError(
                        f"pre_freeze_governance_flag_must_be_false:{label}:{child}"
                    )
                # The explicit false safeguard itself is allowed. Continue
                # without token-classifying its key as RESULT/ODDS/etc.
                continue

            tokens=_tokens(key)
            bad=sorted(tokens & _FORBIDDEN_ASCII_TOKENS)
            if bad or any(fragment in key for fragment in _FORBIDDEN_JP_FRAGMENTS):
                marker=bad[0] if bad else key
                raise FormulaFreezeError(
                    f"forbidden_post_decision_field_in_membership:{label}:{child}:{marker}"
                )

            _recursive_pre_only_firewall(value,label,child)

    elif isinstance(obj,list):
        for i,value in enumerate(obj):
            _recursive_pre_only_firewall(value,label,f"{path}[{i}]")

    # Scalar values need no content scan. We intentionally inspect schema
    # names, not arbitrary string values such as rider/source names.


def _validate_authorization_v2(auth:Mapping[str,Any])->None:
    v1._validate_authorization(auth)

    # Outcome/model-fit authority must not already be active before formula
    # freeze. Explicit False is acceptable.
    for key in (
        "result_join_authorized",
        "formula_fit_authorized",
        "model_promotion_authorized",
    ):
        if auth.get(key) is True:
            raise FormulaFreezeError(
                f"authority_must_not_precede_formula_freeze:{key}"
            )

    # Authorization itself must not smuggle outcome payload fields in nested
    # metadata. Governance false flags remain allowed.
    _recursive_pre_only_firewall(auth,"AUTHORIZATION")


def freeze(
    auth:Mapping[str,Any],
    fit_membership:Mapping[str,Any],
    eval_membership:Mapping[str,Any],
)->dict:
    # SECURITY ORDER:
    # 1) authorization only
    # 2) recursive PRE-only membership firewall
    # 3) unchanged v1 static Blob bindings + membership role/window checks
    _validate_authorization_v2(auth)
    _recursive_pre_only_firewall(fit_membership,"DEVELOPMENT_FIT_PRE_ONLY")
    _recursive_pre_only_firewall(
        eval_membership,"DEVELOPMENT_EVALUATION_PRE_ONLY"
    )

    out=v1.freeze(auth,fit_membership,eval_membership)
    out["record"]="KEIRIN_RIDER_CIRCUMFERENCE_EXACT_FORMULA_FREEZE_v2"
    out["pre_only_membership_firewall"]="RECURSIVE_SCHEMA_KEY_FAIL_CLOSED"
    out["governance_false_flags_allowed_only_when_false"]=sorted(_FALSE_ONLY_KEYS)
    out["v1_formula_math_unchanged"]=True
    out["v1_parent_blob_bindings_unchanged"]=True
    out["result_accessed"]=False
    out["result_join_authorized"]=False
    out["formula_fit_authorized"]=False
    out["runtime"]=False

    # Recompute freeze hash after v2 hardening metadata is added.
    payload=dict(out)
    payload.pop("freeze_sha256",None)
    out["freeze_sha256"]=v1.sha256_obj(payload)
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--authorization",required=True)
    ap.add_argument("--fit-membership",required=True)
    ap.add_argument("--evaluation-membership",required=True)
    ap.add_argument("--out")
    a=ap.parse_args()

    try:
        auth=v1.load_json(a.authorization)
        # Authorization is validated before PRE membership files are opened.
        _validate_authorization_v2(auth)

        fit=v1.load_json(a.fit_membership)
        evaluation=v1.load_json(a.evaluation_membership)
        out=freeze(auth,fit,evaluation)

        rendered=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
        if a.out:
            Path(a.out).write_text(rendered,encoding="utf-8")
        print(rendered,end="")
        return 0
    except Exception as exc:
        fail={
            "record":"KEIRIN_RIDER_CIRCUMFERENCE_EXACT_FORMULA_FREEZE_v2",
            "status":"FAIL_CLOSED",
            "fatal_error":f"{type(exc).__name__}: {str(exc)[:800]}",
            "formula_frozen":False,
            "result_join_authorized":False,
            "formula_fit_authorized":False,
            "result_accessed":False,
            "runtime":False,
        }
        print(json.dumps(fail,ensure_ascii=False))
        return 3


if __name__=="__main__":
    raise SystemExit(main())
