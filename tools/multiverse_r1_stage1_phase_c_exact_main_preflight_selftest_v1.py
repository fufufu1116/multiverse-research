#!/usr/bin/env python3
"""Nonsecret structural/adversarial tests for Phase-C exact-main remediation."""
from __future__ import annotations

import ast
import subprocess
import tempfile
from pathlib import Path

from multiverse_r1_stage1_phase_c_execution_preflight_v1 import (
    EXPECTED_EXECUTION_ROOT,
    EXPECTED_ORIGIN_URL,
    Denied,
    _assert_no_index_suppression,
    _verify_exact_paths_against_head,
)

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "tools/multiverse_r1_stage1_phase_c_execution_preflight_v1.py"
PROVISIONER = ROOT / "tools/multiverse_r1_stage1_writer_key_provisioner_v1.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(name)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )


def _expect_denied(fn, expected: str) -> None:
    try:
        fn()
    except Denied as exc:
        assert str(exc) == expected, (str(exc), expected)
    else:
        raise AssertionError("expected Denied: " + expected)


def _adversarial_index_suppression_test() -> None:
    """Reproduce Auditor 5002962014's false-clean class and prove rejection."""
    with tempfile.TemporaryDirectory(prefix="multiverse-phase-c-index-selftest-") as tmp:
        repo = Path(tmp)
        assert _git(repo, "init", "-q").returncode == 0
        assert _git(repo, "config", "user.email", "phase-c-selftest@example.invalid").returncode == 0
        assert _git(repo, "config", "user.name", "Phase C Selftest").returncode == 0
        tracked = repo / "tracked.py"
        tracked.write_text("reviewed = True\n", encoding="utf-8")
        assert _git(repo, "add", "tracked.py").returncode == 0
        assert _git(repo, "commit", "-q", "-m", "reviewed").returncode == 0
        head = _git(repo, "rev-parse", "HEAD").stdout.strip()
        assert len(head) == 40
        assert _git(repo, "checkout", "-q", "--detach", head).returncode == 0

        _verify_exact_paths_against_head(repo, head, ("tracked.py",))
        _assert_no_index_suppression(repo)

        tracked.write_text("reviewed = False\n", encoding="utf-8")
        assert _git(repo, "update-index", "--assume-unchanged", "tracked.py").returncode == 0
        status = _git(repo, "status", "--porcelain=v1", "--untracked-files=all")
        assert status.returncode == 0 and not status.stdout.strip()
        _expect_denied(
            lambda: _verify_exact_paths_against_head(repo, head, ("tracked.py",)),
            "PHASE_C_EXECUTION_REVIEWED_BYTES_MISMATCH",
        )
        _expect_denied(
            lambda: _assert_no_index_suppression(repo),
            "PHASE_C_EXECUTION_ASSUME_UNCHANGED_PROHIBITED",
        )

        assert _git(repo, "update-index", "--no-assume-unchanged", "tracked.py").returncode == 0
        assert _git(repo, "checkout", "-q", "--", "tracked.py").returncode == 0
        assert _git(repo, "update-index", "--skip-worktree", "tracked.py").returncode == 0
        tracked.write_text("reviewed = 'skip-worktree-tamper'\n", encoding="utf-8")
        _expect_denied(
            lambda: _verify_exact_paths_against_head(repo, head, ("tracked.py",)),
            "PHASE_C_EXECUTION_REVIEWED_BYTES_MISMATCH",
        )
        _expect_denied(
            lambda: _assert_no_index_suppression(repo),
            "PHASE_C_EXECUTION_SKIP_WORKTREE_PROHIBITED",
        )


