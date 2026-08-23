#!/usr/bin/env python3
"""Nonsecret structural/race selftest for the R1 Stage-1 Phase-C support candidate."""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import multiverse_r1_stage1_writer_key_provisioner_v1 as provisioner
from multiverse_r1_stage1_writer_key_admin_channel_v1 import (
    ENVIRONMENT_NAME,
    FENCE_REF,
    RULESET_ID,
    RULESET_UPDATED_AT,
    WRITER_PREFIX,
    Denied,
)

ROOT = Path(__file__).resolve().parents[1]
ADMIN = ROOT / "tools/multiverse_r1_stage1_writer_key_admin_channel_v1.py"
PROVISIONER = ROOT / "tools/multiverse_r1_stage1_writer_key_provisioner_v1.py"
LAUNCHER = ROOT / "tools/multiverse_r1_stage1_writer_key_runtime_launcher_v1.py"
WORKFLOW = ROOT / ".github/workflows/multiverse-r1-stage1-writer-key-runtime-v1.yml"


class FakeChannel:
    def __init__(self, *, fence_status: int = 201, secret_status: int = 201):
        self.main = "a" * 40
        self.fence_status = fence_status
        self.secret_status = secret_status
        self.fence_target = None
        self.secret_put_calls = 0
        self.writer_key_id = None
        self.environment_created = False

    def verify_identity_and_scope(self):
        return ["gist", "read:org", "repo"]

    def fresh_main(self):
        return self.main

    def verify_ruleset(self):
        return {"id": RULESET_ID, "updated_at": RULESET_UPDATED_AT}

    def fence(self):
        return self.fence_target

    def create_fence(self, target_sha: str):
        if self.fence_status == 201:
            self.fence_target = target_sha
        return self.fence_status

    def probe_environment(self):
        return SimpleNamespace(status=404, payload=None)

    def configure_locked_environment(self):
        self.environment_created = True
        return 200

    def environment(self):
        assert self.environment_created
        return {
            "deployment_branch_policy": {
                "protected_branches": False,
                "custom_branch_policies": True,
            },
            "can_admins_bypass": False,
        }

    def policies(self):
        return []

    def secret_names(self):
        if self.secret_put_calls and self.secret_status == 201:
            return set(), {self.writer_key_id}
        return set(), set()

    def public_key(self):
        return "fake-key-id", "A" * 44

    def put_encrypted_secret(self, writer_key_id: str, *, key_id: str, encrypted_value: str):
        assert key_id == "fake-key-id"
        assert encrypted_value == "fake-ciphertext"
        self.secret_put_calls += 1
        self.writer_key_id = writer_key_id
        return self.secret_status


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _syntax_and_static_boundary_test() -> None:
    for path in (ADMIN, PROVISIONER, LAUNCHER):
        ast.parse(_read(path), filename=str(path))

    psrc = _read(PROVISIONER)
    lsrc = _read(LAUNCHER)
    wsrc = _read(WORKFLOW)
    asrc = _read(ADMIN)

    assert psrc.count(".put_encrypted_secret(") == 1
    fence_pos = psrc.index("channel.create_fence(main_before)")
    assert fence_pos < psrc.index("session_marker_factory()")
    assert fence_pos < psrc.index("random_bytes(WRITER_ID_NONCE_BYTES)")
    assert fence_pos < psrc.index("random_bytes(WRITER_KEY_ENTROPY_BYTES)")
    assert "pip install" not in psrc and "apt-get" not in psrc and "curl " not in psrc and "wget " not in psrc
    assert "EXPECTED_EFFECTIVE_OAUTH_SCOPES = {\"repo\", \"read:org\", \"gist\"}" in asrc
    assert 'method not in {"GET", "POST", "PUT"}' in asrc

    assert "workflow_dispatch:" in wsrc
    for trigger in ("schedule:", "push:", "pull_request:", "pull_request_target:", "repository_dispatch:", "workflow_run:"):
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


