from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from automation.multimodel_research_v1 import model as canonical_model


EXPECTED_TASK_SCHEMA = "MULTIVERSE_RESEARCH_TASK_v2"
EXPECTED_RESULT_SCHEMA = "MULTIVERSE_RESEARCH_RESULT_v1"
EXPECTED_REQUIRED_PRIMITIVES = frozenset({"SOURCE_REF"})
EXPECTED_NETWORK_MODES = frozenset({"NONE", "PUBLIC_READ_ONLY"})


@dataclass(frozen=True)
class ContractBinding:
    compatible: bool
    findings: tuple[str, ...]
    task_schema: str
    result_schema: str


def assess_current_main_contract_binding() -> ContractBinding:
    """Fail closed when canonical MULTIVERSE contracts drift from bridge assumptions.

    This performs no provider call, network action, review dispatch, adoption, merge,
    publication, spend, customer effect, or Runtime activation.
    """
    findings: list[str] = []

    if getattr(canonical_model, "TASK_SCHEMA_V2", None) != EXPECTED_TASK_SCHEMA:
        findings.append("TASK_V2_SCHEMA_DRIFT")
    if getattr(canonical_model, "RESULT_SCHEMA", None) != EXPECTED_RESULT_SCHEMA:
        findings.append("RESULT_SCHEMA_DRIFT")

    primitives = frozenset(getattr(canonical_model, "ALLOWED_PRIMITIVES", set()))
    if not EXPECTED_REQUIRED_PRIMITIVES.issubset(primitives):
        findings.append("SOURCE_REF_PRIMITIVE_MISSING")

    nonauthority = frozenset(getattr(canonical_model, "NONAUTHORITY_KEYS", set()))
    required_nonauthority = {
        "adoption",
        "merge",
        "main_mutation",
        "runtime_activation",
        "provider_effect",
        "live_business_effect",
        "spend",
    }
    if not required_nonauthority.issubset(nonauthority):
        findings.append("NONAUTHORITY_BOUNDARY_WEAKENED")

    task_v2_keys = frozenset(getattr(canonical_model, "TASK_V2_KEYS", set()))
    if "evidence_manifest" not in task_v2_keys:
        findings.append("EVIDENCE_MANIFEST_MISSING")

    return ContractBinding(
        compatible=not findings,
        findings=tuple(findings),
        task_schema=getattr(canonical_model, "TASK_SCHEMA_V2", ""),
        result_schema=getattr(canonical_model, "RESULT_SCHEMA", ""),
    )


def validate_bridge_packet_against_current_main(packet: dict[str, Any]) -> dict[str, Any]:
    """Validate a frozen bridge packet using the current canonical task validator."""
    binding = assess_current_main_contract_binding()
    if not binding.compatible:
        raise ValueError("CURRENT_MAIN_CONTRACT_DRIFT:" + ",".join(binding.findings))
    if not isinstance(packet, dict) or "research_task" not in packet:
        raise ValueError("BRIDGE_PACKET_RESEARCH_TASK_MISSING")
    canonical_model.validate_task(packet["research_task"])
    return packet


def binding_authority_ceiling() -> dict[str, bool]:
    return {
        "formal_review_authorized": False,
        "canonical_adoption_authorized": False,
        "merge_authorized": False,
        "provider_call_authorized": False,
        "credential_use_authorized": False,
        "spend_authorized": False,
        "publication_authorized": False,
        "customer_effect_authorized": False,
        "runtime_activation_authorized": False,
    }
