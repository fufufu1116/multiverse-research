#!/usr/bin/env python3
"""Strict outcome-free core + hole shadow pipeline v2."""

from typing import Dict, Iterable, Optional, Mapping

from keirin_longshot_shadow_selector_v2 import select_one
from keirin_shadow_risk_aggregator_v2 import aggregate

BAND_RISK={"MID_HOLE":0.50,"LONGSHOT":0.25,"EXTREME_LONGSHOT":0.10}


class LongshotPipelineError(ValueError):
    pass


def run_pipeline(
    hole_ticket_rows: Iterable[Dict],
    core_selection: Optional[Dict]=None,
    race_risk_cap: float=1.0,
) -> Dict:
    hole=select_one(hole_ticket_rows)
    selections=[]

    if core_selection is not None:
        if not isinstance(core_selection,Mapping):
            raise LongshotPipelineError("core_selection_must_be_mapping")
        c=dict(core_selection)
        c.setdefault("lane","CORE")
        c.setdefault("requested_risk_units",1.0)
        selections.append(c)

    if hole["action"]=="SHADOW_SELECT_ONE":
        h=dict(hole["selected"])
        band=h["band"]
        if band not in BAND_RISK:
            raise LongshotPipelineError(f"unsupported_selected_hole_band:{band}")
        h["lane"]=band
        h["requested_risk_units"]=BAND_RISK[band]
        selections.append(h)

    risk=aggregate(selections,race_risk_cap=race_risk_cap)
    if sum(1 for x in risk["selections"] if x.get("lane") in BAND_RISK)>1:
        raise LongshotPipelineError("more_than_one_hole_selection_after_aggregation")

    return {
        "hole_selector":hole,
        "risk_aggregation":risk,
        "race_longshot_ticket_cap":1,
        "real_money_instruction":False,
    }
