#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess

import multiverse_r1_stage1_codespaces_admin_channel_v1 as m


class FakeRun:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.operator_apply = False
        self.scopes = "gist, read:org, repo"
        self.admin = True

    def __call__(self, cmd: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(cmd))
        if cmd[:4] == ["stat", "-f", "-c", "%T"]:
            return subprocess.CompletedProcess(cmd, 0, "tmpfs\n", "")
        if cmd[:4] == ["gh", "config", "list", "--host"]:
            return subprocess.CompletedProcess(cmd, 0, "git_protocol=https\nhttp_unix_socket=\n", "")
        if cmd[:3] == ["gh", "api", "--hostname"]:
            endpoint = cmd[-1]
            if endpoint == "/user":
                text = (
                    "HTTP/2 200\n"
                    f"x-oauth-scopes: {self.scopes}\n"
                    "date: Sat, 22 Aug 2026 10:00:00 GMT\n\n"
                    + json.dumps({"login": m.EXPECTED_LOGIN})
                )
                return subprocess.CompletedProcess(cmd, 0, text, "")
            if endpoint == f"/repos/{m.CANONICAL_REPO}":
                text = (
                    "HTTP/2 200\n"
                    "x-oauth-scopes: gist, read:org, repo\n"
                    "date: Sat, 22 Aug 2026 10:00:00 GMT\n\n"
                    + json.dumps({"permissions": {"admin": self.admin}})
                )
                return subprocess.CompletedProcess(cmd, 0, text, "")
        if cmd[:2] == ["git", "hash-object"]:
            return subprocess.CompletedProcess(cmd, 0, m.APPROVED_OPERATOR_BLOB + "\n", "")
        if cmd[:3] == ["git", "merge-base", "--is-ancestor"]:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if len(cmd) >= 2 and cmd[1] == m.APPROVED_OPERATOR_PATH:
            apply = "--apply" in cmd
            self.operator_apply = apply
            status = "CREATED_AND_FRESH_VERIFIED" if apply else "DRY_RUN_WOULD_CREATE_EXACT_RULESET"
            result = {
                "status": status,
                "ruleset_id": 123 if apply else None,
                "ruleset_updated_at": "2026-08-22T10:00:00Z" if apply else None,
            }
            return subprocess.CompletedProcess(cmd, 0, json.dumps(result), "")
        raise AssertionError(f"unexpected command: {cmd}")


def setup_env() -> dict[str, str | None]:
    keys = [
        "CODESPACES", "GH_CONFIG_DIR", "GH_TOKEN", "GITHUB_TOKEN",
        "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN", "GH_HOST",
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy",
        "SSL_CERT_FILE", "SSL_CERT_DIR", "GH_DEBUG", "DEBUG",
    ]
    old = {key: os.environ.get(key) for key in keys}
    for key in keys:
        os.environ.pop(key, None)
    os.environ["CODESPACES"] = "true"
    os.environ["GH_CONFIG_DIR"] = m.EXPECTED_GH_CONFIG_DIR
    return old


def restore_env(old: dict[str, str | None]) -> None:
    for key, value in old.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def run_main(*, apply: bool, fake: FakeRun) -> dict:
    original = m._run
    m._run = fake
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            rc = m.main(["--apply"] if apply else [])
    finally:
        m._run = original
    assert rc == 0
    return json.loads(out.getvalue())


def expect_denied_before_run(env_key: str, env_value: str) -> None:
    old = setup_env()
    original = m._run
    calls: list[list[str]] = []

    def forbidden(cmd: list[str], *, input_text: str | None = None):
        calls.append(cmd)
        raise AssertionError("transport/local gh must not run")

    os.environ[env_key] = env_value
    m._run = forbidden
    try:
        try:
            m._assert_environment_before_any_gh()
        except m.Denied:
            pass
        else:
            raise AssertionError(f"expected denial for {env_key}")
    finally:
        m._run = original
        restore_env(old)
    assert calls == []


def main() -> None:
    old = setup_env()
    try:
        fake = FakeRun()
        dry = run_main(apply=False, fake=fake)
        assert dry["status"] == "CODESPACES_DRY_RUN_COMPLETE"
        assert dry["authentication_method"] == "GH_CLI_WEB_OAUTH_TMPFS_ONLY"
        assert dry["environment_token_used"] is False
        assert dry["credential_material_printed"] is False
        assert dry["credential_material_accepted_as_argument"] is False
        assert fake.operator_apply is False

        fake = FakeRun()
        applied = run_main(apply=True, fake=fake)
        assert applied["status"] == "CODESPACES_APPLY_COMPLETE"
        assert applied["operator_status"] == "CREATED_AND_FRESH_VERIFIED"
        assert applied["ruleset_id"] == 123
        assert fake.operator_apply is True

        # Standard Codespaces/environment tokens must be rejected before any gh call.
        for key in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
            expect_denied_before_run(key, "secret-must-not-be-used")

        # Host/proxy/debug overrides must also be rejected before any gh call.
        for key, value in (
            ("GH_HOST", "evil.example"),
            ("HTTPS_PROXY", "https://proxy.example"),
            ("SSL_CERT_FILE", "/tmp/evil-ca.pem"),
            ("GH_DEBUG", "api"),
        ):
            expect_denied_before_run(key, value)

        # Browser OAuth must have repo scope and no unreviewed scopes.
        fake = FakeRun()
        fake.scopes = "gist, read:org"
        original = m._run
        m._run = fake
        try:
            try:
                m._assert_environment_before_any_gh()
                m._assert_local_gh_config_safe()
                m._verify_browser_oauth_identity_and_scope()
            except m.Denied as exc:
                assert "REPO_SCOPE_MISSING" in str(exc)
            else:
                raise AssertionError("missing repo scope must deny")
        finally:
            m._run = original

        fake = FakeRun()
        fake.scopes = "gist, read:org, repo, admin:org"
        original = m._run
        m._run = fake
        try:
            try:
                m._assert_environment_before_any_gh()
                m._assert_local_gh_config_safe()
                m._verify_browser_oauth_identity_and_scope()
            except m.Denied as exc:
                assert "UNREVIEWED_SCOPE_PRESENT" in str(exc)
            else:
                raise AssertionError("unreviewed oauth scope must deny")
        finally:
            m._run = original

        fake = FakeRun()
        fake.admin = False
        original = m._run
        m._run = fake
        try:
            try:
                m._assert_environment_before_any_gh()
                m._assert_local_gh_config_safe()
                m._verify_browser_oauth_identity_and_scope()
            except m.Denied as exc:
                assert "ADMIN_PERMISSION_REQUIRED" in str(exc)
            else:
                raise AssertionError("repo admin permission must be required")
        finally:
            m._run = original

        assert m.APPROVED_ADMIN_HEAD == "49ab50cfce03e29eedd95d66ee76a41de159940e"
        assert m.APPROVED_OPERATOR_BLOB == "673501d6c083ee240811156ce5917d34b7a1bee4"
        print("MULTIVERSE_R1_STAGE1_CODESPACES_ADMIN_CHANNEL_SELFTEST_PASS")
    finally:
        restore_env(old)


if __name__ == "__main__":
    main()
