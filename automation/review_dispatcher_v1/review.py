from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import signal
import socket
import ssl
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable

from automation.review_dispatcher_v1.github_read_resilience_v1 import (
    github_json_read,
)
from automation.review_dispatcher_v1.model import (
    AUDITOR_APP_ID,
    AUDITOR_APP_SLUG,
    AUDITOR_LOGIN,
    LAB_APP_ID,
    LAB_APP_SLUG,
    LAB_LOGIN,
    RESULT_SCHEMA,
    ReviewContractError,
    canonical_json,
    dotted_get,
    fetch_all_pages,
    github_branch_commit_sha,
    github_comment_id,
    github_commit_tree_sha,
    github_full_pr_binding,
    issue_comment_owner_trusted,
    lane_result_comment_trusted,
    lane_result_outer_app_trusted,
    latest_exact_current_owner_request,
    require,
    resolve_public_https_target,
    required_object,
    result_marker,
    safe_repo_path,
    sha256_json,
    validate_request,
)

ARTIFACT_SCHEMA = "MULTIVERSE_FIXED_REVIEW_ARTIFACT_v1"


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(
        self,
        host: str,
        port: int,
        connect_ip: str,
        *,
        timeout: int = 45,
        context: ssl.SSLContext | None = None,
    ) -> None:
        super().__init__(
            host,
            port,
            timeout=timeout,
            context=context or ssl.create_default_context(),
        )
        self._connect_ip = connect_ip

    def connect(self) -> None:
        raw = socket.create_connection(
            (self._connect_ip, self.port),
            self.timeout,
            self.source_address,
        )
        self.sock = self._context.wrap_socket(
            raw,
            server_hostname=self.host,
        )


def github_get(url: str) -> Any:
    return github_json_read(
        url,
        user_agent="multiverse-fixed-review-runner-v1",
    )


def endpoint(
    base_url: str,
    method: str,
    path: str,
    *,
    attempts: int = 6,
) -> tuple[int, Any]:
    last: Any = None
    for attempt in range(attempts):
        host, port, addresses = resolve_public_https_target(base_url)
        connect_ip = addresses[attempt % len(addresses)]
        connection = _PinnedHTTPSConnection(
            host,
            port,
            connect_ip,
            timeout=45,
        )
        try:
            connection.request(
                method,
                path,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "multiverse-fixed-review-runner-v1",
                },
            )
            response = connection.getresponse()
            status = response.status
            raw = response.read().decode()
            if 300 <= status <= 399:
                raise ReviewContractError("HTTP_REDIRECT_DENIED")
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {"raw": raw}
            if (
                status in (502, 503, 504)
                and attempt + 1 < attempts
            ):
                last = (status, payload)
                time.sleep(3)
                continue
            return status, payload
        except ReviewContractError:
            raise
        except Exception as exc:
            last = repr(exc)
            if attempt + 1 < attempts:
                time.sleep(3)
                continue
            raise
        finally:
            connection.close()
    raise RuntimeError(f"HTTP_RETRIES_EXHAUSTED:{last!r}")


def _fresh_binding(
    job: dict[str, Any],
    fetch: Callable[[str], Any],
    checks: dict[str, str],
    findings: list[str],
) -> None:
    repo = job["repo"]
    pr_number = job["pr"]
    head = job["head"]
    tree = job["tree"]
    base = job["base"]
    main = job["main"]

    pr_raw = fetch(
        f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    )
    commit_raw = fetch(
        f"https://api.github.com/repos/{repo}/commits/{head}"
    )
    main_raw = fetch(
        f"https://api.github.com/repos/{repo}/branches/main"
    )

    def check(name: str, condition: bool, detail: str) -> None:
        if condition:
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: {detail}")

    try:
        pr = github_full_pr_binding(
            pr_raw,
            expected_number=pr_number,
            expected_head=head,
        )
        fresh_tree = github_commit_tree_sha(commit_raw)
        fresh_main = github_branch_commit_sha(main_raw)
    except ReviewContractError as exc:
        checks["fresh_binding_contract"] = "FIX_REQUIRED"
        findings.append(f"fresh_binding_contract: {exc}")
        return

    checks["fresh_binding_contract"] = "PASS"
    check("fresh_pr_head", pr["head_sha"] == head, repr(pr["head_sha"]))
    check("fresh_pr_tree", fresh_tree == tree, repr(fresh_tree))
    check("fresh_pr_base", pr["base_sha"] == base, repr(pr["base_sha"]))
    check("fresh_main", fresh_main == main, repr(fresh_main))
    check("pr_open", pr["state"] == "open", repr(pr["state"]))
    check("pr_draft", pr["draft"] is True, repr(pr["draft"]))
    check("pr_unmerged", pr["merged"] is False, repr(pr["merged"]))


