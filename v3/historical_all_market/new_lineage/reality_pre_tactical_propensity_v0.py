"""PRE-observable ordinal tactical evidence for the Reality foundation.

This module converts point-in-time historical PRE counts into ordinal evidence only.
It deliberately does not assign on-track event probabilities or finish effects.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


class TacticalPropensityError(ValueError):
    pass


_BANDS = ("VERY_LOW", "LOW", "MID", "HIGH", "VERY_HIGH")
_FEATURES = ("ST", "BK", "nige", "makuri", "sashi", "mark")


def ordinal_band(registry: Mapping[str, object], class_band: str, feature: str, value: float) -> str:
    if feature not in _FEATURES:
        raise TacticalPropensityError("unsupported tactical evidence feature")
    if not isfinite(float(value)) or float(value) < 0:
        raise TacticalPropensityError("finite nonnegative observation required")
    classes = registry.get("class_conditional_thresholds")
    if not isinstance(classes, Mapping) or class_band not in classes:
        raise TacticalPropensityError("unknown class band")
    class_row = classes[class_band]
    if not isinstance(class_row, Mapping) or feature not in class_row:
        raise TacticalPropensityError("missing class-feature thresholds")
    t = class_row[feature]
    if not isinstance(t, Mapping):
        raise TacticalPropensityError("invalid threshold object")
    q05 = float(t["q05"])
    q25 = float(t["q25"])
    q75 = float(t["q75"])
    q95 = float(t["q95"])
    if not q05 <= q25 <= q75 <= q95:
        raise TacticalPropensityError("non-monotone tactical thresholds")
    x = float(value)
    if x <= q05:
        return "VERY_LOW"
    if x <= q25:
        return "LOW"
    if x < q75:
        return "MID"
    if x < q95:
        return "HIGH"
    return "VERY_HIGH"


def successful_finish_technique_mix(nige: float, makuri: float, sashi: float, mark: float) -> Mapping[str, float] | None:
    vals = [float(nige), float(makuri), float(sashi), float(mark)]
    if any((not isfinite(v) or v < 0) for v in vals):
        raise TacticalPropensityError("finite nonnegative technique counts required")
    total = sum(vals)
    if total <= 0:
        return None
    return {
        "nige": vals[0] / total,
        "makuri": vals[1] / total,
        "sashi": vals[2] / total,
        "mark": vals[3] / total,
    }


def successful_finish_lean(nige: float, makuri: float, sashi: float, mark: float) -> str:
    front = float(nige) + float(makuri)
    following = float(sashi) + float(mark)
    if any((not isfinite(v) or v < 0) for v in (front, following)):
        raise TacticalPropensityError("finite nonnegative technique counts required")
    if front == 0 and following == 0:
        return "NO_SIGNAL"
    if front > following:
        return "SELF_POWERED_LEAN"
    if following > front:
        return "FOLLOWING_LEAN"
    return "BALANCED"


@dataclass(frozen=True)
class TacticalEvidenceProfile:
    rider_id: str
    class_band: str
    style: str
    early_position_band: str
    late_front_exposure_band: str
    nige_band: str
    makuri_band: str
    sashi_band: str
    mark_band: str
    successful_technique_lean: str
    successful_technique_mix: Mapping[str, float] | None

    def evidence_tags_for_expected_line_position(self, zero_based_line_position: int) -> tuple[str, ...]:
        if zero_based_line_position < 0:
            raise TacticalPropensityError("line position must be nonnegative")
        tags = ["EXPECTED_FRONT_ROLE" if zero_based_line_position == 0 else "EXPECTED_FOLLOW_ROLE"]
        if self.style in {"逃", "両"}:
            tags.append("STYLE_SUPPORTS_SELF_POWERED_ACTION")
        if self.style in {"追", "両"}:
            tags.append("STYLE_SUPPORTS_FOLLOWING_ACTION")
        if self.early_position_band in {"HIGH", "VERY_HIGH"}:
            tags.append("PRE_HISTORY_SUPPORTS_EARLY_FRONT_POSITION")
        if self.late_front_exposure_band in {"HIGH", "VERY_HIGH"}:
            tags.append("PRE_HISTORY_SUPPORTS_LATE_FRONT_EXPOSURE")
        if self.successful_technique_lean == "SELF_POWERED_LEAN":
            tags.append("SUCCESSFUL_HISTORY_SELF_POWERED_LEAN")
        elif self.successful_technique_lean == "FOLLOWING_LEAN":
            tags.append("SUCCESSFUL_HISTORY_FOLLOWING_LEAN")
        elif self.successful_technique_lean == "BALANCED":
            tags.append("SUCCESSFUL_HISTORY_BALANCED")
        else:
            tags.append("SUCCESSFUL_HISTORY_NO_SIGNAL")
        return tuple(tags)


def build_tactical_evidence_profile(
    registry: Mapping[str, object],
    rider_id: str,
    class_band: str,
    style: str,
    *,
    ST: float,
    BK: float,
    nige: float,
    makuri: float,
    sashi: float,
    mark: float,
) -> TacticalEvidenceProfile:
    if not rider_id:
        raise TacticalPropensityError("rider_id required")
    if style not in {"逃", "両", "追"}:
        raise TacticalPropensityError("unsupported style")
    return TacticalEvidenceProfile(
        rider_id=rider_id,
        class_band=class_band,
        style=style,
        early_position_band=ordinal_band(registry, class_band, "ST", ST),
        late_front_exposure_band=ordinal_band(registry, class_band, "BK", BK),
        nige_band=ordinal_band(registry, class_band, "nige", nige),
        makuri_band=ordinal_band(registry, class_band, "makuri", makuri),
        sashi_band=ordinal_band(registry, class_band, "sashi", sashi),
        mark_band=ordinal_band(registry, class_band, "mark", mark),
        successful_technique_lean=successful_finish_lean(nige, makuri, sashi, mark),
        successful_technique_mix=successful_finish_technique_mix(nige, makuri, sashi, mark),
    )


def event_probability(*_args: object, **_kwargs: object) -> float:
    raise TacticalPropensityError("PRE tactical evidence does not identify an on-track event probability")


def finish_effect(*_args: object, **_kwargs: object) -> float:
    raise TacticalPropensityError("PRE tactical evidence does not identify a finish effect")
