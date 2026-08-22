#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import inspect
import io
import json
import os
import pathlib
import stat
import subprocess
import tempfile
from types import SimpleNamespace

import multiverse_r1_stage1_codespaces_admin_channel_v1 as m


class FakeRun:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.operator_apply = False
        self.scopes = "gist, read:org, repo"
        self.admin = True

    def __call__(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(cmd))
        if cmd[:4] == ["gh", "config", "list", "--host"]:
            return subprocess.CompletedProcess(cmd, 0, "git_protocol=https\nhttp_unix_socket=\n", "")
        if cmd[:3] == ["gh", "api", "--hostname"]:
            endpoint = cmd[-1]
            if endpoint == "/user":
                return subprocess.CompletedProcess(
                    cmd, 0,
                    "HTTP/2 200\nx-oauth-scopes: " + self.scopes + "\n\n" + json.dumps({"login": m.EXPECTED_LOGIN}), ""
                )
            if endpoint == f"/repos/{m.CANONICAL_REPO}":
                return subprocess.CompletedProcess(
                    cmd, 0,
                    "HTTP/2 200\nx-oauth-scopes: gist, read:org, repo\n\n"
                    + json.dumps({"permissions": {"admin": self.admin}}), ""
                )
        if cmd[:2] == ["git", "hash-object"]:
            return subprocess.CompletedProcess(cmd, 0, m.APPROVED_OPERATOR_BLOB + "\n", "")
        if cmd[:3] == ["git", "merge-base", "--is-ancestor"]:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if len(cmd) >= 2 and cmd[1] == m.APPROVED_OPERATOR_PATH:
            apply = "--apply" in cmd
            self.operator_apply = apply
            status = "CREATED_AND_FRESH_VERIFIED" if apply else "DRY_RUN_WOULD_CREATE_EXACT_RULESET"
            return subprocess.CompletedProcess(cmd, 0, json.dumps({
                "status": status,
                "ruleset_id": 123 if apply else None,
                "ruleset_updated_at": "2026-08-22T10:00:00Z" if apply else None,
            }), "")
        raise AssertionError(f"unexpected command: {cmd}")


def setup_env(*, auth_dir: bool = True) -> dict[str, str | None]:
    keys = [
        "CODESPACES", "CODESPACE_NAME", "GH_CONFIG_DIR", "GH_TOKEN", "GITHUB_TOKEN",
        "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN", "GH_HOST",
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy",
        "SSL_CERT_FILE", "SSL_CERT_DIR", "GH_DEBUG", "DEBUG",
    ]
    old = {key: os.environ.get(key) for key in keys}
    for key in keys:
        os.environ.pop(key, None)
    os.environ["CODESPACES"] = "true"
    os.environ["CODESPACE_NAME"] = "rehearsal-test-codespace"
    if auth_dir:
        os.environ["GH_CONFIG_DIR"] = m.EXPECTED_GH_CONFIG_DIR
    return old


def restore_env(old: dict[str, str | None]) -> None:
    for key, value in old.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def run_main(*, apply: bool, fake: FakeRun) -> dict:
    original_run = m._run
    original_storage = m._assert_auth_storage_secure
    original_marker = m._create_origin_session_marker
    m._run = fake
    m._assert_auth_storage_secure = lambda **kwargs: "tmpfs"
    m._create_origin_session_marker = lambda *, apply: ("b" if apply else "a") * 32
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            rc = m.main(["--apply"] if apply else [])
    finally:
        m._run = original_run
        m._assert_auth_storage_secure = original_storage
        m._create_origin_session_marker = original_marker
    assert rc == 0
    return json.loads(out.getvalue())


def expect_env_denied_before_run(key: str, value: str) -> None:
    old = setup_env()
    original = m._run
    calls: list[list[str]] = []
    def forbidden(cmd: list[str]):
        calls.append(cmd)
        raise AssertionError("no local/gh call expected")
    os.environ[key] = value
    m._run = forbidden
    try:
        try:
            m._assert_env_clean()
        except m.Denied:
            pass
        else:
            raise AssertionError("expected env denial")
    finally:
        m._run = original
        restore_env(old)
    assert calls == []


