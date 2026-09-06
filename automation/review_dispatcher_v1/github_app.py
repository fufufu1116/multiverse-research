from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
from typing import Any


class GitHubAppError(RuntimeError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise GitHubAppError(code)


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def app_jwt(app_id: int, private_key: str) -> str:
    if "\\n" in private_key:
        private_key = private_key.replace("\\n", "\n")

    require(shutil.which("openssl") is not None, "OPENSSL_NOT_AVAILABLE")

    now = int(time.time())
    header = b64url(
        json.dumps(
            {"alg": "RS256", "typ": "JWT"},
            separators=(",", ":"),
        ).encode()
    )
    payload = b64url(
        json.dumps(
            {
                "iat": now - 30,
                "exp": now + 540,
                "iss": str(app_id),
            },
            separators=(",", ":"),
        ).encode()
    )
    unsigned = f"{header}.{payload}"

    key_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
        ) as f:
            f.write(private_key)
            key_path = f.name
        os.chmod(key_path, 0o600)
        signature = subprocess.run(
            [
                "openssl",
                "dgst",
                "-sha256",
                "-sign",
                key_path,
            ],
            input=unsigned.encode(),
            capture_output=True,
            check=True,
        ).stdout
    finally:
        if key_path:
            try:
                os.unlink(key_path)
            except FileNotFoundError:
                pass

    return unsigned + "." + b64url(signature)


def github_json(
    method: str,
    url: str,
    token: str,
    payload: Any | None = None,
) -> Any:
    data = (
        None
        if payload is None
        else json.dumps(payload).encode()
    )
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "multiverse-fixed-review-dispatcher-v1",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read().decode()
        return json.loads(raw) if raw else None


def installation_token(
    *,
    repo: str,
    app_id: int,
    private_key: str,
) -> str:
    jwt = app_jwt(app_id, private_key)
    installation = github_json(
        "GET",
        f"https://api.github.com/repos/{repo}/installation",
        jwt,
    )
    token_result = github_json(
        "POST",
        (
            "https://api.github.com/app/installations/"
            f"{installation['id']}/access_tokens"
        ),
        jwt,
        {},
    )
    return token_result["token"]
