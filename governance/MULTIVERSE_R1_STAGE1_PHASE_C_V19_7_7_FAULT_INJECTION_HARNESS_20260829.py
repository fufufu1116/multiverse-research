#!/usr/bin/env python3
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
EXECUTOR_PATH = HERE / "MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_7_STEP3_STANDALONE_NONMUTATING_EXECUTOR_20260829.py"
spec = importlib.util.spec_from_file_location("v1977_executor", EXECUTOR_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

RESULTS = []


def expect_stop(label, expected, fn):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stderr(buf):
            fn()
    except SystemExit as e:
        text = buf.getvalue().strip()
        ok = e.code == 92 and (":" + expected) in text
    else:
        text = buf.getvalue().strip()
        ok = False
    RESULTS.append((label, ok, text))
    if not ok:
        raise AssertionError(f"{label}: expected {expected!r}, got {text!r}")


def run(*args, cwd=None, check=True):
    return subprocess.run(args, cwd=cwd, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def write_critical(root):
    for rel in mod.CRITICAL_PATHS:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("fixture:" + rel + "\n", encoding="utf-8")
        p.chmod(0o644)


def make_repo(tmp):
    root = Path(tmp) / "repo"
    root.mkdir()
    run("git", "init", "-q", str(root))
    run("git", "-C", str(root), "config", "user.name", "fixture")
    run("git", "-C", str(root), "config", "user.email", "fixture@example.invalid")
    run("git", "-C", str(root), "remote", "add", "origin", mod.CANONICAL_ORIGIN)
    write_critical(root)
    run("git", "-C", str(root), "add", ".")
    run("git", "-C", str(root), "commit", "-q", "-m", "fixture")
    sha = run("git", "-C", str(root), "rev-parse", "HEAD").stdout.strip()
    run("git", "-C", str(root), "checkout", "-q", "--detach", sha)
    return root, sha


def with_checkout_fixture(test_fn):
    with tempfile.TemporaryDirectory(prefix="v1977-fixture-") as td:
        root, sha = make_repo(td)
        old_root, old_sha, old_mem = mod.EXEC_ROOT, mod.CANONICAL_SHA, mod.require_memory_root
        mod.EXEC_ROOT = root
        mod.CANONICAL_SHA = sha
        mod.require_memory_root = lambda path, stage: None
        try:
            test_fn(root, sha)
        finally:
            mod.EXEC_ROOT, mod.CANONICAL_SHA, mod.require_memory_root = old_root, old_sha, old_mem


def checkout_baseline(root, sha):
    mod.verify_checkout()
    RESULTS.append(("baseline_checkout", True, "PASS"))


def checkout_wrong_head(root, sha):
    old = mod.CANONICAL_SHA
    mod.CANONICAL_SHA = "0" * 40
    try:
        expect_stop("wrong_head", "HEAD", mod.verify_checkout)
    finally:
        mod.CANONICAL_SHA = old


def checkout_attached(root, sha):
    run("git", "-C", str(root), "checkout", "-q", "-B", "fixture-branch", sha)
    expect_stop("attached_head", "DETACHED_HEAD", mod.verify_checkout)


def checkout_wrong_origin(root, sha):
    run("git", "-C", str(root), "remote", "set-url", "origin", "https://example.invalid/wrong.git")
    expect_stop("wrong_origin", "ORIGIN", mod.verify_checkout)


def checkout_dirty(root, sha):
    (root / "untracked.txt").write_text("dirty\n", encoding="utf-8")
    expect_stop("dirty_worktree", "WORKTREE_DIRTY", mod.verify_checkout)


def checkout_wrong_blob(root, sha):
    p = root / mod.CRITICAL_PATHS[0]
    p.write_text("tampered\n", encoding="utf-8")
    expect_stop("wrong_critical_blob", "CRITICAL_FILE_BLOB", mod.verify_checkout)


def fake_cp(rc=0, out="", err=""):
    return subprocess.CompletedProcess(args=["fixture"], returncode=rc, stdout=out, stderr=err)


def test_preflight_cases():
    real_run = mod.subprocess.run
    cases = [
        ("preflight_nonzero", "PREFLIGHT_NONZERO:7", fake_cp(7, "", "x")),
        ("preflight_malformed_json", "PREFLIGHT_JSON", fake_cp(0, "not-json", "")),
        ("preflight_status", "PREFLIGHT_STATUS", fake_cp(0, json.dumps({"status":"WRONG","production_mutation_performed":False,"runtime_activation_performed":False}), "")),
        ("preflight_mutation_flag", "PRODUCTION_MUTATION_FLAG", fake_cp(0, json.dumps({"status":"PHASE_C_NONMUTATING_PREFLIGHT_PASS","production_mutation_performed":True,"runtime_activation_performed":False}), "")),
        ("preflight_runtime_flag", "RUNTIME_ACTIVATION_FLAG", fake_cp(0, json.dumps({"status":"PHASE_C_NONMUTATING_PREFLIGHT_PASS","production_mutation_performed":False,"runtime_activation_performed":True}), "")),
    ]
    try:
        for label, expected, cp in cases:
            mod.subprocess.run = lambda *a, _cp=cp, **k: _cp
            expect_stop(label, expected, mod.run_preflight)
        good = fake_cp(0, json.dumps({"status":"PHASE_C_NONMUTATING_PREFLIGHT_PASS","production_mutation_performed":False,"runtime_activation_performed":False}), "")
        mod.subprocess.run = lambda *a, **k: good
        mod.run_preflight()
        RESULTS.append(("preflight_baseline", True, "PASS"))
    finally:
        mod.subprocess.run = real_run


def test_env_classes():
    old_env = dict(mod.os.environ)
    old_exe = mod.sys.executable
    try:
        mod.os.environ.clear()
        mod.os.environ.update({"PATH": mod.CONTROLLED_PATH, "GH_CONFIG_DIR": mod.GH_CONFIG_DIR, "CODESPACES": "true", "CODESPACE_NAME": "fixture"})
        mod.sys.executable = "/usr/local/python/current/bin/python"
        mod.require_env()
        RESULTS.append(("env_baseline", True, "PASS"))
        mod.os.environ["PATH"] = "/wrong"
        expect_stop("path_mismatch", "PATH", mod.require_env)
        mod.os.environ["PATH"] = mod.CONTROLLED_PATH
        mod.os.environ["GH_CONFIG_DIR"] = "/wrong"
        expect_stop("gh_config_mismatch", "GH_CONFIG_DIR", mod.require_env)
        mod.os.environ["GH_CONFIG_DIR"] = mod.GH_CONFIG_DIR
        mod.os.environ["CODESPACES"] = "false"
        expect_stop("codespaces_binding", "CODESPACE_BINDING", mod.require_env)
        mod.os.environ["CODESPACES"] = "true"
        mod.sys.executable = "/wrong/python"
        expect_stop("trusted_python", "TRUSTED_PYTHON", mod.require_env)
    finally:
        mod.os.environ.clear()
        mod.os.environ.update(old_env)
        mod.sys.executable = old_exe


def main():
    test_env_classes()
    with_checkout_fixture(checkout_baseline)
    with_checkout_fixture(checkout_wrong_head)
    with_checkout_fixture(checkout_attached)
    with_checkout_fixture(checkout_wrong_origin)
    with_checkout_fixture(checkout_dirty)
    with_checkout_fixture(checkout_wrong_blob)
    test_preflight_cases()
    for label, ok, detail in RESULTS:
        print(f"{label}: {'PASS' if ok else 'FAIL'}: {detail}")
    print("PHASE_C_V19_7_7_FAULT_INJECTION_HARNESS_PASS")


if __name__ == "__main__":
    main()
