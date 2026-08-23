#!/usr/bin/env python3
"""Nonmutating live preflight for R1 Stage-1 Phase C.

The production trust root is deliberately outside repository Python code.
Before this module may execute on an approved production path, the separately
reviewed literal iPhone/Codespaces operator sequence must create a fresh,
memory-backed Git checkout directly from GitHub at the exact Owner-approved
canonical main commit. Existing workspace project code must not be executed to
construct that checkout.

Once execution begins from that external bootstrap root, this module performs
defense-in-depth authentication of the detached commit and the actual reviewed
source bytes without trusting mutable Git index suppression state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import stat
import subprocess
from typing import Any, Iterable

from multiverse_r1_stage1_writer_key_admin_channel_v1 import (
    CANONICAL_REPO,
    RULESET_ID,
    RULESET_UPDATED_AT,
    Denied,
    PhaseCAdminChannel,
)

EXPECTED_EXECUTION_ROOT = pathlib.Path(
    "/dev/shm/multiverse-r1-stage1-phase-c-execution"
)
EXPECTED_ORIGIN_URL = "https://github.com/fufufu1116/multiverse-research.git"
ROOT = pathlib.Path(__file__).resolve().parents[1]
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_SECURITY_CRITICAL_EXECUTION_PATHS = (
    "tools/multiverse_r1_stage1_phase_c_execution_preflight_v1.py",
    "tools/multiverse_r1_stage1_writer_key_provisioner_v1.py",
    "tools/multiverse_r1_stage1_writer_key_admin_channel_v1.py",
)
_PROHIBITED_GIT_ENV = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_NAMESPACE",
    "GIT_REPLACE_REF_BASE",
    "GIT_CONFIG_COUNT",
)


def _deny(code: str) -> None:
    raise Denied(code)


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in _PROHIBITED_GIT_ENV:
        if env.get(key):
            _deny("PHASE_C_EXECUTION_GIT_CONTROL_ENV_PROHIBITED:" + key)
    for key in env:
        if key.startswith("GIT_CONFIG_KEY_") or key.startswith("GIT_CONFIG_VALUE_"):
            _deny("PHASE_C_EXECUTION_GIT_CONTROL_ENV_PROHIBITED:" + key)
    env["GIT_NO_REPLACE_OBJECTS"] = "1"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_SYSTEM"] = "/dev/null"
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_ATTR_NOSYSTEM"] = "1"
    return env


def _run_git(cmd: list[str], *, cwd: pathlib.Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *cmd],
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_git_env(),
    )


def _git_blob_sha(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def _expected_head_blob(root: pathlib.Path, head: str, relpath: str) -> tuple[str, str]:
    proc = _run_git(["ls-tree", "-z", head, "--", relpath], cwd=root)
    if proc.returncode != 0:
        _deny("PHASE_C_EXECUTION_HEAD_TREE_READ_FAILED")
    rows = [row for row in proc.stdout.split("\0") if row]
    if len(rows) != 1 or "\t" not in rows[0]:
        _deny("PHASE_C_EXECUTION_HEAD_TREE_ENTRY_MISSING_OR_AMBIGUOUS")
    meta, path = rows[0].split("\t", 1)
    parts = meta.split()
    if len(parts) != 3 or path != relpath:
        _deny("PHASE_C_EXECUTION_HEAD_TREE_ENTRY_INVALID")
    mode, obj_type, blob_sha = parts
    if mode not in {"100644", "100755"} or obj_type != "blob" or not _HEX40.fullmatch(blob_sha):
        _deny("PHASE_C_EXECUTION_HEAD_TREE_BLOB_INVALID")
    return mode, blob_sha


def _verify_exact_paths_against_head(root: pathlib.Path, head: str, relpaths: Iterable[str]) -> None:
    """Verify actual file bytes directly against HEAD tree blobs, never the index."""
    resolved_root = root.resolve(strict=True)
    for relpath in relpaths:
        if relpath.startswith("/") or ".." in pathlib.PurePosixPath(relpath).parts:
            _deny("PHASE_C_EXECUTION_REVIEWED_PATH_INVALID")
        path = resolved_root / relpath
        try:
            before = os.lstat(path)
        except FileNotFoundError as exc:
            raise Denied("PHASE_C_EXECUTION_REVIEWED_FILE_MISSING") from exc
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            _deny("PHASE_C_EXECUTION_REVIEWED_FILE_IDENTITY")
        if before.st_uid != os.geteuid() or stat.S_IMODE(before.st_mode) & 0o022:
            _deny("PHASE_C_EXECUTION_REVIEWED_FILE_PERMISSIONS")
        mode, expected_blob = _expected_head_blob(resolved_root, head, relpath)
        data = path.read_bytes()
        after = os.lstat(path)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
        ):
            _deny("PHASE_C_EXECUTION_REVIEWED_FILE_CHANGED_DURING_HASH")
        if _git_blob_sha(data) != expected_blob:
            _deny("PHASE_C_EXECUTION_REVIEWED_BYTES_MISMATCH")
        executable = bool(before.st_mode & 0o111)
        if (mode == "100755") != executable:
            _deny("PHASE_C_EXECUTION_REVIEWED_FILE_MODE_MISMATCH")


def _assert_no_index_suppression(root: pathlib.Path) -> None:
    verbose = _run_git(["ls-files", "-v", "-z"], cwd=root)
    if verbose.returncode != 0:
        _deny("PHASE_C_EXECUTION_INDEX_FLAGS_UNREADABLE")
    for row in (x for x in verbose.stdout.split("\0") if x):
        if row[0].islower():
            _deny("PHASE_C_EXECUTION_ASSUME_UNCHANGED_PROHIBITED")
    tagged = _run_git(["ls-files", "-t", "-z"], cwd=root)
    if tagged.returncode != 0:
        _deny("PHASE_C_EXECUTION_INDEX_FLAGS_UNREADABLE")
    for row in (x for x in tagged.stdout.split("\0") if x):
        if row.startswith("S "):
            _deny("PHASE_C_EXECUTION_SKIP_WORKTREE_PROHIBITED")


def _assert_external_bootstrap_root() -> pathlib.Path:
    """Require the exact fresh memory-backed execution root built before Python starts."""
    try:
        actual_root = ROOT.resolve(strict=True)
        expected_root = EXPECTED_EXECUTION_ROOT.resolve(strict=True)
    except Exception as exc:
        raise Denied("PHASE_C_EXECUTION_BOOTSTRAP_ROOT_UNRESOLVED") from exc
    if actual_root != expected_root:
        _deny("PHASE_C_EXECUTION_ROOT_NOT_EXTERNAL_BOOTSTRAP")

    root_st = os.lstat(actual_root)
    if stat.S_ISLNK(root_st.st_mode) or not stat.S_ISDIR(root_st.st_mode):
        _deny("PHASE_C_EXECUTION_BOOTSTRAP_ROOT_IDENTITY")
    if root_st.st_uid != os.geteuid() or stat.S_IMODE(root_st.st_mode) != 0o700:
        _deny("PHASE_C_EXECUTION_BOOTSTRAP_ROOT_PERMISSIONS")
    fs = subprocess.run(
        ["stat", "-f", "-c", "%T", str(actual_root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy(),
    )
    if fs.returncode != 0 or fs.stdout.strip() not in {"tmpfs", "ramfs"}:
        _deny("PHASE_C_EXECUTION_BOOTSTRAP_ROOT_NOT_MEMORY_FILESYSTEM")

    dot_git = actual_root / ".git"
    try:
        st = os.lstat(dot_git)
    except FileNotFoundError as exc:
        raise Denied("PHASE_C_EXECUTION_BOOTSTRAP_GITDIR_MISSING") from exc
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        _deny("PHASE_C_EXECUTION_BOOTSTRAP_GITDIR_INVALID")

    git_dir_proc = _run_git(["rev-parse", "--absolute-git-dir"], cwd=actual_root)
    if git_dir_proc.returncode != 0 or not git_dir_proc.stdout.strip():
        _deny("PHASE_C_EXECUTION_BOOTSTRAP_GITDIR_UNREADABLE")
    try:
        git_dir = pathlib.Path(git_dir_proc.stdout.strip()).resolve(strict=True)
        expected_git_dir = dot_git.resolve(strict=True)
    except Exception as exc:
        raise Denied("PHASE_C_EXECUTION_BOOTSTRAP_GITDIR_UNRESOLVED") from exc
    if git_dir != expected_git_dir:
        _deny("PHASE_C_EXECUTION_BOOTSTRAP_GITDIR_MISMATCH")

    remotes = _run_git(["remote"], cwd=actual_root)
    if remotes.returncode != 0 or [x for x in remotes.stdout.splitlines() if x] != ["origin"]:
        _deny("PHASE_C_EXECUTION_BOOTSTRAP_REMOTE_SET_INVALID")
    origin = _run_git(["config", "--local", "--get", "remote.origin.url"], cwd=actual_root)
    if origin.returncode != 0 or origin.stdout.strip() != EXPECTED_ORIGIN_URL:
        _deny("PHASE_C_EXECUTION_BOOTSTRAP_ORIGIN_MISMATCH")
    return actual_root


def verified_execution_checkout_head() -> str:
    """Authenticate the externally bootstrapped exact execution checkout."""
    actual_root = _assert_external_bootstrap_root()

    top = _run_git(["rev-parse", "--show-toplevel"], cwd=actual_root)
    if top.returncode != 0 or not top.stdout.strip():
        _deny("PHASE_C_EXECUTION_GIT_TOPLEVEL_UNAVAILABLE")
    try:
        top_root = pathlib.Path(top.stdout.strip()).resolve(strict=True)
    except Exception as exc:
        raise Denied("PHASE_C_EXECUTION_GIT_ROOT_UNRESOLVED") from exc
    if top_root != actual_root:
        _deny("PHASE_C_EXECUTION_GIT_ROOT_MISMATCH")

    symbolic = _run_git(["symbolic-ref", "-q", "HEAD"], cwd=actual_root)
    if symbolic.returncode == 0:
        _deny("PHASE_C_EXECUTION_CHECKOUT_MUST_BE_DETACHED")
    if symbolic.returncode != 1:
        _deny("PHASE_C_EXECUTION_HEAD_STATE_UNREADABLE")

    head_proc = _run_git(["rev-parse", "--verify", "HEAD^{commit}"], cwd=actual_root)
    head = head_proc.stdout.strip()
    if head_proc.returncode != 0 or not _HEX40.fullmatch(head):
        _deny("PHASE_C_EXECUTION_CHECKOUT_SHA_INVALID")

    # Defense in depth after the pre-execution external bootstrap has already
    # established the first trust anchor. These checks do not claim to create
    # that anchor by self-verification.
    _assert_no_index_suppression(actual_root)
    _verify_exact_paths_against_head(actual_root, head, _SECURITY_CRITICAL_EXECUTION_PATHS)

    status = _run_git(["status", "--porcelain=v1", "--untracked-files=all"], cwd=actual_root)
    if status.returncode != 0:
        _deny("PHASE_C_EXECUTION_WORKTREE_STATUS_FAILED")
    if status.stdout.strip():
        _deny("PHASE_C_EXECUTION_WORKTREE_NOT_CLEAN")
    return head


def live_preflight() -> dict[str, Any]:
    """Run the complete reviewed nonmutating live pre-apply proof set."""
    checkout = verified_execution_checkout_head()
    channel = PhaseCAdminChannel()
    scopes = channel.verify_identity_and_scope()
    main_sha = channel.fresh_main()
    if main_sha != checkout:
        _deny("PHASE_C_PREFLIGHT_MAIN_NOT_EXACT_EXECUTION_CHECKOUT")

    ruleset = channel.verify_ruleset()
    if channel.fence() is not None:
        _deny("PHASE_C_PREFLIGHT_PROVISION_FENCE_ALREADY_EXISTS")

    environment = channel.probe_environment()
    if environment.status != 404:
        _deny("PHASE_C_PREFLIGHT_ENVIRONMENT_NOT_ABSENT_404")

    try:
        from nacl.public import PublicKey, SealedBox  # type: ignore
    except Exception as exc:
        raise Denied("PHASE_C_PREFLIGHT_PYNACL_REQUIRED_NO_NETWORK_INSTALL") from exc
    if PublicKey is None or SealedBox is None:
        _deny("PHASE_C_PREFLIGHT_PYNACL_IMPORT_INVALID")

    return {
        "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_EXECUTION_PREFLIGHT_v1",
        "status": "PHASE_C_NONMUTATING_PREFLIGHT_PASS",
        "canonical_repo": CANONICAL_REPO,
        "execution_checkout_sha": checkout,
        "fresh_main_sha": main_sha,
        "pre_execution_external_bootstrap_required": True,
        "execution_root": str(EXPECTED_EXECUTION_ROOT),
        "execution_root_memory_backed": True,
        "origin_url": EXPECTED_ORIGIN_URL,
        "detached_checkout": True,
        "reviewed_execution_bytes_match_head_tree": True,
        "index_suppression_absent": True,
        "secondary_git_status_clean": True,
        "oauth_effective_scopes": scopes,
        "ruleset_id": ruleset["id"],
        "ruleset_updated_at": ruleset["updated_at"],
        "ruleset_expected_id": RULESET_ID,
        "ruleset_expected_updated_at": RULESET_UPDATED_AT,
        "provision_fence_absent_404": True,
        "environment_absent_404": True,
        "gh_api_include_non_2xx_capture_proven": True,
        "pynacl_publickey_sealedbox_available_without_install": True,
        "secret_value_read": False,
        "production_mutation_performed": False,
        "runtime_activation_performed": False,
    }


def selftest() -> None:
    assert CANONICAL_REPO == "fufufu1116/multiverse-research"
    assert EXPECTED_EXECUTION_ROOT == pathlib.Path(
        "/dev/shm/multiverse-r1-stage1-phase-c-execution"
    )
    assert EXPECTED_ORIGIN_URL == "https://github.com/fufufu1116/multiverse-research.git"
    assert _HEX40.fullmatch("0" * 40)
    assert _git_blob_sha(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
    print("PHASE_C_EXECUTION_PREFLIGHT_STATIC_SELFTEST_PASS")
    print("PRE_EXECUTION_EXTERNAL_BOOTSTRAP_REQUIRED=true")
    print("EXECUTION_ROOT_MEMORY_BACKED_REQUIRED=true")
    print("INDEX_INDEPENDENT_REVIEWED_BYTE_BINDING=true")
    print("PRODUCTION_MUTATION_PERFORMED=false")
    print("RUNTIME_ACTIVATION_PERFORMED=false")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    try:
        result = None if args.selftest else live_preflight()
        if args.selftest:
            selftest()
        else:
            print(json.dumps(result, sort_keys=True))
    except Denied as exc:
        print(json.dumps({
            "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_EXECUTION_PREFLIGHT_v1",
            "status": "DENIED_FAIL_CLOSED",
            "reason": str(exc),
            "production_mutation_performed": False,
            "runtime_activation_performed": False,
        }, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
