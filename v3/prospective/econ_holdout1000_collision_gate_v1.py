#!/usr/bin/env python3
from datetime import date, datetime

HOLDOUT_MAX_DATE=date.fromisoformat("2026-04-10")
EXPECTED_HOLDOUT_ROWS=1000
EXPECTED_ORDERED_SHA="814e72d228ebaf40b4fa1aae636c55c69add71d941f27f6900a0e21d91f2e2c8"
EXPECTED_SORTED_SET_SHA="54c33d907e2e610599bbdf03b81b655707e2b2a71fce9e1ca1c44295cce54"

def date_partition_collision_gate(candidate_race_date, activation_iso):
    rd=date.fromisoformat(str(candidate_race_date))
    act=datetime.fromisoformat(str(activation_iso))
    if rd <= HOLDOUT_MAX_DATE:
        raise RuntimeError("HALT_FAIL_CLOSED candidate not date-disjoint from HOLDOUT membership interval")
    if act.date() <= HOLDOUT_MAX_DATE:
        raise RuntimeError("HALT_FAIL_CLOSED activation not after HOLDOUT interval")
    return {"status":"PASS","intersection":0,"proof":"DATE_PARTITION"}
