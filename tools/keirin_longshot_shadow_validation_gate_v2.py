#!/usr/bin/env python3
"""Strict prospective validation gate for Keirin longshot shadow ledgers v2.

v2 integrates the anti-jackpot evidence requirement that was only diagnostic
in v1: a stable pass requires at least five expected hits under the frozen
conservative probabilities, in addition to actual hits, time span, positive
ROI, positive leave-largest-hit-out ROI, and <=50% largest-hit profit share.
"""

from collections import defaultdict
from datetime import date
from math import isfinite
from typing import Iterable, Dict, Mapping

BANDS=("MID_HOLE","LONGSHOT","EXTREME_LONGSHOT")
MIN_DECISIONS={"MID_HOLE":100,"LONGSHOT":200,"EXTREME_LONGSHOT":500}
MIN_HITS={"MID_HOLE":5,"LONGSHOT":5,"EXTREME_LONGSHOT":5}
MIN_EXPECTED_HITS=5.0
MIN_WEEKS=8


class LongshotValidationError(ValueError):
    pass


def _finite(value,label):
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise LongshotValidationError(f"{label}_must_be_numeric")
    x=float(value)
    if not isfinite(x):
        raise LongshotValidationError(f"{label}_must_be_finite")
    return x


def _roi(stake,ret):
    return None if stake<=0 else ret/stake-1.0


def _normalize(rows: Iterable[Dict]) -> list[dict]:
    out=[]
    for i,raw in enumerate(rows):
        if not isinstance(raw,Mapping):
            raise LongshotValidationError(f"row_must_be_mapping:{i}")
        band=raw.get("band")
        if band not in BANDS:
            raise LongshotValidationError(f"unsupported_band:{band}")
        stake=_finite(raw.get("stake_units"),"stake_units")
        ret=_finite(raw.get("return_units"),"return_units")
        prob=_finite(raw.get("conservative_probability"),"conservative_probability")
        if stake<=0:
            raise LongshotValidationError("stake_units_must_be_positive")
        if ret<0:
            raise LongshotValidationError("return_units_must_be_nonnegative")
        if not (0.0<=prob<=1.0):
            raise LongshotValidationError("conservative_probability_must_be_in_[0,1]")
        raw_date=raw.get("date")
        if not isinstance(raw_date,str):
            raise LongshotValidationError("date_must_be_iso_string")
        try:
            parsed=date.fromisoformat(raw_date)
        except ValueError as exc:
            raise LongshotValidationError("invalid_iso_date") from exc
        row=dict(raw)
        row["stake_units"]=stake
        row["return_units"]=ret
        row["conservative_probability"]=prob
        row["_date"]=parsed
        row["_order"]=i
        out.append(row)
    return out


def _max_drawdown_and_losing_streak(xs: list[dict]) -> tuple[float,int]:
    ordered=sorted(xs,key=lambda x:(x["_date"],x["_order"]))
    cumulative=0.0
    peak=0.0
    max_drawdown=0.0
    streak=0
    max_streak=0
    for x in ordered:
        net=x["return_units"]-x["stake_units"]
        cumulative+=net
        peak=max(peak,cumulative)
        max_drawdown=max(max_drawdown,peak-cumulative)
        if net<0:
            streak+=1
            max_streak=max(max_streak,streak)
        else:
            streak=0
    return max_drawdown,max_streak


def evaluate_band(rows: Iterable[Dict], band: str) -> Dict:
    if band not in BANDS:
        raise LongshotValidationError(f"unsupported_band:{band}")
    normalized=_normalize(rows)
    xs=[x for x in normalized if x["band"]==band]

    stake=sum(x["stake_units"] for x in xs)
    ret=sum(x["return_units"] for x in xs)
    expected_hits=sum(x["conservative_probability"] for x in xs)
    hits=[x for x in xs if x["return_units"]>0.0]

    largest_index=None
    if hits:
        largest=max(hits,key=lambda x:(x["return_units"],-x["_order"]))
        largest_index=largest["_order"]

    leave_rows=[x for x in xs if x["_order"]!=largest_index]
    leave_stake=sum(x["stake_units"] for x in leave_rows)
    leave_ret=sum(x["return_units"] for x in leave_rows)

    roi=_roi(stake,ret)
    leave_roi=_roi(leave_stake,leave_ret)
    profit=max(ret-stake,0.0)
    largest_profit_contribution=0.0
    if largest_index is not None and profit>0.0:
        largest=next(x for x in xs if x["_order"]==largest_index)
        largest_profit_contribution=(
            max(largest["return_units"]-largest["stake_units"],0.0)/profit
        )

    weeks=defaultdict(lambda:[0.0,0.0])
    months=defaultdict(lambda:[0.0,0.0])
    for x in xs:
        iso=x["_date"].isocalendar()
        week_key=f"{iso.year}-W{iso.week:02d}"
        month_key=f"{x['_date'].year}-{x['_date'].month:02d}"
        weeks[week_key][0]+=x["stake_units"]
        weeks[week_key][1]+=x["return_units"]
        months[month_key][0]+=x["stake_units"]
        months[month_key][1]+=x["return_units"]

    weekly_roi={k:_roi(v[0],v[1]) for k,v in sorted(weeks.items())}
    monthly_roi={k:_roi(v[0],v[1]) for k,v in sorted(months.items())}
    max_drawdown,max_losing_streak=_max_drawdown_and_losing_streak(xs)

    evidence_pass=(
        expected_hits>=MIN_EXPECTED_HITS
        and len(hits)>=MIN_HITS[band]
        and len(weeks)>=MIN_WEEKS
    )
    proposed_pass=(
        len(xs)>=MIN_DECISIONS[band]
        and evidence_pass
        and roi is not None and roi>0.0
        and leave_roi is not None and leave_roi>0.0
        and largest_profit_contribution<=0.50
    )

    return {
        "band":band,
        "decisions":len(xs),
        "hits":len(hits),
        "expected_hits_under_frozen_conservative_probability":expected_hits,
        "stake_units":stake,
        "return_units":ret,
        "roi":roi,
        "leave_largest_hit_out_roi":leave_roi,
        "largest_hit_share_of_profit":largest_profit_contribution,
        "calendar_weeks":len(weeks),
        "weekly_roi":weekly_roi,
        "monthly_roi":monthly_roi,
        "maximum_drawdown_units":max_drawdown,
        "maximum_consecutive_losing_decisions":max_losing_streak,
        "proposed_min_decisions":MIN_DECISIONS[band],
        "minimum_actual_hits":MIN_HITS[band],
        "minimum_expected_hits":MIN_EXPECTED_HITS,
        "minimum_weeks":MIN_WEEKS,
        "evidence_sufficient":evidence_pass,
        "proposed_stable_pass":proposed_pass,
    }


def evaluate(rows: Iterable[Dict]) -> Dict:
    normalized=_normalize(rows)
    bands=[]
    for band in BANDS:
        subset=[
            {k:v for k,v in x.items() if not k.startswith("_")}
            for x in normalized if x["band"]==band
        ]
        bands.append(evaluate_band(subset,band))
    return {
        "status":"PROPOSED_VALIDATION_GATE_ONLY_V2",
        "bands":bands,
        "any_band_stable_pass":any(x["proposed_stable_pass"] for x in bands),
        "stable_pass_requires_expected_hits":True,
        "real_money_authorized":False,
    }
