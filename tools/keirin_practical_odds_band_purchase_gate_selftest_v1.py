#!/usr/bin/env python3
from keirin_practical_odds_band_purchase_gate_v1 import (
    PracticalOddsBandError, band_for_odds, evaluate
)

def main():
    assert band_for_odds(20.0)["name"]=="CORE"
    assert band_for_odds(20.1)["name"]=="MID_HOLE"
    assert band_for_odds(80.0)["name"]=="MID_HOLE"
    assert band_for_odds(80.1)["name"]=="LONGSHOT"
    assert band_for_odds(300.0)["name"]=="LONGSHOT"
    assert band_for_odds(300.1)["name"]=="EXTREME_LONGSHOT"

    # Core: p=10%, 11x => +10% EV, qualifies.
    assert evaluate(0.10,0.11,11.0)["qualifies"] is True

    # Mid-hole: p=4%, 30x => +20% EV only, does not meet +35%.
    assert evaluate(0.04,0.05,30.0)["qualifies"] is False

    # Mid-hole: p=5%, 30x => +50%, qualifies.
    assert evaluate(0.05,0.06,30.0)["qualifies"] is True

    # Longshot: p=1%, 150x => +50%, below required +75%.
    assert evaluate(0.01,0.012,150.0)["qualifies"] is False

    # Longshot: p=1.2%, 150x => +80%, qualifies.
    assert evaluate(0.012,0.014,150.0)["qualifies"] is True

    # Extreme: p=0.6%, 500x => +200%, qualifies.
    assert evaluate(0.006,0.007,500.0)["qualifies"] is True

    # Today's R8 frozen p: any valid odds >=3.3 qualifies under its current band;
    # crucially >20x is not rejected merely for being >20.
    assert evaluate(0.342756614995,0.342756614995,3.3)["qualifies"] is True
    assert evaluate(0.342756614995,0.342756614995,25.0)["qualifies"] is True
    assert evaluate(0.342756614995,0.342756614995,100.0)["qualifies"] is True
    assert evaluate(0.342756614995,0.342756614995,500.0)["qualifies"] is True

    try:
        evaluate(True,0.1,10.0)
        raise AssertionError("bool should fail")
    except PracticalOddsBandError:
        pass

    print("PASS")

if __name__=="__main__":
    main()
