#!/usr/bin/env python3
"""Nonsecret structural selftest for the R1 Stage-1 Phase-C support candidate."""
from __future__ import annotations

import ast
from pathlib import Path

from multiverse_r1_stage1_writer_key_admin_channel_v1 import ENVIRONMENT_NAME

ROOT = Path(__file__).resolve().parents[1]
ADMIN = ROOT / "tools/multiverse_r1_stage1_writer_key_admin_channel_v1.py"
PROVISIONER = ROOT / "tools/multiverse_r1_stage1_writer_key_provisioner_v1.py"
LAUNCHER = ROOT / "tools/multiverse_r1_stage1_writer_key_runtime_launcher_v1.py"
WORKFLOW = ROOT / ".github/workflows/multiverse-r1-stage1-writer-key-runtime-v1.yml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(name)


def _class(tree: ast.Module, name: str) -> ast.ClassDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(name)


def _syntax_and_call_boundary_test() -> None:
    asrc = _read(ADMIN)
    psrc = _read(PROVISIONER)
    lsrc = _read(LAUNCHER)
    wsrc = _read(WORKFLOW)

    atree = ast.parse(asrc, filename=str(ADMIN))
    ptree = ast.parse(psrc, filename=str(PROVISIONER))
    ast.parse(lsrc, filename=str(LAUNCHER))

    # The authenticated admin object is read-only. No reviewed public mutation
    # primitive remains available to an importer with the approved credential.
    admin_class = _class(atree, "PhaseCAdminChannel")
    public_methods = {
        node.name for node in admin_class.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    }
    forbidden_public = {
        "api", "create_fence", "configure_locked_environment",
        "put_encrypted_secret", "delete_fence", "update_fence",
    }
    assert not public_methods.intersection(forbidden_public)
    assert {"verify_identity_and_scope", "fresh_main", "fence", "verify_ruleset",
            "probe_environment", "environment", "policies", "secret_names",
            "public_key", "assert_transport_ready"}.issubset(public_methods)
    assert '"--method", "GET"' in asrc
    assert '"--method", "POST"' not in asrc
    assert '"--method", "PUT"' not in asrc

    # Production apply accepts no caller-selected factories, entropy, encryptor,
    # identity, endpoint, method or payload parameters.
    apply_node = _function(ptree, "apply_once")
    assert not apply_node.args.args
    assert not apply_node.args.posonlyargs
    assert not apply_node.args.kwonlyargs
    assert apply_node.args.vararg is None and apply_node.args.kwarg is None
    for forbidden in (
        "channel_factory", "random_bytes", "session_marker_factory", "encryptor",
        "Callable", "def apply_once(",
    ):
        if forbidden == "def apply_once(":
            assert "def apply_once()" in psrc
        else:
            assert forbidden not in psrc

    # Generic mutation transport exists only as a nested lexical helper inside
    # the zero-argument apply_once function, never as a module/class call surface.
    top_level_functions = {node.name for node in ptree.body if isinstance(node, ast.FunctionDef)}
    assert "_invoke_exact" not in top_level_functions
    nested = [node for node in apply_node.body if isinstance(node, ast.FunctionDef)]
    assert [node.name for node in nested] == ["_invoke_exact"]

    fence_pos = psrc.index("fence_status = _invoke_exact(")
    marker_pos = psrc.index("session_id = _create_session_marker_after_fence()")
    env_pos = psrc.index("environment_status = _invoke_exact(")
    id_pos = psrc.index("secrets.token_bytes(WRITER_ID_NONCE_BYTES)")
    key_pos = psrc.index("secrets.token_bytes(WRITER_KEY_ENTROPY_BYTES)")
    secret_pos = psrc.index("secret_status = _invoke_exact(")
    assert fence_pos < marker_pos < env_pos < id_pos < key_pos < secret_pos
    assert psrc.count("secret_status = _invoke_exact(") == 1
    assert "if secret_status != 201:" in psrc
    assert "PHASE_C_PROHIBITED_SECRET_OVERWRITE_204_MATERIAL_INCIDENT" in psrc
    assert "PHASE_C_SECRET_STORE_NOT_CONFIRMED_201_NO_RETRY" in psrc
    assert not any(isinstance(node, ast.While) for node in ast.walk(apply_node))

    # No package/network-install fallback exists in the secret-bearing path.
    for fragment in ("pip install", "apt-get", "curl ", "wget "):
        assert fragment not in psrc

    # Runtime workflow/launcher boundaries retained from the prior PASS scope.
    assert "workflow_dispatch:" in wsrc
    for trigger in ("schedule:", "push:", "pull_request:", "pull_request_target:",
                    "repository_dispatch:", "workflow_run:"):
        assert trigger not in wsrc
    assert "permissions:\n  contents: write" in wsrc
    assert "ubuntu-24.04" in wsrc
    assert "actions/checkout@11d5960a326750d5838078e36cf38b85af677262" in wsrc
    assert "environment: " + ENVIRONMENT_NAME in wsrc
    assert "secrets[needs.preflight.outputs.writer_key_id]" in wsrc
    assert "refs/tags/multiverse-r1-stage1-activation-v1" in wsrc

    assert "load_verified_stage1_context" in lsrc
    assert "build_runtime_ledger(writer_auth_key=writer_bytes)" in lsrc
    assert "ledger.load_snapshot()" in lsrc
    for mutator in ("process_one_controlled", ".claim_invocation(", ".persist_r1_state(", ".release_invocation("):
        assert mutator not in lsrc


def main() -> int:
    _syntax_and_call_boundary_test()
    print("PHASE_C_SUPPORT_IMPLEMENTATION_SELFTEST_PASS")
    print("ADMIN_CHANNEL_PUBLIC_MUTATION_PRIMITIVE_PRESENT=false")
    print("PRODUCTION_APPLY_CALLER_INJECTION_PARAMETERS=false")
    print("PRODUCTION_MUTATION_PERFORMED=false")
    print("PRODUCTION_SECRET_GENERATED=false")
    print("RUNTIME_ACTIVATION_PERFORMED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
