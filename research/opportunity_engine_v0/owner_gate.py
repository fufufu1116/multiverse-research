from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class ContinuationDecision(str, Enum):
    CONTINUE_AUTONOMOUS_RESEARCH = "CONTINUE_AUTONOMOUS_RESEARCH"
    OWNER_ACTION_REQUIRED = "OWNER_ACTION_REQUIRED"
    HOLD_FAIL_CLOSED = "HOLD_FAIL_CLOSED"


@dataclass(frozen=True)
class ProposedAction:
    action_id: str
    description: str
    reversible_repository_only: bool
    changes_canonical_main: bool = False
    changes_fixed_lab_or_auditor_steps: bool = False
    triggers_live_provider_or_network_effect: bool = False
    uses_credentials: bool = False
    spends_money: bool = False
    publishes_or_contacts_external_party: bool = False
    creates_live_business_effect: bool = False
    activates_runtime: bool = False
    grants_adoption_or_merge_authority: bool = False
    deletes_or_exposes_sensitive_owner_data: bool = False
    requires_owner_secret_or_external_fact_unavailable_to_repo: bool = False
    ambiguous_authority_boundary: bool = False

    def __post_init__(self) -> None:
        if not self.action_id.strip():
            raise ValueError("action_id is required")
        if not self.description.strip():
            raise ValueError("description is required")


def classify_owner_gate(action: ProposedAction) -> dict[str, object]:
    """Decide whether work should continue without interrupting the Owner.

    Default posture is continuation for reversible research-branch work. The Owner
    is interrupted only when the next useful step crosses a real authority boundary
    or cannot be resolved safely from repository/evidence already available.
    """
    owner_gate_reasons: list[str] = []
    hard_hold_reasons: list[str] = []

    if action.changes_canonical_main:
        owner_gate_reasons.append("CANONICAL_MAIN_MUTATION")
    if action.changes_fixed_lab_or_auditor_steps:
        owner_gate_reasons.append("FIXED_REVIEW_INFRASTRUCTURE_CHANGE")
    if action.triggers_live_provider_or_network_effect:
        owner_gate_reasons.append("LIVE_PROVIDER_OR_NETWORK_EFFECT")
    if action.uses_credentials:
        owner_gate_reasons.append("CREDENTIAL_USE")
    if action.spends_money:
        owner_gate_reasons.append("SPEND")
    if action.publishes_or_contacts_external_party:
        owner_gate_reasons.append("PUBLICATION_OR_EXTERNAL_CONTACT")
    if action.creates_live_business_effect:
        owner_gate_reasons.append("LIVE_BUSINESS_EFFECT")
    if action.activates_runtime:
        owner_gate_reasons.append("RUNTIME_ACTIVATION")
    if action.grants_adoption_or_merge_authority:
        owner_gate_reasons.append("ADOPTION_OR_MERGE_AUTHORITY")
    if action.requires_owner_secret_or_external_fact_unavailable_to_repo:
        owner_gate_reasons.append("OWNER_ONLY_INPUT_REQUIRED")

    if action.deletes_or_exposes_sensitive_owner_data:
        hard_hold_reasons.append("SENSITIVE_OWNER_DATA_RISK")
    if action.ambiguous_authority_boundary:
        hard_hold_reasons.append("AUTHORITY_BOUNDARY_AMBIGUOUS")

    if hard_hold_reasons:
        decision = ContinuationDecision.HOLD_FAIL_CLOSED
    elif owner_gate_reasons:
        decision = ContinuationDecision.OWNER_ACTION_REQUIRED
    elif action.reversible_repository_only:
        decision = ContinuationDecision.CONTINUE_AUTONOMOUS_RESEARCH
    else:
        decision = ContinuationDecision.HOLD_FAIL_CLOSED
        hard_hold_reasons.append("NONREVERSIBLE_OR_UNCLASSIFIED_ACTION")

    exact_owner_request = None
    if decision == ContinuationDecision.OWNER_ACTION_REQUIRED:
        exact_owner_request = {
            "action_id": action.action_id,
            "request": "Authorize only this bounded next action.",
            "reasons": owner_gate_reasons,
        }

    return {
        "decision": decision.value,
        "action_id": action.action_id,
        "owner_gate_reasons": owner_gate_reasons,
        "hard_hold_reasons": hard_hold_reasons,
        "exact_owner_request": exact_owner_request,
        "continue_without_owner": decision == ContinuationDecision.CONTINUE_AUTONOMOUS_RESEARCH,
        "provider_call_authorized": False,
        "spend_authorized": False,
        "publication_authorized": False,
        "live_execution_authorized": False,
        "runtime_activation_authorized": False,
        "adoption_authorized": False,
        "merge_authorized": False,
    }


def choose_next_continuable_action(actions: Tuple[ProposedAction, ...]) -> dict[str, object]:
    """Select the first useful action that can proceed without Owner interruption.

    Owner-gated actions do not stop the lane if another useful reversible research
    action remains. This prevents false stalls while preserving fail-closed gates.
    """
    if not actions:
        return {
            "decision": "NO_ACTIONS_AVAILABLE",
            "selected_action_id": None,
            "owner_action_required": False,
        }

    gated: list[dict[str, object]] = []
    held: list[dict[str, object]] = []
    for action in actions:
        result = classify_owner_gate(action)
        if result["decision"] == ContinuationDecision.CONTINUE_AUTONOMOUS_RESEARCH.value:
            return {
                "decision": ContinuationDecision.CONTINUE_AUTONOMOUS_RESEARCH.value,
                "selected_action_id": action.action_id,
                "owner_action_required": False,
                "deferred_owner_gates": gated,
                "deferred_holds": held,
            }
        if result["decision"] == ContinuationDecision.OWNER_ACTION_REQUIRED.value:
            gated.append(result)
        else:
            held.append(result)

    if gated:
        first = gated[0]
        return {
            "decision": ContinuationDecision.OWNER_ACTION_REQUIRED.value,
            "selected_action_id": first["action_id"],
            "owner_action_required": True,
            "exact_owner_request": first["exact_owner_request"],
            "deferred_owner_gates": gated[1:],
            "deferred_holds": held,
        }

    return {
        "decision": ContinuationDecision.HOLD_FAIL_CLOSED.value,
        "selected_action_id": None,
        "owner_action_required": False,
        "deferred_holds": held,
    }
