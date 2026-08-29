#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, os, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ACTION=ROOT/'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_15_PRE_OAUTH_LOADER_ACTION_20260830.txt'
BUILDER=ROOT/'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_15_PRE_OAUTH_LOADER_BUILDER_20260830.py'
EXPECTED_BYTES=5563
EXPECTED_SHA256='21574a5a724aa3d5966720193b433ba4fbdf028602786f8cf7ad635eac402747'
FAIL='fail(){ command printf \'%s\\n\' "$1" >&2; exit 88; }; '
MARK='mark(){ command printf \'%s\\n\' "$1"; }; '
CASES=[('PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES', '{ test "${CODESPACES:-}" = "true" && test -n "${CODESPACE_NAME:-}"; } || fail PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES', 'unset CODESPACES CODESPACE_NAME; '), ('PHASE_C_V19_7_15_FAIL_FRESH_PATHS', '{ test ! -e "$p" && test ! -L "$p"; } || fail PHASE_C_V19_7_15_FAIL_FRESH_PATHS', 'p="$FIX/existing"; : >"$p"; '), ('PHASE_C_V19_7_15_FAIL_TMPFS_TRUST', '{ test "$(command stat -c "%a" "$p" 2>/dev/null)" = "700" && test "$(command stat -c "%u" "$p" 2>/dev/null)" = "$(command id -u 2>/dev/null)"; } || fail PHASE_C_V19_7_15_FAIL_TMPFS_TRUST', 'p="$FIX/badmode"; mkdir "$p"; chmod 755 "$p"; '), ('PHASE_C_V19_7_15_FAIL_GIT_CONTROL', 'git_clean clone --no-checkout --no-recurse-submodules --template="$RTEMPLATE" "$ORIGIN" "$ROOT" >/dev/null || fail PHASE_C_V19_7_15_FAIL_GIT_CONTROL', 'git_clean(){ return 1; }; RTEMPLATE="$FIX/t"; ORIGIN=x; ROOT="$FIX/r"; '), ('PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN', 'test "$(git_clean -C "$ROOT" rev-parse --verify "refs/remotes/origin/main^{commit}")" = "$CANONICAL_MAIN" || fail PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN', 'git_clean(){ printf "%s\\n" wrong; }; ROOT="$FIX/r"; CANONICAL_MAIN=expected; '), ('PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD', 'git_clean -C "$ROOT" checkout --detach "$RECOVERY_HEAD" >/dev/null || fail PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD', 'git_clean(){ return 1; }; ROOT="$FIX/r"; RECOVERY_HEAD=x; '), ('PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD', 'test "$(git_clean -C "$ROOT" rev-parse --verify "HEAD^{commit}")" = "$RECOVERY_HEAD" || fail PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD', 'git_clean(){ printf "%s\\n" wrong; }; ROOT="$FIX/r"; RECOVERY_HEAD=expected; '), ('PHASE_C_V19_7_15_FAIL_REPO_STATE', 'if git_clean -C "$ROOT" symbolic-ref -q HEAD >/dev/null; then fail PHASE_C_V19_7_15_FAIL_REPO_STATE; else test "$?" -eq 1 || fail PHASE_C_V19_7_15_FAIL_REPO_STATE; fi', 'git_clean(){ return 0; }; ROOT="$FIX/r"; '), ('PHASE_C_V19_7_15_FAIL_REPO_STATE', 'test -z "$(git_clean -C "$ROOT" status --porcelain=v1 --untracked-files=all)" || fail PHASE_C_V19_7_15_FAIL_REPO_STATE', 'git_clean(){ printf "%s\\n" " M dirty"; }; ROOT="$FIX/r"; '), ('PHASE_C_V19_7_15_FAIL_RUNNER_TRUST', 'entry="$(git_clean -C "$ROOT" ls-tree "$RECOVERY_HEAD" -- "$RUNNER")" || fail PHASE_C_V19_7_15_FAIL_RUNNER_TRUST', 'git_clean(){ return 1; }; ROOT="$FIX/r"; RECOVERY_HEAD=x; RUNNER=x; '), ('PHASE_C_V19_7_15_FAIL_RUNNER_SHA256', 'digest="$(/usr/bin/sha256sum -- "$ROOT/$RUNNER" 2>/dev/null)" || fail PHASE_C_V19_7_15_FAIL_RUNNER_SHA256', 'ROOT="$FIX"; RUNNER=missing; '), ('PHASE_C_V19_7_15_FAIL_RUNNER_SHA256', 'test "$1" = "$RUNNER_SHA256" || fail PHASE_C_V19_7_15_FAIL_RUNNER_SHA256', 'set -- wrong; RUNNER_SHA256=expected; '), ('PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH', '/bin/bash --noprofile --norc -n "$ROOT/$RUNNER" >/dev/null 2>&1 || fail PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH', 'ROOT="$FIX"; RUNNER=missing; ')]
SNIPS={'PLATFORM': '{ test "${CODESPACES:-}" = "true" && test -n "${CODESPACE_NAME:-}"; } || fail PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES', 'FRESH': '{ test ! -e "$p" && test ! -L "$p"; } || fail PHASE_C_V19_7_15_FAIL_FRESH_PATHS', 'MODEOWNER': '{ test "$(command stat -c "%a" "$p" 2>/dev/null)" = "700" && test "$(command stat -c "%u" "$p" 2>/dev/null)" = "$(command id -u 2>/dev/null)"; } || fail PHASE_C_V19_7_15_FAIL_TMPFS_TRUST', 'FSTYPE': 'fs="$(command stat -f -c "%T" "$p" 2>/dev/null)" || fail PHASE_C_V19_7_15_FAIL_TMPFS_TRUST; { test "$fs" = "tmpfs" || test "$fs" = "ramfs"; } || fail PHASE_C_V19_7_15_FAIL_TMPFS_TRUST', 'GIT': 'git_clean clone --no-checkout --no-recurse-submodules --template="$RTEMPLATE" "$ORIGIN" "$ROOT" >/dev/null || fail PHASE_C_V19_7_15_FAIL_GIT_CONTROL', 'MAIN': 'test "$(git_clean -C "$ROOT" rev-parse --verify "refs/remotes/origin/main^{commit}")" = "$CANONICAL_MAIN" || fail PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN', 'CHECKOUT': 'git_clean -C "$ROOT" checkout --detach "$RECOVERY_HEAD" >/dev/null || fail PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD', 'HEADMATCH': 'test "$(git_clean -C "$ROOT" rev-parse --verify "HEAD^{commit}")" = "$RECOVERY_HEAD" || fail PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD', 'SYMBOLIC': 'if git_clean -C "$ROOT" symbolic-ref -q HEAD >/dev/null; then fail PHASE_C_V19_7_15_FAIL_REPO_STATE; else test "$?" -eq 1 || fail PHASE_C_V19_7_15_FAIL_REPO_STATE; fi', 'DIRTY': 'test -z "$(git_clean -C "$ROOT" status --porcelain=v1 --untracked-files=all)" || fail PHASE_C_V19_7_15_FAIL_REPO_STATE', 'ENTRY': 'entry="$(git_clean -C "$ROOT" ls-tree "$RECOVERY_HEAD" -- "$RUNNER")" || fail PHASE_C_V19_7_15_FAIL_RUNNER_TRUST', 'READ': 'read -r mode type oid listed <<< "$entry" || fail PHASE_C_V19_7_15_FAIL_RUNNER_TRUST', 'TRUST': '{ test "$mode" = "100644" && test "$type" = "blob" && test "$oid" = "$RUNNER_BLOB" && test "$listed" = "$RUNNER" && test -f "$ROOT/$RUNNER" && test ! -L "$ROOT/$RUNNER" && test ! -x "$ROOT/$RUNNER" && test "$(command stat -c "%h" "$ROOT/$RUNNER" 2>/dev/null)" = "1" && test "$(command stat -c "%u" "$ROOT/$RUNNER" 2>/dev/null)" = "$(command id -u 2>/dev/null)"; } || fail PHASE_C_V19_7_15_FAIL_RUNNER_TRUST', 'DIGEST': 'digest="$(/usr/bin/sha256sum -- "$ROOT/$RUNNER" 2>/dev/null)" || fail PHASE_C_V19_7_15_FAIL_RUNNER_SHA256', 'SHA': 'test "$1" = "$RUNNER_SHA256" || fail PHASE_C_V19_7_15_FAIL_RUNNER_SHA256', 'PRELAUNCH': '/bin/bash --noprofile --norc -n "$ROOT/$RUNNER" >/dev/null 2>&1 || fail PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH', 'START': 'mark PHASE_C_V19_7_15_RUNNER_START', 'RUN': 'if /bin/bash --noprofile --norc "$ROOT/$RUNNER"; then exit 0; else fail PHASE_C_V19_7_15_FAIL_RUNNER_RETURN; fi'}
def load_builder():
    s=importlib.util.spec_from_file_location("b",BUILDER); assert s and s.loader
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def run(script,fix,extra=None):
    e=dict(os.environ); e["FIX"]=str(fix)
    if extra:e.update(extra)
    return subprocess.run(['/bin/bash','--noprofile','--norc','-c',script],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=e)
