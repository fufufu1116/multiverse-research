#!/usr/bin/env python3
"""Zero-argument one-shot R1 Stage-1 Phase-C writer-key provisioner candidate.

Default mode is non-mutating. ``--apply`` is present only for a separately
reviewed future execution. The production call surface accepts no caller-supplied
repository, Environment, secret name, writer-key ID, endpoint, method, payload,
random source, session-marker factory, encryptor, or canonical-main SHA.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import stat
import subprocess
from typing import Any, Mapping
from urllib.parse import quote

from multiverse_r1_stage1_phase_c_execution_preflight_v1 import verified_execution_checkout_head
from multiverse_r1_stage1_writer_key_admin_channel_v1 import (
    API_VERSION,
    CANONICAL_REPO,
    ENVIRONMENT_NAME,
    EXPECTED_GH_CONFIG_DIR,
    FENCE_REF,
    SESSION_STATE_DIR,
    WRITER_PREFIX,
    Denied,
    PhaseCAdminChannel,
    _assert_memory_dir,
    _parse_included_response,
)

WRITER_ID_NONCE_BYTES = 16
WRITER_KEY_ENTROPY_BYTES = 32
_WRITER_ID_PATTERN_SUFFIX = "[0-9A-F]{32}"


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


def _dry_run_result() -> dict[str, Any]:
    return {
        "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_WRITER_KEY_PROVISIONER_RESULT_v1",
        "status": "DRY_RUN_REVIEW_ONLY_NO_MUTATION",
        "canonical_repo": CANONICAL_REPO,
        "environment": ENVIRONMENT_NAME,
        "provision_fence_ref": FENCE_REF,
        "writer_key_id_pattern": WRITER_PREFIX + _WRITER_ID_PATTERN_SUFFIX,
        "writer_key_entropy_bits_minimum": 256,
        "writer_key_id_entropy_bits": 128,
        "secret_put_attempt_ceiling": 1,
        "production_apply_argument_count": 0,
        "canonical_main_binding_source": "DETACHED_CLEAN_REVIEWED_EXECUTION_CHECKOUT_HEAD",
        "production_secret_generated": False,
        "production_mutation_performed": False,
        "runtime_activation_performed": False,
    }


def apply_once() -> dict[str, Any]:
    """Future production path. Zero caller-controlled production parameters."""
    execution_checkout = verified_execution_checkout_head()
    channel = PhaseCAdminChannel()
    scopes = channel.verify_identity_and_scope()

    main_before = channel.fresh_main()
    if main_before != execution_checkout:
        _deny("PHASE_C_MAIN_NOT_EXACT_DETACHED_EXECUTION_CHECKOUT")
    ruleset = channel.verify_ruleset()
    if channel.fence() is not None:
        _deny("PHASE_C_PROVISION_FENCE_ALREADY_EXISTS")

    def _invoke_exact(method: str, endpoint: str, payload: Mapping[str, Any]) -> int:
        """Lexically scoped transport; never exposed through the admin object."""
        channel.assert_transport_ready()
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        cmd = [
            "gh", "api", "--hostname", "github.com", "--include",
            "-H", "Accept: application/vnd.github+json",
            "-H", f"X-GitHub-Api-Version: {API_VERSION}",
            "--method", method,
            "--input", "-",
            endpoint,
        ]
        proc = subprocess.run(
            cmd,
            input=body,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
        )
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
            "mode": "apply",
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
        try:
            from nacl.public import PublicKey, SealedBox  # type: ignore
        except Exception as exc:
            raise Denied("PHASE_C_PYNACL_REQUIRED_NO_NETWORK_INSTALL") from exc
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

    # First production mutation. Its target is the detached, clean reviewed
    # checkout already proven equal to Fresh canonical main. A main change after
    # any external preflight therefore cannot silently rebind authority here.
    fence_status = _invoke_exact(
        "POST",
        f"/repos/{CANONICAL_REPO}/git/refs",
        {"ref": FENCE_REF, "sha": execution_checkout},
    )
    if fence_status != 201:
        _deny("PHASE_C_PROVISION_FENCE_NOT_ACQUIRED_201")

    if channel.fresh_main() != execution_checkout:
        _deny("PHASE_C_MAIN_DRIFT_AFTER_FENCE")
    channel.verify_ruleset()
    if channel.fence() != execution_checkout:
        _deny("PHASE_C_PROVISION_FENCE_TARGET_DRIFT")

    # All Phase-C CSPRNG begins only after the fence and post-fence barriers.
    session_id = _create_session_marker()

    env_probe = channel.probe_environment()
    if env_probe.status != 404:
        _deny("PHASE_C_ENVIRONMENT_PREEXISTS_OR_AMBIGUOUS")
    environment_status = _invoke_exact(
        "PUT",
        f"/repos/{CANONICAL_REPO}/environments/{quote(ENVIRONMENT_NAME, safe='')}",
        {
            "wait_timer": 0,
            "prevent_self_review": False,
            "reviewers": [],
            "can_admins_bypass": False,
            "deployment_branch_policy": {
                "protected_branches": False,
                "custom_branch_policies": True,
            },
        },
    )
    if environment_status not in {200, 201}:
        _deny("PHASE_C_ENVIRONMENT_CREATE_FAILED")
    _assert_locked_environment(channel)
    _assert_zero_reserved_inventory(channel)

    id_nonce = secrets.token_bytes(WRITER_ID_NONCE_BYTES)
    key_entropy = secrets.token_bytes(WRITER_KEY_ENTROPY_BYTES)
    if len(id_nonce) != WRITER_ID_NONCE_BYTES or len(key_entropy) != WRITER_KEY_ENTROPY_BYTES:
        _deny("PHASE_C_CSPRNG_LENGTH_INVALID")
    writer_key_id = WRITER_PREFIX + id_nonce.hex().upper()

    stored_text = base64.urlsafe_b64encode(key_entropy).decode("ascii")
    stored_bytes = stored_text.encode("utf-8")
    writer_key_sha256 = hashlib.sha256(stored_bytes).hexdigest()

    public_key_id, public_key_b64 = channel.public_key()
    encrypted_value = _encrypt_exact(public_key_b64, stored_bytes)

    # Sole secret PUT attempt. The caller never supplies the secret name, ID,
    # endpoint, method, encrypted payload, key ID, or plaintext bytes.
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
    if channel.fresh_main() != execution_checkout:
        _deny("PHASE_C_MAIN_DRIFT_AFTER_SECRET_STORE")
    if channel.fence() != execution_checkout:
        _deny("PHASE_C_PROVISION_FENCE_DRIFT_AFTER_SECRET_STORE")

    return {
        "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_WRITER_KEY_PROVISIONER_RESULT_v1",
        "status": "PHASE_C_WRITER_KEY_STORED_PENDING_MANDATORY_CLEANUP",
        "canonical_repo": CANONICAL_REPO,
        "canonical_main": execution_checkout,
        "execution_checkout_sha": execution_checkout,
        "environment": ENVIRONMENT_NAME,
        "provision_fence_ref": FENCE_REF,
        "provision_fence_target_sha": execution_checkout,
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        print(json.dumps(_dry_run_result(), sort_keys=True))
        return 0
    try:
        result = apply_once()
    except Denied as exc:
        print(json.dumps({
            "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_WRITER_KEY_PROVISIONER_RESULT_v1",
            "status": "DENIED_FAIL_CLOSED",
            "reason": str(exc),
            "writer_secret_printed": False,
            "blind_retry_authorized": False,
            "runtime_activation_performed": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
