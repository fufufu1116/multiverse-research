#!/usr/bin/env python3
import math

import keirin_manual_odds_purchase_gate_v2 as g


def must_fail(fn, contains=None):
    try:
        fn()
    except g.OddsGateError as exc:
        if contains is not None:
            assert contains in str(exc), (contains,str(exc))
        return
    raise AssertionError("expected OddsGateError")


def main():
    assert g.minimum_purchase_odds(0.072,0.10)==15.3
    assert g.minimum_purchase_odds(0.10,0.0)==10.0
    x=g.decision(0.072,0.10,15.3)
    y=g.decision(0.072,0.10,15.2)
    assert x["threshold_met"] is True
    assert y["threshold_met"] is False
    assert x["network_access"] is False
    assert x["automated_execution"] is False

    must_fail(lambda:g.decision(0.072,0.10,float("nan")),"current_odds_must_be_finite")
    must_fail(lambda:g.decision(0.072,0.10,float("inf")),"current_odds_must_be_finite")
    must_fail(lambda:g.decision(0.072,0.10,0.9),"current_odds_must_be_at_least_1")
    must_fail(lambda:g.minimum_purchase_odds(0.072,float("nan")),"required_roi_must_be_finite")
    must_fail(lambda:g.minimum_purchase_odds(0.072,0.10,float("inf")),"display_step_must_be_finite")
    must_fail(lambda:g.minimum_purchase_odds(0.0,0.10),"probability_must_be_in_(0,1]")
    must_fail(lambda:g.minimum_purchase_odds(1.1,0.10),"probability_must_be_in_(0,1]")

    print("PASS 11/11")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
