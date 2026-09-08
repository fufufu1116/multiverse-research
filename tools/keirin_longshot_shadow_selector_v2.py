#!/usr/bin/env python3
"""Select at most one qualified longshot shadow ticket per race v2."""

from typing import Iterable, Dict, List, Mapping

from keirin_longshot_shadow_guard_v2 import evaluate_ticket

LONGSHOT_BANDS={"MID_HOLE","LONGSHOT","EXTREME_LONGSHOT"}


class LongshotSelectorError(ValueError):
    pass


def select_one(ticket_rows: Iterable[Dict]) -> Dict:
    evaluated: List[Dict] = []
    seen_tickets=set()

    for index, raw in enumerate(ticket_rows):
        if not isinstance(raw, Mapping):
            raise LongshotSelectorError(f"ticket_row_must_be_mapping:{index}")
        ticket=raw.get("ticket")
        if not isinstance(ticket,str) or not ticket.strip():
            raise LongshotSelectorError(f"ticket_must_be_nonempty_string:{index}")
        if ticket in seen_tickets:
            raise LongshotSelectorError(f"duplicate_ticket:{ticket}")
        seen_tickets.add(ticket)

        try:
            ev=evaluate_ticket(
                raw["s0_probability"],
                raw["challenger_probability"],
                raw["decimal_odds"],
            )
        except KeyError as exc:
            raise LongshotSelectorError(f"missing_guard_input:{index}:{exc.args[0]}") from exc

        merged=dict(raw)
        merged.update(ev)
        evaluated.append(merged)

    qualified=[
        x for x in evaluated
        if x["qualifies"] and x["band"] in LONGSHOT_BANDS
    ]
    if not qualified:
        return {
            "action":"NO_BET",
            "selected":None,
            "qualified_count":0,
            "evaluated_count":len(evaluated),
            "race_longshot_ticket_cap":1,
            "real_money_instruction":False,
        }

    qualified.sort(
        key=lambda x:(
            -float(x["probability_ratio"]),
            float(x["decimal_odds"]),
            x["ticket"],
        )
    )
    chosen=qualified[0]
    return {
        "action":"SHADOW_SELECT_ONE",
        "selected":chosen,
        "qualified_count":len(qualified),
        "evaluated_count":len(evaluated),
        "discarded_qualified_count":len(qualified)-1,
        "race_longshot_ticket_cap":1,
        "real_money_instruction":False,
    }
