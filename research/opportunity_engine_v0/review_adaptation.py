from __future__ import annotations

import copy
from typing import Any

from automation.multimodel_research_v1.model import NONAUTHORITY_KEYS

from .multiverse_bridge import OpportunityBridgeError, sha256_json
from .multiverse_review_ensemble import ENSEMBLE_SCHEMA

ADAPTATION_SCHEMA = "MULTIVERSE_OPPORTUNITY_ADAPTATION_PLAN_v1"

SUBSYSTEM_ACTIONS = {
    "COMPETITION": (
        "REFRESH_COMPETITOR_MATRIX",
        "Re-run direct competitor, substitute, incumbent and general-AI replacement research before rescoring.",
    ),
    "ECONOMICS": (
        "RECALCULATE_LOW_BASE_HIGH",
        "Recalculate low/base/high economics, payback and owner-hour return using the challenged assumptions.",
    ),
    "LEVERAGE": (
        "REOPTIMIZE_LOADOUT",
        "Remove or discount challenged leverage assumptions and re-optimize the safe loadout under the same cash/time limits.",
    ),
    "FORECASTING": (
        "REFREEZE_FORECAST_VERSION",
        "Create a new forecast version after new evidence; never rewrite or erase the old frozen forecast.",
    ),
    "LEGAL_SAFETY": (
        "HOLD_FOR_OFFICIAL_VERIFICATION",
        "Hold advancement and require official or deterministic evidence before any legal/safety-sensitive action.",
    ),
    "AI_SUBSTITUTION": (
        "RERUN_AI_SUBSTITUTION_GATE",
        "Re-test whether general AI can already solve roughly 80%+ and require a concrete proprietary/action-completion edge.",
    ),
    "EXECUTION": (
        "REVISE_TACTIC_SEQUENCE",
        "Reduce owner burden and risk; re-check validation, conversion proof, automation, distribution, scaling and exit order.",
    ),
    "GENERAL_REVIEW": (
        "TARGETED_FALSIFICATION",
        "Design the smallest reversible test that can falsify the challenged claim.",
    ),
}


def _nonauthority() -> dict[str, bool]:
    return {key: False for key in sorted(NONAUTHORITY_KEYS)}


def _validate_ensemble(ensemble: dict[str, Any]) -> None:
    if not isinstance(ensemble, dict):
        raise OpportunityBridgeError("ensemble must be an object")
    if ensemble.get("schema") != ENSEMBLE_SCHEMA:
        raise OpportunityBridgeError("ensemble schema mismatch")
    expected = ensemble.get("ensemble_sha256")
    if not isinstance(expected, str):
        raise OpportunityBridgeError("ensemble hash required")
    unsigned = dict(ensemble)
    del unsigned["ensemble_sha256"]
    if sha256_json(unsigned) != expected:
        raise OpportunityBridgeError("ensemble hash mismatch")
    if ensemble.get("majority_confers_truth") is not False:
        raise OpportunityBridgeError("majority cannot confer truth")
    if ensemble.get("support_confers_approval") is not False:
        raise OpportunityBridgeError("support cannot confer approval")
    if ensemble.get("automatic_advance_authorized") is not False:
        raise OpportunityBridgeError("ensemble cannot authorize automatic advance")
    if ensemble.get("authority") != _nonauthority():
        raise OpportunityBridgeError("ensemble cannot grant authority")


def build_adaptation_plan(ensemble: dict[str, Any]) -> dict[str, Any]:
    """Translate advisory review pressure into bounded re-research instructions.

    The plan changes neither canonical state nor live execution. Even a clean review
    only becomes READY_FOR_NEXT_GOVERNED_GATE, never automatic BUILD/GO.
    """
    _validate_ensemble(ensemble)
    overall = ensemble["overall_state"]

    candidate_state = {
        "REVIEW_INCOMPLETE": "HOLD_REVIEW_INCOMPLETE",
        "CHALLENGE_REQUIRED": "DOWNRANK_AND_HOLD",
        "FALSIFICATION_REQUIRED": "HOLD_FOR_FALSIFICATION",
        "MORE_EVIDENCE_OR_REVISION": "HOLD_FOR_REVISION",
        "NO_BLOCKER_FOUND_YET": "READY_FOR_NEXT_GOVERNED_GATE",
    }.get(overall)
    if candidate_state is None:
        raise OpportunityBridgeError("unknown ensemble state")

    tasks = []
    for subsystem in ensemble["affected_subsystems"]:
        if subsystem not in SUBSYSTEM_ACTIONS:
            raise OpportunityBridgeError("unknown affected subsystem")
        action, instruction = SUBSYSTEM_ACTIONS[subsystem]
        related_claims = sorted(
            claim["claim_key"]
            for claim in ensemble["claim_states"]
            if claim["subsystem"] == subsystem
            and claim["state"] != "NO_BLOCKER_FOUND_YET"
        )
        tasks.append(
            {
                "subsystem": subsystem,
                "action": action,
                "instruction": instruction,
                "related_claims": related_claims,
            }
        )

    if overall == "REVIEW_INCOMPLETE":
        tasks.insert(
            0,
            {
                "subsystem": "REVIEW_COVERAGE",
                "action": "RESTORE_MISSING_REVIEW_ROLES",
                "instruction": "Restore completed coverage for every requested review role before interpreting the ensemble as complete.",
                "related_claims": [],
            },
        )
    elif overall == "FALSIFICATION_REQUIRED":
        tasks.insert(
            0,
            {
                "subsystem": "DIVERGENCE",
                "action": "RUN_MECHANICAL_FALSIFICATION",
                "instruction": "Resolve support-versus-opposition with a discriminating evidence test rather than a vote.",
                "related_claims": sorted(
                    claim["claim_key"]
                    for claim in ensemble["claim_states"]
                    if claim["state"] == "FALSIFICATION_REQUIRED"
                ),
            },
        )

    plan = {
        "schema": ADAPTATION_SCHEMA,
        "case_id": ensemble["case_id"],
        "task_id": ensemble["task_id"],
        "source_ensemble_sha256": ensemble["ensemble_sha256"],
        "candidate_state": candidate_state,
        "tasks": tasks,
        "preserve_old_forecasts": True,
        "automatic_execution_authorized": False,
        "automatic_adoption_authorized": False,
        "authority": _nonauthority(),
        "note": (
            "Research adaptation only. Tasks may generate new evidence, score/loadout revisions, "
            "or a new forecast version; they cannot erase prior evidence or grant live authority."
        ),
    }
    plan["adaptation_sha256"] = sha256_json(plan)
    return plan
