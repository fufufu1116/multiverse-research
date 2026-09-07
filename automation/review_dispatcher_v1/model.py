from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import socket
from pathlib import PurePosixPath
from typing import Any, Callable
from urllib.parse import urlparse

REQUEST_SCHEMA = "MULTIVERSE_REVIEW_REQUEST_v1"
RESULT_SCHEMA = "MULTIVERSE_FIXED_REVIEW_RESULT_v1"
T2_SCHEMA = "MULTIVERSE_FIXED_T2_RESULT_v1"
REQUEST_MARKER = "<!-- MULTIVERSE_REVIEW_REQUEST_V1 -->"
RESULT_MARKER_PREFIX = "<!-- MULTIVERSE_FIXED_REVIEW_RESULT_V1:"
T2_MARKER_PREFIX = "<!-- MULTIVERSE_FIXED_T2_V1:"

LANES = {"LAB", "AUDITOR"}
MODES = {"REPOSITORY_ONLY", "PUBLIC_HTTP_NO_EFFECT"}

LAB_LOGIN = "multiverse-independent-lab[bot]"
LAB_APP_ID = 4819755
AUDITOR_LOGIN = "multiverse-independent-auditor[bot]"
AUDITOR_APP_ID = 4821179
LAB_APP_SLUG = "multiverse-independent-lab"
AUDITOR_APP_SLUG = "multiverse-independent-auditor"

REQUEST_KEYS = {
    "schema", "request_id", "lane", "mode", "repo", "pr",
    "head", "tree", "base", "main", "proof_ceiling",
    "execution_state", "supersedes_request_sha256",
    "recipe", "upstream", "nonauthority",
}

RECIPE_KEYS = {
    "subtrees", "durable_comments", "source_rules",
    "unittest_modules", "validators", "secret_scan_paths",
    "forbidden_patterns", "http",
}

NONAUTHORITY_KEYS = {
    "provider_resource_mutation", "deploy", "database_mutation",
    "provider_effect_enablement", "runtime_activation_bridge_enablement",
    "runtime_activation", "production_credentials", "production_deployment",
    "protected_data", "live_business_effect", "additional_spend", "merge",
    "main_mutation", "ruleset_mutation", "workflow_dispatch_rerun",
}

FORBIDDEN_RECIPE_KEY_FRAGMENTS = {
    "shell", "command", "yaml", "python", "script",
    "token", "password", "credential", "private_key",
}


