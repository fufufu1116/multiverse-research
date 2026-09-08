from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ALLOWED_STATES = {"ADOPTED_PROVEN", "FROZEN_CANDIDATE", "OPEN_INTEGRATION"}
SCHEMA = "MULTIVERSE_LANE_B_COMPLETION_MATRIX_v1"


def load_matrix(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text())
    if not isinstance(payload, dict):
        raise ValueError("MATRIX_OBJECT_REQUIRED")
    if payload.get("schema") != SCHEMA:
        raise ValueError("MATRIX_SCHEMA")
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("MATRIX_ROWS_REQUIRED")
    credit = payload.get("credit")
    if not isinstance(credit, dict) or set(credit) != ALLOWED_STATES:
        raise ValueError("MATRIX_CREDIT_SCHEMA")
    ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("MATRIX_ROW_OBJECT")
        if set(row) != {"id", "critical", "state", "evidence", "note"}:
            raise ValueError("MATRIX_ROW_KEYS")
        rid = row["id"]
        if not isinstance(rid, str) or not rid or rid in ids:
            raise ValueError("MATRIX_ROW_ID")
        ids.add(rid)
        if row["critical"] is not True:
            raise ValueError("MATRIX_ROW_CRITICAL")
        if row["state"] not in ALLOWED_STATES:
            raise ValueError("MATRIX_ROW_STATE")
        if not isinstance(row["evidence"], str) or not row["evidence"]:
            raise ValueError("MATRIX_ROW_EVIDENCE")
        if not isinstance(row["note"], str) or not row["note"]:
            raise ValueError("MATRIX_ROW_NOTE")
    return payload


def completion_summary(matrix: dict[str, Any]) -> dict[str, Any]:
    rows = matrix["rows"]
    credit = matrix["credit"]
    total = len(rows)
    counts = {state: 0 for state in ALLOWED_STATES}
    earned = 0.0
    for row in rows:
        state = row["state"]
        counts[state] += 1
        earned += float(credit[state])
    score = round(100.0 * earned / total, 2)
    complete = all(row["state"] == "ADOPTED_PROVEN" for row in rows)
    return {
        "critical_rows": total,
        "counts": counts,
        "progress_percent": score,
        "major_goal_complete": complete,
        "remaining_rows": [row["id"] for row in rows if row["state"] != "ADOPTED_PROVEN"],
    }
