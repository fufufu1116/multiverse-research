#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, os, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / "governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_15_PRE_OAUTH_LOADER_ACTION_V5_20260830.txt"
BUILDER = ROOT / "governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_15_PRE_OAUTH_LOADER_BUILDER_V5_20260830.py"
EXPECTED_BYTES = 5588
EXPECTED_SHA256 = "ee71fd11219b97c3b54443638291f59fc4f1db7c6916a344c5be17e48f5b69e4"
FAIL = "fail(){ command printf '%s\\n' \"$1\" >&2; exit 88; }; "
MARK = "mark(){ command printf '%s\\n' \"$1\"; }; "

def load_builder():
    s = importlib.util.spec_from_file_location("b", BUILDER)
    assert s and s.loader
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

def run(script: str, fix: Path, extra=None):
    e = dict(os.environ)
    e["FIX"] = str(fix)
    if extra:
        e.update(extra)
    return subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-c", script],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=e
    )

def exact_boundary(fragment: str) -> str:
    text = ACTION.read_text("ascii")
    assert text.count(fragment) == 1, fragment
    start = text.index(fragment)
    return text[start:start+len(fragment)]

def expect(marker: str, fragment: str, setup: str, fix: Path, extra=None):
    exact = exact_boundary(fragment)
    p = run("set -u; " + FAIL + setup + exact, fix, extra)
    assert p.returncode != 0, (marker, p.returncode, p.stdout, p.stderr)
    assert p.stdout == "", (marker, "unexpected stdout", p.stdout)
    assert p.stderr == marker + "\n", (marker, "unexpected stderr", p.stderr)

def shim(path: Path, name: str, body: str):
    p = path / name
    p.write_text("#!/bin/sh\n" + body + "\n")
    p.chmod(0o755)

