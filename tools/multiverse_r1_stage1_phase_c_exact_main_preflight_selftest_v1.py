#!/usr/bin/env python3
"""Nonsecret structural tests for the Phase-C exact-main/preflight remediation."""
from __future__ import annotations

import ast
from pathlib import Path

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


def main() -> int:
    fsrc = _read(PREFLIGHT)
    psrc = _read(PROVISIONER)
    ftree = ast.parse(fsrc, filename=str(PREFLIGHT))
    ptree = ast.parse(psrc, filename=str(PROVISIONER))

    binding = _function(ftree, "verified_execution_checkout_head")
    live = _function(ftree, "live_preflight")
    apply = _function(ptree, "apply_once")
    assert not binding.args.args and not live.args.args and not apply.args.args
    assert not apply.args.posonlyargs and not apply.args.kwonlyargs
    assert apply.args.vararg is None and apply.args.kwarg is None

    for required in (
        '["git", "symbolic-ref", "-q", "HEAD"]',
        "PHASE_C_EXECUTION_CHECKOUT_MUST_BE_DETACHED",
        '["git", "status", "--porcelain=v1", "--untracked-files=all"]',
        "PHASE_C_EXECUTION_WORKTREE_NOT_CLEAN",
        "main_sha = channel.fresh_main()",
        "if main_sha != checkout:",
        "channel.verify_ruleset()",
        "channel.fence()",
        "environment.status != 404",
        "from nacl.public import PublicKey, SealedBox",
    ):
        assert required in fsrc

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
    assert "main_before = channel.fresh_main()\n    if main_before != execution_checkout:" in psrc

    for forbidden in ("expected_main=", "main_sha=", "canonical_main_sha=", "caller_main", "os.environ.get(\"EXPECTED_MAIN")"):
        assert forbidden not in psrc

    assert not any(isinstance(node, ast.While) for node in ast.walk(apply))
    assert "PHASE_C_MAIN_NOT_EXACT_DETACHED_EXECUTION_CHECKOUT" in psrc
    assert "PHASE_C_MAIN_DRIFT_AFTER_FENCE" in psrc
    assert "PHASE_C_MAIN_DRIFT_AFTER_SECRET_STORE" in psrc

    print("PHASE_C_EXACT_MAIN_PREFLIGHT_REMEDIATION_SELFTEST_PASS")
    print("DETACHED_CLEAN_EXECUTION_CHECKOUT_REQUIRED=true")
    print("REMOTE_MAIN_MUST_EQUAL_EXECUTION_CHECKOUT_BEFORE_FENCE=true")
    print("LIVE_PREFLIGHT_NONMUTATING=true")
    print("PRODUCTION_MUTATION_PERFORMED=false")
    print("PRODUCTION_SECRET_GENERATED=false")
    print("RUNTIME_ACTIVATION_PERFORMED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
