"""Deterministic repository-only validator for Runtime activation integration v1."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROOF = "RUNTIME_ACTIVATION_INTEGRATION_REPOSITORY_PREPARATION_ONLY"
STATE = "ACTIVATION_INTEGRATION_PREPARATION_NOT_ACTIVATABLE"
EXPECTED_MAIN = "a6f56facc80709f2e7b8218d927484d522bfa356"
EXPECTED_CONVERGENCE_HEAD = "6778bbfada03dd70ffe47b1e715c470b6a671585"
EXPECTED_CONVERGENCE_TREE = "538b98c6cd7d98207cf96871af620f43f42f629e"
EXPECTED_OWNER_ADOPTION = 5555227138


def validate() -> dict[str, str]:
    contract = json.loads((ROOT / "ACTIVATION_INTEGRATION_CONTRACT_v1.json").read_text())
    assert contract["canonical_main"] == EXPECTED_MAIN
    assert contract["adopted_convergence"]["head"] == EXPECTED_CONVERGENCE_HEAD
    assert contract["adopted_convergence"]["tree"] == EXPECTED_CONVERGENCE_TREE
    assert contract["adopted_convergence"]["owner_adoption_comment"] == EXPECTED_OWNER_ADOPTION
    assert contract["proof_ceiling"] == PROOF
    assert contract["integration_state"] == STATE
    assert contract["activation_ready"] is False
    assert contract["runtime"] == "OFF"
    authority = contract["authority"]
    assert authority and all(value is False for value in authority.values())
    gates = contract["activation_gates"]
    assert gates == {
        "kill_switch_default_engaged": True,
        "provider_effect_adapter_enabled": False,
        "runtime_activation_bridge_enabled": False,
    }
    pg = (ROOT / "postgres_contract.py").read_text()
    assert "import psycopg" not in pg
    assert "import requests" not in pg
    assert "import socket" not in pg
    bridge = (ROOT / "runtime_activation_bridge.py").read_text()
    assert "RUNTIME_ACTIVATION_BRIDGE_ENABLED = False" in bridge
    assert "PROVIDER_EFFECT_ADAPTER_ENABLED = False" in bridge
    assert "KILL_SWITCH_DEFAULT_ENGAGED = True" in bridge
    return {
        "proof_ceiling": PROOF,
        "integration_state": STATE,
        "activation_ready": "false",
        "runtime": "OFF",
        "verdict": "PASS",
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
