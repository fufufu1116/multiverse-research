from __future__ import annotations

from typing import Any, Dict

from validate_pre_structure_v1 import fail_closed


LINE_DEPENDENT_MODEL_FAMILIES = {"C1", "N1"}
STANDARD_LINE_REGIME = "STANDARD_ORIGINAL_LINE_KEIRIN"


def assert_line_dependent_route_allowed(
    pre_record: Dict[str, Any],
    model_family: str,
) -> None:
    """Fail closed unless C1/N1 receives validated standard original-line PRE.

    This guard does not claim that C0 or any other model is valid for fixed-pacer or
    unknown regimes. It closes only the mechanical routing boundary for the current
    line-dependent families.
    """

    if model_family not in LINE_DEPENDENT_MODEL_FAMILIES:
        raise ValueError(f"UNSUPPORTED_GUARD_MODEL_FAMILY:{model_family}")

    fail_closed(pre_record, require_line_for_standard=True)

    regime = pre_record.get("race_regime")
    if regime != STANDARD_LINE_REGIME:
        raise ValueError(
            "LINE_DEPENDENT_MODEL_ROUTE_BLOCKED:"
            f"model={model_family}:race_regime={regime}"
        )
