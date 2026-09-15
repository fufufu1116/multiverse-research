from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import urllib.request
from urllib.parse import urlparse

from automation.review_dispatcher_v1.github_app import app_jwt, github_json
from automation.review_dispatcher_v1.model import LAB_APP_ID, ReviewContractError

LAB_PRIVATE_KEY_ENV = "MULTIVERSE_INDEPENDENT_LAB_PRIVATE_KEY"
AUDITOR_PRIVATE_KEY_ENV = "MULTIVERSE_INDEPENDENT_AUDITOR_PRIVATE_KEY"
LEGACY_READ_TOKEN_ENV = "MULTIVERSE_GITHUB_READ_TOKEN"
REPO = "fufufu1116/multiverse-research"
REPO_NAME = "multiverse-research"
READ_PERMISSIONS = {
    "contents": "read",
    "issues": "read",
    "pull_requests": "read",
}
_ORIGINAL_URLOPEN = urllib.request.urlopen


class BootstrapTransportError(RuntimeError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise BootstrapTransportError(code)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise BootstrapTransportError("AUTHENTICATED_READ_REDIRECT_DENIED")


def mint_read_token() -> str:
    _require(
        not os.environ.get(AUDITOR_PRIVATE_KEY_ENV),
        "CROSS_LANE_AUDITOR_PRIVATE_KEY_PRESENT",
    )
    private_key = os.environ.pop(LAB_PRIVATE_KEY_ENV, "")
    _require(bool(private_key.strip()), "LAB_PRIVATE_KEY_REQUIRED")

    jwt = app_jwt(LAB_APP_ID, private_key)
    private_key = ""

    installation = github_json(
        "GET",
        f"https://api.github.com/repos/{REPO}/installation",
        jwt,
    )
    _require(isinstance(installation, dict), "INSTALLATION_RESPONSE_OBJECT")
    installation_id = installation.get("id")
    _require(
        isinstance(installation_id, int)
        and not isinstance(installation_id, bool)
        and installation_id > 0,
        "INSTALLATION_ID",
    )

    token_result = github_json(
        "POST",
        (
            "https://api.github.com/app/installations/"
            f"{installation_id}/access_tokens"
        ),
        jwt,
        {
            "repositories": [REPO_NAME],
            "permissions": dict(READ_PERMISSIONS),
        },
    )
    _require(isinstance(token_result, dict), "TOKEN_RESPONSE_OBJECT")
    token = token_result.get("token")
    _require(isinstance(token, str) and bool(token.strip()), "READ_TOKEN")
    return token


def install_authenticated_get_transport(token: str) -> None:
    _require(isinstance(token, str) and bool(token.strip()), "READ_TOKEN")
    os.environ.pop(LEGACY_READ_TOKEN_ENV, None)
    no_redirect_opener = urllib.request.build_opener(_NoRedirect)

    def authenticated_get_only(req, *args, **kwargs):
        if isinstance(req, str):
            request = urllib.request.Request(req)
            url = req
        elif isinstance(req, urllib.request.Request):
            request = req
            url = req.full_url
        else:
            return _ORIGINAL_URLOPEN(req, *args, **kwargs)

        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or (parsed.hostname or "").lower() != "api.github.com"
        ):
            return _ORIGINAL_URLOPEN(req, *args, **kwargs)

        _require(
            request.get_method().upper() == "GET",
            "AUTHENTICATED_NON_GET_DENIED",
        )
        _require(not args, "AUTHENTICATED_POSITIONAL_ARGS_DENIED")
        _require(
            set(kwargs).issubset({"timeout"}),
            "AUTHENTICATED_URLLIB_KWARGS_DENIED",
        )
        request.add_unredirected_header(
            "Authorization",
            f"Bearer {token}",
        )
        return no_redirect_opener.open(
            request,
            timeout=kwargs.get("timeout"),
        )

    urllib.request.urlopen = authenticated_get_only


def run_dispatch(args: argparse.Namespace) -> int:
    dispatcher = importlib.import_module(
        "automation.review_dispatcher_v1.dispatcher"
    )
    job = dispatcher.discover_request(
        repo=args.repo,
        lane="LAB",
        head=args.head,
    )
    dispatcher.write_job(job, args.output)
    print(
        json.dumps(
            {
                "schema": job["schema"],
                "request_id": job["request_id"],
                "request_comment": job["request_comment"],
                "request_sha256": job["request_sha256"],
                "lane": job["lane"],
                "pr": job["pr"],
                "head": job["head"],
                "tree": job["tree"],
                "main": job["main"],
                "dispatcher_ref": job["dispatcher_ref"],
            },
            sort_keys=True,
        )
    )
    return 0


def run_review(args: argparse.Namespace) -> int:
    review = importlib.import_module(
        "automation.review_dispatcher_v1.review"
    )
    old_argv = sys.argv[:]
    try:
        sys.argv = [
            "review.py",
            "--job",
            args.job,
            "--output",
            args.output,
            "--repo-root",
            args.repo_root,
        ]
        return int(review.main())
    except ReviewContractError as exc:
        print(f"REVIEW_FIX_REQUIRED:{exc}")
        return 1
    finally:
        sys.argv = old_argv


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="phase", required=True)

    dispatch = sub.add_parser("dispatch")
    dispatch.add_argument("--repo", required=True)
    dispatch.add_argument("--head", required=True)
    dispatch.add_argument("--output", required=True)

    review = sub.add_parser("review")
    review.add_argument("--job", required=True)
    review.add_argument("--output", required=True)
    review.add_argument("--repo-root", required=True)

    args = parser.parse_args()
    token = mint_read_token()
    install_authenticated_get_transport(token)

    if args.phase == "dispatch":
        return run_dispatch(args)
    if args.phase == "review":
        return run_review(args)
    raise AssertionError("unreachable")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BootstrapTransportError as exc:
        print(f"BOOTSTRAP_FIX_REQUIRED:{exc}")
        raise SystemExit(1)
