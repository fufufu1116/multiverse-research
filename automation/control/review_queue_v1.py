from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "MULTIVERSE_REVIEW_QUEUE_v1"
ITEM_SCHEMA = "MULTIVERSE_REVIEW_QUEUE_ITEM_v1"
STATES = {
    "WAITING",
    "OWNER_GATE_REQUIRED",
    "AUTHORIZED",
    "RUNNING",
    "CONSUMED",
    "PASS",
    "FAIL",
    "BLOCKED",
    "SUPERSEDED",
}
REVIEW_TYPES = {"LAB", "AUDITOR"}
ACTIVE_RESOURCE_STATES = {"AUTHORIZED", "RUNNING", "CONSUMED"}


class QueueContractError(ValueError):
    pass


def require(cond: bool, code: str) -> None:
    if not cond:
        raise QueueContractError(code)


def text(obj: dict[str, Any], key: str) -> str:
    v = obj.get(key)
    require(isinstance(v, str) and bool(v.strip()), f"INVALID_OR_MISSING:{key}")
    return v.strip()


def integer(obj: dict[str, Any], key: str, minimum: int = 0) -> int:
    v = obj.get(key)
    require(isinstance(v, int) and not isinstance(v, bool) and v >= minimum, f"INVALID_OR_MISSING:{key}")
    return v


