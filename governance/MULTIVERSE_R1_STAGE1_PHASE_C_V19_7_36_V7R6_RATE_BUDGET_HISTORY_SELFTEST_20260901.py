#!/usr/bin/env python3
"""Deterministic pre-Lab model of v7r6 anonymous comment polling budget.
Review-only: no network, no authority, no Runtime activation.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

PAGE=100
HARD=40
EXTERNAL=60
POLL_SECONDS=30
WINDOW_SECONDS=600
LATE_SECONDS=510

@dataclass(frozen=True)
class C:
    id:int
    created_at:datetime
    updated_at:datetime
    kind:str

def pages(n:int)->int:
    return n//PAGE + 1

def merge(state:dict[int,C], items:list[C])->None:
    for c in items:
        state[c.id]=c

def delta(all_comments:list[C], since:datetime)->list[C]:
    return [c for c in all_comments if c.updated_at > since]

def main()->None:
    t0=datetime(2033,5,18,tzinfo=timezone.utc)
    history=[C(i,t0-timedelta(days=2),t0-timedelta(days=2),'other') for i in range(1,601)]
    freeze=C(601,t0-timedelta(minutes=1),t0-timedelta(minutes=1),'freeze')
    corpus=history+[freeze]
    state={c.id:c for c in corpus}
    used=1+pages(len(corpus))
    assert pages(len(corpus))==7
    assert used==8
    cursor=t0
    late_at=t0+timedelta(seconds=LATE_SECONDS)
    approval=C(602,late_at,late_at,'approval')
    session=C(603,late_at+timedelta(seconds=1),late_at+timedelta(seconds=1),'session')
    observed_at=None
    for elapsed in range(POLL_SECONDS, WINDOW_SECONDS+1, POLL_SECONDS):
        now=t0+timedelta(seconds=elapsed)
        visible=list(corpus)
        if now>=late_at:
            visible += [approval,session]
        d=delta(visible,cursor-timedelta(seconds=2))
        used += pages(len(d))
        merge(state,d)
        cursor=now
        if 602 in state and 603 in state and observed_at is None:
            observed_at=elapsed
            break
    assert observed_at is not None and 510 <= observed_at <= 540
    assert state[602].kind=='approval' and state[603].kind=='session'
    assert used <= 26, used
    assert used < HARD < EXTERNAL
    edited=C(602,approval.created_at,approval.updated_at+timedelta(seconds=45),'approval-edited')
    used += pages(1)
    merge(state,[edited])
    assert state[602].kind=='approval-edited'
    assert used < HARD < EXTERNAL
    full_used=1+pages(len(corpus))+(WINDOW_SECONDS//POLL_SECONDS)
    assert full_used==28
    assert full_used < HARD < EXTERNAL
    print('PHASE_C_V19_7_36_V7R6_HISTORY_RATE_BUDGET_SELFTEST_PASS')
    print(f'CURRENT_SIZE_MODEL_COMMENTS={len(corpus)} INITIAL_PAGES={pages(len(corpus))} LATE_OBSERVED_SECONDS={observed_at} REQUESTS_AT_LATE_OBSERVATION={used} FULL_WINDOW_REQUESTS={full_used} HARD_BUDGET={HARD} EXTERNAL_LIMIT={EXTERNAL}')
    print('SECURITY_AUTHORITY_GRANTED=false')
    print('RUNTIME=OFF')

if __name__=='__main__':
    main()
