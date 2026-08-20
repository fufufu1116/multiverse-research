from __future__ import annotations
import math
from c0_c1_n1_broad_assumption_range_stress_v1 import (
    LINE_SHAPES,TIER_A_LINE_SHAPES,TIER_B_LINE_SHAPES,RHOS,_materialize,_base_race,_apply_exact_rho,_car_order
)
from long_line_topology_fixture_v1 import apply_line_shape_fixture,assert_line_topology_invariants
from digital_twin_v1 import pre_view

def partitions(n,max_part=None):
    if n==0:
        yield (); return
    if max_part is None or max_part>n: max_part=n
    for first in range(max_part,0,-1):
        for rest in partitions(n-first,first): yield (first,)+rest

def corr(a,b):
    ma=sum(a)/len(a); mb=sum(b)/len(b)
    da=[x-ma for x in a]; db=[x-mb for x in b]
    return sum(x*y for x,y in zip(da,db))/math.sqrt(sum(x*x for x in da)*sum(y*y for y in db))

def nonline(pre):
    return [(r['car_no'],r['class'],r['score'],r['style'],r['H'],r['B'],r['S'],r['nige'],r['makuri'],r['sashi'],r['mark']) for r in pre['riders']]

def main():
    expected=set(partitions(7))
    assert len(expected)==15 and set(LINE_SHAPES.values())==expected
    assert len(TIER_A_LINE_SHAPES)==6 and len(TIER_B_LINE_SHAPES)==9
    base=_base_race('R2_EMPIRICAL_JOINT',20260820,3); basepre=pre_view(base)
    order=_car_order(20260820,3,base)
    for name,shape in LINE_SHAPES.items():
        changed=apply_line_shape_fixture(base,shape,car_order=order); assert_line_topology_invariants(changed,shape)
        p=pre_view(changed)
        assert nonline(p)==nonline(basepre), name
        assert p['bank_length_m']==basepre['bank_length_m'] and p['wind_speed_mps']==basepre['wind_speed_mps']
    for rho in RHOS:
        rr=_apply_exact_rho(base,20260820,3,rho)
        assert nonline(pre_view(rr))==nonline(basepre)
        c=corr([r.observed_score for r in rr.riders],[r.latent_skill for r in rr.riders])
        assert abs(c-rho)<1e-10,(rho,c)
    a=_materialize('R1_EMPIRICAL_MARGINAL','L43',400,3.0,0.75,20260820,5)
    b=_materialize('R1_EMPIRICAL_MARGINAL','L43',400,3.0,0.75,20260820,5)
    assert a==b
    assert a.bank_length_m==400 and a.wind_speed_mps==3.0
    assert_line_topology_invariants(a,(4,3))
    print('BROAD_ASSUMPTION_RANGE_STRESS_SELFTEST_PASS')
if __name__=='__main__': main()
