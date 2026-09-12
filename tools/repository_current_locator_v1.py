from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "MULTIVERSE_REPOSITORY_SCOPE_REGISTRY_v1"
INDEX_SCHEMA = "MULTIVERSE_REPOSITORY_INDEX_v1"
ALLOWED_KINDS = {
    "issue",
    "pull_request",
    "repo_path_on_main",
    "repo_path_on_named_branch",
}
REQUIRED_SCOPES = {
    "SOLE_CONTROL",
    "OPPORTUNITY_ENGINE",
    "KEIRIN_RESEARCH",
    "MULTIMODEL_RESEARCH",
    "SYSTEM_IMPROVEMENT",
    "COMMON_BOOTSTRAP_GOVERNANCE",
}


class LocatorValidationError(ValueError):
    pass


def _require_text(obj: dict[str, Any], key: str, context: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LocatorValidationError(f"{context}: missing/non-text {key}")
    return value


def _validate_pointer(pointer: dict[str, Any], context: str) -> None:
    if not isinstance(pointer, dict):
        raise LocatorValidationError(f"{context}: pointer must be object")
    kind = _require_text(pointer, "kind", context)
    if kind not in ALLOWED_KINDS:
        raise LocatorValidationError(f"{context}: unknown pointer kind {kind}")

    if kind in {"issue", "pull_request"}:
        locator = _require_text(pointer, "locator", context)
        if not locator.isdigit() or int(locator) <= 0:
            raise LocatorValidationError(f"{context}: invalid numeric locator")
    elif kind == "repo_path_on_main":
        _require_text(pointer, "path", context)
    elif kind == "repo_path_on_named_branch":
        _require_text(pointer, "branch", context)
        _require_text(pointer, "path", context)


def validate_registry(registry: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(registry, dict):
        raise LocatorValidationError("registry must be object")
    if registry.get("schema") != SCHEMA:
        raise LocatorValidationError("wrong schema")
    if registry.get("authority_role") != "LOCATOR_ONLY_NOT_AUTHORITY_REPLACEMENT":
        raise LocatorValidationError("locator must not claim authority")
    if registry.get("runtime") != "OFF":
        raise LocatorValidationError("runtime must remain OFF")
    if registry.get("ambiguity_rule") != "FAIL_CLOSED":
        raise LocatorValidationError("ambiguity must fail closed")

    scopes = registry.get("scopes")
    if not isinstance(scopes, list) or not scopes:
        raise LocatorValidationError("scopes must be non-empty list")

    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for i, scope in enumerate(scopes):
        context = f"scopes[{i}]"
        if not isinstance(scope, dict):
            raise LocatorValidationError(f"{context}: scope must be object")
        scope_id = _require_text(scope, "scope_id", context)
        if scope_id in seen:
            raise LocatorValidationError(f"duplicate scope_id: {scope_id}")
        seen.add(scope_id)
        _require_text(scope, "owner_label", context)

        if "primary" not in scope:
            raise LocatorValidationError(f"{context}: missing PRIMARY pointer")
        _validate_pointer(scope["primary"], f"{context}.primary")
        _require_text(scope["primary"], "verification", f"{context}.primary")

        secondary = scope.get("secondary", [])
        if not isinstance(secondary, list):
            raise LocatorValidationError(f"{context}: secondary must be list")
        for j, pointer in enumerate(secondary):
            _validate_pointer(pointer, f"{context}.secondary[{j}]")

        normalized.append(scope)

    missing = REQUIRED_SCOPES - seen
    extra = seen - REQUIRED_SCOPES
    if missing:
        raise LocatorValidationError(f"missing required scopes: {sorted(missing)}")
    if extra:
        raise LocatorValidationError(f"unknown scopes fail closed: {sorted(extra)}")

    protected = registry.get("protected_root_policy")
    if not isinstance(protected, dict):
        raise LocatorValidationError("protected_root_policy missing")
    complete = protected.get("complete_registry_available")
    state = protected.get("state")
    if complete is not True and state != "UNKNOWN_FAIL_CLOSED":
        raise LocatorValidationError("incomplete protected roots must be UNKNOWN_FAIL_CLOSED")

    return {
        "schema": SCHEMA,
        "scope_count": len(normalized),
        "scope_ids": sorted(seen),
        "runtime": "OFF",
        "authority_role": "LOCATOR_ONLY_NOT_AUTHORITY_REPLACEMENT",
        "protected_root_state": state,
        "validation": "PASS",
    }


def build_observed_index(registry: dict[str, Any], observed_main_sha: str) -> dict[str, Any]:
    summary = validate_registry(registry)
    if not isinstance(observed_main_sha, str) or len(observed_main_sha) != 40:
        raise LocatorValidationError("observed_main_sha must be 40-char Git SHA")
    try:
        int(observed_main_sha, 16)
    except ValueError as exc:
        raise LocatorValidationError("observed_main_sha must be hexadecimal") from exc

    return {
        "schema": INDEX_SCHEMA,
        "status": "OBSERVED_LOCATOR_SNAPSHOT_NON_AUTHORITY",
        "authority_role": "LOCATOR_ONLY_NOT_AUTHORITY_REPLACEMENT",
        "canonical_main_observed": observed_main_sha,
        "freshness_rule": "REVERIFY_ALL_PRIMARY_POINTERS_BEFORE_USE",
        "runtime": "OFF",
        "protected_root_state": summary["protected_root_state"],
        "current_entrypoints": [
            {
                "scope_id": scope["scope_id"],
                "owner_label": scope["owner_label"],
                "primary": scope["primary"],
            }
            for scope in registry["scopes"]
        ],
        "nonauthority": True,
        "write_effects": False,
    }


def load_registry(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise LocatorValidationError("registry JSON root must be object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate MULTIVERSE repository CURRENT locator registry")
    parser.add_argument("--registry", default="governance/MULTIVERSE_REPOSITORY_SCOPE_REGISTRY_v1.json")
    parser.add_argument("--observed-main-sha")
    parser.add_argument("--output")
    args = parser.parse_args()

    registry = load_registry(Path(args.registry))
    summary = validate_registry(registry)
    payload: dict[str, Any] = summary
    if args.observed_main_sha:
        payload = build_observed_index(registry, args.observed_main_sha)

    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