def _check_secret_environment(
    checks: dict[str, str],
    findings: list[str],
) -> None:
    forbidden = (
        "DATABASE_URL",
        "RENDER_API_KEY",
        "MULTIVERSE_INDEPENDENT_LAB_PRIVATE_KEY",
        "MULTIVERSE_INDEPENDENT_AUDITOR_PRIVATE_KEY",
    )
    for name in forbidden:
        if os.environ.get(name):
            checks[f"secret_env_absent:{name}"] = "FIX_REQUIRED"
            findings.append(f"secret_env_absent:{name}: value present")
        else:
            checks[f"secret_env_absent:{name}"] = "PASS"


def _check_subtrees(
    job: dict[str, Any],
    fetch: Callable[[str], Any],
    checks: dict[str, str],
    findings: list[str],
) -> None:
    expected = job["request"]["recipe"]["subtrees"]
    if not expected:
        return

    try:
        tree_response = required_object(
            fetch(
                f"https://api.github.com/repos/{job['repo']}/git/trees/{job['tree']}?recursive=1"
            ),
            "TREE_RESPONSE_OBJECT",
        )
        items = tree_response.get("tree")
        require(isinstance(items, list), "TREE_ITEMS_LIST")
        actual: dict[str, str] = {}
        for item in items:
            require(isinstance(item, dict), "TREE_ITEM_OBJECT")
            path = item.get("path")
            sha = item.get("sha")
            require(
                isinstance(path, str) and bool(path),
                "TREE_ITEM_PATH",
            )
            require(
                isinstance(sha, str) and bool(sha),
                "TREE_ITEM_SHA",
            )
            actual[path] = sha
    except ReviewContractError as exc:
        checks["subtree_response_contract"] = "FIX_REQUIRED"
        findings.append(f"subtree_response_contract: {exc}")
        return

    checks["subtree_response_contract"] = "PASS"
    for path, sha in expected.items():
        name = f"subtree:{path}"
        if actual.get(path) == sha:
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(
                f"{name}: {actual.get(path)!r} != {sha!r}"
            )


def _check_comments(
    job: dict[str, Any],
    fetch: Callable[[str], Any],
    checks: dict[str, str],
    findings: list[str],
) -> None:
    for rule in job["request"]["recipe"]["durable_comments"]:
        cid = rule["id"]
        comment = required_object(
            fetch(
                f"https://api.github.com/repos/{job['repo']}/issues/comments/{cid}"
            ),
            "COMMENT_RESPONSE_OBJECT",
        )
        login = (comment.get("user") or {}).get("login")
        app_slug = (
            (comment.get("performed_via_github_app") or {}).get("slug")
        )
        body = comment.get("body") or ""

        if rule["login"] is not None:
            name = f"comment:{cid}:login"
            if login == rule["login"]:
                checks[name] = "PASS"
            else:
                checks[name] = "FIX_REQUIRED"
                findings.append(
                    f"{name}: {login!r} != {rule['login']!r}"
                )

        if rule["app_slug"] is not None:
            name = f"comment:{cid}:app_slug"
            lane: str | None = None
            if (
                rule["login"] == LAB_LOGIN
                and rule["app_slug"] == LAB_APP_SLUG
            ):
                lane = "LAB"
            elif (
                rule["login"] == AUDITOR_LOGIN
                and rule["app_slug"] == AUDITOR_APP_SLUG
            ):
                lane = "AUDITOR"

            if lane is not None:
                app_ok = lane_result_comment_trusted(comment, lane)
            else:
                app_ok = app_slug == rule["app_slug"]

            if app_ok:
                checks[name] = "PASS"
            else:
                checks[name] = "FIX_REQUIRED"
                findings.append(
                    f"{name}: {app_slug!r} != {rule['app_slug']!r}"
                )

        for token in rule["body_contains"]:
            name = f"comment:{cid}:contains:{token[:24]}"
            if token in body:
                checks[name] = "PASS"
            else:
                checks[name] = "FIX_REQUIRED"
                findings.append(f"{name}: missing token")


