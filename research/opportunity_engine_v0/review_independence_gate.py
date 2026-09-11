from __future__ import annotations

from typing import Any

from automation.multimodel_research_v1.model import NONAUTHORITY_KEYS

from .multiverse_bridge import OpportunityBridgeError, sha256_json

INDEPENDENCE_SCHEMA = "MULTIVERSE_OPPORTUNITY_REVIEW_INDEPENDENCE_v1"


def _nonauthority() -> dict[str, bool]:
    return {key: False for key in sorted(NONAUTHORITY_KEYS)}


def assess_review_independence(
    *,
    ensemble: dict[str, Any],
    min_providers_for_clearance: int = 2,
    min_provider_models_for_clearance: int = 2,
) -> dict[str, Any]:
    """Apply an asymmetric independence gate to Opportunity Engine review synthesis.

    Negative/challenging evidence may block even when it comes from a single provider.
    Positive/no-blocker evidence may only support readiness for the next governed gate
    when there is cross-provider diversity. Multiple roles played by one model do not
    become independent voices merely because the role labels differ.
    """
    if not isinstance(ensemble, dict):
        raise OpportunityBridgeError("ensemble must be an object")
    if ensemble.get("schema") != "MULTIVERSE_OPPORTUNITY_REVIEW_ENSEMBLE_v1":
        raise OpportunityBridgeError("unexpected ensemble schema")
    if not isinstance(min_providers_for_clearance, int) or min_providers_for_clearance < 2:
        raise OpportunityBridgeError("min_providers_for_clearance must be >= 2")
    if not isinstance(min_provider_models_for_clearance, int) or min_provider_models_for_clearance < 2:
        raise OpportunityBridgeError("min_provider_models_for_clearance must be >= 2")

    feedback = ensemble.get("individual_feedback")
    if not isinstance(feedback, list) or not feedback:
        raise OpportunityBridgeError("ensemble requires individual feedback")

    providers: set[str] = set()
    provider_models: set[tuple[str, str]] = set()
    advisory_identities: set[tuple[str, str, str]] = set()
    for item in feedback:
        if not isinstance(item, dict):
            raise OpportunityBridgeError("individual feedback must be objects")
        identity = item.get("model_identity")
        if not isinstance(identity, dict):
            raise OpportunityBridgeError("model identity is required")
        provider = identity.get("provider")
        model = identity.get("model")
        role = identity.get("role")
        if not all(isinstance(value, str) and value for value in (provider, model, role)):
            raise OpportunityBridgeError("provider/model/role must be non-empty text")
        providers.add(provider)
        provider_models.add((provider, model))
        advisory_identities.add((provider, model, role))

    if len(providers) >= min_providers_for_clearance:
        diversity_class = "CROSS_PROVIDER"
    elif len(provider_models) >= 2:
        diversity_class = "SINGLE_PROVIDER_MULTI_MODEL"
    else:
        diversity_class = "SINGLE_PROVIDER_SINGLE_MODEL"

    source_state = ensemble.get("overall_state")
    allowed_states = {
        "REVIEW_INCOMPLETE",
        "CHALLENGE_REQUIRED",
        "FALSIFICATION_REQUIRED",
        "MORE_EVIDENCE_OR_REVISION",
        "NO_BLOCKER_FOUND_YET",
    }
    if source_state not in allowed_states:
        raise OpportunityBridgeError("unexpected ensemble state")

    if source_state == "REVIEW_INCOMPLETE":
        final_state = "REVIEW_INCOMPLETE"
        next_action = "RESTORE_REVIEW_COVERAGE"
    elif source_state == "CHALLENGE_REQUIRED":
        final_state = "CHALLENGE_REQUIRED"
        next_action = "DOWNRANK_AND_RUN_FALSIFICATION"
    elif source_state == "FALSIFICATION_REQUIRED":
        final_state = "FALSIFICATION_REQUIRED"
        next_action = "RUN_MECHANICAL_FALSIFICATION"
    elif source_state == "MORE_EVIDENCE_OR_REVISION":
        final_state = "MORE_EVIDENCE_OR_REVISION"
        next_action = "RESEARCH_REVISE_AND_REFREEZE"
    elif (
        len(providers) < min_providers_for_clearance
        or len(provider_models) < min_provider_models_for_clearance
    ):
        final_state = "INDEPENDENCE_INSUFFICIENT"
        next_action = "ADD_CROSS_PROVIDER_CHALLENGE"
    else:
        final_state = "CROSS_PROVIDER_NO_BLOCKER_FOUND_YET"
        next_action = "HOLD_FOR_NEXT_GOVERNED_GATE"

    output = {
        "schema": INDEPENDENCE_SCHEMA,
        "case_id": ensemble.get("case_id"),
        "task_id": ensemble.get("task_id"),
        "ensemble_sha256": ensemble.get("ensemble_sha256"),
        "source_review_state": source_state,
        "independence_state": final_state,
        "recommended_next_action": next_action,
        "diversity_class": diversity_class,
        "provider_count": len(providers),
        "provider_model_count": len(provider_models),
        "advisory_identity_count": len(advisory_identities),
        "providers": sorted(providers),
        "provider_models": sorted(
            {f"{provider}/{model}" for provider, model in provider_models}
        ),
        "positive_clearance_requires_cross_provider": True,
        "negative_evidence_can_block_without_cross_provider": True,
        "same_model_multiple_roles_are_not_independent_models": True,
        "same_provider_multiple_models_are_not_cross_provider": True,
        "support_confers_approval": False,
        "automatic_advance_authorized": False,
        "authority": _nonauthority(),
        "note": (
            "Provider diversity is a confidence gate, not a truth vote. A single-provider "
            "review can discover blockers, but it cannot by itself establish cross-provider "
            "clearance for a material opportunity."
        ),
    }
    output["independence_sha256"] = sha256_json(output)
    return output
