#!/usr/bin/env python3
"""Decompose cumulative odds-cap sweep rows into incremental odds segments.

Research-only helper for already-burned development diagnostics.
It never fetches data, never places bets, and never touches protected holdouts.
"""

from math import isfinite


class OddsCapDecompositionError(ValueError):
    pass


def _num(x, label):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise OddsCapDecompositionError(f"{label}_must_be_numeric")
    x=float(x)
    if not isfinite(x):
        raise OddsCapDecompositionError(f"{label}_must_be_finite")
    return x


def cumulative_return_units(bets, roi):
    bets=_num(bets,"bets")
    roi=_num(roi,"roi")
    if bets < 0 or int(bets) != bets:
        raise OddsCapDecompositionError("bets_must_be_nonnegative_integer")
    if roi < -1:
        raise OddsCapDecompositionError("roi_below_minus_one")
    return bets * (1.0 + roi)


def incremental_segment(prev, cur, precision=3):
    """prev/cur: {'cap', 'bets', 'roi'} cumulative rows."""
    pb=int(_num(prev["bets"],"prev_bets"))
    cb=int(_num(cur["bets"],"cur_bets"))
    if cb < pb:
        raise OddsCapDecompositionError("cumulative_bets_must_be_monotone")
    pr=cumulative_return_units(pb,prev["roi"])
    cr=cumulative_return_units(cb,cur["roi"])
    bets=cb-pb
    returns=round(cr-pr,precision)
    if abs(returns) < 10**(-precision):
        returns=0.0
    roi=(returns/bets - 1.0) if bets else None
    return {
        "odds_segment": f">{prev['cap']}..{cur['cap']}",
        "bets": bets,
        "return_units": returns,
        "roi": roi,
    }


def tail_after_cap(cap_row, unbounded_row, precision=3):
    cb=int(_num(cap_row["bets"],"cap_bets"))
    ub=int(_num(unbounded_row["bets"],"unbounded_bets"))
    if ub < cb:
        raise OddsCapDecompositionError("unbounded_bets_below_cap_bets")
    cr=cumulative_return_units(cb,cap_row["roi"])
    ur=cumulative_return_units(ub,unbounded_row["roi"])
    bets=ub-cb
    returns=round(ur-cr,precision)
    if abs(returns) < 10**(-precision):
        returns=0.0
    roi=(returns/bets - 1.0) if bets else None
    return {
        "odds_segment": f">{cap_row['cap']}",
        "bets": bets,
        "return_units": returns,
        "roi": roi,
    }
