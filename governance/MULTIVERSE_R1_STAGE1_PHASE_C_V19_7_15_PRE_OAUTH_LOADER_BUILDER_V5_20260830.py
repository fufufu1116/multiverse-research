#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_15_PRE_OAUTH_LOADER_BUILDER_20260830.py"
BASE_BYTES = 5563
BASE_SHA256 = "21574a5a724aa3d5966720193b433ba4fbdf028602786f8cf7ad635eac402747"

OLD = b'digest="$(/usr/bin/sha256sum -- "$ROOT/$RUNNER" 2>/dev/null)" || fail PHASE_C_V19_7_15_FAIL_RUNNER_SHA256; set -- $digest; test "$#" -ge 1 || fail PHASE_C_V19_7_15_FAIL_RUNNER_SHA256; test "$1" = "$RUNNER_SHA256" || fail PHASE_C_V19_7_15_FAIL_RUNNER_SHA256;'
NEW = b'digest="$(/usr/bin/sha256sum -- "$ROOT/$RUNNER" 2>/dev/null)" || fail PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND; set -- $digest; test "$#" -ge 1 || fail PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND; test "$1" = "$RUNNER_SHA256" || fail PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_MISMATCH;'

def _load_base():
    s = importlib.util.spec_from_file_location("v4_builder", BASE)
    assert s and s.loader
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

def build() -> bytes:
    d = _load_base().build()
    assert len(d) == BASE_BYTES
    assert hashlib.sha256(d).hexdigest() == BASE_SHA256
    assert d.count(OLD) == 1
    out = d.replace(OLD, NEW)
    assert out.count(b"PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND") == 2
    assert out.count(b"PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_MISMATCH") == 1
    return out

if __name__ == "__main__":
    import sys
    sys.stdout.buffer.write(build())
