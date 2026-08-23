#!/usr/bin/env python3
"""One-shot R1 Stage-1 Phase-C writer-key provisioner candidate.

Default mode is non-mutating. ``--apply`` is intentionally present for later
reviewed execution only; this candidate/PR does not authorize running it.
The production secret is generated in memory and only its ID plus SHA-256 may
leave this process after confirmed storage and Fresh inventory verification.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import secrets
from typing import Any, Callable

from multiverse_r1_stage1_writer_key_admin_channel_v1 import (
    CANONICAL_REPO,
    ENVIRONMENT_NAME,
    FENCE_REF,
    WRITER_PREFIX,
    Denied,
    PhaseCAdminChannel,
    create_session_marker,
)

WRITER_ID_NONCE_BYTES = 16
WRITER_KEY_ENTROPY_BYTES = 32
WRITER_ID_PREFIX = WRITER_PREFIX


def _deny(code: str) -> None:
    raise Denied(code)


def _reserved(names: set[str]) -> set[str]:
    return {name for name in names if name.startswith(WRITER_PREFIX)}


def _assert_zero_reserved_inventory(channel: PhaseCAdminChannel) -> None:
    repo_names, env_names = channel.secret_names()
    if _reserved(repo_names) or _reserved(env_names):
        _deny("PHASE_C_RESERVED_WRITER_SECRET_ALREADY_PRESENT")


def _assert_exact_single_reserved_inventory(
    channel: PhaseCAdminChannel, writer_key_id: str
) -> None:
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


def _sealed_box_encrypt(public_key_b64: str, plaintext: bytes) -> str:
    """Encrypt exact stored bytes. No package installation or fallback path."""
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


def _dry_run_result() -> dict[str, Any]:
    return {
        "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_WRITER_KEY_PROVISIONER_RESULT_v1",
        "status": "DRY_RUN_REVIEW_ONLY_NO_MUTATION",
        "canonical_repo": CANONICAL_REPO,
        "environment": ENVIRONMENT_NAME,
        "provision_fence_ref": FENCE_REF,
        "writer_key_id_pattern": WRITER_PREFIX + "[0-9A-F]{32}",
        "writer_key_entropy_bits_minimum": 256,
        "writer_key_id_entropy_bits": 128,
        "secret_put_attempt_ceiling": 1,
        "production_secret_generated": False,
        "production_mutation_performed": False,
        "runtime_activation_performed": False,
    }


def apply_once(
    *,
    channel_factory: Callable[[], PhaseCAdminChannel] = PhaseCAdminChannel,
    random_bytes: Callable[[int], bytes] = secrets.token_bytes,
) -> dict[str, Any]:
    """Future production path. Call only after later independent execution approval."""
    channel = channel_factory()
    scopes = channel.verify_identity_and_scope()
    session_id = create_session_marker()

    main_before = channel.fresh_main()
    ruleset = channel.verify_ruleset()
    if channel.fence() is not None:
        _deny("PHASE_C_PROVISION_FENCE_ALREADY_EXISTS")

    # First production mutation. Only this exact 201 winner may ever reach
    # Environment mutation, CSPRNG, or writer-secret PUT.
    fence_status = channel.create_fence(main_before)
    if fence_status != 201:
        _deny("PHASE_C_PROVISION_FENCE_NOT_ACQUIRED_201")

    if channel.fresh_main() != main_before:
        _deny("PHASE_C_MAIN_DRIFT_AFTER_FENCE")
    channel.verify_ruleset()
    if channel.fence() != main_before:
        _deny("PHASE_C_PROVISION_FENCE_TARGET_DRIFT")

    # The exact Environment must be absent before this winner creates the
    # reviewed locked state. Any pre-existing state requires separate review.
    env_probe = channel.api("GET", channel.environment_endpoint())
    if env_probe.status != 404:
        _deny("PHASE_C_ENVIRONMENT_PREEXISTS_OR_AMBIGUOUS")
    environment_status = channel.configure_locked_environment()
    if environment_status not in {200, 201}:
        _deny("PHASE_C_ENVIRONMENT_CREATE_FAILED")
    _assert_locked_environment(channel)
    _assert_zero_reserved_inventory(channel)

    # Secret identity and secret material are independent CSPRNG draws and are
    # generated only after the permanent fence and zero-prefix inventory gate.
    id_nonce = random_bytes(WRITER_ID_NONCE_BYTES)
    key_entropy = random_bytes(WRITER_KEY_ENTROPY_BYTES)
    if len(id_nonce) != WRITER_ID_NONCE_BYTES or len(key_entropy) != WRITER_KEY_ENTROPY_BYTES:
        _deny("PHASE_C_CSPRNG_LENGTH_INVALID")
    writer_key_id = WRITER_PREFIX + id_nonce.hex().upper()

    # GitHub Actions secrets are string values. Preserve >=256 bits of entropy
    # by storing URL-safe base64 text; the commitment covers the exact UTF-8
    # bytes the Runtime launcher will later receive and pass to canonical CAS.
    stored_text = base64.urlsafe_b64encode(key_entropy).decode("ascii")
    stored_bytes = stored_text.encode("utf-8")
    writer_key_sha256 = hashlib.sha256(stored_bytes).hexdigest()

    public_key_id, public_key_b64 = channel.public_key()
    encrypted_value = _sealed_box_encrypt(public_key_b64, stored_bytes)

    # Exactly one secret-write call site and one attempt. 201 is the sole
    # accepted result; 204 means a prohibited overwrite already occurred and
    # therefore fails closed with no receipt and no retry.
    secret_status = channel.put_encrypted_secret(
        writer_key_id,
        key_id=public_key_id,
        encrypted_value=encrypted_value,
    )
    if secret_status != 201:
        if secret_status == 204:
            _deny("PHASE_C_PROHIBITED_SECRET_OVERWRITE_204_MATERIAL_INCIDENT")
        _deny("PHASE_C_SECRET_STORE_NOT_CONFIRMED_201_NO_RETRY")

    _assert_exact_single_reserved_inventory(channel, writer_key_id)
    if channel.fresh_main() != main_before:
        _deny("PHASE_C_MAIN_DRIFT_AFTER_SECRET_STORE")
    if channel.fence() != main_before:
        _deny("PHASE_C_PROVISION_FENCE_DRIFT_AFTER_SECRET_STORE")

    return {
        "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_WRITER_KEY_PROVISIONER_RESULT_v1",
        "status": "PHASE_C_WRITER_KEY_STORED_PENDING_MANDATORY_CLEANUP",
        "canonical_repo": CANONICAL_REPO,
        "canonical_main": main_before,
        "environment": ENVIRONMENT_NAME,
        "provision_fence_ref": FENCE_REF,
        "provision_fence_target_sha": main_before,
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
        # Error codes contain no secret material. The future approved operator
        # must perform the separately reviewed cleanup path after any failure.
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