def expect(marker, exact, prefix, fix, extra=None):
    t=ACTION.read_text('ascii'); assert exact in t
    p=run('set -u; '+FAIL+prefix+exact,fix,extra)
    assert p.returncode!=0,(marker,p.returncode,p.stdout,p.stderr)
    assert p.stderr.splitlines()==[marker],(marker,p.stderr)
def shim(path,name,body):
    p=path/name;p.write_text('#!/bin/sh\n'+body+'\n');p.chmod(0o755)
def main():
    d=ACTION.read_bytes();t=d.decode('ascii')
    assert len(d)==EXPECTED_BYTES and hashlib.sha256(d).hexdigest()==EXPECTED_SHA256
    assert d.count(b'\n')==0 and not d.endswith(b'\n') and len(d.splitlines())==1
    b=load_builder();assert b.build()==d and b.build()==d
    assert subprocess.run(['/bin/bash','-n','-c',t],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    assert t.startswith('{ ') and t.endswith('; }')
    assert subprocess.run(['/bin/bash','-n','-c',d[:-1].decode('ascii')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
    with tempfile.TemporaryDirectory(prefix='mv-v19715-') as td:
        fix=Path(td)
        for marker,exact,prefix in CASES: expect(marker,exact,prefix,fix)
        # ownership mismatch: exact mode/owner predicate with controlled command resolution
        bd=fix/'bin';bd.mkdir()
        shim(bd,'stat','if [ "$1" = "-c" ] && [ "$2" = "%a" ]; then echo 700; else echo 999; fi')
        shim(bd,'id','echo 1000')
        expect('PHASE_C_V19_7_15_FAIL_TMPFS_TRUST',SNIPS['MODEOWNER'],'p="$FIX/owned"; mkdir -p "$p"; ',fix,{'PATH':str(bd)+':/usr/bin:/bin'})
        # filesystem-type mismatch
        shim(bd,'stat','if [ "$1" = "-f" ]; then echo overlay; else /usr/bin/stat "$@"; fi')
        expect('PHASE_C_V19_7_15_FAIL_TMPFS_TRUST',SNIPS['FSTYPE'],'p="$FIX/type"; mkdir -p "$p"; ',fix,{'PATH':str(bd)+':/usr/bin:/bin'})
        # runner blob mismatch using exact trust predicate
        r=fix/'runner.sh';r.write_text('exit 0\n');r.chmod(0o644)
        expect('PHASE_C_V19_7_15_FAIL_RUNNER_TRUST',SNIPS['TRUST'],'ROOT="$FIX"; RUNNER=runner.sh; mode=100644; type=blob; oid=wrong; RUNNER_BLOB=expected; listed=runner.sh; ',fix)
        # runner child nonzero maps only to fixed return marker for a quiet runner
        bad=fix/'bad.sh';bad.write_text('exit 7\n');bad.chmod(0o644)
        expect('PHASE_C_V19_7_15_FAIL_RUNNER_RETURN',SNIPS['RUN'],'ROOT="$FIX"; RUNNER=bad.sh; ',fix)
        # exact prelaunch + start + run succeeds against harmless runner
        ok=fix/'ok.sh';ok.write_text('exit 0\n');ok.chmod(0o644)
        script='set -u; '+FAIL+MARK+'ROOT="$FIX"; RUNNER=ok.sh; '+SNIPS['PRELAUNCH']+'; export RECOVERY_ROOT="$ROOT"; '+SNIPS['START']+'; '+SNIPS['RUN']
        p=run(script,fix);assert p.returncode==0 and p.stdout.splitlines()==['PHASE_C_V19_7_15_RUNNER_START'] and p.stderr==''
    assert '--apply' not in t and 'Step4' not in t
    print('PHASE_C_V19_7_15_PRE_OAUTH_HARNESS_PASS')
if __name__=='__main__':main()
