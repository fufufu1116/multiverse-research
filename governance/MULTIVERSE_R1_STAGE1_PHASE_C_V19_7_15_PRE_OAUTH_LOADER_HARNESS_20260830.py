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
MARK='mark(){ command printf "%s\n" "$1"; }; '

def load_builder():
    s=importlib.util.spec_from_file_location("b",BUILDER); assert s and s.loader
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def run(script:str, fix:Path, env_extra=None):
    e=dict(os.environ); e['FIX']=str(fix)
    if env_extra: e.update(env_extra)
    return subprocess.run(['/bin/bash','--noprofile','--norc','-c',script],text=True,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=e)

def expect_fail(t:str, marker:str, exact:str, prefix:str, fix:Path, env_extra=None):
    assert exact in t, (marker,'exact-source-binding-missing')
    p=run('set -u; '+FAIL+prefix+exact,fix,env_extra)
    assert p.returncode!=0, (marker,p.returncode,p.stdout,p.stderr)
    assert p.stderr.splitlines()[-1:]==[marker], (marker,p.stderr)

def make_shim(bin_dir:Path,name:str,body:str):
    p=bin_dir/name
    p.write_text('#!/bin/sh\n'+body+'\n',encoding='utf-8')
    p.chmod(0o755)

def main():
    d=ACTION.read_bytes(); t=d.decode('ascii')
    assert len(d)==EXPECTED_BYTES and hashlib.sha256(d).hexdigest()==EXPECTED_SHA256
    assert d.count(b'\n')==0 and not d.endswith(b'\n') and len(d.splitlines())==1
    b=load_builder(); assert b.build()==d and b.build()==d
    assert subprocess.run(['/bin/bash','-n','-c',t],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    assert t.startswith('{ ') and t.endswith('; }')
    assert subprocess.run(['/bin/bash','-n','-c',d[:-1].decode('ascii')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0

    with tempfile.TemporaryDirectory(prefix='mv-v19-7-15-fixture-') as td:
        fix=Path(td); bindir=fix/'bin'; bindir.mkdir()

        # platform / Codespaces
        exact='{ test "${CODESPACES:-}" = "true" && test -n "${CODESPACE_NAME:-}"; } || fail PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES'
        expect_fail(t,'PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES',exact,'unset CODESPACES CODESPACE_NAME; ',fix)

        # freshness / preexisting path
        exact='{ test ! -e "$p" && test ! -L "$p"; } || fail PHASE_C_V19_7_15_FAIL_FRESH_PATHS'
        expect_fail(t,'PHASE_C_V19_7_15_FAIL_FRESH_PATHS',exact,'p="$FIX/existing"; : >"$p"; ',fix)

        # tmpfs trust: mode
        exact='{ test "$(command stat -c "%a" "$p")" = "700" && test "$(command stat -c "%u" "$p")" = "$(command id -u)"; } || fail PHASE_C_V19_7_15_FAIL_TMPFS_TRUST'
        expect_fail(t,'PHASE_C_V19_7_15_FAIL_TMPFS_TRUST',exact,'p="$FIX/badmode"; mkdir "$p"; chmod 755 "$p"; ',fix)

        # tmpfs trust: ownership via controlled stat/id shims, while executing exact predicate
        make_shim(bindir,'stat','if [ "$1" = "-c" ] && [ "$2" = "%a" ]; then echo 700; else echo 999; fi')
        make_shim(bindir,'id','echo 1000')
        expect_fail(t,'PHASE_C_V19_7_15_FAIL_TMPFS_TRUST',exact,'p="$FIX/owned"; mkdir -p "$p"; ',
                    fix,{'PATH':str(bindir)+':/usr/bin:/bin'})

        # tmpfs trust: filesystem type via controlled stat shim, exact fs predicate
        make_shim(bindir,'stat','if [ "$1" = "-f" ]; then echo overlay; else /usr/bin/stat "$@"; fi')
        exact='fs="$(command stat -f -c "%T" "$p")" || fail PHASE_C_V19_7_15_FAIL_TMPFS_TRUST; { test "$fs" = "tmpfs" || test "$fs" = "ramfs"; } || fail PHASE_C_V19_7_15_FAIL_TMPFS_TRUST'
        expect_fail(t,'PHASE_C_V19_7_15_FAIL_TMPFS_TRUST',exact,'p="$FIX/type"; mkdir -p "$p"; ',
                    fix,{'PATH':str(bindir)+':/usr/bin:/bin'})

        # Git/control
        exact='git_clean clone --no-checkout --no-recurse-submodules --template="$RTEMPLATE" "$ORIGIN" "$ROOT" >/dev/null 2>&1 || fail PHASE_C_V19_7_15_FAIL_GIT_CONTROL'
        expect_fail(t,'PHASE_C_V19_7_15_FAIL_GIT_CONTROL',exact,
                    'git_clean(){ return 1; }; RTEMPLATE="$FIX/t"; ORIGIN=x; ROOT="$FIX/r"; ',fix)

        # canonical main mismatch
        exact='test "$(git_clean -C "$ROOT" rev-parse --verify "refs/remotes/origin/main^{commit}")" = "$CANONICAL_MAIN" || fail PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN'
        expect_fail(t,'PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN',exact,
                    'git_clean(){ printf "%s\n" wrong; }; ROOT="$FIX/r"; CANONICAL_MAIN=expected; ',fix)

        # recovery-head checkout failure
        exact='git_clean -C "$ROOT" checkout --detach "$RECOVERY_HEAD" >/dev/null 2>&1 || fail PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD'
        expect_fail(t,'PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD',exact,
                    'git_clean(){ return 1; }; ROOT="$FIX/r"; RECOVERY_HEAD=x; ',fix)

        # recovery-head post-checkout mismatch
        exact='test "$(git_clean -C "$ROOT" rev-parse --verify "HEAD^{commit}")" = "$RECOVERY_HEAD" || fail PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD'
        expect_fail(t,'PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD',exact,
                    'git_clean(){ printf "%s\n" wrong; }; ROOT="$FIX/r"; RECOVERY_HEAD=expected; ',fix)

        # repo symbolic/non-detached
        exact='if git_clean -C "$ROOT" symbolic-ref -q HEAD >/dev/null 2>&1; then fail PHASE_C_V19_7_15_FAIL_REPO_STATE; else test "$?" -eq 1 || fail PHASE_C_V19_7_15_FAIL_REPO_STATE; fi'
        expect_fail(t,'PHASE_C_V19_7_15_FAIL_REPO_STATE',exact,
                    'git_clean(){ return 0; }; ROOT="$FIX/r"; ',fix)

        # repo dirty state
        exact='test -z "$(git_clean -C "$ROOT" status --porcelain=v1 --untracked-files=all)" || fail PHASE_C_V19_7_15_FAIL_REPO_STATE'
        expect_fail(t,'PHASE_C_V19_7_15_FAIL_REPO_STATE',exact,
                    'git_clean(){ printf "%s\n" " M dirty"; }; ROOT="$FIX/r"; ',fix)

        # runner trust lookup failure
        exact='entry="$(git_clean -C "$ROOT" ls-tree "$RECOVERY_HEAD" -- "$RUNNER")" || fail PHASE_C_V19_7_15_FAIL_RUNNER_TRUST'
        expect_fail(t,'PHASE_C_V19_7_15_FAIL_RUNNER_TRUST',exact,
                    'git_clean(){ return 1; }; ROOT="$FIX/r"; RECOVERY_HEAD=x; RUNNER=x; ',fix)

        # runner blob mismatch in exact trust predicate
        runner=fix/'runner.sh'; runner.write_text('exit 0\n',encoding='utf-8'); runner.chmod(0o644)
        exact='{ test "$mode" = "100644" && test "$type" = "blob" && test "$oid" = "$RUNNER_BLOB" && test "$listed" = "$RUNNER" && test -f "$ROOT/$RUNNER" && test ! -L "$ROOT/$RUNNER" && test ! -x "$ROOT/$RUNNER" && test "$(command stat -c "%h" "$ROOT/$RUNNER")" = "1" && test "$(command stat -c "%u" "$ROOT/$RUNNER")" = "$(command id -u)"; } || fail PHASE_C_V19_7_15_FAIL_RUNNER_TRUST'
        expect_fail(t,'PHASE_C_V19_7_15_FAIL_RUNNER_TRUST',exact,
                    'ROOT="$FIX"; RUNNER=runner.sh; mode=100644; type=blob; oid=wrong; RUNNER_BLOB=expected; listed=runner.sh; ',fix)

        # runner SHA mismatch
        exact='test "$1" = "$RUNNER_SHA256" || fail PHASE_C_V19_7_15_FAIL_RUNNER_SHA256'
        expect_fail(t,'PHASE_C_V19_7_15_FAIL_RUNNER_SHA256',exact,'set -- wrong; RUNNER_SHA256=expected; ',fix)

        # runner launch/read failure
        exact='if /bin/bash --noprofile --norc "$ROOT/$RUNNER"; then exit 0; else fail PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH; fi'
        expect_fail(t,'PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH',exact,'ROOT="$FIX"; RUNNER=does-not-exist; ',fix)

        # source-bound success transition actually executes the exact runner invocation.
        ok=fix/'ok.sh'; ok.write_text('exit 0\n',encoding='utf-8'); ok.chmod(0o644)
        exact_mark='mark PHASE_C_V19_7_15_RUNNER_START'
        assert exact_mark in t and exact in t
        p=run('set -u; '+FAIL+MARK+'ROOT="$FIX"; RUNNER=ok.sh; '+exact_mark+'; '+exact,fix)
        assert p.returncode==0, (p.returncode,p.stdout,p.stderr)
        assert p.stdout.splitlines()==['PHASE_C_V19_7_15_RUNNER_START']
        assert 'PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH' not in p.stderr

    assert '--apply' not in t and 'Step4' not in t
    print('PHASE_C_V19_7_15_PRE_OAUTH_HARNESS_PASS')

if __name__=='__main__':
    main()