class ReviewContractError(RuntimeError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ReviewContractError(code)


def issue_comment_owner_trusted(
    comment: dict[str, Any],
    repo: str,
) -> bool:
    owner = repo.split("/", 1)[0]
    return (comment.get("user") or {}).get("login") == owner


def lane_result_comment_trusted(
    comment: dict[str, Any],
    lane: str,
) -> bool:
    if lane == "LAB":
        expected_login = LAB_LOGIN
        expected_app = LAB_APP_SLUG
    elif lane == "AUDITOR":
        expected_login = AUDITOR_LOGIN
        expected_app = AUDITOR_APP_SLUG
    else:
        return False

    user = comment.get("user") or {}
    login = user.get("login")
    user_type = user.get("type")
    if login != expected_login or user_type != "Bot":
        return False

    app = comment.get("performed_via_github_app")
    if app is None:
        return True
    if not isinstance(app, dict):
        return False
    return app.get("slug") == expected_app


def fetch_all_pages(
    fetch: Callable[[str], Any],
    url: str,
    *,
    max_pages: int = 100,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    separator = "&" if "?" in url else "?"
    for page in range(1, max_pages + 1):
        batch = fetch(
            f"{url}{separator}per_page=100&page={page}"
        )
        require(isinstance(batch, list), "PAGINATED_RESPONSE_NOT_LIST")
        items.extend(batch)
        if len(batch) < 100:
            return items
    raise ReviewContractError("PAGINATION_LIMIT_EXCEEDED")


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def sha40(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(c in "0123456789abcdef" for c in value)
    )


def sha256_hex(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def required_object(value: Any, code: str) -> dict[str, Any]:
    require(isinstance(value, dict), code)
    return value


def required_positive_int(value: Any, code: str) -> int:
    require(
        isinstance(value, int)
        and not isinstance(value, bool)
        and value > 0,
        code,
    )
    return value


def required_sha40(value: Any, code: str) -> str:
    require(sha40(value), code)
    return value


def required_nonempty_str(value: Any, code: str) -> str:
    require(isinstance(value, str) and bool(value), code)
    return value


def github_full_pr_binding(
    payload: Any,
    *,
    expected_number: int | None = None,
    expected_head: str | None = None,
) -> dict[str, Any]:
    pr = required_object(payload, "PR_RESPONSE_OBJECT")

    number = required_positive_int(pr.get("number"), "PR_NUMBER")
    if expected_number is not None:
        require(number == expected_number, "PR_NUMBER_DRIFT")

    state = required_nonempty_str(pr.get("state"), "PR_STATE_STRING")
    require(state == "open", "PR_NOT_OPEN")

    draft = pr.get("draft")
    require(isinstance(draft, bool), "PR_DRAFT_BOOL")
    require(draft is True, "PR_NOT_DRAFT")

    merged = pr.get("merged")
    require(isinstance(merged, bool), "PR_MERGED_BOOL")
    require(merged is False, "PR_ALREADY_MERGED")

    head_obj = required_object(pr.get("head"), "PR_HEAD_OBJECT")
    head_sha = required_sha40(head_obj.get("sha"), "PR_HEAD_SHA")
    if expected_head is not None:
        require(head_sha == expected_head, "PR_HEAD_DRIFT")
    head_ref = required_nonempty_str(head_obj.get("ref"), "PR_HEAD_REF")

    base_obj = required_object(pr.get("base"), "PR_BASE_OBJECT")
    base_sha = required_sha40(base_obj.get("sha"), "PR_BASE_SHA")

    return {
        "number": number,
        "state": state,
        "draft": draft,
        "merged": merged,
        "head_sha": head_sha,
        "head_ref": head_ref,
        "base_sha": base_sha,
    }


def github_commit_tree_sha(payload: Any) -> str:
    commit = required_object(payload, "COMMIT_RESPONSE_OBJECT")
    commit_meta = required_object(
        commit.get("commit"),
        "COMMIT_METADATA_OBJECT",
    )
    tree_obj = required_object(
        commit_meta.get("tree"),
        "COMMIT_TREE_OBJECT",
    )
    return required_sha40(tree_obj.get("sha"), "COMMIT_TREE_SHA")


def github_branch_commit_sha(payload: Any) -> str:
    branch = required_object(payload, "BRANCH_RESPONSE_OBJECT")
    commit = required_object(
        branch.get("commit"),
        "BRANCH_COMMIT_OBJECT",
    )
    return required_sha40(commit.get("sha"), "BRANCH_COMMIT_SHA")


def github_comment_id(payload: Any, code: str = "COMMENT_ID") -> int:
    comment = required_object(payload, "COMMENT_RESPONSE_OBJECT")
    return required_positive_int(comment.get("id"), code)


def safe_repo_path(value: Any) -> str:
    require(isinstance(value, str) and bool(value), "PATH_REQUIRED")
    p = PurePosixPath(value)
    require(not p.is_absolute(), "ABSOLUTE_PATH_DENIED")
    require(".." not in p.parts, "PATH_TRAVERSAL_DENIED")
    require("\x00" not in value, "PATH_NUL_DENIED")
    return value


def _address_allowed(ip: ipaddress._BaseAddress) -> bool:
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_public_https_url(value: Any) -> str:
    require(isinstance(value, str) and bool(value), "URL_REQUIRED")
    parsed = urlparse(value)
    require(parsed.scheme == "https", "HTTPS_REQUIRED")
    require(bool(parsed.hostname), "URL_HOST_REQUIRED")
    require(
        parsed.username is None and parsed.password is None,
        "URL_USERINFO_DENIED",
    )
    require(not parsed.query and not parsed.fragment, "URL_QUERY_FRAGMENT_DENIED")
    require(parsed.path in ("", "/"), "URL_BASE_PATH_DENIED")
    host = (parsed.hostname or "").lower()
    require(host not in {"localhost", "localhost.localdomain"}, "LOCALHOST_DENIED")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        require(_address_allowed(ip), "PRIVATE_OR_SPECIAL_IP_DENIED")
    return value


def resolve_public_https_target(
    value: Any,
) -> tuple[str, int, tuple[str, ...]]:
    value = validate_public_https_url(value)
    parsed = urlparse(value)
    host = parsed.hostname or ""
    port = parsed.port or 443
    try:
        infos = socket.getaddrinfo(
            host,
            port,
            type=socket.SOCK_STREAM,
        )
    except OSError as exc:
        raise ReviewContractError("URL_DNS_RESOLUTION_FAILED") from exc

    addresses = {
        item[4][0].split("%", 1)[0]
        for item in infos
        if item and len(item) >= 5 and item[4]
    }
    require(bool(addresses), "URL_DNS_EMPTY")
    for raw in addresses:
        ip = ipaddress.ip_address(raw)
        require(_address_allowed(ip), "PRIVATE_OR_SPECIAL_DNS_IP_DENIED")
    return host, port, tuple(sorted(addresses))


def resolve_public_https_url(value: Any) -> str:
    resolve_public_https_target(value)
    return value


def validate_http_path(value: Any) -> str:
    require(isinstance(value, str) and value.startswith("/"), "HTTP_PATH")
    require(not value.startswith("//"), "HTTP_NETWORK_PATH_DENIED")
    require("\x00" not in value, "HTTP_PATH_NUL_DENIED")
    require("?" not in value and "#" not in value, "HTTP_PATH_QUERY_FRAGMENT_DENIED")
    require("\\" not in value, "HTTP_PATH_BACKSLASH_DENIED")
    return value


def _scan_recipe_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            low = str(key).lower()
            for fragment in FORBIDDEN_RECIPE_KEY_FRAGMENTS:
                require(fragment not in low, f"FORBIDDEN_RECIPE_KEY:{key}")
            _scan_recipe_keys(child)
    elif isinstance(value, list):
        for child in value:
            _scan_recipe_keys(child)


def _validate_json_equals(value: Any, code: str) -> None:
    require(isinstance(value, dict), code)
    for key in value:
        require(isinstance(key, str) and bool(key), f"{code}_KEY")


def validate_request(request: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(request, dict), "REQUEST_OBJECT")
    require(set(request) == REQUEST_KEYS, "REQUEST_SCHEMA_KEYS")
    require(request["schema"] == REQUEST_SCHEMA, "REQUEST_SCHEMA_VERSION")

    rid = request["request_id"]
    require(
        isinstance(rid, str)
        and bool(re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,127}", rid)),
        "REQUEST_ID",
    )

    require(request["lane"] in LANES, "REQUEST_LANE")
    require(request["mode"] in MODES, "REQUEST_MODE")
    require(
        isinstance(request["repo"], str)
        and request["repo"].count("/") == 1,
        "REQUEST_REPO",
    )
    require(
        isinstance(request["pr"], int)
        and not isinstance(request["pr"], bool)
        and request["pr"] > 0,
        "REQUEST_PR",
    )

    for key in ("head", "tree", "base", "main"):
        require(sha40(request[key]), f"REQUEST_{key.upper()}")

    for key in ("proof_ceiling", "execution_state"):
        require(
            isinstance(request[key], str) and bool(request[key]),
            f"REQUEST_{key.upper()}",
        )

    supersedes = request["supersedes_request_sha256"]
    require(
        supersedes is None or sha256_hex(supersedes),
        "REQUEST_SUPERSEDES_SHA256",
    )

    nonauth = request["nonauthority"]
    require(
        isinstance(nonauth, dict)
        and set(nonauth) == NONAUTHORITY_KEYS,
        "NONAUTHORITY_SCHEMA",
    )
    for key, value in nonauth.items():
        require(value is False, f"NONAUTHORITY_NOT_FALSE:{key}")

    upstream = request["upstream"]
    require(isinstance(upstream, dict), "UPSTREAM_OBJECT")
    if request["lane"] == "LAB":
        require(upstream == {}, "LAB_UPSTREAM_MUST_BE_EMPTY")
    else:
        require(
            set(upstream)
            == {"lab_pass_comment", "lab_request_sha256", "t1_comment"},
            "AUDITOR_UPSTREAM_SCHEMA",
        )
        for key in ("lab_pass_comment", "t1_comment"):
            require(
                isinstance(upstream[key], int)
                and not isinstance(upstream[key], bool)
                and upstream[key] > 0,
                f"AUDITOR_UPSTREAM_{key.upper()}",
            )
        require(
            sha256_hex(upstream["lab_request_sha256"]),
            "AUDITOR_UPSTREAM_LAB_REQUEST_SHA256",
        )

    recipe = request["recipe"]
    require(isinstance(recipe, dict), "RECIPE_OBJECT")
    require(set(recipe) == RECIPE_KEYS, "RECIPE_SCHEMA_KEYS")
    _scan_recipe_keys(recipe)

    subtrees = recipe["subtrees"]
    require(isinstance(subtrees, dict), "SUBTREES_OBJECT")
    for path, expected in subtrees.items():
        safe_repo_path(path)
        require(sha40(expected), f"SUBTREE_SHA:{path}")

    comments = recipe["durable_comments"]
    require(isinstance(comments, list), "COMMENTS_LIST")
    for item in comments:
        require(
            isinstance(item, dict)
            and set(item)
            == {"id", "login", "app_slug", "body_contains"},
            "COMMENT_RULE_SCHEMA",
        )
        require(
            isinstance(item["id"], int)
            and not isinstance(item["id"], bool)
            and item["id"] > 0,
            "COMMENT_ID",
        )
        require(
            item["login"] is None or isinstance(item["login"], str),
            "COMMENT_LOGIN",
        )
        require(
            item["app_slug"] is None or isinstance(item["app_slug"], str),
            "COMMENT_APP_SLUG",
        )
        require(isinstance(item["body_contains"], list), "COMMENT_BODY_CONTAINS")
        for token in item["body_contains"]:
            require(isinstance(token, str) and bool(token), "COMMENT_BODY_TOKEN")

    source_rules = recipe["source_rules"]
    require(isinstance(source_rules, list), "SOURCE_RULES_LIST")
    for item in source_rules:
        require(
            isinstance(item, dict)
            and set(item) == {"path", "contains", "not_contains"},
            "SOURCE_RULE_SCHEMA",
        )
        safe_repo_path(item["path"])
        for key in ("contains", "not_contains"):
            require(isinstance(item[key], list), f"SOURCE_{key.upper()}")
            for token in item[key]:
                require(isinstance(token, str) and bool(token), "SOURCE_TOKEN")

    modules = recipe["unittest_modules"]
    require(isinstance(modules, list), "UNITTEST_MODULES_LIST")
    for item in modules:
        require(
            isinstance(item, dict)
            and set(item) == {"module", "count"},
            "UNITTEST_RULE_SCHEMA",
        )
        require(
            isinstance(item["module"], str)
            and bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", item["module"])),
            "UNITTEST_MODULE",
        )
        require(
            isinstance(item["count"], int)
            and not isinstance(item["count"], bool)
            and item["count"] >= 0,
            "UNITTEST_COUNT",
        )

    validators = recipe["validators"]
    require(isinstance(validators, list), "VALIDATORS_LIST")
    for item in validators:
        require(
            isinstance(item, dict)
            and set(item) == {"path", "expect"},
            "VALIDATOR_RULE_SCHEMA",
        )
        safe_repo_path(item["path"])
        require(isinstance(item["expect"], dict), "VALIDATOR_EXPECT")

    scan_paths = recipe["secret_scan_paths"]
    require(isinstance(scan_paths, list), "SECRET_SCAN_PATHS")
    for path in scan_paths:
        safe_repo_path(path)

    patterns = recipe["forbidden_patterns"]
    require(isinstance(patterns, list), "FORBIDDEN_PATTERNS")
    for pattern in patterns:
        require(isinstance(pattern, str) and bool(pattern), "FORBIDDEN_PATTERN")

    http = recipe["http"]
    if request["mode"] == "REPOSITORY_ONLY":
        require(http is None, "REPOSITORY_HTTP_MUST_BE_NULL")
    else:
        require(isinstance(http, dict), "HTTP_OBJECT")
        require(set(http) == {"base_url", "get", "deny"}, "HTTP_SCHEMA_KEYS")
        validate_public_https_url(http["base_url"])

        gets = http["get"]
        require(isinstance(gets, list) and bool(gets), "HTTP_GET_LIST")
        for item in gets:
            require(
                isinstance(item, dict)
                and set(item)
                == {"path", "status", "json_equals", "capture_digest_as"},
                "HTTP_GET_SCHEMA",
            )
            validate_http_path(item["path"])
            require(
                isinstance(item["status"], int)
                and 100 <= item["status"] <= 599,
                "HTTP_GET_STATUS",
            )
            _validate_json_equals(item["json_equals"], "HTTP_GET_JSON_EQUALS")
            require(
                item["capture_digest_as"] is None
                or (
                    isinstance(item["capture_digest_as"], str)
                    and bool(item["capture_digest_as"])
                ),
                "HTTP_CAPTURE_DIGEST_AS",
            )

        deny = http["deny"]
        require(
            isinstance(deny, dict)
            and set(deny)
            == {
                "path",
                "methods",
                "status",
                "json_equals",
                "evidence_unchanged_path",
            },
            "HTTP_DENY_SCHEMA",
        )
        validate_http_path(deny["path"])
        require(
            isinstance(deny["methods"], list)
            and bool(deny["methods"]),
            "HTTP_DENY_METHODS",
        )
        allowed_methods = {"POST", "PUT", "PATCH", "DELETE"}
        require(
            set(deny["methods"]).issubset(allowed_methods),
            "HTTP_DENY_METHOD_NOT_ALLOWED",
        )
        require(
            len(set(deny["methods"])) == len(deny["methods"]),
            "HTTP_DENY_METHOD_DUPLICATE",
        )
        require(
            isinstance(deny["status"], int)
            and 100 <= deny["status"] <= 599,
            "HTTP_DENY_STATUS",
        )
        _validate_json_equals(deny["json_equals"], "HTTP_DENY_JSON_EQUALS")
        validate_http_path(deny["evidence_unchanged_path"])

    return request


def parse_request_from_comment(body: str) -> dict[str, Any] | None:
    if REQUEST_MARKER not in body:
        return None
    fence = r"\x60\x60\x60"
    pattern = (
        r"<!-- MULTIVERSE_REVIEW_REQUEST_V1 -->.*?"
        + fence
        + r"json\s*(\{.*?\})\s*"
        + fence
    )
    match = re.search(pattern, body, re.S)
    require(match is not None, "REQUEST_JSON_BLOCK_MISSING")
    request = json.loads(match.group(1))
    require(isinstance(request, dict), "REQUEST_OBJECT")
    return request


def extract_request_from_comment(body: str) -> dict[str, Any] | None:
    request = parse_request_from_comment(body)
    if request is None:
        return None
    validate_request(request)
    return request


def exact_current_owner_requests(
    comments: list[dict[str, Any]],
    *,
    repo: str,
    pr: int,
    lane: str,
    head: str,
    tree: str,
    base: str,
    main: str,
) -> list[tuple[int, dict[str, Any], dict[str, Any]]]:
    candidates: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    for comment in comments:
        body = comment.get("body") or ""
        if REQUEST_MARKER not in body:
            continue
        if not issue_comment_owner_trusted(comment, repo):
            continue
        request = parse_request_from_comment(body)
        if request is None:
            continue

        envelope_keys = ("lane", "repo", "pr", "head", "tree", "base", "main")
        if not all(key in request for key in envelope_keys):
            raise ReviewContractError("OWNER_REQUEST_ENVELOPE_INCOMPLETE")

        if (
            request["lane"] == lane
            and request["repo"] == repo
            and request["pr"] == pr
            and request["head"] == head
            and request["tree"] == tree
            and request["base"] == base
            and request["main"] == main
        ):
            validate_request(request)
            candidates.append((int(comment["id"]), request, comment))

    candidates.sort(key=lambda item: item[0])

    seen_ids: set[str] = set()
    previous_sha256: str | None = None
    for comment_id, request, _ in candidates:
        rid = request["request_id"]
        require(rid not in seen_ids, f"DUPLICATE_EXACT_REQUEST_ID:{rid}")
        seen_ids.add(rid)
        supersedes = request["supersedes_request_sha256"]
        require(
            supersedes == previous_sha256,
            (
                "SAME_HEAD_SUPERSESSION_CHAIN_INVALID:"
                f"{comment_id}:{supersedes!r}!={previous_sha256!r}"
            ),
        )
        previous_sha256 = sha256_json(request)

    candidates.reverse()
    return candidates


def latest_exact_current_owner_request(
    comments: list[dict[str, Any]],
    *,
    repo: str,
    pr: int,
    lane: str,
    head: str,
    tree: str,
    base: str,
    main: str,
) -> tuple[int, dict[str, Any], dict[str, Any]]:
    candidates = exact_current_owner_requests(
        comments,
        repo=repo,
        pr=pr,
        lane=lane,
        head=head,
        tree=tree,
        base=base,
        main=main,
    )
    require(bool(candidates), f"NO_EXACT_CURRENT_{lane}_REQUEST")
    return candidates[0]


def dotted_get(value: Any, dotted: str) -> Any:
    current = value
    if dotted == "":
        return current
    for part in dotted.split("."):
        if isinstance(current, dict):
            require(part in current, f"JSON_PATH_MISSING:{dotted}")
            current = current[part]
        elif isinstance(current, list):
            require(part.isdigit(), f"JSON_LIST_INDEX:{dotted}")
            idx = int(part)
            require(0 <= idx < len(current), f"JSON_LIST_RANGE:{dotted}")
            current = current[idx]
        else:
            raise ReviewContractError(f"JSON_PATH_NONCONTAINER:{dotted}")
    return current


def result_marker(
    request_id: str,
    head: str,
    request_comment: int,
    request_sha256: str,
) -> str:
    require(sha256_hex(request_sha256), "RESULT_MARKER_REQUEST_SHA256")
    return (
        RESULT_MARKER_PREFIX
        + request_id
        + ":"
        + head
        + ":"
        + str(request_comment)
        + ":"
        + request_sha256
        + ":"
    )


def t2_marker(
    request_id: str,
    head: str,
    auditor_comment: int,
    request_sha256: str,
) -> str:
    require(sha256_hex(request_sha256), "T2_MARKER_REQUEST_SHA256")
    return (
        T2_MARKER_PREFIX
        + request_id
        + ":"
        + head
        + ":"
        + str(auditor_comment)
        + ":"
        + request_sha256
        + ":"
    )