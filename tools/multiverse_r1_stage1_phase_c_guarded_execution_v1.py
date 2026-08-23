#!/usr/bin/env python3
"""Exact-main guarded one-shot Phase-C execution overlay."""
from __future__ import annotations
import argparse, base64, hashlib, inspect, json, os, secrets, stat, subprocess
from typing import Any, Mapping
from urllib.parse import quote
from multiverse_r1_stage1_writer_key_admin_channel_v1 import (
    API_VERSION, CANONICAL_REPO, ENVIRONMENT_NAME, EXPECTED_GH_CONFIG_DIR,
    FENCE_REF, SESSION_STATE_DIR, WRITER_PREFIX, Denied, PhaseCAdminChannel,
    _assert_memory_dir, _parse_included_response,
)
AUTHORIZED_CANONICAL_MAIN = "ff07e5ee02fa84405eb2fc89cfdbff1d26267cc9"
WRITER_ID_NONCE_BYTES = 16
WRITER_KEY_ENTROPY_BYTES = 32

def _deny(code: str) -> None:
    raise Denied(code)

def _reserved(names: set[str]) -> set[str]:
    return {name for name in names if name.startswith(WRITER_PREFIX)}

def _assert_zero_reserved_inventory(channel: PhaseCAdminChannel) -> None:
    repo_names, env_names = channel.secret_names()
    if _reserved(repo_names) or _reserved(env_names):
        _deny("PHASE_C_RESERVED_WRITER_SECRET_ALREADY_PRESENT")

def _assert_exact_single_reserved_inventory(channel: PhaseCAdminChannel, writer_key_id: str) -> None:
    repo_names, env_names = channel.secret_names()
    repo_matches = _reserved(repo_names)
    env_matches = _reserved(env_names)
    if repo_matches or env_matches != {writer_key_id}:
        _deny("PHASE_C_POSTWRITE_WRITER_SECRET_INVENTORY_MISMATCH")
    if len(repo_matches) + len(env_matches) != 1:
        _deny("PHASE_C_POSTWRITE_WRITER_SECRET_INVENTORY_AMBIGUOUS")

def _assert_locked_environment(channel: PhaseCAdminChannel) -> None:
    env = channel.environment()
    policy = env.get("deployment_branch_policy")
    if policy != {"protected_branches": False, "custom_branch_policies": True}:
        _deny("PHASE_C_ENVIRONMENT_NOT_SELECTED_POLICY_LOCK_MODE")
    if env.get("can_admins_bypass") is not False:
        _deny("PHASE_C_ENVIRONMENT_ADMIN_BYPASS_NOT_DISABLED")
    if channel.policies() != []:
        _deny("PHASE_C_ENVIRONMENT_NOT_DENY_ALL_ZERO_POLICY")

def _assert_pynacl_available() -> None:
    try:
        from nacl.public import PublicKey, SealedBox  # noqa: F401
    except Exception as exc:
        raise Denied("PHASE_C_PYNACL_REQUIRED_NO_NETWORK_INSTALL") from exc

def live_preflight() -> dict[str, Any]:
    channel = PhaseCAdminChannel()
    scopes = channel.verify_identity_and_scope()
    main_now = channel.fresh_main()
    if main_now != AUTHORIZED_CANONICAL_MAIN:
        _deny("PHASE_C_OWNER_AUTHORIZED_MAIN_MISMATCH")
    ruleset = channel.verify_ruleset()
    if channel.fence() is not None:
        _deny("PHASE_C_PROVISION_FENCE_ALREADY_EXISTS")
    env_probe = channel.probe_environment()
    if env_probe.status != 404:
        _deny("PHASE_C_ENVIRONMENT_PREEXISTS_OR_AMBIGUOUS")
    _assert_pynacl_available()
    return {
        "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_EXECUTION_LIVE_PREFLIGHT_v1",
        "status": "PHASE_C_LIVE_PREFLIGHT_PASS_NO_MUTATION",
        "authorized_canonical_main": AUTHORIZED_CANONICAL_MAIN,
        "fresh_main": main_now,
        "ruleset_id": ruleset["id"],
        "ruleset_updated_at": ruleset["updated_at"],
        "fence_absence_404_capture_proven": True,
        "environment_absence_404_capture_proven": True,
        "pynacl_available_without_network_install": True,
        "oauth_effective_scopes": scopes,
        "production_mutation_performed": False,
        "writer_secret_generated": False,
        "runtime_activation_performed": False,
    }

