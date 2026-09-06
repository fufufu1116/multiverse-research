"""Deterministic repository-only validator for remote PostgreSQL adapter execution prep."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROOF = "REMOTE_POSTGRES_ADAPTER_PREPRODUCTION_EXECUTION_PREPARATION_ONLY"
STATE = "REMOTE_EXECUTION_NOT_AUTHORIZED"
ADOPTED_HEAD = "d44b9c8262888182801cb3f6355538f63e7dc21b"
ADOPTED_TREE = "34d3a2045ea24cfa7eec80bc691e37a64adbb2ab"
ADOPTION_COMMENT = 5557497002


def validate() -> dict[str, object]:
    contract = json.loads(
        (ROOT / "EXECUTION_PREPARATION_CONTRACT_v1.json").read_text()
    )

    assert contract["adopted_postgres_adapter"]["head"] == ADOPTED_HEAD
    assert contract["adopted_postgres_adapter"]["tree"] == ADOPTED_TREE
    assert (
        contract["adopted_postgres_adapter"]["owner_adoption_comment"]
        == ADOPTION_COMMENT
    )

    assert contract["proof_ceiling"] == PROOF
    assert contract["execution_state"] == STATE
    assert contract["remote_postgres_execution"] is False
    assert contract["activation_ready"] is False
    assert contract["runtime"] == "OFF"

    assert contract["provider_target"]["new_service_creation_authorized"] is False
    assert contract["provider_target"]["deploy_authorized"] is False
    assert all(value is False for value in contract["authority"].values())

    app = (ROOT / "app.py").read_text()
    durable = (
        (ROOT / "EXECUTION_PREPARATION_CONTRACT_v1.json").read_text()
        + (ROOT / "README.md").read_text()
    )

    main_start = app.index("def main()")
    authority_index = app.index("validate_nonsecret_environment()", main_start)
    thread_index = app.index("thread = threading.Thread", main_start)
    assert authority_index < thread_index

    build_factory = app.index("def build_connection_factory")
    psycopg_import = app.index("import psycopg", build_factory)
    assert psycopg_import > build_factory

    forbidden_secret_literals = ("postgresql://", "postgres://", "DATABASE_URL=")
    assert not any(token in durable for token in forbidden_secret_literals)

    assert "FINAL_EVIDENCE_CHECKPOINT" in app
    assert "recovered_after_restart" in app
    assert "state_changes_disabled_over_http" in app
    assert "external_effect_executed" in app
    assert '"runtime": RUNTIME' in app
    assert 'RUNTIME = "OFF"' in app

    return {
        "proof_ceiling": PROOF,
        "execution_state": STATE,
        "remote_postgres_execution": False,
        "activation_ready": False,
        "runtime": "OFF",
        "verdict": "PASS",
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
