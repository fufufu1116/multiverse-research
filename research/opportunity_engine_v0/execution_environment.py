from __future__ import annotations

from enum import Enum
from typing import Any


class WorkloadKind(str, Enum):
    RESEARCH = "RESEARCH"
    WEB_APP = "WEB_APP"
    NATIVE_IOS_APP = "NATIVE_IOS_APP"
    NATIVE_ANDROID_APP = "NATIVE_ANDROID_APP"
    LARGE_SIMULATION = "LARGE_SIMULATION"
    DATA_PIPELINE = "DATA_PIPELINE"


def _score(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 5:
        raise ValueError(f"{name} must be an integer from 0 to 5")
    return value


def route_execution_environment(
    *,
    workload: WorkloadKind,
    owner_has_mac: bool,
    cloud_build_available: bool,
    local_xcode_required: bool = False,
    local_compute_need: int = 0,
    parallel_work_need: int = 0,
    privacy_sensitive_local_data: bool = False,
) -> dict[str, Any]:
    """Choose the cheapest practical execution surface without turning hardware into a dependency.

    Phone-only operation is allowed where cloud services can carry the build/compute burden.
    A Mac is treated as a force multiplier for native Apple toolchains, local simulation,
    parallel development and private/local datasets, not as a prerequisite for the whole engine.
    """
    local_compute = _score(local_compute_need, "local_compute_need")
    parallel_work = _score(parallel_work_need, "parallel_work_need")
    for value, name in (
        (owner_has_mac, "owner_has_mac"),
        (cloud_build_available, "cloud_build_available"),
        (local_xcode_required, "local_xcode_required"),
        (privacy_sensitive_local_data, "privacy_sensitive_local_data"),
    ):
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be boolean")
    if local_xcode_required and workload != WorkloadKind.NATIVE_IOS_APP:
        raise ValueError("local_xcode_required is only valid for native iOS work")

    if workload == WorkloadKind.NATIVE_IOS_APP and local_xcode_required and not owner_has_mac:
        state = "MAC_REQUIRED_FOR_SELECTED_LOCAL_TOOLCHAIN"
        primary = "WAIT_OR_USE_REMOTE_MAC"
        phone_can_complete = False
        mac_leverage_score = 5
    elif workload == WorkloadKind.NATIVE_IOS_APP and not owner_has_mac and cloud_build_available:
        state = "CLOUD_BRIDGE_AVAILABLE"
        primary = "PHONE_PLUS_CLOUD_MAC_BUILD"
        phone_can_complete = True
        mac_leverage_score = 4
    elif workload in {WorkloadKind.WEB_APP, WorkloadKind.RESEARCH} and not owner_has_mac:
        state = "FEASIBLE_PHONE_ONLY"
        primary = "PHONE_CLOUD"
        phone_can_complete = True
        mac_leverage_score = 2 if workload == WorkloadKind.RESEARCH else 3
    elif workload in {WorkloadKind.LARGE_SIMULATION, WorkloadKind.DATA_PIPELINE} and not owner_has_mac:
        state = "CLOUD_COMPUTE_PREFERRED"
        primary = "PHONE_CONTROLLED_CLOUD_COMPUTE"
        phone_can_complete = True
        mac_leverage_score = 5 if local_compute >= 3 else 4
    elif owner_has_mac and (
        privacy_sensitive_local_data or local_compute >= 3 or parallel_work >= 3
    ):
        state = "MAC_PREFERRED"
        primary = "MAC_LOCAL"
        phone_can_complete = workload != WorkloadKind.NATIVE_IOS_APP or cloud_build_available
        mac_leverage_score = 5 if local_compute >= 4 else 4
    elif owner_has_mac:
        state = "MAC_OPTIONAL_BUT_FASTER"
        primary = "MAC_LOCAL"
        phone_can_complete = workload != WorkloadKind.NATIVE_IOS_APP or cloud_build_available
        mac_leverage_score = 3
    else:
        state = "FEASIBLE_PHONE_ONLY"
        primary = "PHONE_CLOUD"
        phone_can_complete = True
        mac_leverage_score = 2

    return {
        "state": state,
        "primary_environment": primary,
        "phone_can_complete": phone_can_complete,
        "mac_leverage_score": mac_leverage_score,
        "hardware_is_not_strategy_authority": True,
        "prefer_replaceable_cloud_services": True,
        "note": (
            "Execution routing only. Native store submission, provider spend, credentials and live effects "
            "remain governed by their own current platform and MULTIVERSE authority gates."
        ),
    }