def test_nonmemory_fs_rejected() -> None:
    old = setup_env()
    original_lstat = m.os.lstat
    original_run = m._run
    original_walk = m.os.walk
    fake_dir = SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_uid=os.geteuid())
    m.os.lstat = lambda path: fake_dir
    m.os.walk = lambda *args, **kwargs: []
    m._run = lambda cmd: subprocess.CompletedProcess(cmd, 0, "ext2/ext3\n", "")
    try:
        try:
            m._assert_auth_storage_secure()
        except m.Denied as exc:
            assert "MEMORY_FILESYSTEM" in str(exc)
        else:
            raise AssertionError("non-memory filesystem must be rejected")
    finally:
        m.os.lstat = original_lstat
        m.os.walk = original_walk
        m._run = original_run
        restore_env(old)


def test_tmpfs_requires_swap_check() -> None:
    source = inspect.getsource(m._assert_auth_storage_secure)
    assert "_memory_filesystem_type" in source
    assert "_assert_swap_absent()" in source
    memory_source = inspect.getsource(m._memory_filesystem_type)
    assert '{"tmpfs", "ramfs"}' in memory_source
    swap_source = inspect.getsource(m._assert_swap_absent)
    assert "/proc/swaps" in swap_source and "ACTIVE_SWAP_PROHIBITED" in swap_source


def test_pre_auth_storage_gate() -> None:
    old = setup_env()
    original_storage = m._assert_auth_storage_secure
    calls: list[bool] = []
    def fake_storage(*, require_empty: bool = False) -> str:
        calls.append(require_empty)
        return "tmpfs"
    m._assert_auth_storage_secure = fake_storage
    try:
        proof = m._pre_auth_check()
        assert proof["status"] == "CODESPACES_PRE_AUTH_STORAGE_VERIFIED"
        assert proof["active_swap_absent"] is True
        assert proof["auth_directory_empty"] is True
        assert proof["credential_material_accessed"] is False
        assert calls == [True]
    finally:
        m._assert_auth_storage_secure = original_storage
        restore_env(old)
    source = inspect.getsource(m._pre_auth_check)
    assert "_assert_auth_storage_secure(require_empty=True)" in source
    owner_source = inspect.getsource(m._effective_uid)
    assert "os.geteuid()" in owner_source
    assert "os.getuid()" not in inspect.getsource(m._assert_auth_storage_secure)


def test_origin_session_binding_and_replay() -> None:
    old = setup_env(auth_dir=False)
    original_dir = m.SESSION_STATE_DIR
    original_secure = m._assert_session_state_storage_secure
    with tempfile.TemporaryDirectory() as td:
        m.SESSION_STATE_DIR = td
        m._assert_session_state_storage_secure = lambda *, create: pathlib.Path(td)
        try:
            session_id = m._create_origin_session_marker(apply=False)
            assert len(session_id) == 32
            marker = pathlib.Path(td) / (session_id + ".json")
            assert marker.exists()
            os.environ["CODESPACE_NAME"] = "different-codespace"
            try:
                m._consume_origin_session_marker(session_id)
            except m.Denied as exc:
                assert "BINDING_MISMATCH:codespace_name" in str(exc)
            else:
                raise AssertionError("different Codespace must not consume marker")
            assert marker.exists()
            os.environ["CODESPACE_NAME"] = "rehearsal-test-codespace"
            payload = m._consume_origin_session_marker(session_id)
            assert payload["session_id"] == session_id
            assert payload["codespace_name"] == "rehearsal-test-codespace"
            assert not os.path.lexists(marker)
            try:
                m._consume_origin_session_marker(session_id)
            except m.Denied as exc:
                assert "MARKER_MISSING" in str(exc)
            else:
                raise AssertionError("consumed marker must not replay")
            fabricated = "f" * 32
            try:
                m._consume_origin_session_marker(fabricated)
            except m.Denied as exc:
                assert "MARKER_MISSING" in str(exc)
            else:
                raise AssertionError("fabricated session id must not verify")
        finally:
            m.SESSION_STATE_DIR = original_dir
            m._assert_session_state_storage_secure = original_secure
            restore_env(old)