def _comment_json_block(body: str) -> dict[str, Any]:
    fence = r"\x60\x60\x60"
    match = re.search(
        fence + r"json\s*(\{.*?\})\s*" + fence,
        body,
        re.S,
    )
    if match is None:
        raise ValueError("JSON_BLOCK_MISSING")
    return json.loads(match.group(1))


def _check_auditor_upstream(
    job: dict[str, Any],
    fetch: Callable[[str], Any],
    checks: dict[str, str],
    findings: list[str],
) -> None:
    if job["lane"] != "AUDITOR":
        return

    def check(name: str, condition: bool, detail: str) -> None:
        if condition:
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: {detail}")

    upstream = job["request"]["upstream"]
    lab_comment_id = upstream["lab_pass_comment"]
    t1_comment_id = upstream["t1_comment"]

    comments = fetch_all_pages(
        fetch,
        f"https://api.github.com/repos/{job['repo']}/issues/{job['pr']}/comments",
    )
    try:
        latest_lab_request_id, latest_lab_request, _ = (
            latest_exact_current_owner_request(
                comments,
                repo=job["repo"],
                pr=job["pr"],
                lane="LAB",
                head=job["head"],
                tree=job["tree"],
                base=job["base"],
                main=job["main"],
            )
        )
        check(
            "upstream_lab_result_bound_to_latest_request",
            latest_lab_request_id > 0,
            repr(latest_lab_request_id),
        )
        check(
            "upstream_lab_request_proof_ceiling",
            latest_lab_request["proof_ceiling"]
            == job["request"]["proof_ceiling"],
            repr(latest_lab_request["proof_ceiling"]),
        )
        check(
            "upstream_lab_request_execution_state",
            latest_lab_request["execution_state"]
            == job["request"]["execution_state"],
            repr(latest_lab_request["execution_state"]),
        )
        latest_lab_request_sha256 = sha256_json(latest_lab_request)
        check(
            "upstream_lab_request_sha256",
            upstream["lab_request_sha256"] == latest_lab_request_sha256,
            (
                f"{upstream['lab_request_sha256']!r} "
                f"!= {latest_lab_request_sha256!r}"
            ),
        )
    except Exception as exc:
        checks["upstream_latest_lab_request"] = "FIX_REQUIRED"
        findings.append(f"upstream_latest_lab_request: {exc}")
        latest_lab_request_id = -1
        latest_lab_request = {}
        latest_lab_request_sha256 = ""

    lab_comment = required_object(
        fetch(
            f"https://api.github.com/repos/{job['repo']}/issues/comments/{lab_comment_id}"
        ),
        "LAB_COMMENT_RESPONSE_OBJECT",
    )
    lab_login = (lab_comment.get("user") or {}).get("login")
    lab_app = lab_comment.get("performed_via_github_app")
    check(
        "upstream_lab_login",
        lab_login == LAB_LOGIN,
        repr(lab_login),
    )
    check(
        "upstream_lab_app",
        lane_result_outer_app_trusted(lab_comment, "LAB"),
        repr(lab_app),
    )

    try:
        lab_artifact = _comment_json_block(lab_comment.get("body") or "")
    except Exception as exc:
        checks["upstream_lab_artifact"] = "FIX_REQUIRED"
        findings.append(f"upstream_lab_artifact: {exc!r}")
        lab_artifact = None

    if lab_artifact is not None:
        exact_fields = {
            "schema_version": ARTIFACT_SCHEMA,
            "result_schema": RESULT_SCHEMA,
            "lane": "LAB",
            "request_id": latest_lab_request.get("request_id"),
            "request_comment": latest_lab_request_id,
            "request_sha256": latest_lab_request_sha256,
            "mode": latest_lab_request.get("mode"),
            "verdict": "PASS",
            "findings": [],
            "reviewed_repo": job["repo"],
            "reviewed_pr": job["pr"],
            "reviewed_head": job["head"],
            "reviewed_tree": job["tree"],
            "reviewed_base": job["base"],
            "reviewed_main": job["main"],
            "proof_ceiling": job["request"]["proof_ceiling"],
            "execution_state": job["request"]["execution_state"],
        }
        for key, expected in exact_fields.items():
            actual = lab_artifact.get(key)
            check(
                f"upstream_lab_artifact:{key}",
                actual == expected,
                f"{actual!r} != {expected!r}",
            )
        producer = lab_artifact.get("producer") or {}
        check(
            "upstream_lab_artifact:producer_login",
            producer.get("github_login") == LAB_LOGIN,
            repr(producer.get("github_login")),
        )
        check(
            "upstream_lab_artifact:producer_app_id",
            producer.get("github_app_id") == LAB_APP_ID,
            repr(producer.get("github_app_id")),
        )

        marker = result_marker(
            latest_lab_request.get("request_id", ""),
            job["head"],
            latest_lab_request_id,
            latest_lab_request_sha256,
        )
        authentic_result_ids = []
        for item in comments:
            if (
                marker in (item.get("body") or "")
                and lane_result_comment_trusted(item, "LAB")
            ):
                try:
                    authentic_result_ids.append(
                        github_comment_id(
                            item,
                            "LAB_RESULT_COMMENT_ID",
                        )
                    )
                except ReviewContractError as exc:
                    findings.append(
                        f"upstream_lab_result_comment_id: {exc}"
                    )
        check(
            "upstream_lab_single_authentic_latest_result",
            authentic_result_ids == [lab_comment_id],
            repr(authentic_result_ids),
        )

    t1_comment = required_object(
        fetch(
            f"https://api.github.com/repos/{job['repo']}/issues/comments/{t1_comment_id}"
        ),
        "T1_COMMENT_RESPONSE_OBJECT",
    )
    check(
        "upstream_t1_owner",
        issue_comment_owner_trusted(t1_comment, job["repo"]),
        repr((t1_comment.get("user") or {}).get("login")),
    )
    t1_body = t1_comment.get("body") or ""
    for label, token in (
        ("lab_comment", str(lab_comment_id)),
        ("lab_request_sha256", latest_lab_request_sha256),
        ("head", job["head"]),
        ("tree", job["tree"]),
        ("base", job["base"]),
        ("main", job["main"]),
        ("pass", "PASS"),
    ):
        check(
            f"upstream_t1_binding:{label}",
            token in t1_body,
            f"missing {token!r}",
        )