def main():
    d = ACTION.read_bytes()
    t = d.decode("ascii")
    assert len(d) == EXPECTED_BYTES
    assert hashlib.sha256(d).hexdigest() == EXPECTED_SHA256
    assert d.count(b"\n") == 0
    assert not d.endswith(b"\n")
    assert len(d.splitlines()) == 1
    b = load_builder()
    assert b.build() == d
    assert b.build() == d
    assert subprocess.run(["/bin/bash", "-n", "-c", t],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

    def prefix_rc(i: int):
        rc = subprocess.run(["/bin/bash", "-n", "-c", d[:i].decode("ascii")],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
        return i, rc
    with ThreadPoolExecutor(max_workers=min(32, os.cpu_count() or 4)) as ex:
        for i, rc in ex.map(prefix_rc, range(1, len(d)), chunksize=32):
            assert rc != 0, ("strict prefix parsed", i)

    with tempfile.TemporaryDirectory(prefix="mv-v19715-v5-") as td:
        fix = Path(td)

        expect("PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES",
               '{ test "${CODESPACES:-}" = "true" && test -n "${CODESPACE_NAME:-}"; } || fail PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES',
               'unset CODESPACES CODESPACE_NAME; ', fix)

        expect("PHASE_C_V19_7_15_FAIL_FRESH_PATHS",
               '{ test ! -e "$p" && test ! -L "$p"; } || fail PHASE_C_V19_7_15_FAIL_FRESH_PATHS',
               'p="$FIX/existing"; : >"$p"; ', fix)

        expect("PHASE_C_V19_7_15_FAIL_FRESH_PATHS",
               '{ test ! -e "$p" && test ! -L "$p"; } || fail PHASE_C_V19_7_15_FAIL_FRESH_PATHS',
               'p="$FIX/link"; ln -s "$FIX/target" "$p"; ', fix)

        expect("PHASE_C_V19_7_15_FAIL_TMPFS_TRUST",
               '{ test "$(command stat -c "%a" "$p" 2>/dev/null)" = "700" && test "$(command stat -c "%u" "$p" 2>/dev/null)" = "$(command id -u 2>/dev/null)"; } || fail PHASE_C_V19_7_15_FAIL_TMPFS_TRUST',
               'p="$FIX/badmode"; mkdir "$p"; chmod 755 "$p"; ', fix)

        bd = fix / "bin"
        bd.mkdir()
        shim(bd, "stat", 'if [ "$1" = "-c" ] && [ "$2" = "%a" ]; then echo 700; else echo 999; fi')
        shim(bd, "id", "echo 1000")
        expect("PHASE_C_V19_7_15_FAIL_TMPFS_TRUST",
               '{ test "$(command stat -c "%a" "$p" 2>/dev/null)" = "700" && test "$(command stat -c "%u" "$p" 2>/dev/null)" = "$(command id -u 2>/dev/null)"; } || fail PHASE_C_V19_7_15_FAIL_TMPFS_TRUST',
               'p="$FIX/owned"; mkdir -p "$p"; ',
               fix, {"PATH": str(bd)+":/usr/bin:/bin"})

        shim(bd, "stat", 'if [ "$1" = "-f" ]; then echo overlay; else /usr/bin/stat "$@"; fi')
        expect("PHASE_C_V19_7_15_FAIL_TMPFS_TRUST",
               'fs="$(command stat -f -c "%T" "$p" 2>/dev/null)" || fail PHASE_C_V19_7_15_FAIL_TMPFS_TRUST; { test "$fs" = "tmpfs" || test "$fs" = "ramfs"; } || fail PHASE_C_V19_7_15_FAIL_TMPFS_TRUST',
               'p="$FIX/type"; mkdir -p "$p"; ',
               fix, {"PATH": str(bd)+":/usr/bin:/bin"})

        expect("PHASE_C_V19_7_15_FAIL_GIT_CONTROL",
               'git_clean clone --no-checkout --no-recurse-submodules --template="$RTEMPLATE" "$ORIGIN" "$ROOT" >/dev/null || fail PHASE_C_V19_7_15_FAIL_GIT_CONTROL',
               'git_clean(){ return 1; }; RTEMPLATE="$FIX/t"; ORIGIN=x; ROOT="$FIX/r"; ', fix)

        expect("PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN",
               'test "$(git_clean -C "$ROOT" rev-parse --verify "refs/remotes/origin/main^{commit}")" = "$CANONICAL_MAIN" || fail PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN',
               'git_clean(){ printf "%s\\n" wrong; }; ROOT="$FIX/r"; CANONICAL_MAIN=expected; ', fix)

        expect("PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD",
               'test "$(git_clean -C "$ROOT" rev-parse --verify "HEAD^{commit}")" = "$RECOVERY_HEAD" || fail PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD',
               'git_clean(){ printf "%s\\n" wrong; }; ROOT="$FIX/r"; RECOVERY_HEAD=expected; ', fix)

        expect("PHASE_C_V19_7_15_FAIL_REPO_STATE",
               'if git_clean -C "$ROOT" symbolic-ref -q HEAD >/dev/null; then fail PHASE_C_V19_7_15_FAIL_REPO_STATE; else test "$?" -eq 1 || fail PHASE_C_V19_7_15_FAIL_REPO_STATE; fi',
               'git_clean(){ return 0; }; ROOT="$FIX/r"; ', fix)

        expect("PHASE_C_V19_7_15_FAIL_REPO_STATE",
               'test -z "$(git_clean -C "$ROOT" status --porcelain=v1 --untracked-files=all)" || fail PHASE_C_V19_7_15_FAIL_REPO_STATE',
               'git_clean(){ printf "%s\\n" " M dirty"; }; ROOT="$FIX/r"; ', fix)

        expect("PHASE_C_V19_7_15_FAIL_RUNNER_TRUST",
               'entry="$(git_clean -C "$ROOT" ls-tree "$RECOVERY_HEAD" -- "$RUNNER")" || fail PHASE_C_V19_7_15_FAIL_RUNNER_TRUST',
               'git_clean(){ return 1; }; ROOT="$FIX/r"; RECOVERY_HEAD=x; RUNNER=x; ', fix)

        r = fix / "runner.sh"
        r.write_text("exit 0\n")
        r.chmod(0o644)
        expect("PHASE_C_V19_7_15_FAIL_RUNNER_TRUST",
               '{ test "$mode" = "100644" && test "$type" = "blob" && test "$oid" = "$RUNNER_BLOB" && test "$listed" = "$RUNNER" && test -f "$ROOT/$RUNNER" && test ! -L "$ROOT/$RUNNER" && test ! -x "$ROOT/$RUNNER" && test "$(command stat -c "%h" "$ROOT/$RUNNER" 2>/dev/null)" = "1" && test "$(command stat -c "%u" "$ROOT/$RUNNER" 2>/dev/null)" = "$(command id -u 2>/dev/null)"; } || fail PHASE_C_V19_7_15_FAIL_RUNNER_TRUST',
               'ROOT="$FIX"; RUNNER=runner.sh; mode=100644; type=blob; oid=wrong; RUNNER_BLOB=expected; listed=runner.sh; ', fix)

        expect("PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND",
               'digest="$(/usr/bin/sha256sum -- "$ROOT/$RUNNER" 2>/dev/null)" || fail PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND',
               'ROOT="$FIX"; RUNNER=missing; ', fix)

        expect("PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_MISMATCH",
               'test "$1" = "$RUNNER_SHA256" || fail PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_MISMATCH',
               'set -- wrong; RUNNER_SHA256=expected; ', fix)

        expect("PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH",
               '/bin/bash --noprofile --norc -n "$ROOT/$RUNNER" >/dev/null 2>&1 || fail PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH',
               'ROOT="$FIX"; RUNNER=missing; ', fix)

        bad = fix / "bad.sh"
        bad.write_text("exit 7\n")
        bad.chmod(0o644)
        expect("PHASE_C_V19_7_15_FAIL_RUNNER_RETURN",
               'if /bin/bash --noprofile --norc "$ROOT/$RUNNER"; then exit 0; else fail PHASE_C_V19_7_15_FAIL_RUNNER_RETURN; fi',
               'ROOT="$FIX"; RUNNER=bad.sh; ', fix)

        ok = fix / "ok.sh"
        ok.write_text("exit 0\n")
        ok.chmod(0o644)
        pre = exact_boundary('/bin/bash --noprofile --norc -n "$ROOT/$RUNNER" >/dev/null 2>&1 || fail PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH')
        start = exact_boundary('mark PHASE_C_V19_7_15_RUNNER_START')
        runfrag = exact_boundary('if /bin/bash --noprofile --norc "$ROOT/$RUNNER"; then exit 0; else fail PHASE_C_V19_7_15_FAIL_RUNNER_RETURN; fi')
        p = run('set -u; '+FAIL+MARK+'ROOT="$FIX"; RUNNER=ok.sh; '+pre+'; '+start+'; '+runfrag, fix)
        assert p.returncode == 0
        assert p.stdout == "PHASE_C_V19_7_15_RUNNER_START\n"
        assert p.stderr == ""

    assert "--apply" not in t and "Step4" not in t
    print("PHASE_C_V19_7_15_PRE_OAUTH_HARNESS_V5_PASS")

if __name__ == "__main__":
    main()
