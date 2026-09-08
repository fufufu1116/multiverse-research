#!/usr/bin/env python3
"""Post-event reconstruction guard for the locked-35 PRE finalizer v7.

v7 preserves v6 integrity/gate semantics and closes one unambiguous timing hole:
a future-support row captured on a JST calendar date *after* its bound race_date
cannot be treated as prospective PRE.

This intentionally does NOT require an exact pit/cutoff timestamp. Same-day
capture remains eligible under the 2026-09-08 owner policy. The guard only
blocks clearly post-event next-day-or-later reconstruction.

No RESULT/PAYOUT/ODDS/PREDICTION/HUMAN COMMENT access is added.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

import keirin_35_formal_support_finalizer_v6 as v6

JST=timezone(timedelta(hours=9))
POST_EVENT_SENTINEL="__POST_EVENT_CAPTURE_RECONSTRUCTION_BLOCKED__"


def _parse_aware(value: Any):
    text=str(value or "").strip()
    if not text:
        return None
    try:
        dt=datetime.fromisoformat(text.replace("Z","+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None or dt.utcoffset() is None:
        return None
    return dt


def _poison_unambiguously_post_event_rows(future_pre: Mapping[str,Any]) -> tuple[dict,list[dict]]:
    out=deepcopy(dict(future_pre))
    rows=out.get("rows")
    if not isinstance(rows,list):
        return out,[]

    blocked=[]
    for row in rows:
        if not isinstance(row,dict):
            continue
        race_date_raw=str(row.get("race_date") or "").strip()
        captured=_parse_aware(row.get("captured_at_jst"))
        if not race_date_raw or captured is None:
            # Leave malformed/missing fields for v6/v5's existing row-level
            # fail-closed validation.
            continue
        try:
            race_date=datetime.strptime(race_date_raw,"%Y-%m-%d").date()
        except ValueError:
            continue

        captured_jst_date=captured.astimezone(JST).date()
        if captured_jst_date>race_date:
            blocked.append({
                "priority":row.get("priority"),
                "official_registration_number":row.get("official_registration_number"),
                "race_date":race_date_raw,
                "captured_at_jst":str(row.get("captured_at_jst")),
                "captured_jst_date":captured_jst_date.isoformat(),
                "reason":"UNAMBIGUOUS_POST_EVENT_NEXT_DAY_OR_LATER_CAPTURE",
            })
            # v6/v5 will fail this candidate row without aborting the remaining
            # fixed-order candidates, preserving the six-failure margin.
            row["captured_at_jst"]=POST_EVENT_SENTINEL

    return out,blocked


def finalize(order:dict,matrix:dict,registry:dict,future_pre:dict)->dict:
    guarded,blocked=_poison_unambiguously_post_event_rows(future_pre)
    out=v6.finalize(order,matrix,registry,guarded)
    out["record"]="KEIRIN_35_FORMAL_SUPPORT_FINALIZATION_OUTPUT_v7"
    out["post_event_reconstruction_guard"]={
        "policy":"CAPTURED_JST_DATE_MUST_NOT_BE_AFTER_BOUND_RACE_DATE",
        "same_day_capture_allowed":True,
        "exact_pit_cutoff_timestamp_required":False,
        "blocked_row_count":len(blocked),
        "blocked_rows":blocked,
        "v6_integrity_and_gate_semantics_preserved":True,
        "residual_same_day_timing_policy":"OWNER_RELAXED_NO_EXACT_CUTOFF_REQUIRED; ACQUISITION_MUST_REMAIN_PROSPECTIVE",
    }
    return out


def main():
    raise SystemExit(
        "Library finalizer v7: invoke finalize() with locked order/matrix/registry/manifest."
    )


if __name__=="__main__":
    main()