def _repo_file(repo_root: Path, rel: str) -> Path:
    safe_repo_path(rel)
    root = repo_root.resolve()
    current = root
    for part in Path(rel).parts:
        current = current / part
        require(not current.is_symlink(), f"REPO_PATH_SYMLINK_DENIED:{rel}")
    try:
        resolved = current.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ReviewContractError(f"REPO_PATH_MISSING:{rel}") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ReviewContractError(f"REPO_PATH_ESCAPE:{rel}") from exc
    require(resolved.is_file(), f"REPO_PATH_NOT_FILE:{rel}")
    return resolved


def _candidate_env(repo_root: Path) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "LANG": "C",
        "LC_ALL": "C",
        "PYTHONHASHSEED": "0",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(repo_root.resolve()),
    }


def _run_candidate_process(
    argv: list[str],
    repo_root: Path,
    *,
    timeout: int = 180,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        argv,
        cwd=str(repo_root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_candidate_env(repo_root),
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
        return subprocess.CompletedProcess(
            argv,
            124,
            stdout,
            stderr + "\nCANDIDATE_PROCESS_TIMEOUT",
        )
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    return subprocess.CompletedProcess(
        argv,
        int(process.returncode or 0),
        stdout,
        stderr,
    )


def _check_source_rules(
    repo_root: Path,
    job: dict[str, Any],
    checks: dict[str, str],
    findings: list[str],
) -> None:
    for rule in job["request"]["recipe"]["source_rules"]:
        name = f"source_exists:{rule['path']}"
        try:
            path = _repo_file(repo_root, rule["path"])
            checks[name] = "PASS"
        except ReviewContractError as exc:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: {exc}")
            continue

        text = path.read_text()

        for token in rule["contains"]:
            key = f"source_contains:{rule['path']}:{token[:20]}"
            if token in text:
                checks[key] = "PASS"
            else:
                checks[key] = "FIX_REQUIRED"
                findings.append(f"{key}: missing")

        for token in rule["not_contains"]:
            key = f"source_not_contains:{rule['path']}:{token[:20]}"
            if token not in text:
                checks[key] = "PASS"
            else:
                checks[key] = "FIX_REQUIRED"
                findings.append(f"{key}: found")


def _run_unittests(
    repo_root: Path,
    job: dict[str, Any],
    checks: dict[str, str],
    findings: list[str],
) -> int:
    total = 0
    for rule in job["request"]["recipe"]["unittest_modules"]:
        module = rule["module"]
        module_path = module.replace(".", "/") + ".py"
        try:
            _repo_file(repo_root, module_path)
        except ReviewContractError as exc:
            checks[f"unittest_module_file:{module}"] = "FIX_REQUIRED"
            findings.append(f"unittest_module_file:{module}: {exc}")
            continue
        checks[f"unittest_module_file:{module}"] = "PASS"

        proc = _run_candidate_process(
            [sys.executable, "-m", "unittest", module, "-v"],
            repo_root,
        )
        if proc.stdout:
            print(proc.stdout)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)

        combined = "\n".join([proc.stdout or "", proc.stderr or ""])
        matches = re.findall(
            r"^Ran\s+(\d+)\s+tests?\s+in\s+",
            combined,
            re.M,
        )
        count = int(matches[0]) if len(matches) == 1 else -1
        if count >= 0:
            total += count

        name = f"unittest_count:{module}"
        if count == rule["count"]:
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(
                f"{name}: {count} != {rule['count']}"
            )

        name = f"unittest_result:{module}"
        if proc.returncode == 0 and count >= 0:
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(
                f"{name}: exit={proc.returncode} summary_count={count}"
            )
    return total


def _run_validators(
    repo_root: Path,
    job: dict[str, Any],
    checks: dict[str, str],
    findings: list[str],
) -> None:
    for rule in job["request"]["recipe"]["validators"]:
        name = f"validator_exit:{rule['path']}"
        try:
            path = _repo_file(repo_root, rule["path"])
        except ReviewContractError as exc:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: {exc}")
            continue
        proc = _run_candidate_process(
            [sys.executable, str(path)],
            repo_root,
        )
        if proc.stdout:
            print(proc.stdout)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)

        if proc.returncode == 0:
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(
                f"{name}: exit={proc.returncode}"
            )
            continue

        try:
            lines = [
                line
                for line in proc.stdout.splitlines()
                if line.strip()
            ]
            payload = json.loads(lines[-1])
        except Exception as exc:
            checks[f"validator_json:{rule['path']}"] = "FIX_REQUIRED"
            findings.append(
                f"validator_json:{rule['path']}: {exc!r}"
            )
            continue

        checks[f"validator_json:{rule['path']}"] = "PASS"

        for dotted, expected in rule["expect"].items():
            name = f"validator_expect:{rule['path']}:{dotted}"
            try:
                actual = dotted_get(payload, dotted)
            except Exception as exc:
                checks[name] = "FIX_REQUIRED"
                findings.append(f"{name}: {exc}")
                continue

            if actual == expected:
                checks[name] = "PASS"
            else:
                checks[name] = "FIX_REQUIRED"
                findings.append(
                    f"{name}: {actual!r} != {expected!r}"
                )


