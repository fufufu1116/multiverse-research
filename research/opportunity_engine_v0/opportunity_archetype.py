from __future__ import annotations

from enum import Enum


class OpportunityArchetype(str, Enum):
    SHORT_WAVE_ONE_HIT = "SHORT_WAVE_ONE_HIT"
    RECURRING_BURST = "RECURRING_BURST"
    DURABLE_COMPOUNDER = "DURABLE_COMPOUNDER"
    EXPERIMENT_ONLY = "EXPERIMENT_ONLY"


UI_LABELS = {
    OpportunityArchetype.SHORT_WAVE_ONE_HIT: "使い切り百人将",
    OpportunityArchetype.RECURRING_BURST: "再出撃型百人将",
    OpportunityArchetype.DURABLE_COMPOUNDER: "昇格候補",
    OpportunityArchetype.EXPERIMENT_ONLY: "訓練候補",
}


def _small_score(value: int, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 5:
        raise ValueError(f"{name} must be an integer from 0 to 5")
    return value


def classify_opportunity_archetype(
    *,
    demand_life_days: int,
    build_days: int,
    payback_days: int,
    spike_concentration_pct: int,
    recurrence_score: int,
    repeatability_score: int,
    durable_asset_score: int,
    exit_trigger_defined: bool,
) -> OpportunityArchetype:
    """Classify operating shape without confusing one big hit with durable scale."""
    for value, name in (
        (demand_life_days, "demand_life_days"),
        (build_days, "build_days"),
        (payback_days, "payback_days"),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{name} must be a nonnegative integer")
    if not isinstance(spike_concentration_pct, int) or isinstance(spike_concentration_pct, bool) or not 0 <= spike_concentration_pct <= 100:
        raise ValueError("spike_concentration_pct must be an integer from 0 to 100")
    recurrence = _small_score(recurrence_score, "recurrence_score")
    repeatability = _small_score(repeatability_score, "repeatability_score")
    durable_asset = _small_score(durable_asset_score, "durable_asset_score")
    if not isinstance(exit_trigger_defined, bool):
        raise ValueError("exit_trigger_defined must be boolean")

    short_lived = demand_life_days <= 90
    fast_build = build_days <= max(2, int(demand_life_days * 0.10))
    fast_payback = payback_days <= max(7, int(demand_life_days * 0.25))

    if (
        short_lived
        and spike_concentration_pct >= 60
        and fast_build
        and fast_payback
        and exit_trigger_defined
    ):
        return OpportunityArchetype.SHORT_WAVE_ONE_HIT
    if short_lived and recurrence >= 3 and exit_trigger_defined:
        return OpportunityArchetype.RECURRING_BURST
    if demand_life_days >= 365 and repeatability >= 3 and durable_asset >= 3:
        return OpportunityArchetype.DURABLE_COMPOUNDER
    return OpportunityArchetype.EXPERIMENT_ONLY


def ui_label(archetype: OpportunityArchetype) -> str:
    return UI_LABELS[archetype]
