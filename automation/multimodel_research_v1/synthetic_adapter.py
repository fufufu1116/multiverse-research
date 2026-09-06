from __future__ import annotations

import copy
from typing import Any

from automation.multimodel_research_v1.model import (
    validate_result,
    validate_task,
)


class SyntheticAdvisoryAdapter:
    """Offline fixture adapter. It performs no network/provider execution."""

    def __init__(self, fixture_result: dict[str, Any]):
        self._fixture_result = copy.deepcopy(fixture_result)

    def run(self, task: dict[str, Any]) -> dict[str, Any]:
        validate_task(task)

        result = copy.deepcopy(self._fixture_result)
        validate_result(result)

        if result["task_id"] != task["task_id"]:
            raise ValueError("TASK_ID_MISMATCH")

        if result["snapshot_id"] != task["snapshot_id"]:
            raise ValueError("SNAPSHOT_ID_MISMATCH")

        return result