def queue_id_for(item: dict[str, Any]) -> str:
    canonical = {
        "review_type": item["review_type"],
        "pr": item["pr"],
        "branch": item["branch"],
        "head": item["head"],
        "tree": item["tree"],
        "base": item["base"],
        "main": item["main"],
        "request_id": item["request_id"],
        "request_sha256": item["request_sha256"],
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return "rq-" + hashlib.sha256(raw).hexdigest()[:24]


def _validate_result_binding(item: dict[str, Any], result: dict[str, Any], verdict: str) -> None:
    require(result.get("request_id") == item["request_id"], "RESULT_REQUEST_ID_MISMATCH")
    require(result.get("request_sha256") == item["request_sha256"], "RESULT_REQUEST_SHA_MISMATCH")
    require(result.get("head") == item["head"], "RESULT_HEAD_MISMATCH")
    require(result.get("tree") == item["tree"], "RESULT_TREE_MISMATCH")
    require(result.get("review_type") == item["review_type"], "RESULT_REVIEW_TYPE_MISMATCH")
    require(result.get("verdict") == verdict, "RESULT_VERDICT_MISMATCH")


def validate_item(item: dict[str, Any]) -> None:
    require(item.get("schema") == ITEM_SCHEMA, "INVALID_ITEM_SCHEMA")
    review_type = text(item, "review_type")
    require(review_type in REVIEW_TYPES, "INVALID_REVIEW_TYPE")
    state = text(item, "state")
    require(state in STATES, "INVALID_STATE")
    integer(item, "pr", 1)
    integer(item, "created_seq", 0)
    for key in ("lane", "branch", "head", "tree", "base", "main", "request_id", "request_sha256", "gate_ref"):
        text(item, key)
    priority = integer(item, "priority", 0)
    require(priority <= 1000, "PRIORITY_TOO_HIGH")
    deps = item.get("depends_on", [])
    require(isinstance(deps, list) and all(isinstance(x, str) and x for x in deps), "INVALID_DEPENDS_ON")
    require(len(deps) == len(set(deps)), "DUPLICATE_DEPENDENCY")
    consumed = item.get("one_shot_consumed")
    require(isinstance(consumed, bool), "ONE_SHOT_CONSUMED_MUST_BE_BOOL")
    expected = queue_id_for(item)
    require(item.get("queue_id") == expected, "QUEUE_ID_BINDING_MISMATCH")
    if state in {"RUNNING", "CONSUMED", "PASS", "FAIL"}:
        require(consumed, f"STATE_REQUIRES_CONSUMED:{state}")
    if state in {"WAITING", "OWNER_GATE_REQUIRED", "AUTHORIZED"}:
        require(not consumed, f"PREBUILD_STATE_CANNOT_BE_CONSUMED:{state}")
    if state in {"PASS", "FAIL"}:
        result = item.get("result")
        require(isinstance(result, dict), "TERMINAL_REVIEW_REQUIRES_RESULT")
        _validate_result_binding(item, result, state)


def validate_queue(queue: dict[str, Any]) -> None:
    require(queue.get("schema") == SCHEMA, "INVALID_QUEUE_SCHEMA")
    require(queue.get("runtime") == "OFF", "RUNTIME_MUST_BE_OFF")
    require(queue.get("exclusive_review_resources") is True, "EXCLUSIVE_RESOURCES_REQUIRED")
    items = queue.get("items")
    require(isinstance(items, list), "ITEMS_MUST_BE_LIST")
    ids: set[str] = set()
    envelope_keys: set[tuple[str, str]] = set()
    for item in items:
        require(isinstance(item, dict), "ITEM_MUST_BE_OBJECT")
        validate_item(item)
        qid = item["queue_id"]
        require(qid not in ids, f"DUPLICATE_QUEUE_ID:{qid}")
        ids.add(qid)
        env = (item["review_type"], item["request_sha256"])
        require(env not in envelope_keys, f"DUPLICATE_REVIEW_ENVELOPE:{env[0]}:{env[1]}")
        envelope_keys.add(env)
    for item in items:
        for dep in item.get("depends_on", []):
            require(dep in ids, f"UNKNOWN_DEPENDENCY:{dep}")
            require(dep != item["queue_id"], "SELF_DEPENDENCY")
    active_by_resource: dict[str, list[str]] = {"LAB": [], "AUDITOR": []}
    for item in items:
        if item["state"] in ACTIVE_RESOURCE_STATES:
            active_by_resource[item["review_type"]].append(item["queue_id"])
    for resource, active in active_by_resource.items():
        require(len(active) <= 1, f"RESOURCE_COLLISION:{resource}:{','.join(active)}")


def _deps_satisfied(item: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> bool:
    return all(by_id[dep]["state"] == "PASS" for dep in item.get("depends_on", []))


def select_next(queue: dict[str, Any], review_type: str) -> dict[str, Any] | None:
    validate_queue(queue)
    require(review_type in REVIEW_TYPES, "INVALID_REVIEW_TYPE")
    items = queue["items"]
    if any(i["review_type"] == review_type and i["state"] in ACTIVE_RESOURCE_STATES for i in items):
        return None
    by_id = {i["queue_id"]: i for i in items}
    eligible = [
        i for i in items
        if i["review_type"] == review_type
        and i["state"] in {"WAITING", "OWNER_GATE_REQUIRED"}
        and not i["one_shot_consumed"]
        and _deps_satisfied(i, by_id)
    ]
    if not eligible:
        return None
    eligible.sort(key=lambda i: (-i["priority"], i["created_seq"], i["queue_id"]))
    return eligible[0]


def authorize(queue: dict[str, Any], queue_id: str) -> dict[str, Any]:
    validate_queue(queue)
    item = next((i for i in queue["items"] if i["queue_id"] == queue_id), None)
    require(item is not None, "QUEUE_ITEM_NOT_FOUND")
    require(item["state"] in {"WAITING", "OWNER_GATE_REQUIRED"}, "ITEM_NOT_AUTHORIZABLE")
    selected = select_next(queue, item["review_type"])
    require(selected is not None and selected["queue_id"] == queue_id, "ITEM_NOT_ARBITRATION_WINNER")
    item["state"] = "AUTHORIZED"
    validate_queue(queue)
    return item


def consume_on_build_create(queue: dict[str, Any], queue_id: str, build_ref: str) -> dict[str, Any]:
    validate_queue(queue)
    item = next((i for i in queue["items"] if i["queue_id"] == queue_id), None)
    require(item is not None, "QUEUE_ITEM_NOT_FOUND")
    require(item["state"] == "AUTHORIZED", "ITEM_NOT_AUTHORIZED")
    require(not item["one_shot_consumed"], "ONE_SHOT_ALREADY_CONSUMED")
    require(isinstance(build_ref, str) and build_ref.strip(), "BUILD_REF_REQUIRED")
    item["one_shot_consumed"] = True
    item["state"] = "CONSUMED"
    item["build_ref"] = build_ref.strip()
    validate_queue(queue)
    return item


def record_result(queue: dict[str, Any], queue_id: str, result: dict[str, Any]) -> dict[str, Any]:
    validate_queue(queue)
    item = next((i for i in queue["items"] if i["queue_id"] == queue_id), None)
    require(item is not None, "QUEUE_ITEM_NOT_FOUND")
    require(item["state"] in {"CONSUMED", "RUNNING"}, "RESULT_BEFORE_CONSUMPTION")
    verdict = result.get("verdict")
    require(verdict in {"PASS", "FAIL"}, "INVALID_RESULT_VERDICT")
    _validate_result_binding(item, result, verdict)
    item["result"] = dict(result)
    item["state"] = verdict
    validate_queue(queue)
    return item


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("queue")
    parser.add_argument("--select", choices=sorted(REVIEW_TYPES))
    args = parser.parse_args()
    queue = json.loads(Path(args.queue).read_text())
    validate_queue(queue)
    if args.select:
        item = select_next(queue, args.select)
        print(json.dumps(item, sort_keys=True) if item else "null")
    else:
        print(json.dumps({"ok": True, "items": len(queue["items"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except QueueContractError as exc:
        print(f"REVIEW_QUEUE_FIX_REQUIRED:{exc}")
        raise SystemExit(1)
