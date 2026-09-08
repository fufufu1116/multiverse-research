#!/usr/bin/env python3
from keirin_35_formal_support_finalizer_v1 import selftest

if __name__ == "__main__":
    out=selftest()
    assert out["status"]=="PASS"
    print("PASS")
