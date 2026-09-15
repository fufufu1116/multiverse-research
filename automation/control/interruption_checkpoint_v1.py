from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VALID_ACTION_STATES = {"RECEIPTED", "NOT_RECEIPTED", "UNCERTAIN"}
ONE_SHOT_KINDS = {
    "build",
    "payment",
    "provider_call",
    "credential_change",
    "production_change",
    "merge",
    "deployment",
    "purchase",
    "sale",
    "bet",
}


@dataclass(frozen=True)
class ResumeDecision:
    action_id: str
    state: str
    decision: str
    reason: str


def _require_text(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"INVALID_OR_MISSING:{key}")
    return value.strip()


def validate_checkpoint(payload: dict[str, Any]) -> None:
    if payload.get("schema") != "MULTIVERSE_INTERRUPTION_CHECKPOINT_v1":
        raise ValueError("INVALID_SCHEMA")
    _require_text(payload, "lane")
    _require_text(payload, "authority_ref")
    if payload.get("runtime") != "OFF":
        raise ValueError("RUNTIME_MUST_BE_OFF")
    actions = payload.get("actions")
    if not isinstance(actions, list):
        raise ValueError("ACTIONS_MUST_BE_LIST")
    seen: set[str] = set()
    for action in actions:
        if not isinstance(action, dict):
            raise ValueError("ACTION_MUST_BE_OBJECT")
        action_id = _require_text(action, "action_id")
        if action_id in seen:
            raise ValueError(f"DUPLICATE_ACTION_ID:{action_id}")
        seen.add(action_id)
        state = _require_text(action, "state")
        if state not in VALID_ACTION_STATES:
            raise ValueError(f"INVALID_ACTION_STATE:{action_id}:{state}")
        kind = _require_text(action, "kind")
        one_shot = action.get("one_shot")
        if not isinstance(one_shot, bool):
            raise ValueError(f"ONE_SHOT_MUST_BE_BOOL:{action_id}")
        if kind in ONE_SHOT_KINDS and one_shot is not True:
            raise ValueError(f"KNOWN_ONE_SHOT_KIND_MUST_BE_ONE_SHOT:{action_id}:{kind}")
        receipt_ref = action.get("receipt_ref")
        if state == "RECEIPTED" and (not isinstance(receipt_ref, str) or not receipt_ref.strip()):
            raise ValueError(f"RECEIPTED_REQUIRES_RECEIPT_REF:{action_id}")
        if state != "RECEIPTED" and receipt_ref not in (None, ""):
            raise ValueError(f"UNRECEIPTED_MUST_NOT_CLAIM_RECEIPT:{action_id}")


def classify_resume(payload: dict[str, Any]) -> list[ResumeDecision]:
    validate_checkpoint(payload)
    decisions: list[ResumeDecision] = []
    for action in payload["actions"]:
        action_id = action["action_id"]
        state = action["state"]
        one_shot = action["one_shot"]
        if state == "RECEIPTED":
            decisions.append(ResumeDecision(action_id, state, "DO_NOT_REPLAY", "durable receipt exists"))
        elif state == "UNCERTAIN":
            decisions.append(ResumeDecision(action_id, state, "VERIFY_EXTERNALLY_FAIL_CLOSED", "side effect is uncertain"))
        elif one_shot:
            decisions.append(ResumeDecision(action_id, state, "REQUIRE_FRESH_AUTHORITY_BEFORE_ACTION", "unreceipted one-shot action"))
        else:
            decisions.append(ResumeDecision(action_id, state, "CONTINUE_IF_STILL_AUTHORIZED", "unreceipted non-one-shot work"))
    return decisions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint")
    args = parser.parse_args()
    payload = json.loads(Path(args.checkpoint).read_text())
    decisions = classify_resume(payload)
    print(json.dumps([d.__dict__ for d in decisions], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