def apply_once() -> dict[str, Any]:
    channel = PhaseCAdminChannel()
    scopes = channel.verify_identity_and_scope()
    main_before = channel.fresh_main()
    if main_before != AUTHORIZED_CANONICAL_MAIN:
        _deny("PHASE_C_OWNER_AUTHORIZED_MAIN_MISMATCH")
    ruleset = channel.verify_ruleset()
    if channel.fence() is not None:
        _deny("PHASE_C_PROVISION_FENCE_ALREADY_EXISTS")
    env_before = channel.probe_environment()
    if env_before.status != 404:
        _deny("PHASE_C_ENVIRONMENT_PREEXISTS_OR_AMBIGUOUS")
    _assert_pynacl_available()

    def _invoke_exact(method: str, endpoint: str, payload: Mapping[str, Any]) -> int:
        channel.assert_transport_ready()
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        cmd = [
            "gh", "api", "--hostname", "github.com", "--include",
            "-H", "Accept: application/vnd.github+json",
            "-H", f"X-GitHub-Api-Version: {API_VERSION}",
            "--method", method, "--input", "-", endpoint,
        ]
        proc = subprocess.run(cmd, input=body, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=os.environ.copy())
        if not proc.stdout.strip():
            _deny("PHASE_C_MUTATION_API_NO_RESPONSE")
        status, _headers, _payload = _parse_included_response(proc.stdout)
        return status

    def _create_session_marker() -> str:
        root = _assert_memory_dir(SESSION_STATE_DIR, create=True)
        session_id = secrets.token_hex(16)
        path = root / (session_id + ".json")
        payload = {
            "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_ORIGIN_SESSION_MARKER_v1",
            "session_id": session_id,
            "codespace_name": os.environ.get("CODESPACE_NAME"),
            "gh_config_dir": EXPECTED_GH_CONFIG_DIR,
            "mode": "guarded-apply",
            "authorized_canonical_main": AUTHORIZED_CANONICAL_MAIN,
            "runtime_activation_performed": False,
        }
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        st = os.lstat(path)
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
            _deny("PHASE_C_SESSION_MARKER_IDENTITY")
        if st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) != 0o600:
            _deny("PHASE_C_SESSION_MARKER_PERMISSIONS")
        return session_id

    def _encrypt_exact(public_key_b64: str, plaintext: bytes) -> str:
        from nacl.public import PublicKey, SealedBox
        try:
            key_raw = base64.b64decode(public_key_b64, validate=True)
            if len(key_raw) != 32:
                _deny("PHASE_C_ENVIRONMENT_PUBLIC_KEY_LENGTH")
            ciphertext = SealedBox(PublicKey(key_raw)).encrypt(plaintext)
        except Denied:
            raise
        except Exception as exc:
            raise Denied("PHASE_C_SEALED_BOX_ENCRYPTION_FAILED") from exc
        return base64.b64encode(ciphertext).decode("ascii")

    fence_status = _invoke_exact(
        "POST", f"/repos/{CANONICAL_REPO}/git/refs",
        {"ref": FENCE_REF, "sha": AUTHORIZED_CANONICAL_MAIN},
    )
    if fence_status != 201:
        _deny("PHASE_C_PROVISION_FENCE_NOT_ACQUIRED_201")
    if channel.fresh_main() != AUTHORIZED_CANONICAL_MAIN:
        _deny("PHASE_C_MAIN_DRIFT_AFTER_FENCE")
    channel.verify_ruleset()
    if channel.fence() != AUTHORIZED_CANONICAL_MAIN:
        _deny("PHASE_C_PROVISION_FENCE_TARGET_DRIFT")

    session_id = _create_session_marker()
    env_probe = channel.probe_environment()
    if env_probe.status != 404:
        _deny("PHASE_C_ENVIRONMENT_PREEXISTS_OR_AMBIGUOUS_AFTER_FENCE")
    environment_status = _invoke_exact(
        "PUT",
        f"/repos/{CANONICAL_REPO}/environments/{quote(ENVIRONMENT_NAME, safe='')}",
        {
            "wait_timer": 0, "prevent_self_review": False, "reviewers": [],
            "can_admins_bypass": False,
            "deployment_branch_policy": {
                "protected_branches": False, "custom_branch_policies": True,
            },
        },
    )
    if environment_status not in {200, 201}:
        _deny("PHASE_C_ENVIRONMENT_CREATE_FAILED")
    _assert_locked_environment(channel)
    _assert_zero_reserved_inventory(channel)

    id_nonce = secrets.token_bytes(WRITER_ID_NONCE_BYTES)
    key_entropy = secrets.token_bytes(WRITER_KEY_ENTROPY_BYTES)
    writer_key_id = WRITER_PREFIX + id_nonce.hex().upper()
    stored_text = base64.urlsafe_b64encode(key_entropy).decode("ascii")
    stored_bytes = stored_text.encode("utf-8")
    writer_key_sha256 = hashlib.sha256(stored_bytes).hexdigest()
    public_key_id, public_key_b64 = channel.public_key()
    encrypted_value = _encrypt_exact(public_key_b64, stored_bytes)

    secret_status = _invoke_exact(
        "PUT",
        f"/repos/{CANONICAL_REPO}/environments/{quote(ENVIRONMENT_NAME, safe='')}/secrets/{writer_key_id}",
        {"encrypted_value": encrypted_value, "key_id": public_key_id},
    )
    if secret_status != 201:
        if secret_status == 204:
            _deny("PHASE_C_PROHIBITED_SECRET_OVERWRITE_204_MATERIAL_INCIDENT")
        _deny("PHASE_C_SECRET_STORE_NOT_CONFIRMED_201_NO_RETRY")
    _assert_exact_single_reserved_inventory(channel, writer_key_id)
    if channel.fresh_main() != AUTHORIZED_CANONICAL_MAIN:
        _deny("PHASE_C_MAIN_DRIFT_AFTER_SECRET_STORE")
    if channel.fence() != AUTHORIZED_CANONICAL_MAIN:
        _deny("PHASE_C_PROVISION_FENCE_DRIFT_AFTER_SECRET_STORE")

    return {
        "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_GUARDED_EXECUTION_RESULT_v1",
        "status": "PHASE_C_WRITER_KEY_STORED_PENDING_MANDATORY_CLEANUP",
        "canonical_repo": CANONICAL_REPO,
        "authorized_canonical_main": AUTHORIZED_CANONICAL_MAIN,
        "canonical_main": main_before,
        "environment": ENVIRONMENT_NAME,
        "provision_fence_ref": FENCE_REF,
        "provision_fence_target_sha": AUTHORIZED_CANONICAL_MAIN,
        "phase_c_session_id": session_id,
        "writer_key_id": writer_key_id,
        "writer_key_sha256": writer_key_sha256,
        "store_identity": "GITHUB_ACTIONS_ENVIRONMENT:" + ENVIRONMENT_NAME,
        "oauth_effective_scopes": scopes,
        "ruleset_id": ruleset["id"],
        "ruleset_updated_at": ruleset["updated_at"],
        "secret_put_http_status": 201,
        "writer_secret_plaintext_printed": False,
        "writer_secret_persisted_locally": False,
        "caller_supplied_production_parameter": False,
        "local_credential_cleanup_required": True,
        "codespace_deletion_required": True,
        "durable_phase_c_receipt_required": True,
        "runtime_branch_created": False,
        "activation_receipt_or_tag_created": False,
        "runtime_activation_performed": False,
    }

def selftest() -> None:
    assert len(inspect.signature(apply_once).parameters) == 0
    assert len(inspect.signature(live_preflight).parameters) == 0
    src = inspect.getsource(apply_once)
    fence_pos = src.index("fence_status = _invoke_exact(")
    assert src.index("PHASE_C_OWNER_AUTHORIZED_MAIN_MISMATCH") < fence_pos
    assert src.index("env_before = channel.probe_environment()") < fence_pos
    assert src.index("_assert_pynacl_available()") < fence_pos
    assert src.count("/secrets/{writer_key_id}") == 1
    print("PHASE_C_GUARDED_EXECUTION_SELFTEST_PASS")
    print("PRODUCTION_MUTATION_PERFORMED=false")
    print("RUNTIME_ACTIVATION_PERFORMED=false")

def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    try:
        if args.preflight:
            result = live_preflight()
        elif args.apply:
            result = apply_once()
        else:
            selftest()
            return 0
    except Denied as exc:
        print(json.dumps({
            "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_GUARDED_EXECUTION_RESULT_v1",
            "status": "DENIED_FAIL_CLOSED", "reason": str(exc),
            "blind_retry_authorized": False, "writer_secret_printed": False,
            "runtime_activation_performed": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