def _scan_secrets(
    repo_root: Path,
    job: dict[str, Any],
    checks: dict[str, str],
    findings: list[str],
) -> None:
    paths = job["request"]["recipe"]["secret_scan_paths"]
    patterns = job["request"]["recipe"]["forbidden_patterns"]
    for rel in paths:
        try:
            path = _repo_file(repo_root, rel)
        except ReviewContractError as exc:
            checks[f"secret_scan_exists:{rel}"] = "FIX_REQUIRED"
            findings.append(f"secret_scan_exists:{rel}: {exc}")
            continue
        checks[f"secret_scan_exists:{rel}"] = "PASS"
        text = path.read_text()
        for pattern in patterns:
            name = f"secret_scan:{rel}:{pattern[:20]}"
            if pattern not in text:
                checks[name] = "PASS"
            else:
                checks[name] = "FIX_REQUIRED"
                findings.append(f"{name}: forbidden pattern found")


def _check_json_equals(
    payload: Any,
    expected: dict[str, Any],
    prefix: str,
    checks: dict[str, str],
    findings: list[str],
) -> None:
    for dotted, value in expected.items():
        name = f"{prefix}:{dotted}"
        try:
            actual = dotted_get(payload, dotted)
        except Exception as exc:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: {exc}")
            continue

        if actual == value:
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(
                f"{name}: {actual!r} != {value!r}"
            )


