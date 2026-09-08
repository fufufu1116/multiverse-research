#!/usr/bin/env python3
"""Non-authoritative LOCAL_DAY1_RACE_DATE calendar-block shadow evaluator.

This tool never adopts PR177 and never authorizes the full support gate.
It exists only to precompute the two calendar-block dimensions under the exact
candidate definition LOCAL_DAY1_RACE_DATE so Control can bind the result
immediately if/when that definition is independently adopted.

Input: confirmed cross-circumference support receipts.
Output: distinct Day1 dates per circumference and shadow PASS/FAIL.
No RESULT/PAYOUT/ODDS/PREDICTION/comment access is used.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import keirin_support_gate_partial_evaluator_v1 as partial

CANDIDATE_DEFINITION="LOCAL_DAY1_RACE_DATE"


class CalendarShadowError(ValueError):
    pass


def load_json(path):
    obj=json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj,dict):
        raise CalendarShadowError("receipt_root_must_be_object")
    return obj


def evaluate(receipts:list[dict])->dict:
    spec=partial.validate_prespec()
    threshold=spec["minimum_gate"]["minimum_distinct_calendar_blocks_per_circumference"]

    dates=defaultdict(set)
    regs=set()
    row_count=0
    for receipt in receipts:
        reg,rows=partial.extract_receipt(receipt)
        regs.add(reg)
        for row in rows:
            dates[row["circumference_bucket"]].add(row["race_date"])
            row_count+=1

    checks={}
    for bucket in ("333_OR_333_33","400"):
        values=sorted(dates[bucket])
        checks[bucket]={
            "calendar_block_definition":CANDIDATE_DEFINITION,
            "distinct_local_day1_race_dates":values,
            "value":len(values),
            "threshold":threshold,
            "shadow_status":"PASS" if len(values)>=threshold else "FAIL",
        }

    return {
        "record":"KEIRIN_SUPPORT_GATE_LOCAL_DAY1_CALENDAR_SHADOW_v1",
        "status":"SHADOW_ONLY_NO_ADOPTION_AUTHORITY",
        "candidate_definition":CANDIDATE_DEFINITION,
        "confirmed_receipts":len(receipts),
        "unique_riders":len(regs),
        "supported_rows_seen":row_count,
        "checks":checks,
        "both_calendar_dimensions_shadow_pass":all(
            x["shadow_status"]=="PASS" for x in checks.values()
        ),
        "definition_adopted":False,
        "full_gate_pass_authorized":False,
        "support_increment_authorized_now":0,
        "result_accessed":False,
        "payout_accessed":False,
        "odds_accessed":False,
        "prediction_accessed":False,
        "human_comments_accessed":False,
        "runtime":False,
        "note":"Control may bind these calculations only if the exact LOCAL_DAY1_RACE_DATE definition is independently adopted. This tool itself cannot convert shadow PASS into canonical PASS.",
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("receipts",nargs="+")
    ap.add_argument("--out")
    a=ap.parse_args()
    try:
        out=evaluate([load_json(x) for x in a.receipts])
        rendered=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
        if a.out:
            Path(a.out).write_text(rendered,encoding="utf-8")
        print(rendered,end="")
        return 0
    except Exception as exc:
        fail={
            "record":"KEIRIN_SUPPORT_GATE_LOCAL_DAY1_CALENDAR_SHADOW_v1",
            "status":"FAIL_CLOSED_EVALUATOR_ERROR",
            "fatal_error":f"{type(exc).__name__}: {str(exc)[:500]}",
            "definition_adopted":False,
            "full_gate_pass_authorized":False,
            "result_accessed":False,
            "runtime":False,
        }
        print(json.dumps(fail,ensure_ascii=False))
        return 3


if __name__=="__main__":
    raise SystemExit(main())
