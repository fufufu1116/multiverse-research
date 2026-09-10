from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path
from typing import Any, Dict, Mapping

from .engine import evaluate
from .model import CompetitorResearch, OpportunityCandidate


_CANDIDATE_FIELDS = {field.name for field in fields(OpportunityCandidate)}
_COMPETITOR_FIELDS = {field.name for field in fields(CompetitorResearch)}


def _strict_keys(data: Mapping[str, Any], allowed: set[str], *, label: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ValueError(f"{label} contains unknown fields: {', '.join(unknown)}")


def candidate_from_mapping(data: Mapping[str, Any]) -> OpportunityCandidate:
    _strict_keys(data, _CANDIDATE_FIELDS, label="candidate")
    raw = dict(data)

    competitor = raw.get("competitor_research")
    if not isinstance(competitor, Mapping):
        raise ValueError("competitor_research must be an object")
    _strict_keys(competitor, _COMPETITOR_FIELDS, label="competitor_research")

    competitor_data = dict(competitor)
    for tuple_field in ("existing_systems_to_reuse", "notes"):
        if tuple_field in competitor_data:
            competitor_data[tuple_field] = tuple(competitor_data[tuple_field])
    raw["competitor_research"] = CompetitorResearch(**competitor_data)

    if "future_steps" in raw:
        raw["future_steps"] = tuple(raw["future_steps"])

    return OpportunityCandidate(**raw)


def evaluate_packet(data: Mapping[str, Any]) -> Dict[str, Any]:
    result = evaluate(candidate_from_mapping(data))
    return {
        "decision": result.decision.value,
        "score": result.score,
        "revenue_route": result.revenue_route.value,
        "reasons": list(result.reasons),
        "hard_failures": list(result.hard_failures),
    }


def evaluate_packet_file(path: str | Path) -> Dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("packet root must be an object")
    return evaluate_packet(payload)
