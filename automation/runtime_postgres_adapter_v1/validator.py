"""Deterministic validator for Runtime PostgreSQL adapter repository implementation v1."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROOF = "RUNTIME_POSTGRES_ADAPTER_REPOSITORY_IMPLEMENTATION_ONLY"
STATE = "POSTGRES_ADAPTER_IMPLEMENTED_NOT_REMOTE_VALIDATED"
ADOPTED_HEAD = "efe180d91ff4fd2149c4d0cfba1af6821269602d"
ADOPTED_TREE = "af99595781224844d2867392e7aa3ce4d41a92bf"
ADOPTION_COMMENT = 5557340887


def validate() -> dict[str, object]:
    contract = json.loads((ROOT / "POSTGRES_ADAPTER_CONTRACT_v1.json").read_text())
    assert contract["adopted_activation_integration"]["head"] == ADOPTED_HEAD
    assert contract["adopted_activation_integration"]["tree"] == ADOPTED_TREE
    assert contract["adopted_activation_integration"]["owner_adoption_comment"] == ADOPTION_COMMENT
    assert contract["proof_ceiling"] == PROOF
    assert contract["implementation_state"] == STATE
    assert contract["activation_ready"] is False
    assert contract["runtime"] == "OFF"
    assert contract["adapter"]["connection_string_handling"] is False
    assert contract["adapter"]["network_dialing_in_candidate"] is False
    assert contract["adapter"]["postgres_driver_import"] is False
    assert contract["adapter"]["remote_validation_required"] is True
    assert all(value is False for value in contract["authority"].values())

    adapter = (ROOT / "postgres_adapter.py").read_text()
    bridge = (ROOT / "postgres_runtime_bridge.py").read_text()
    durable = (
        (ROOT / "POSTGRES_ADAPTER_CONTRACT_v1.json").read_text()
        + (ROOT / "README.md").read_text()
        + adapter
        + bridge
    )

    forbidden_imports = (
        "import psycopg",
        "from psycopg",
        "import requests",
        "from requests",
        "import socket",
        "from socket",
    )
    assert not any(token in adapter for token in forbidden_imports)
    assert "KILL_SWITCH_DEFAULT_ENGAGED = True" in adapter
    assert "PROVIDER_EFFECT_ADAPTER_ENABLED = False" in adapter
    assert "RUNTIME_ACTIVATION_BRIDGE_ENABLED = False" in adapter
    assert "ACTIVATION_READY = False" in adapter
    assert "def enable_activation" not in bridge
    assert "def enable_runtime" not in bridge
    assert "def enable_provider_effect" not in bridge

    forbidden_secret_sentinels = ("postgresql://", "postgres://", "DATABASE_URL=")
    assert not any(token in durable for token in forbidden_secret_sentinels)

    return {
        "proof_ceiling": PROOF,
        "implementation_state": STATE,
        "activation_ready": False,
        "runtime": "OFF",
        "verdict": "PASS",
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
