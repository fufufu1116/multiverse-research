#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, os, subprocess, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ACTION=ROOT/'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_15_PRE_OAUTH_LOADER_ACTION_20260830.txt'
BUILDER=ROOT/'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_15_PRE_OAUTH_LOADER_BUILDER_20260830.py'
EXPECTED_BYTES=5192
EXPECTED_SHA256='e0ddcdd5bfbff8fd7d4deefd0b0601bb0d1bc69e6f3fb36580c638b6bd9c9564'
FAIL='fail(){ command printf "%s\n" "$1" >&2; exit 88; }; '
CASES=[
('PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES',
 '{ test "${CODESPACES:-}" = "true" && test -n "${CODESPACE_NAME:-}"; } || fail PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES',
 'unset CODESPACES CODESPACE_NAME; '),
('PHASE_C_V19_7_15_FAIL_FRESH_PATHS',
 '{ test ! -e "$p" && test ! -L "$p"; } || fail PHASE_C_V19_7_15_FAIL_FRESH_PATHS',
 'p="$FIX/existing"; : >"$p"; '),
('PHASE_C_V19_7_15_FAIL_TMPFS_TRUST',
 '{ test "$(command stat -c "%a" "$p")" = "700" && test "$(command stat -c "%u" "$p")" = "$(command id -u)"; } || fail PHASE_C_V19_7_15_FAIL_TMPFS_TRUST',
 'p="$FIX/badmode"; mkdir "$p"; chmod 755 "$p"; '),
('PHASE_C_V19_7_15_FAIL_GIT_CONTROL',
 'git_clean clone --no-checkout --no-recurse-submodules --template="$RTEMPLATE" "$ORIGIN" "$ROOT" >/dev/null 2>&1 || fail PHASE_C_V19_7_15_FAIL_GIT_CONTROL',
 'git_clean(){ return 1; }; RTEMPLATE="$FIX/t"; ORIGIN=x; ROOT="$FIX/r"; '),
('PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN',
 'test "$(git_clean -C "$ROOT" rev-parse --verify "refs/remotes/origin/main^{commit}")" = "$CANONICAL_MAIN" || fail PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN',
 'git_clean(){ printf "%s\n" wrong; }; ROOT="$FIX/r"; CANONICAL_MAIN=expected; '),
('PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD',
 'git_clean -C "$ROOT" checkout --detach "$RECOVERY_HEAD" >/dev/null 2>&1 || fail PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD',
 'git_clean(){ return 1; }; ROOT="$FIX/r"; RECOVERY_HEAD=x; '),
('PHASE_C_V19_7_15_FAIL_REPO_STATE',
 'if git_clean -C "$ROOT" symbolic-ref -q HEAD >/dev/null 2>&1; then fail PHASE_C_V19_7_15_FAIL_REPO_STATE; else test "$?" -eq 1 || fail PHASE_C_V19_7_15_FAIL_REPO_STATE; fi',
 'git_clean(){ return 0; }; ROOT="$FIX/r"; '),
('PHASE_C_V19_7_15_FAIL_RUNNER_TRUST',
 'entry="$(git_clean -C "$ROOT" ls-tree "$RECOVERY_HEAD" -- "$RUNNER")" || fail PHASE_C_V19_7_15_FAIL_RUNNER_TRUST',
 'git_clean(){ return 1; }; ROOT="$FIX/r"; RECOVERY_HEAD=x; RUNNER=x; '),
('PHASE_C_V19_7_15_FAIL_RUNNER_SHA256',
 'test "$1" = "$RUNNER_SHA256" || fail PHASE_C_V19_7_15_FAIL_RUNNER_SHA256',
 'set -- wrong; RUNNER_SHA256=expected; '),
('PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH',
 'if /bin/bash --noprofile --norc "$ROOT/$RUNNER"; then exit 0; else fail PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH; fi',
 'ROOT="$FIX"; RUNNER=does-not-exist; ')
]

def load_builder():
    s=importlib.util.spec_from_file_location("b",BUILDER); assert s and s.loader
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def run(script:str, fix:str):
    e=dict(os.environ); e['FIX']=fix
    return subprocess.run(['/bin/bash','--noprofile','--norc','-c',script],text=True,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=e)

def main():
    d=ACTION.read_bytes(); t=d.decode('ascii')
    assert len(d)==EXPECTED_BYTES and hashlib.sha256(d).hexdigest()==EXPECTED_SHA256
    assert d.count(b'\n')==0 and not d.endswith(b'\n') and len(d.splitlines())==1
    b=load_builder(); assert b.build()==d and b.build()==d
    assert subprocess.run(['/bin/bash','-n','-c',t],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    # Strict-prefix transport proof. The exact action is one outer brace-group whose only
    # syntactic closing brace is the final byte. Any strict byte prefix therefore lacks
    # that closing token. Independently confirm the maximal strict prefix is syntax-invalid.
    assert t.startswith('{ ') and t.endswith('; }')
    assert subprocess.run(['/bin/bash','-n','-c',d[:-1].decode('ascii')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
    with tempfile.TemporaryDirectory(prefix='mv-v19-7-15-fixture-') as td:
        for marker,exact,prefix in CASES:
            assert exact in t, (marker,'exact-source-binding-missing')
            p=run('set -u; '+FAIL+prefix+exact,td)
            assert p.returncode!=0, (marker,p.returncode)
            assert p.stderr.splitlines()[-1:]==[marker], (marker,p.stderr)
        # Source-bound success fixture for the terminal transition: after all prior regions
        # are independently covered above, the exact fixed marker is emitted and an exact
        # harmless runner succeeds without OAuth/network.
        exact_mark='mark PHASE_C_V19_7_15_RUNNER_START'
        assert exact_mark in t
        p=run('set -u; mark(){ command printf "%s\\n" "$1"; }; '+exact_mark,td)
        assert p.returncode==0 and p.stdout.splitlines()==['PHASE_C_V19_7_15_RUNNER_START']
    assert '--apply' not in t and 'Step4' not in t
    print('PHASE_C_V19_7_15_PRE_OAUTH_HARNESS_PASS')

if __name__=='__main__':
    main()