def _run_http(
    job: dict[str, Any],
    checks: dict[str, str],
    findings: list[str],
    endpoint_fn: Callable[..., tuple[int, Any]],
) -> dict[str, str]:
    http = job["request"]["recipe"]["http"]
    if http is None:
        return {}

    base_url = http["base_url"]
    digests: dict[str, str] = {}
    captured_payloads: dict[str, Any] = {}

    for rule in http["get"]:
        status, payload = endpoint_fn(
            base_url,
            "GET",
            rule["path"],
        )
        name = f"http_get_status:{rule['path']}"
        if status == rule["status"]:
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(
                f"{name}: {status} != {rule['status']}"
            )

        _check_json_equals(
            payload,
            rule["json_equals"],
            f"http_get_json:{rule['path']}",
            checks,
            findings,
        )
        captured_payloads[rule["path"]] = payload

        capture = rule["capture_digest_as"]
        if capture is not None:
            digests[capture] = hashlib.sha256(
                canonical_json(payload).encode()
            ).hexdigest()

    deny = http["deny"]
    evidence_path = deny["evidence_unchanged_path"]

    before = captured_payloads.get(evidence_path)
    if before is None:
        status, before = endpoint_fn(
            base_url,
            "GET",
            evidence_path,
        )
        if status != 200:
            findings.append(
                f"http_evidence_before:{evidence_path}: status={status}"
            )
            checks[
                f"http_evidence_before:{evidence_path}"
            ] = "FIX_REQUIRED"
        else:
            checks[
                f"http_evidence_before:{evidence_path}"
            ] = "PASS"

    for method in deny["methods"]:
        status, payload = endpoint_fn(
            base_url,
            method,
            deny["path"],
            attempts=1,
        )
        name = f"http_deny_status:{method}:{deny['path']}"
        if status == deny["status"]:
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(
                f"{name}: {status} != {deny['status']}"
            )

        _check_json_equals(
            payload,
            deny["json_equals"],
            f"http_deny_json:{method}:{deny['path']}",
            checks,
            findings,
        )

    status, after = endpoint_fn(
        base_url,
        "GET",
        evidence_path,
    )
    if status == 200:
        checks[
            f"http_evidence_after:{evidence_path}"
        ] = "PASS"
    else:
        checks[
            f"http_evidence_after:{evidence_path}"
        ] = "FIX_REQUIRED"
        findings.append(
            f"http_evidence_after:{evidence_path}: status={status}"
        )

    if after == before:
        checks["http_evidence_unchanged_after_denied_methods"] = "PASS"
    else:
        checks[
            "http_evidence_unchanged_after_denied_methods"
        ] = "FIX_REQUIRED"
        findings.append(
            "http_evidence_unchanged_after_denied_methods: changed"
        )

    return digests


