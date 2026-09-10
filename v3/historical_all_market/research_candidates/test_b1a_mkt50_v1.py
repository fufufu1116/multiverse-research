#!/usr/bin/env python3
import math
from b1a_mkt50_v1 import (
    MODEL_NAME, POOL_WEIGHT_MODEL, POOL_WEIGHT_MARKET, EPS,
    FailClosed, pool_ticket_distribution, market_shape_from_decimal_odds,
    transform_race_market
)

def close(a,b,tol=1e-12): assert abs(a-b)<=tol,(a,b)
def expect_fail(fn):
    try: fn()
    except FailClosed: return
    raise AssertionError("expected FailClosed")

def test_constants():
    assert MODEL_NAME=="B1a_MKT50_v1"; close(POOL_WEIGHT_MODEL,.5); close(POOL_WEIGHT_MARKET,.5); close(EPS,1e-15)
def test_equal_identity():
    p={"a":.6,"b":.3,"c":.1}; o=pool_ticket_distribution(p,p)
    for k in p: close(o[k],p[k])
def test_geometric():
    m={"a":.81,"b":.19}; q={"a":.36,"b":.64}; o=pool_ticket_distribution(m,q)
    a=math.sqrt(.81*.36); b=math.sqrt(.19*.64); z=a+b
    close(o["a"],a/z); close(o["b"],b/z); close(sum(o.values()),1)
def test_zero_floor():
    o=pool_ticket_distribution({"a":1.0,"b":0.0},{"a":.5,"b":.5})
    assert o["b"]>0 and o["b"]<1e-6
def test_scale_invariance():
    x=pool_ticket_distribution({"a":8.1,"b":1.9},{"a":36,"b":64})
    y=pool_ticket_distribution({"a":.81,"b":.19},{"a":.36,"b":.64})
    for k in x: close(x[k],y[k])
def test_market_shape():
    q=market_shape_from_decimal_odds({"a":2.0,"b":4.0})
    close(q["a"],2/3); close(q["b"],1/3)
def test_fail_closed():
    expect_fail(lambda: pool_ticket_distribution({}, {"a":1}))
    expect_fail(lambda: pool_ticket_distribution({"a":1},{"b":1}))
    expect_fail(lambda: pool_ticket_distribution({"a":-1,"b":2},{"a":.5,"b":.5}))
    expect_fail(lambda: pool_ticket_distribution({"a":float("nan")},{"a":1}))
    expect_fail(lambda: market_shape_from_decimal_odds({"a":1.0}))
    expect_fail(lambda: transform_race_market("win",{"a":1},{"a":1}))
def main():
    tests=[test_constants,test_equal_identity,test_geometric,test_zero_floor,test_scale_invariance,test_market_shape,test_fail_closed]
    for t in tests:t()
    print(f"PASS {len(tests)}/{len(tests)}")
if __name__=="__main__":main()