def _random_source(counter: dict[str, int]):
    def draw(size: int) -> bytes:
        counter["calls"] += 1
        if size == 16:
            return b"\x01" * 16
        if size == 32:
            return b"\x02" * 32
        raise AssertionError(size)
    return draw


def _session_marker_source(counter: dict[str, int], value: str):
    def create() -> str:
        counter["calls"] += 1
        return value
    return create


def _fence_blocks_second_provisioner_before_all_csprng_and_secret_capability_test() -> None:
    fake = FakeChannel(fence_status=422, secret_status=201)
    random_counter = {"calls": 0}
    marker_counter = {"calls": 0}
    try:
        provisioner.apply_once(
            channel_factory=lambda: fake,
            random_bytes=_random_source(random_counter),
            session_marker_factory=_session_marker_source(marker_counter, "1" * 32),
            encryptor=lambda _key, _plain: "fake-ciphertext",
        )
        raise AssertionError("second provisioner unexpectedly passed permanent fence")
    except Denied as exc:
        assert "FENCE_NOT_ACQUIRED_201" in str(exc)
    assert marker_counter["calls"] == 0
    assert random_counter["calls"] == 0
    assert fake.secret_put_calls == 0
    assert not fake.environment_created


def _secret_204_has_exactly_one_attempt_and_no_retry_test() -> None:
    fake = FakeChannel(fence_status=201, secret_status=204)
    random_counter = {"calls": 0}
    marker_counter = {"calls": 0}
    try:
        provisioner.apply_once(
            channel_factory=lambda: fake,
            random_bytes=_random_source(random_counter),
            session_marker_factory=_session_marker_source(marker_counter, "2" * 32),
            encryptor=lambda _key, plain: "fake-ciphertext" if len(plain) == 44 else "bad",
        )
        raise AssertionError("204 overwrite unexpectedly accepted")
    except Denied as exc:
        assert "PROHIBITED_SECRET_OVERWRITE_204" in str(exc)
    assert marker_counter["calls"] == 1
    assert random_counter["calls"] == 2
    assert fake.secret_put_calls == 1


def _successful_candidate_path_outputs_nonsecret_commitment_only_test() -> None:
    fake = FakeChannel(fence_status=201, secret_status=201)
    random_counter = {"calls": 0}
    marker_counter = {"calls": 0}
    result = provisioner.apply_once(
        channel_factory=lambda: fake,
        random_bytes=_random_source(random_counter),
        session_marker_factory=_session_marker_source(marker_counter, "3" * 32),
        encryptor=lambda _key, plain: "fake-ciphertext" if len(plain) == 44 else "bad",
    )
    assert result["status"] == "PHASE_C_WRITER_KEY_STORED_PENDING_MANDATORY_CLEANUP"
    assert result["provision_fence_ref"] == FENCE_REF
    assert result["phase_c_session_id"] == "3" * 32
    assert result["writer_key_id"] == WRITER_PREFIX + "01" * 16
    assert len(result["writer_key_sha256"]) == 64
    assert fake.secret_put_calls == 1
    assert marker_counter["calls"] == 1
    assert random_counter["calls"] == 2
    forbidden_output_keys = {"writer_key", "writer_secret", "secret", "plaintext", "encrypted_value"}
    assert not forbidden_output_keys.intersection(result)
    assert result["runtime_activation_performed"] is False


def main() -> int:
    _syntax_and_static_boundary_test()
    _fence_blocks_second_provisioner_before_all_csprng_and_secret_capability_test()
    _secret_204_has_exactly_one_attempt_and_no_retry_test()
    _successful_candidate_path_outputs_nonsecret_commitment_only_test()
    print("PHASE_C_SUPPORT_IMPLEMENTATION_SELFTEST_PASS")
    print("PRODUCTION_MUTATION_PERFORMED=false")
    print("PRODUCTION_SECRET_GENERATED=false")
    print("RUNTIME_ACTIVATION_PERFORMED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
