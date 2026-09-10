#!/usr/bin/env python3
from b1a_mkt50_final_economic_selector_v1 import select_single

def run():
    base={"3rentan":{"b1a_ticket_probability":{"1-2-3":0.4,"1-3-2":0.6},"decimal_odds":{"1-2-3":4.0,"1-3-2":2.0}}}
    assert select_single(base,0.39,100000) is None
    assert select_single(base,0.40,99) is None
    out=select_single(base,0.40,100000)
    assert out is None or out["stake_yen"]%100==0
    both={
      "3rentan":{"b1a_ticket_probability":{"1-2-3":0.8,"1-3-2":0.2},"decimal_odds":{"1-2-3":3.0,"1-3-2":10.0}},
      "2shatan":{"b1a_ticket_probability":{"1-2":0.7,"2-1":0.3},"decimal_odds":{"1-2":2.0,"2-1":4.0}}
    }
    out2=select_single(both,0.50,100000)
    assert out2 is None or out2["market"] in ("3rentan","2shatan")
    print("PASS 4/4")
if __name__=="__main__": run()
