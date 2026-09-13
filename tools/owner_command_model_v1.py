from __future__ import annotations

from datetime import datetime
from typing import Any

SCHEMA = "MULTIVERSE_OWNER_COMMAND_v1"
KINDS = {"TASK", "OWNER_GATE", "FINAL_DECISION", "DEADLINE", "STATUS", "RECOVERY"}
STATUSES = {"NOW", "NEXT", "WAITING", "BLOCKED", "READY_FOR_DECISION", "DONE"}
AUTHORITIES = {"INFORMATION_ONLY", "OWNER_GATE_REQUIRED", "OWNER_AUTHORIZED", "NONAUTHORITY"}
PRIORITIES = {"P1", "P2", "P3", "P4"}
OWNER_ACTION_KEYS = {"location", "link", "input", "action", "reply_with"}


class OwnerCommandError(ValueError):
    pass


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OwnerCommandError(f"{field}:NONEMPTY_STRING_REQUIRED")
    return value


def _parse_datetime(value: Any, field: str) -> None:
    _require_string(value, field)
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OwnerCommandError(f"{field}:INVALID_DATETIME") from exc


def validate_owner_command(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise OwnerCommandError("PAYLOAD:OBJECT_REQUIRED")
    if payload.get("schema") != SCHEMA:
        raise OwnerCommandError("schema:INVALID")
    _parse_datetime(payload.get("generated_at"), "generated_at")

    canonical = payload.get("canonical_ref")
    if not isinstance(canonical, dict):
        raise OwnerCommandError("canonical_ref:OBJECT_REQUIRED")
    if set(canonical) != {"backend", "locator", "revision"}:
        raise OwnerCommandError("canonical_ref:EXACT_KEYS_REQUIRED")
    for key in ("backend", "locator", "revision"):
        _require_string(canonical[key], f"canonical_ref.{key}")

    if payload.get("runtime") not in {"OFF", "ON"}:
        raise OwnerCommandError("runtime:INVALID")

    items = payload.get("items")
    if not isinstance(items, list):
        raise OwnerCommandError("items:ARRAY_REQUIRED")

    seen: set[str] = set()
    for index, item in enumerate(items):
        prefix = f"items[{index}]"
        if not isinstance(item, dict):
            raise OwnerCommandError(f"{prefix}:OBJECT_REQUIRED")
        required = {"id", "kind", "title", "lane", "status", "owner_action_required", "authority", "evidence_refs"}
        missing = sorted(required - set(item))
        if missing:
            raise OwnerCommandError(f"{prefix}:MISSING:{','.join(missing)}")

        item_id = _require_string(item["id"], f"{prefix}.id")
        if item_id in seen:
            raise OwnerCommandError(f"{prefix}.id:DUPLICATE")
        seen.add(item_id)
        _require_string(item["title"], f"{prefix}.title")
        _require_string(item["lane"], f"{prefix}.lane")

        if item["kind"] not in KINDS:
            raise OwnerCommandError(f"{prefix}.kind:INVALID")
        if item["status"] not in STATUSES:
            raise OwnerCommandError(f"{prefix}.status:INVALID")
        if item["authority"] not in AUTHORITIES:
            raise OwnerCommandError(f"{prefix}.authority:INVALID")
        if "priority" in item and item["priority"] not in PRIORITIES:
            raise OwnerCommandError(f"{prefix}.priority:INVALID")
        if not isinstance(item["owner_action_required"], bool):
            raise OwnerCommandError(f"{prefix}.owner_action_required:BOOLEAN_REQUIRED")

        refs = item["evidence_refs"]
        if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs):
            raise OwnerCommandError(f"{prefix}.evidence_refs:STRING_ARRAY_REQUIRED")

        if item["owner_action_required"]:
            action = item.get("owner_action")
            if not isinstance(action, dict):
                raise OwnerCommandError(f"{prefix}.owner_action:REQUIRED")
            missing_action = sorted(OWNER_ACTION_KEYS - set(action))
            if missing_action:
                raise OwnerCommandError(f"{prefix}.owner_action:MISSING:{','.join(missing_action)}")
            for key in OWNER_ACTION_KEYS:
                if not isinstance(action[key], str):
                    raise OwnerCommandError(f"{prefix}.owner_action.{key}:STRING_REQUIRED")
        elif "owner_action" in item and item["owner_action"] is not None:
            raise OwnerCommandError(f"{prefix}.owner_action:FORBIDDEN_WITHOUT_OWNER_ACTION")

    return payload


def owner_visible_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    validate_owner_command(payload)
    return [
        item for item in payload["items"]
        if item["owner_action_required"] or item["kind"] in {"FINAL_DECISION", "DEADLINE"}
    ]
