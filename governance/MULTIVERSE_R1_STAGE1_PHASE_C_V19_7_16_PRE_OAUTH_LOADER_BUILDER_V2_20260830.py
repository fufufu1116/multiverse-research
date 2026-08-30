#!/usr/bin/env python3
from __future__ import annotations
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_15_PRE_OAUTH_LOADER_ACTION_V5_20260830.txt"
OUT=ROOT/"governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_ACTION_V2_20260830.txt"
BASE_BYTES=5588
BASE_SHA256="ee71fd11219b97c3b54443638291f59fc4f1db7c6916a344c5be17e48f5b69e4"
OLD_FAIL=b'''fail(){ command printf '\"'\"'%s\\n'\"'\"' "$1" >&2; exit 88; };'''
NEW_FAIL=b'''fail(){ c=115; case "$1" in PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES) c=103 ;; PHASE_C_V19_7_15_FAIL_FRESH_PATHS) c=104 ;; PHASE_C_V19_7_15_FAIL_TMPFS_TRUST) c=105 ;; PHASE_C_V19_7_15_FAIL_GIT_CONTROL) c=106 ;; PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN) c=107 ;; PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD) c=108 ;; PHASE_C_V19_7_15_FAIL_REPO_STATE) c=109 ;; PHASE_C_V19_7_15_FAIL_RUNNER_TRUST) c=110 ;; PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND) c=111 ;; PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_MISMATCH) c=112 ;; PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH) c=113 ;; PHASE_C_V19_7_15_FAIL_RUNNER_RETURN) c=114 ;; esac; command printf '\"'\"'%s\\n'\"'\"' "$1" >&2; exit "$c"; };'''
OLD_MAIN=b'''CANONICAL_MAIN="74ea95e59ac0654e1a0c1f811a178b3eef7b073c";'''
NEW_MAIN=b'''CANONICAL_MAIN="5c1403c1f5aabb80d29e8c868440aede8888ce61"; CANONICAL_TREE="3d47741b4863411e5c36cb4c28925ac455ab6441";'''
OLD_GATE=b'''test "$(git_clean -C "$ROOT" rev-parse --verify "refs/remotes/origin/main^{commit}")" = "$CANONICAL_MAIN" || fail PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN; mark PHASE_C_V19_7_15_PASS_CANONICAL_MAIN;'''
NEW_GATE=b'''test "$(git_clean -C "$ROOT" rev-parse --verify "refs/remotes/origin/main^{commit}")" = "$CANONICAL_MAIN" || fail PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN; test "$(git_clean -C "$ROOT" rev-parse --verify "$CANONICAL_MAIN^{tree}")" = "$CANONICAL_TREE" || fail PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN; mark PHASE_C_V19_7_15_PASS_CANONICAL_MAIN;'''
def build():
 d=BASE.read_bytes(); assert len(d)==BASE_BYTES and hashlib.sha256(d).hexdigest()==BASE_SHA256
 for old in (OLD_FAIL,OLD_MAIN,OLD_GATE): assert d.count(old)==1
 d=d.replace(OLD_FAIL,NEW_FAIL).replace(OLD_MAIN,NEW_MAIN).replace(OLD_GATE,NEW_GATE)
 assert b'c=115;' in d and b'c=103 ;;' in d and b'c=114 ;;' in d
 assert b'CANONICAL_MAIN="5c1403c1f5aabb80d29e8c868440aede8888ce61"' in d
 assert b'CANONICAL_TREE="3d47741b4863411e5c36cb4c28925ac455ab6441"' in d
 assert d.count(b'\n')==0 and not d.endswith(b'\n')
 return d
if __name__=="__main__":
 import sys
 d=build()
 if len(sys.argv)>1 and sys.argv[1]=="--meta": print(len(d),hashlib.sha256(d).hexdigest())
 else: sys.stdout.buffer.write(d)
