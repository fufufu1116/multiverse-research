#!/usr/bin/env python3
"""Fail-closed formula freezer for the low-DOF Rider x Circumference model.

This tool does NOT fit outcomes. It freezes the exact already-prespecified
formula and evaluation contract only after:
- support gate PASS,
- exact LOCAL_DAY1_RACE_DATE adoption,
- exact PRE-only development-fit membership frozen,
- exact PRE-only development-evaluation membership frozen,
- and explicit confirmation that RESULT has not yet been opened.

It binds immutable parent proposal/evaluation files by git-blob SHA.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"v3/historical_all_market/research_candidates"

PROPOSAL=BASE/"KEIRIN_RIDER_CIRCUMFERENCE_LOW_DOF_FORMULA_PROPOSAL_20260907_v1.json"
PROPOSAL_BLOB="3c1d74ce7690137e41ba833066dc51b1672c5fe3"
EVAL_WINDOW=BASE/"KEIRIN_RIDER_CIRCUMFERENCE_DEVELOPMENT_EVAL_WINDOW_PREOUTCOME_LOCK_20260908_v1.json"
EVAL_WINDOW_BLOB="a185a19f9554618a1da83ab05e6674530e2a27d0"
EVAL_MATH=BASE/"KEIRIN_RIDER_CIRCUMFERENCE_EVALUATION_MATH_FREEZE_20260908_v1.json"
EVAL_MATH_BLOB="290351d1f8954d7158649e3482f41d7289da2b5d"
READINESS=BASE/"KEIRIN_RIDER_CIRCUMFERENCE_FORMULA_FREEZE_READINESS_CHECKLIST_20260907_v1.json"
READINESS_BLOB="a6694fb6f4f2bb4a8518b2bd0f29386202e19b7c"

FORMULA_ID="S0_PLUS_SHRUNK_RIDER_X_CIRCUMFERENCE_OFFSET_v1"
CALENDAR_DEF="LOCAL_DAY1_RACE_DATE"
S0_BETA=0.22260435254784533
LAMBDA_GRID=[1,4,16,64]

FORBIDDEN_ACCESS_FIELDS=(
    "result_accessed","target_result_accessed","payout_accessed","odds_accessed",
    "prediction_accessed","human_comments_accessed","human_forecast_accessed"
)


class FormulaFreezeError(ValueError):
    pass


def git_blob(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()


def sha256_obj(obj:Any)->str:
    payload=json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(payload).hexdigest()


def load_json(path):
    obj=json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj,dict):
        raise FormulaFreezeError(f"json_root_must_be_object:{path}")
    return obj


def _validate_static_parent(path,expected_blob,record,status):
    got=git_blob(path)
    if got!=expected_blob:
        raise FormulaFreezeError(f"static_parent_blob_drift:{path.name}:{got}")
    obj=load_json(path)
    if obj.get("record")!=record or obj.get("status")!=status:
        raise FormulaFreezeError(f"static_parent_record_or_status_drift:{path.name}")
    return obj


def _assert_no_forbidden_access(obj:Mapping[str,Any],label:str):
    for key in FORBIDDEN_ACCESS_FIELDS:
        if obj.get(key) is True:
            raise FormulaFreezeError(f"forbidden_access_before_formula_freeze:{label}:{key}")
    if obj.get("result_join_authorized") is True:
        raise FormulaFreezeError(f"result_join_must_not_precede_formula_freeze:{label}")


def _validate_authorization(auth:Mapping[str,Any]):
    if not isinstance(auth,Mapping):
        raise FormulaFreezeError("authorization_must_be_mapping")
    for key in (
        "support_gate_pass",
        "calendar_definition_adopted",
        "fit_membership_frozen",
        "evaluation_membership_frozen",
        "result_still_closed",
    ):
        if auth.get(key) is not True:
            raise FormulaFreezeError(f"authorization_gate_not_true:{key}")
    if auth.get("calendar_block_definition")!=CALENDAR_DEF:
        raise FormulaFreezeError("unexpected_calendar_block_definition")
    beta=auth.get("s0_beta")
    if isinstance(beta,bool) or not isinstance(beta,(int,float)) or abs(float(beta)-S0_BETA)>1e-15:
        raise FormulaFreezeError("s0_beta_mutation_detected")
    if auth.get("lambda_grid")!=LAMBDA_GRID:
        raise FormulaFreezeError("lambda_grid_mutation_detected")
    for key in ("support_gate_artifact_sha256","calendar_adoption_artifact_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}",str(auth.get(key) or "")):
            raise FormulaFreezeError(f"invalid_{key}")


def _validate_membership(obj:Mapping[str,Any],role:str):
    if not isinstance(obj,Mapping):
        raise FormulaFreezeError(f"{role}_membership_must_be_mapping")
    if obj.get("membership_frozen") is not True:
        raise FormulaFreezeError(f"{role}_membership_not_frozen")
    if obj.get("role")!=role:
        raise FormulaFreezeError(f"{role}_role_mismatch")
    _assert_no_forbidden_access(obj,role)
    races=obj.get("races")
    if not isinstance(races,list) or not races:
        raise FormulaFreezeError(f"{role}_races_must_be_nonempty_list")
    race_ids=[]
    for i,r in enumerate(races):
        if not isinstance(r,Mapping):
            raise FormulaFreezeError(f"{role}_race_must_be_mapping:{i}")
        rid=r.get("race_id")
        if not isinstance(rid,str) or not rid:
            raise FormulaFreezeError(f"{role}_invalid_race_id:{i}")
        race_ids.append(rid)
    if len(race_ids)!=len(set(race_ids)):
        raise FormulaFreezeError(f"{role}_duplicate_race_id")
    return {
        "race_count":len(races),
        "race_ids":sorted(race_ids),
        "sha256":sha256_obj(obj),
    }


def freeze(auth:Mapping[str,Any],fit_membership:Mapping[str,Any],eval_membership:Mapping[str,Any])->dict:
    # Static authority first; no outcome-bearing data is accepted anywhere.
    _validate_authorization(auth)

    proposal=_validate_static_parent(
        PROPOSAL,PROPOSAL_BLOB,
        "KEIRIN_RIDER_CIRCUMFERENCE_LOW_DOF_FORMULA_PROPOSAL_20260907_v1",
        "PRE_RESULT_NONAUTHORITATIVE_FORMULA_PROPOSAL_READY_FOR_FREEZE_AFTER_SUPPORT_AND_CALENDAR_GATES",
    )
    eval_window=_validate_static_parent(
        EVAL_WINDOW,EVAL_WINDOW_BLOB,
        "KEIRIN_RIDER_CIRCUMFERENCE_DEVELOPMENT_EVAL_WINDOW_PREOUTCOME_LOCK_20260908_v1",
        "PREOUTCOME_CONTIGUOUS_DEVELOPMENT_EVAL_WINDOW_LOCKED_EXACT_CARDS_PENDING",
    )
    eval_math=_validate_static_parent(
        EVAL_MATH,EVAL_MATH_BLOB,
        "KEIRIN_RIDER_CIRCUMFERENCE_EVALUATION_MATH_FREEZE_20260908_v1",
        "PREOUTCOME_EVALUATION_MATH_FROZEN_IMPLEMENTED_SYNTHETIC_REPRO_PASS_REAL_TARGET_ACCESS_DENIED",
    )
    _validate_static_parent(
        READINESS,READINESS_BLOB,
        "KEIRIN_RIDER_CIRCUMFERENCE_FORMULA_FREEZE_READINESS_CHECKLIST_20260907_v1",
        "NONAUTHORITATIVE_PRE_RESULT_READINESS_ONLY_FORMULA_NOT_FROZEN_RESULT_ACCESS_STILL_DENIED",
    )

    fit_meta=_validate_membership(fit_membership,"DEVELOPMENT_FIT_PRE_ONLY")
    eval_meta=_validate_membership(eval_membership,"DEVELOPMENT_EVALUATION_PRE_ONLY")

    # Evaluation membership must obey the already-frozen 2026-09-16..09-26 window.
    for r in eval_membership["races"]:
        d=str(r.get("race_date") or "")
        if not ("2026-09-16"<=d<="2026-09-26"):
            raise FormulaFreezeError(f"evaluation_race_outside_frozen_window:{r.get('race_id')}:{d}")

    freeze_payload={
        "record":"KEIRIN_RIDER_CIRCUMFERENCE_EXACT_FORMULA_FREEZE_v1",
        "status":"FORMULA_FROZEN_PRE_RESULT_READY_FOR_SEPARATE_RESULT_JOIN_AUTHORIZATION",
        "formula_frozen":True,
        "formula_id":FORMULA_ID,
        "baseline":{
            "name":"S0_SCORE_ONLY_SOFTMAX",
            "beta":S0_BETA,
            "beta_frozen":True,
        },
        "challenger":proposal["challenger"],
        "rider_support_rule":proposal["rider_support_rule"],
        "estimator":proposal["estimator"],
        "metrics":proposal["metrics"],
        "uncertainty":proposal["uncertainty"],
        "development_advancement":proposal["development_advancement"],
        "missingness":proposal["missingness"],
        "calendar_block_definition":CALENDAR_DEF,
        "lambda_grid":LAMBDA_GRID,
        "development_fit_membership":{
            "role":"DEVELOPMENT_FIT_PRE_ONLY",
            **fit_meta,
        },
        "development_evaluation_membership":{
            "role":"DEVELOPMENT_EVALUATION_PRE_ONLY",
            **eval_meta,
            "window":eval_window["window"],
        },
        "evaluation_math_binding":{
            "artifact":str(EVAL_MATH.relative_to(ROOT)),
            "git_blob_sha":EVAL_MATH_BLOB,
            "frozen_math_record":eval_math["record"],
        },
        "parent_bindings":{
            "formula_proposal_git_blob":PROPOSAL_BLOB,
            "eval_window_git_blob":EVAL_WINDOW_BLOB,
            "eval_math_git_blob":EVAL_MATH_BLOB,
            "readiness_git_blob":READINESS_BLOB,
            "support_gate_artifact_sha256":auth["support_gate_artifact_sha256"],
            "calendar_adoption_artifact_sha256":auth["calendar_adoption_artifact_sha256"],
        },
        "result_accessed":False,
        "payout_accessed":False,
        "odds_accessed":False,
        "prediction_accessed":False,
        "human_comments_accessed":False,
        "result_join_authorized":False,
        "formula_fit_authorized":False,
        "runtime":False,
        "next":"A separate post-freeze authority may authorize RESULT target join. No result may be opened because this file exists alone.",
    }
    freeze_payload["freeze_sha256"]=sha256_obj(freeze_payload)
    return freeze_payload


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--authorization",required=True)
    ap.add_argument("--fit-membership",required=True)
    ap.add_argument("--evaluation-membership",required=True)
    ap.add_argument("--out")
    a=ap.parse_args()
    try:
        out=freeze(
            load_json(a.authorization),
            load_json(a.fit_membership),
            load_json(a.evaluation_membership),
        )
        rendered=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
        if a.out:
            Path(a.out).write_text(rendered,encoding="utf-8")
        print(rendered,end="")
        return 0
    except Exception as exc:
        fail={
            "record":"KEIRIN_RIDER_CIRCUMFERENCE_EXACT_FORMULA_FREEZE_v1",
            "status":"FAIL_CLOSED",
            "fatal_error":f"{type(exc).__name__}: {str(exc)[:800]}",
            "formula_frozen":False,
            "result_join_authorized":False,
            "result_accessed":False,
            "runtime":False,
        }
        print(json.dumps(fail,ensure_ascii=False))
        return 3


if __name__=="__main__":
    raise SystemExit(main())