def _structural_test() -> None:
    fsrc = _read(PREFLIGHT)
    psrc = _read(PROVISIONER)
    ftree = ast.parse(fsrc, filename=str(PREFLIGHT))
    ptree = ast.parse(psrc, filename=str(PROVISIONER))

    bootstrap = _function(ftree, "_assert_external_bootstrap_root")
    binding = _function(ftree, "verified_execution_checkout_head")
    live = _function(ftree, "live_preflight")
    apply = _function(ptree, "apply_once")
    assert not bootstrap.args.args and not binding.args.args and not live.args.args and not apply.args.args
    assert not apply.args.posonlyargs and not apply.args.kwonlyargs
    assert apply.args.vararg is None and apply.args.kwarg is None

    assert EXPECTED_EXECUTION_ROOT == Path("/dev/shm/multiverse-r1-stage1-phase-c-execution")
    assert EXPECTED_ORIGIN_URL == "https://github.com/fufufu1116/multiverse-research.git"

    for required in (
        'EXPECTED_EXECUTION_ROOT = pathlib.Path(',
        '"/dev/shm/multiverse-r1-stage1-phase-c-execution"',
        'EXPECTED_ORIGIN_URL = "https://github.com/fufufu1116/multiverse-research.git"',
        "actual_root = _assert_external_bootstrap_root()",
        "PHASE_C_EXECUTION_ROOT_NOT_EXTERNAL_BOOTSTRAP",
        "PHASE_C_EXECUTION_BOOTSTRAP_ROOT_PERMISSIONS",
        "PHASE_C_EXECUTION_BOOTSTRAP_ROOT_NOT_MEMORY_FILESYSTEM",
        '["stat", "-f", "-c", "%T", str(actual_root)]',
        "PHASE_C_EXECUTION_BOOTSTRAP_GITDIR_MISMATCH",
        "PHASE_C_EXECUTION_BOOTSTRAP_REMOTE_SET_INVALID",
        "PHASE_C_EXECUTION_BOOTSTRAP_ORIGIN_MISMATCH",
        "_SECURITY_CRITICAL_EXECUTION_PATHS",
        "_assert_no_index_suppression(actual_root)",
        "_verify_exact_paths_against_head(actual_root, head, _SECURITY_CRITICAL_EXECUTION_PATHS)",
        '["ls-tree", "-z", head, "--", relpath]',
        "_git_blob_sha(data) != expected_blob",
        "PHASE_C_EXECUTION_REVIEWED_BYTES_MISMATCH",
        "PHASE_C_EXECUTION_ASSUME_UNCHANGED_PROHIBITED",
        "PHASE_C_EXECUTION_SKIP_WORKTREE_PROHIBITED",
        'env["GIT_NO_REPLACE_OBJECTS"] = "1"',
        'env["GIT_CONFIG_NOSYSTEM"] = "1"',
        'env["GIT_CONFIG_GLOBAL"] = "/dev/null"',
        '["symbolic-ref", "-q", "HEAD"]',
        "PHASE_C_EXECUTION_CHECKOUT_MUST_BE_DETACHED",
        "main_sha = channel.fresh_main()",
        "if main_sha != checkout:",
        "channel.verify_ruleset()",
        "channel.fence()",
        "environment.status != 404",
        "from nacl.public import PublicKey, SealedBox",
    ):
        assert required in fsrc

    bootstrap_pos = fsrc.index("actual_root = _assert_external_bootstrap_root()")
    index_pos = fsrc.index("_assert_no_index_suppression(actual_root)")
    bytes_pos = fsrc.index("_verify_exact_paths_against_head(actual_root, head, _SECURITY_CRITICAL_EXECUTION_PATHS)")
    status_pos = fsrc.index('["status", "--porcelain=v1", "--untracked-files=all"]')
    assert bootstrap_pos < index_pos < bytes_pos < status_pos

    for forbidden in (
        '"--method", "POST"', '"--method", "PUT"', "pip install", "apt-get", "curl ", "wget ",
        "secret_names()", "public_key()",
    ):
        assert forbidden not in fsrc

    bind_pos = psrc.index("execution_checkout = verified_execution_checkout_head()")
    main_pos = psrc.index("main_before = channel.fresh_main()")
    equality_pos = psrc.index("if main_before != execution_checkout:")
    ruleset_pos = psrc.index("ruleset = channel.verify_ruleset()")
    fence_absence_pos = psrc.index("if channel.fence() is not None:")
    fence_mutation_pos = psrc.index("fence_status = _invoke_exact(")
    marker_pos = psrc.index("session_id = _create_session_marker()")
    secret_pos = psrc.index("secret_status = _invoke_exact(")
    assert bind_pos < main_pos < equality_pos < ruleset_pos < fence_absence_pos < fence_mutation_pos < marker_pos < secret_pos
    assert '{"ref": FENCE_REF, "sha": execution_checkout}' in psrc
    assert "if channel.fresh_main() != execution_checkout:" in psrc
    assert psrc.count("if channel.fresh_main() != execution_checkout:") == 2
    assert '"provision_fence_target_sha": execution_checkout' in psrc
    assert '"execution_checkout_sha": execution_checkout' in psrc

    for forbidden in ("expected_main=", "main_sha=", "canonical_main_sha=", "caller_main", "os.environ.get(\"EXPECTED_MAIN\")"):
        assert forbidden not in psrc

    assert not any(isinstance(node, ast.While) for node in ast.walk(apply))
    assert "PHASE_C_MAIN_NOT_EXACT_DETACHED_EXECUTION_CHECKOUT" in psrc
    assert "PHASE_C_MAIN_DRIFT_AFTER_FENCE" in psrc
    assert "PHASE_C_MAIN_DRIFT_AFTER_SECRET_STORE" in psrc


def main() -> int:
    _structural_test()
    _adversarial_index_suppression_test()
    print("PHASE_C_EXACT_MAIN_PREFLIGHT_REMEDIATION_SELFTEST_PASS")
    print("PRE_EXECUTION_TRUST_ROOT_IS_EXTERNAL_BOOTSTRAP=true")
    print("EXECUTION_ROOT_MEMORY_BACKED_REQUIRED=true")
    print("EXISTING_WORKSPACE_EXECUTION_ROOT_PROHIBITED=true")
    print("ASSUME_UNCHANGED_FALSE_CLEAN_REPRODUCED_AND_REJECTED=true")
    print("SKIP_WORKTREE_SUPPRESSION_REJECTED=true")
    print("HEAD_TREE_ACTUAL_BYTES_DIRECTLY_VERIFIED=true")
    print("REMOTE_MAIN_MUST_EQUAL_EXECUTION_CHECKOUT_BEFORE_FENCE=true")
    print("LIVE_PREFLIGHT_NONMUTATING=true")
    print("PRODUCTION_MUTATION_PERFORMED=false")
    print("PRODUCTION_SECRET_GENERATED=false")
    print("RUNTIME_ACTIVATION_PERFORMED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
