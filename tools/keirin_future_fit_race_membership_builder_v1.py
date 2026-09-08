#!/usr/bin/env python3
"""Build exact future-side fit-race PRE membership from formalized support.

This tool consumes:
1) a locked-35 finalization output containing confirmed support receipts; and
2) full PRE racecards for the future races containing those confirmed riders.

It outputs exact race/rider PRE membership for later formula fitting, but does
NOT join RESULT, fit any model, authorize formula freeze, or promote anything.

The purpose is speed: on 2026-09-14/15 capture the full PRE card once, so the
support gate and future-side fit membership can be frozen in the same pass.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import argparse
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.parse import urlsplit

import keirin_multisite_final_racecard_normalizer_v2 as n2
import keirin_multisite_final_racecard_normalizer_v5 as n5

JST=timezone(timedelta(hours=9))
FORBIDDEN_ASCII={
    "result","results","outcome","outcomes","payout","payouts","odds",
    "prediction","predictions","forecast","forecasts","comment","comments",
    "finish","finishing","rank","ranking"
}
FORBIDDEN_JP=("結果","払戻","オッズ","予想","コメント","着順")
VALID_STYLES={"逃","追","両"}


class FitMembershipError(ValueError):
    pass


def load_json(path):
    obj=json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj,dict):
        raise FitMembershipError("json_root_must_be_object")
    return obj


def _finite(value,label):
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise FitMembershipError(f"{label}_must_be_numeric")
    x=float(value)
    if not math.isfinite(x):
        raise FitMembershipError(f"{label}_must_be_finite")
    return x


def _exact_int(value,label):
    if isinstance(value,bool):
        raise FitMembershipError(f"{label}_must_be_integer")
    if isinstance(value,int):
        return value
    if isinstance(value,str) and re.fullmatch(r"[0-9]+",value):
        return int(value)
    raise FitMembershipError(f"{label}_must_be_integer")


def _assert_clean_keys(obj:Mapping[str,Any],label:str):
    for key in obj:
        raw=str(key)
        tokens={x for x in re.split(r"[^a-z0-9]+",raw.lower()) if x}
        if tokens & FORBIDDEN_ASCII or any(x in raw for x in FORBIDDEN_JP):
            raise FitMembershipError(f"forbidden_post_decision_field:{label}:{raw}")


def _parse_aware(value,label):
    text=str(value or "").strip()
    try:
        dt=datetime.fromisoformat(text.replace("Z","+00:00"))
    except ValueError as exc:
        raise FitMembershipError(f"{label}_invalid") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise FitMembershipError(f"{label}_must_be_timezone_aware")
    return dt


def _bucket(circ):
    x=_finite(circ,"circumference_m")
    if abs(x-400.0)<1e-6:
        return "400"
    if abs(x-333.0)<1.0 or abs(x-333.33)<1.0:
        return "333_OR_333_33"
    raise FitMembershipError("unsupported_circumference_m")


def _family(raw):
    family=n2._source_family(raw)
    if family not in n2.TRUSTED_SOURCE_FAMILIES:
        raise FitMembershipError(f"untrusted_source_family:{family}")
    return family


def _validate_host(family,url):
    host=(urlsplit(str(url)).hostname or "").lower().rstrip(".")
    root=n5.SOURCE_HOST_ROOTS[family]
    if not (host==root or host.endswith("."+root)):
        raise FitMembershipError(
            f"source_family_hostname_binding_mismatch:{family}:{host}:{root}"
        )


def required_future_races(finalization:Mapping[str,Any])->dict:
    receipts=list(finalization.get("receipts") or [])
    if not receipts:
        raise FitMembershipError("no_confirmed_support_receipts")

    required=defaultdict(list)
    for i,receipt in enumerate(receipts):
        if not isinstance(receipt,Mapping):
            raise FitMembershipError(f"receipt_must_be_mapping:{i}")
        if receipt.get("result_accessed") is True or receipt.get("payout_accessed") is True or receipt.get("odds_accessed") is True:
            raise FitMembershipError(f"forbidden_receipt_access_flag:{i}")
        rider=receipt.get("rider") or {}
        reg=str(rider.get("official_registration_number") or "")
        future=(receipt.get("supported_rows") or {}).get("future") or {}
        race_date=str(future.get("race_date") or "")
        venue=str(future.get("venue") or "")
        race_no=_exact_int(future.get("race_no"),f"receipt_race_no:{i}")
        car_no=_exact_int(future.get("car_no"),f"receipt_car_no:{i}")
        if not re.fullmatch(r"\d{6}",reg):
            raise FitMembershipError(f"invalid_receipt_registration:{i}")
        if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}",race_date) or not venue:
            raise FitMembershipError(f"invalid_receipt_event:{i}")
        key=(race_date,venue,race_no)
        required[key].append({
            "official_registration_number":reg,
            "car_no":car_no,
            "circumference_bucket":_bucket(future.get("circumference_m")),
        })
    return dict(required)


def validate_full_racecard(raw:Mapping[str,Any])->dict:
    if not isinstance(raw,Mapping):
        raise FitMembershipError("racecard_must_be_mapping")
    _assert_clean_keys(raw,"racecard")
    if raw.get("day")!="Day1":
        raise FitMembershipError("racecard_must_be_day1")

    race_date=str(raw.get("race_date") or "")
    venue=str(raw.get("venue") or "").strip()
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}",race_date) or not venue:
        raise FitMembershipError("invalid_racecard_event")
    race_no=_exact_int(raw.get("race_no"),"race_no")
    if not (1<=race_no<=12):
        raise FitMembershipError("race_no_out_of_range")
    bucket=_bucket(raw.get("circumference_m"))

    family=_family(raw)
    source_url=str(raw.get("source_url") or "")
    if not source_url.startswith(("https://","http://")):
        raise FitMembershipError("missing_source_url")
    _validate_host(family,source_url)

    sha=str(raw.get("source_sha256") or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}",sha):
        raise FitMembershipError("invalid_source_sha256")

    captured=_parse_aware(raw.get("captured_at_jst"),"captured_at_jst")
    race_day=datetime.strptime(race_date,"%Y-%m-%d").date()
    if captured.astimezone(JST).date()>race_day:
        raise FitMembershipError("unambiguous_post_event_next_day_or_later_capture")

    riders=raw.get("riders")
    if not isinstance(riders,list) or not (3<=len(riders)<=9):
        raise FitMembershipError("racecard_riders_must_be_3_to_9")

    seen_cars=set()
    seen_regs=set()
    normalized=[]
    for i,r in enumerate(riders):
        if not isinstance(r,Mapping):
            raise FitMembershipError(f"rider_must_be_mapping:{i}")
        _assert_clean_keys(r,f"rider:{i}")
        car=_exact_int(r.get("car_no"),f"car_no:{i}")
        if not (1<=car<=9) or car in seen_cars:
            raise FitMembershipError(f"invalid_or_duplicate_car_no:{car}")
        seen_cars.add(car)
        reg=str(r.get("official_registration_number") or "")
        if not re.fullmatch(r"\d{6}",reg) or reg in seen_regs:
            raise FitMembershipError(f"invalid_or_duplicate_registration:{reg}")
        seen_regs.add(reg)
        name=str(r.get("rider_name") or "").strip()
        cls=str(r.get("class") or "").strip()
        style=str(r.get("style") or "")
        if not name or not cls or style not in VALID_STYLES:
            raise FitMembershipError(f"missing_rider_pre_field:{reg}")
        score=_finite(r.get("competition_score"),f"competition_score:{reg}")
        if score<=0.0:
            raise FitMembershipError(f"competition_score_must_be_positive:{reg}")
        normalized.append({
            "car_no":car,
            "official_registration_number":reg,
            "rider_name":name,
            "class":cls,
            "style":style,
            "competition_score":score,
        })

    return {
        "race_date":race_date,
        "venue":venue,
        "circumference_bucket":bucket,
        "circumference_m":400 if bucket=="400" else 333,
        "day":"Day1",
        "race_no":race_no,
        "source_family":family,
        "source_url":source_url,
        "source_sha256":sha,
        "captured_at_jst":captured.isoformat(),
        "riders":sorted(normalized,key=lambda x:x["car_no"]),
    }


def build(finalization:Mapping[str,Any],racecards:list[Mapping[str,Any]])->dict:
    required=required_future_races(finalization)

    by_key={}
    for raw in racecards:
        card=validate_full_racecard(raw)
        key=(card["race_date"],card["venue"],card["race_no"])
        if key in by_key:
            raise FitMembershipError(f"duplicate_full_racecard:{key}")
        by_key[key]=card

    missing=[]
    exact=[]
    for key,expected_riders in sorted(required.items()):
        card=by_key.get(key)
        if card is None:
            missing.append({
                "race_date":key[0],"venue":key[1],"race_no":key[2],
                "reason":"MISSING_FULL_PRE_RACECARD",
            })
            continue

        by_reg={x["official_registration_number"]:x for x in card["riders"]}
        mismatch=[]
        for expected in expected_riders:
            got=by_reg.get(expected["official_registration_number"])
            if got is None:
                mismatch.append({
                    **expected,"reason":"CONFIRMED_SUPPORT_RIDER_NOT_IN_FULL_RACECARD"
                })
                continue
            if got["car_no"]!=expected["car_no"]:
                mismatch.append({
                    **expected,"observed_car_no":got["car_no"],
                    "reason":"CONFIRMED_SUPPORT_CAR_NO_MISMATCH",
                })
            if card["circumference_bucket"]!=expected["circumference_bucket"]:
                mismatch.append({
                    **expected,"observed_bucket":card["circumference_bucket"],
                    "reason":"CONFIRMED_SUPPORT_CIRCUMFERENCE_MISMATCH",
                })
        if mismatch:
            raise FitMembershipError(f"support_racecard_binding_mismatch:{key}:{mismatch}")

        exact.append({
            **card,
            "confirmed_support_riders_in_race":sorted(
                [x["official_registration_number"] for x in expected_riders]
            ),
            "full_pre_rider_count":len(card["riders"]),
        })

    status="COMPLETE_FUTURE_SIDE_FIT_PRE_MEMBERSHIP" if not missing else "INCOMPLETE_FUTURE_SIDE_FIT_PRE_MEMBERSHIP"

    return {
        "record":"KEIRIN_FUTURE_FIT_RACE_MEMBERSHIP_v1",
        "status":status,
        "required_unique_future_races":len(required),
        "captured_required_races":len(exact),
        "missing_required_races":missing,
        "races":exact,
        "membership_complete":not missing,
        "role":"FUTURE_SIDE_PRE_MEMBERSHIP_CANDIDATE_FOR_POST_SUPPORT_FORMULA_FREEZE",
        "formula_frozen":False,
        "formula_fit_authorized":False,
        "result_join_authorized":False,
        "result_accessed":False,
        "payout_accessed":False,
        "odds_accessed":False,
        "prediction_accessed":False,
        "human_comments_accessed":False,
        "runtime":False,
        "note":"This freezes only future-side full-race PRE membership. Any authoritative formula-fit membership must still satisfy the frozen post-support transition rules and may need additional pre-existing fit-side material.",
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--finalization",required=True)
    ap.add_argument("--racecards",required=True)
    ap.add_argument("--out")
    a=ap.parse_args()
    finalization=load_json(a.finalization)
    raw=json.loads(Path(a.racecards).read_text(encoding="utf-8"))
    racecards=raw.get("racecards") if isinstance(raw,dict) else raw
    if not isinstance(racecards,list):
        raise SystemExit("racecards JSON must be a list or {racecards:[...]}")
    try:
        out=build(finalization,racecards)
        rendered=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
        if a.out:
            Path(a.out).write_text(rendered,encoding="utf-8")
        print(rendered,end="")
        return 0
    except Exception as exc:
        fail={
            "record":"KEIRIN_FUTURE_FIT_RACE_MEMBERSHIP_v1",
            "status":"FAIL_CLOSED",
            "fatal_error":f"{type(exc).__name__}: {str(exc)[:800]}",
            "formula_fit_authorized":False,
            "result_join_authorized":False,
            "result_accessed":False,
            "runtime":False,
        }
        print(json.dumps(fail,ensure_ascii=False))
        return 3


if __name__=="__main__":
    raise SystemExit(main())
