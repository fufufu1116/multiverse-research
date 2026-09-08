#!/usr/bin/env python3
from keirin_odds_cap_incremental_decomposer_v1 import incremental_segment, tail_after_cap

def main():
    a20={"cap":20,"bets":56,"roi":0.082143}
    a25={"cap":25,"bets":65,"roi":-0.067692}
    aun={"cap":None,"bets":76,"roi":-0.202632}
    b20={"cap":20,"bets":33,"roi":0.854545}
    bun={"cap":None,"bets":40,"roi":0.53}

    s=incremental_segment(a20,a25)
    assert s["bets"]==9
    assert abs(s["return_units"]) <= 0.001
    assert s["roi"] == -1.0

    ta=tail_after_cap(a20,aun)
    tb=tail_after_cap(b20,bun)
    assert ta["bets"]==20 and ta["roi"]==-1.0
    assert tb["bets"]==7 and tb["roi"]==-1.0
    print("PASS")

if __name__=="__main__":
    main()
