#!/usr/bin/env python3
import json
import subprocess
import sys

TRUSTED_PYTHON = "/usr/local/python/current/bin/python"
EXEC_ROOT = "/dev/shm/multiverse-r1-stage1-phase-c-execution"
PREFLIGHT = "tools/multiverse_r1_stage1_phase_c_execution_preflight_v1.py"

ALLOWED_PREFIXES = (
    "PHASE_C_EXECUTION_",
    "PHASE_C_PREFLIGHT_",
    "PHASE_C_CODESPACES_",
    "PHASE_C_GH_",
    "PHASE_C_MEMORY_",
    "PHASE_C_ACTIVE_SWAP_",
    "PHASE_C_PROXY_CA_OR_DEBUG_",
    "PHASE_C_GITHUB_",
    "PHASE_C_USER_",
    "PHASE_C_OAUTH_",
    "PHASE_C_REPOSITORY_",
    "PHASE_C_MAIN_",
    "PHASE_C_RULESET_",
    "PHASE_C_FENCE_",
    "PHASE_C_API_",
)


def emit(label: str) -> None:
    print(label, flush=True)


def safe_reason(value: object) -> str:
    if not isinstance(value, str):
        return "UNCLASSIFIED"
    if len(value) > 220 or any(ch in value for ch in "\r\n\t"):
        return "UNCLASSIFIED"
    if value.startswith(ALLOWED_PREFIXES):
        return value
    return "UNCLASSIFIED"


def main() -> int:
    emit("PHASE_C_V19_7_13_DIAGNOSTIC_START")
    cp = subprocess.run(
        [TRUSTED_PYTHON, "-B", PREFLIGHT],
        cwd=EXEC_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if cp.returncode == 0:
        try:
            data = json.loads(cp.stdout)
        except Exception:
            emit("PHASE_C_V19_7_13_DIAGNOSTIC:PREFLIGHT_ZERO_JSON_INVALID")
            return 92
        if data.get("status") != "PHASE_C_NONMUTATING_PREFLIGHT_PASS":
            emit("PHASE_C_V19_7_13_DIAGNOSTIC:PREFLIGHT_ZERO_STATUS_INVALID")
            return 92
        if data.get("production_mutation_performed") is not False:
            emit("PHASE_C_V19_7_13_DIAGNOSTIC:PRODUCTION_MUTATION_FLAG_INVALID")
            return 92
        if data.get("runtime_activation_performed") is not False:
            emit("PHASE_C_V19_7_13_DIAGNOSTIC:RUNTIME_ACTIVATION_FLAG_INVALID")
            return 92
        emit("PHASE_C_V19_7_13_DIAGNOSTIC:PREFLIGHT_PASS")
        return 0

    try:
        data = json.loads(cp.stdout)
    except Exception:
        emit(f"PHASE_C_V19_7_13_DIAGNOSTIC:PREFLIGHT_NONZERO_RC_{cp.returncode}:NO_JSON")
        return 92

    if data.get("status") != "DENIED_FAIL_CLOSED":
        emit(f"PHASE_C_V19_7_13_DIAGNOSTIC:PREFLIGHT_NONZERO_RC_{cp.returncode}:STATUS_UNEXPECTED")
        return 92
    if data.get("production_mutation_performed") is not False or data.get("runtime_activation_performed") is not False:
        emit("PHASE_C_V19_7_13_DIAGNOSTIC:NONMUTATION_FLAGS_INVALID")
        return 92

    reason = safe_reason(data.get("reason"))
    emit(f"PHASE_C_V19_7_13_DIAGNOSTIC:DENIED:{reason}")
    return 92


if __name__ == "__main__":
    raise SystemExit(main())
