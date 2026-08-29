#!/usr/bin/env python3
import json
import os
import pathlib
import shutil
import subprocess
import sys

EXPECTED_LOGIN = "fufufu1116"
EXPECTED_REPO = "fufufu1116/multiverse-research"
EXPECTED_SCOPES = {"repo", "read:org", "gist"}
EXPECTED_GH_CONFIG_DIR = "/dev/shm/multiverse-r1-stage1-phase-c-gh-auth"
CONTROLLED_PATH = "/usr/local/bin:/usr/bin:/bin:/usr/local/python/current/bin"
API_VERSION = "2022-11-28"
SUCCESS = "PHASE_C_V19_7_2_AUTH_SCOPE_ADMIN_NONMUTATING_PASS"
FAIL = "PHASE_C_V19_7_2_AUTH_SCOPE_ADMIN_NONMUTATING_STOP_DELETE_CODESPACE"


def stop(reason: str) -> None:
    print(f"{FAIL}:{reason}", file=sys.stderr)
    raise SystemExit(91)


def resolve_gh() -> str:
    if os.environ.get("PATH") != CONTROLLED_PATH:
        stop("PATH_NOT_EXACT")
    resolved = shutil.which("gh", path=CONTROLLED_PATH)
    if resolved is None:
        stop("GH_NOT_FOUND_IN_CONTROLLED_PATH")
    if not os.path.isabs(resolved) or not os.path.isfile(resolved) or not os.access(resolved, os.X_OK):
        stop("GH_RESOLUTION_INVALID")
    current = shutil.which("gh")
    if current != resolved:
        stop("GH_RESOLUTION_MISMATCH")
    return resolved


def parse_included(text: str):
    header, sep, body = text.replace("\r\n", "\n").partition("\n\n")
    if not sep:
        stop("HEADERS_MISSING")
    lines = [line for line in header.splitlines() if line]
    if not lines or not lines[0].startswith("HTTP/"):
        stop("STATUS_MISSING")
    try:
        status = int(lines[0].split()[1])
    except Exception:
        stop("STATUS_INVALID")
    headers = {}
    for line in lines[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        if key in headers:
            stop("DUPLICATE_HEADER_" + key)
        headers[key] = value.strip()
    try:
        payload = json.loads(body.strip()) if body.strip() else None
    except Exception:
        stop("JSON_INVALID")
    return status, headers, payload


def api_get(gh_bin: str, endpoint: str):
    clean = {
        "PATH": CONTROLLED_PATH,
        "HOME": "/dev/shm/multiverse-r1-stage1-phase-c-home",
        "GH_CONFIG_DIR": EXPECTED_GH_CONFIG_DIR,
        "LANG": "C",
        "LC_ALL": "C",
        "CODESPACES": os.environ.get("CODESPACES", ""),
        "CODESPACE_NAME": os.environ.get("CODESPACE_NAME", ""),
    }
    proc = subprocess.run(
        [gh_bin, "api", "--hostname", "github.com", "--include",
         "-H", "Accept: application/vnd.github+json",
         "-H", f"X-GitHub-Api-Version: {API_VERSION}",
         "--method", "GET", endpoint],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=clean,
    )
    if not proc.stdout.strip():
        stop("NO_RESPONSE")
    return parse_included(proc.stdout)


def main() -> None:
    if os.environ.get("CODESPACES") != "true" or not os.environ.get("CODESPACE_NAME"):
        stop("CODESPACES_IDENTITY")
    if os.environ.get("GH_CONFIG_DIR") != EXPECTED_GH_CONFIG_DIR:
        stop("GH_CONFIG_DIR")
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN",
                "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy",
                "SSL_CERT_FILE", "SSL_CERT_DIR", "GH_DEBUG", "DEBUG"):
        if os.environ.get(key):
            stop("PROHIBITED_ENV_" + key)
    p = pathlib.Path(EXPECTED_GH_CONFIG_DIR)
    try:
        st = p.stat()
    except Exception:
        stop("GH_CONFIG_DIR_MISSING")
    if not p.is_dir() or p.is_symlink() or st.st_uid != os.geteuid() or (st.st_mode & 0o777) != 0o700:
        stop("GH_CONFIG_DIR_IDENTITY")

    gh_bin = resolve_gh()

    status, headers, user = api_get(gh_bin, "/user")
    if status != 200 or not isinstance(user, dict) or user.get("login") != EXPECTED_LOGIN:
        stop("LOGIN")
    raw = headers.get("x-oauth-scopes")
    if raw is None:
        stop("SCOPE_HEADER_MISSING")
    scopes = {item.strip() for item in raw.split(",") if item.strip()}
    if scopes != EXPECTED_SCOPES:
        stop("SCOPE_SET_NOT_EXACT")

    status, _, repo = api_get(gh_bin, f"/repos/{EXPECTED_REPO}")
    permissions = repo.get("permissions") if status == 200 and isinstance(repo, dict) else None
    if not isinstance(permissions, dict) or permissions.get("admin") is not True:
        stop("REPOSITORY_ADMIN_REQUIRED")

    print(SUCCESS)


if __name__ == "__main__":
    main()
