#!/usr/bin/env python3
from __future__ import annotations
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_15_PRE_OAUTH_LOADER_ACTION_V5_20260830.txt"
BASE_BYTES = 5588
BASE_SHA256 = "ee71fd11219b97c3b54443638291f59fc4f1db7c6916a344c5be17e48f5b69e4"
EXPECTED_BYTES = 6372
EXPECTED_SHA256 = "434f4b1a733466cf8d9998361917f3ecf5177c02c2e72fa26b164136f6f14eae"

OLD_FAIL = b'fail(){ command printf '\''"'"'\''%s\\n'\''"'"'\'' "$1" >&2; exit 88; };'
NEW_FAIL = b'fail(){ c=102; case "$1" in PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES) c=90 ;; PHASE_C_V19_7_15_FAIL_FRESH_PATHS) c=91 ;; PHASE_C_V19_7_15_FAIL_TMPFS_TRUST) c=92 ;; PHASE_C_V19_7_15_FAIL_GIT_CONTROL) c=93 ;; PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN) c=94 ;; PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD) c=95 ;; PHASE_C_V19_7_15_FAIL_REPO_STATE) c=96 ;; PHASE_C_V19_7_15_FAIL_RUNNER_TRUST) c=97 ;; PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND) c=98 ;; PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_MISMATCH) c=99 ;; PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH) c=100 ;; PHASE_C_V19_7_15_FAIL_RUNNER_RETURN) c=101 ;; esac; command printf '\''"'"'\''%s\\n'\''"'"'\'' "$1" >&2; exit "$c"; };'
OLD_MAIN = b'CANONICAL_MAIN="74ea95e59ac0654e1a0c1f811a178b3eef7b073c";'
NEW_MAIN = b'CANONICAL_MAIN="5c1403c1f5aabb80d29e8c868440aede8888ce61"; CANONICAL_TREE="3d47741b4863411e5c36cb4c28925ac455ab6441";'
OLD_GATE = b'test "$(git_clean -C "$ROOT" rev-parse --verify "refs/remotes/origin/main^{commit}")" = "$CANONICAL_MAIN" || fail PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN; mark PHASE_C_V19_7_15_PASS_CANONICAL_MAIN;'
NEW_GATE = b'test "$(git_clean -C "$ROOT" rev-parse --verify "refs/remotes/origin/main^{commit}")" = "$CANONICAL_MAIN" || fail PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN; test "$(git_clean -C "$ROOT" rev-parse --verify "$CANONICAL_MAIN^{tree}")" = "$CANONICAL_TREE" || fail PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN; mark PHASE_C_V19_7_15_PASS_CANONICAL_MAIN;'

def build() -> bytes:
    d = BASE.read_bytes()
    assert len(d) == BASE_BYTES
    assert hashlib.sha256(d).hexdigest() == BASE_SHA256
    for old in (OLD_FAIL, OLD_MAIN, OLD_GATE):
        assert d.count(old) == 1
    d = d.replace(OLD_FAIL, NEW_FAIL).replace(OLD_MAIN, NEW_MAIN).replace(OLD_GATE, NEW_GATE)
    assert len(d) == EXPECTED_BYTES
    assert hashlib.sha256(d).hexdigest() == EXPECTED_SHA256
    assert d.count(b"\n") == 0 and not d.endswith(b"\n")
    return d

if __name__ == "__main__":
    import sys
    sys.stdout.buffer.write(build())
