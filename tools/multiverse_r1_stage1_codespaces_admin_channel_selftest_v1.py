#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import inspect
import io
import json
import os
import stat
import subprocess
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
    m._run = fake
    m._assert_auth_storage_secure = lambda: None
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            rc = m.main(["--apply"] if apply else [])
    finally:
        m._run = original_run
        m._assert_auth_storage_secure = original_storage
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


def test_tmpfs_rejected() -> None:
    old = setup_env()
    original_lstat = m.os.lstat
    original_run = m._run
    original_walk = m.os.walk
    fake_dir = SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_uid=os.getuid())
    m.os.lstat = lambda path: fake_dir
    m.os.walk = lambda *args, **kwargs: []
    m._run = lambda cmd: subprocess.CompletedProcess(cmd, 0, "tmpfs\n", "")
    try:
        try:
            m._assert_auth_storage_secure()
        except m.Denied as exc:
            assert "NONSWAPPABLE_RAMFS" in str(exc)
        else:
            raise AssertionError("tmpfs must be rejected")
    finally:
        m.os.lstat = original_lstat
        m.os.walk = original_walk
        m._run = original_run
        restore_env(old)


def main() -> None:
    old = setup_env()
    try:
        dry = run_main(apply=False, fake=FakeRun())
        assert dry["status"] == "CODESPACES_IPHONE_REHEARSAL_DRY_RUN_PENDING_CLEANUP"
        assert dry["phase_c_gate_open"] is False
        assert dry["local_cleanup_proof_required"] is True
        assert dry["codespace_deletion_required"] is True
        assert len(dry["session_id"]) == 32

        fake = FakeRun()
        applied = run_main(apply=True, fake=fake)
        assert applied["status"] == "CODESPACES_APPLY_PENDING_MANDATORY_CLEANUP"
        assert applied["operator_status"] == "CREATED_AND_FRESH_VERIFIED"
        assert applied["phase_c_gate_open"] is False
        assert fake.operator_apply is True

        for key in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
            expect_env_denied_before_run(key, "must-not-be-used")
        for key, value in (("GH_HOST", "evil.example"), ("HTTPS_PROXY", "https://proxy.example"),
                           ("SSL_CERT_FILE", "/tmp/ca"), ("GH_DEBUG", "api")):
            expect_env_denied_before_run(key, value)

        test_tmpfs_rejected()

        # Structural regression assertions for the new storage boundary.
        source = inspect.getsource(m._assert_auth_storage_secure)
        assert '!= "ramfs"' in source
        assert "st_uid" in source and "0o700" in source
        assert "S_ISLNK" in source and "S_ISREG" in source and "st_nlink" in source
        assert "/proc/swaps" in inspect.getsource(m._assert_swap_absent)

        # Local cleanup proof itself is non-network and cannot open Phase C.
        old_mount = m._mountinfo_has_exact
        old_exists = m.pathlib.Path.exists
        os.environ.pop("GH_CONFIG_DIR", None)
        m._mountinfo_has_exact = lambda path: False
        m.pathlib.Path.exists = lambda self: False
        try:
            cleanup = m._cleanup_check(applied["session_id"])
            assert cleanup["status"] == "CODESPACES_LOCAL_CREDENTIAL_CLEANUP_VERIFIED"
            assert cleanup["phase_c_gate_open"] is False
            assert cleanup["codespace_deletion_still_required"] is True
        finally:
            m._mountinfo_has_exact = old_mount
            m.pathlib.Path.exists = old_exists
            os.environ["GH_CONFIG_DIR"] = m.EXPECTED_GH_CONFIG_DIR

        assert m.APPROVED_ADMIN_HEAD == "49ab50cfce03e29eedd95d66ee76a41de159940e"
        assert m.APPROVED_OPERATOR_BLOB == "673501d6c083ee240811156ce5917d34b7a1bee4"
        assert m.LAB_RESULT_COMMENT == 5379999637
        print("MULTIVERSE_R1_STAGE1_CODESPACES_ADMIN_CHANNEL_SELFTEST_PASS")
    finally:
        restore_env(old)


if __name__ == "__main__":
    main()
