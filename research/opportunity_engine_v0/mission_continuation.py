from __future__ import annotations

from typing import Any, Tuple

from .owner_gate import ProposedAction, choose_next_continuable_action


def _research_action(action_id: str, description: str) -> ProposedAction:
    return ProposedAction(
        action_id=action_id,
        description=description,
        reversible_repository_only=True,
    )


def derive_continuation_actions(mission_plan: dict[str, Any]) -> Tuple[ProposedAction, ...]:
    """Translate mission blockers/posture into ordered next actions.

    Research work is always preferred before any action that would require Owner
    authority. This is intentionally conservative: it only proposes reversible
    repository-only work from known blocker classes.
    """
    if not isinstance(mission_plan, dict) or not mission_plan.get("case_id"):
        raise ValueError("valid mission_plan is required")

    blockers = tuple(mission_plan.get("blockers", ()))
    actions: list[ProposedAction] = []

    mapping = {
        "COMPETITOR_RESEARCH_INCOMPLETE": _research_action(
            "research-competitors",
            "Complete competitor, substitute, incumbent and general-AI replacement research.",
        ),
        "LEVERAGE_SEARCH_INCOMPLETE": _research_action(
            "research-leverage",
            "Complete leverage scan across distribution, automation, AI, monetization, data, reuse, geography and infrastructure.",
        ),
        "LOADOUT_NOT_READY": _research_action(
            "prepare-loadout",
            "Prepare a bounded low/base/high loadout without spending or live execution.",
        ),
        "TACTIC_SEQUENCE_NOT_READY": _research_action(
            "prepare-tactic-sequence",
            "Prepare reversible tactic ordering, checkpoints and exit triggers.",
        ),
        "FORECAST_NOT_FROZEN": _research_action(
            "freeze-forecast",
            "Create and commitment-freeze a forecast before any measured outcome exists.",
        ),
        "GROWTH_LOOP_NOT_ASSESSED": _research_action(
            "assess-growth-loop",
            "Assess whether a real bidirectional value loop exists without assuming virality.",
        ),
    }

    for blocker in blockers:
        if blocker in mapping:
            actions.append(mapping[blocker])
            continue
        if blocker.startswith("GROWTH_LOOP_") and blocker != "GROWTH_LOOP_UNSAFE_OR_POLICY_FRAGILE":
            actions.append(_research_action(
                "research-growth-loop",
                "Research and repair the growth-loop hypothesis without live posting, spend or platform actions.",
            ))
            continue
        if blocker in {
            "REVIEW_INDEPENDENCE_INSUFFICIENT",
            "REVIEW_MORE_EVIDENCE_OR_REVISION",
            "REVIEW_FALSIFICATION_REQUIRED",
            "REVIEW_REVIEW_INCOMPLETE",
        }:
            actions.append(_research_action(
                "prepare-more-evidence",
                "Collect repository-available evidence, local falsification cases and review-ready material without invoking live providers.",
            ))
            continue

    if "LEGAL_OR_SAFETY_HOLD" in blockers or "GROWTH_LOOP_UNSAFE_OR_POLICY_FRAGILE" in blockers:
        actions.append(_research_action(
            "resolve-safety-research",
            "Research a compliant, non-deceptive alternative or document a rejection rationale; do not execute the unsafe path.",
        ))

    if not actions:
        posture = mission_plan.get("mission_posture")
        if isinstance(posture, str) and posture.endswith("READY_FOR_GOVERNED_GATE"):
            actions.append(ProposedAction(
                action_id="request-governed-gate",
                description="Advance this exact research packet to the next governed gate.",
                reversible_repository_only=False,
                grants_adoption_or_merge_authority=True,
            ))
        else:
            actions.append(_research_action(
                "audit-mission-completeness",
                "Audit the mission packet for unresolved evidence, forecast, review or lifecycle gaps.",
            ))

    return tuple(actions)


def choose_mission_continuation(mission_plan: dict[str, Any]) -> dict[str, object]:
    """Choose the next step and interrupt Owner only when useful research is exhausted."""
    actions = derive_continuation_actions(mission_plan)
    selected = choose_next_continuable_action(actions)
    return {
        "case_id": mission_plan["case_id"],
        "mission_posture": mission_plan.get("mission_posture"),
        "candidate_action_ids": [a.action_id for a in actions],
        **selected,
        "automatic_execution_authorized": False,
        "spend_authorized": False,
        "provider_call_authorized": False,
        "publication_authorized": False,
        "runtime_activation_authorized": False,
    }
