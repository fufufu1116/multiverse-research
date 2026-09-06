"""Repository-only validator for bridge PRE_PRODUCTION validation preparation."""
from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROOF_CEILING = "POSTGRES_RUNTIME_BRIDGE_PREPRODUCTION_VALIDATION_PREPARATION_ONLY"
EXECUTION_STATE = "BRIDGE_REMOTE_VALIDATION_NOT_AUTHORIZED"


def validate() -> dict:
    findings = []
    contract = json.loads(
        (ROOT / "BRIDGE_VALIDATION_PREPARATION_CONTRACT_v1.json").read_text()
    )
    app_source = (ROOT / "app.py").read_text()
    validation_source = (ROOT / "bridge_validation.py").read_text()

    if contract.get("proof_ceiling") != PROOF_CEILING:
        findings.append("PROOF_CEILING_MISMATCH")
    if contract.get("execution_state") != EXECUTION_STATE:
        findings.append("EXECUTION_STATE_MISMATCH")
    if contract.get("runtime") != "OFF":
        findings.append("RUNTIME_NOT_OFF")
    if contract.get("activation_ready") is not False:
        findings.append("ACTIVATION_READY_NOT_FALSE")
    if contract.get("runtime_activation_bridge_enabled") is not False:
        findings.append("ACTIVATION_BRIDGE_NOT_FALSE")
    if contract.get("provider_effect_adapter_enabled") is not False:
        findings.append("PROVIDER_EFFECT_NOT_FALSE")
    if contract.get("remote_postgres_execution") is not False:
        findings.append("REMOTE_EXECUTION_NOT_FALSE")

    for token in (
        "PreparedPostgresRuntimeBridge",
        "bridge.prepare_session",
        "bridge.renew_session",
        "bridge.checkpoint",
        "bridge.reserve_inert_operation",
        "bridge.readiness",
    ):
        if token not in validation_source:
            findings.append(f"MISSING_BRIDGE_ROUTE:{token}")

    parsed = ast.parse(app_source)
    locations = []

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.stack = []

        def visit_FunctionDef(self, node):
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_Import(self, node):
            for alias in node.names:
                if alias.name == "psycopg":
                    locations.append(tuple(self.stack))
            self.generic_visit(node)

    Visitor().visit(parsed)

    if locations != [("build_connection_factory",)]:
        findings.append(f"PSYCOPG_IMPORT_LOCATION:{locations!r}")

    for token in ("postgresql://", "postgres://", "DATABASE_URL="):
        for name in (
            "app.py",
            "bridge_validation.py",
            "README.md",
            "BRIDGE_VALIDATION_PREPARATION_CONTRACT_v1.json",
        ):
            if token in (ROOT / name).read_text():
                findings.append(f"SECRET_VALUE_PATTERN:{name}:{token}")

    return {
        "schema": "MULTIVERSE_POSTGRES_RUNTIME_BRIDGE_PREPROD_PREPARATION_VALIDATOR_v1",
        "verdict": "PASS" if not findings else "FIX_REQUIRED",
        "findings": findings,
        "proof_ceiling": PROOF_CEILING,
        "execution_state": EXECUTION_STATE,
        "remote_postgres_execution": False,
        "runtime_activation_bridge_enabled": False,
        "activation_ready": False,
        "runtime": "OFF",
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