def test_cleanup_uses_no_follow_absence_and_origin_marker() -> None:
    old = setup_env(auth_dir=False)
    original_lexists = m.os.path.lexists
    original_consume = m._consume_origin_session_marker
    seen: list[str] = []
    m.os.path.lexists = lambda path: False
    def consume(session_id: str) -> dict:
        seen.append(session_id)
        return {"mode": "apply", "codespace_name": os.environ["CODESPACE_NAME"]}
    m._consume_origin_session_marker = consume
    try:
        session_id = "c" * 32
        cleanup = m._cleanup_check(session_id)
        assert seen == [session_id]
        assert cleanup["status"] == "CODESPACES_LOCAL_CREDENTIAL_CLEANUP_VERIFIED"
        assert cleanup["origin_session_bound"] is True
        assert cleanup["origin_codespace_bound"] is True
        assert cleanup["origin_session_marker_consumed"] is True
        assert cleanup["auth_path_absent_no_follow"] is True
        assert cleanup["phase_c_gate_open"] is False
        assert cleanup["codespace_deletion_still_required"] is True
    finally:
        m.os.path.lexists = original_lexists
        m._consume_origin_session_marker = original_consume
        restore_env(old)
    assert "os.path.lexists(EXPECTED_GH_CONFIG_DIR)" in inspect.getsource(m._cleanup_check)


def main() -> None:
    old = setup_env()
    try:
        dry = run_main(apply=False, fake=FakeRun())
        assert dry["status"] == "CODESPACES_IPHONE_REHEARSAL_DRY_RUN_PENDING_CLEANUP"
        assert dry["phase_c_gate_open"] is False
        assert dry["local_cleanup_proof_required"] is True
        assert dry["codespace_deletion_required"] is True
        assert dry["origin_session_marker_created"] is True
        assert len(dry["session_id"]) == 32

        fake = FakeRun()
        applied = run_main(apply=True, fake=fake)
        assert applied["status"] == "CODESPACES_APPLY_PENDING_MANDATORY_CLEANUP"
        assert applied["operator_status"] == "CREATED_AND_FRESH_VERIFIED"
        assert applied["phase_c_gate_open"] is False
        assert applied["origin_session_marker_created"] is True
        assert fake.operator_apply is True

        for key in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
            expect_env_denied_before_run(key, "must-not-be-used")
        for key, value in (("GH_HOST", "evil.example"), ("HTTPS_PROXY", "https://proxy.example"),
                           ("SSL_CERT_FILE", "/tmp/ca"), ("GH_DEBUG", "api")):
            expect_env_denied_before_run(key, value)

        test_nonmemory_fs_rejected()
        test_tmpfs_requires_swap_check()
        test_pre_auth_storage_gate()
        test_origin_session_binding_and_replay()
        test_cleanup_uses_no_follow_absence_and_origin_marker()

        source = inspect.getsource(m._assert_auth_storage_secure)
        assert "st_uid" in source and "0o700" in source
        assert "S_ISLNK" in source and "S_ISREG" in source and "st_nlink" in source

        assert m.APPROVED_ADMIN_HEAD == "49ab50cfce03e29eedd95d66ee76a41de159940e"
        assert m.APPROVED_OPERATOR_BLOB == "673501d6c083ee240811156ce5917d34b7a1bee4"
        assert m.LAB_RESULT_COMMENT == 5379999637
        print("MULTIVERSE_R1_STAGE1_CODESPACES_ADMIN_CHANNEL_SELFTEST_PASS")
    finally:
        restore_env(old)


if __name__ == "__main__":
    main()