def run_review(
    job: dict[str, Any],
    *,
    repo_root: Path,
    fetch: Callable[[str], Any] = github_get,
    endpoint_fn: Callable[..., tuple[int, Any]] = endpoint,
) -> dict[str, Any]:
    require(job.get("schema") == "MULTIVERSE_FIXED_REVIEW_JOB_v1", "JOB_SCHEMA")
    request = job["request"]
    validate_request(request)
    require(
        job.get("request_sha256") == sha256_json(request),
        "JOB_REQUEST_SHA256",
    )

    require(job["lane"] == request["lane"], "JOB_REQUEST_LANE")
    require(job["repo"] == request["repo"], "JOB_REQUEST_REPO")
    require(job["pr"] == request["pr"], "JOB_REQUEST_PR")
    require(job["head"] == request["head"], "JOB_REQUEST_HEAD")
    require(job["tree"] == request["tree"], "JOB_REQUEST_TREE")
    require(job["base"] == request["base"], "JOB_REQUEST_BASE")
    require(job["main"] == request["main"], "JOB_REQUEST_MAIN")

    checks: dict[str, str] = {}
    findings: list[str] = []

    buildkite_commit = os.environ.get("BUILDKITE_COMMIT", "")
    local_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo_root),
        text=True,
    ).strip()

    if buildkite_commit == job["head"]:
        checks["buildkite_commit_exact"] = "PASS"
    else:
        checks["buildkite_commit_exact"] = "FIX_REQUIRED"
        findings.append(
            f"buildkite_commit_exact: {buildkite_commit!r} != {job['head']!r}"
        )

    if local_head == job["head"]:
        checks["local_head_exact"] = "PASS"
    else:
        checks["local_head_exact"] = "FIX_REQUIRED"
        findings.append(
            f"local_head_exact: {local_head!r} != {job['head']!r}"
        )

    _check_secret_environment(checks, findings)
    _fresh_binding(job, fetch, checks, findings)
    _check_auditor_upstream(job, fetch, checks, findings)
    _check_subtrees(job, fetch, checks, findings)
    _check_comments(job, fetch, checks, findings)
    _check_source_rules(repo_root, job, checks, findings)
    test_count = _run_unittests(repo_root, job, checks, findings)
    _run_validators(repo_root, job, checks, findings)
    _scan_secrets(repo_root, job, checks, findings)
    digests = _run_http(job, checks, findings, endpoint_fn)

    verdict = "PASS" if not findings else "FIX_REQUIRED"

    if job["lane"] == "LAB":
        producer_login = LAB_LOGIN
        producer_app_id = LAB_APP_ID
    else:
        producer_login = AUDITOR_LOGIN
        producer_app_id = AUDITOR_APP_ID

    artifact = {
        "schema_version": ARTIFACT_SCHEMA,
        "result_schema": RESULT_SCHEMA,
        "lane": job["lane"],
        "request_id": job["request_id"],
        "request_comment": job["request_comment"],
        "request_sha256": job["request_sha256"],
        "reviewed_repo": job["repo"],
        "reviewed_pr": job["pr"],
        "reviewed_head": job["head"],
        "reviewed_tree": job["tree"],
        "reviewed_base": job["base"],
        "reviewed_main": job["main"],
        "mode": request["mode"],
        "proof_ceiling": request["proof_ceiling"],
        "execution_state": request["execution_state"],
        "dispatcher_ref": job.get("dispatcher_ref", ""),
        "upstream": request["upstream"],
        "digests": digests,
        "test_count": test_count,
        "checks": checks,
        "findings": findings,
        "verdict": verdict,
        "producer": {
            "github_login": producer_login,
            "github_app_id": producer_app_id,
            "build_id": os.environ.get("BUILDKITE_BUILD_ID"),
            "build_number": os.environ.get("BUILDKITE_BUILD_NUMBER"),
            "build_branch": os.environ.get("BUILDKITE_BRANCH"),
            "build_commit": buildkite_commit,
        },
        "nonauthority": request["nonauthority"],
    }
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", default="review_job.json")
    parser.add_argument("--output", default="review_artifact.json")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    job = json.loads(Path(args.job).read_text())
    artifact = run_review(
        job,
        repo_root=Path(args.repo_root).resolve(),
    )
    Path(args.output).write_text(
        json.dumps(
            artifact,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(json.dumps(artifact, indent=2, sort_keys=True))

    if artifact["verdict"] != "PASS":
        print("FIX_REQUIRED")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReviewContractError as exc:
        print(f"REVIEW_FIX_REQUIRED:{exc}")
        raise SystemExit(1)