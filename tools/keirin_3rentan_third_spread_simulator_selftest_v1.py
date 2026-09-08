#!/usr/bin/env python3
import keirin_3rentan_third_spread_simulator_v1 as m

class F:
    settle={1:{"race_id":"R"}}
    def cons_first(self,idx):
        return True,[1,2,3,4,5,6,7],{1:0.5}

def main():
    f=F()
    assert m.select(f,1,1,3,0.4)==["1-2-3","1-2-4"]
    assert len(m.select(f,1,1,6,0.4))==5
    assert len(m.select(f,1,2,3,0.4))==4
    assert len(m.select(f,1,2,6,0.4))==10
    print("PASS")

if __name__=="__main__":
    main()
