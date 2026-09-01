"""Reality environment transport v1.

Foundation only. Forecasts are never admitted as Reality observations or required PRE.
Environment is optional until a separately governed necessity ablation establishes value.
No network access, no truth generation, no model calls, no outcome/economic use.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite


class RealityEnvironmentError(ValueError):
    pass


def _dt(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except Exception as exc:
        raise RealityEnvironmentError(f"invalid ISO timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise RealityEnvironmentError("timestamp must be timezone-aware")
    return parsed


class EnvironmentEvidenceKind(str, Enum):
    OBSERVED_OFFICIAL_STATION = "OBSERVED_OFFICIAL_STATION"
    OBSERVED_VENUE_SENSOR = "OBSERVED_VENUE_SENSOR"
    FORECAST = "FORECAST"
    NOWCAST_OR_MODEL_OUTPUT = "NOWCAST_OR_MODEL_OUTPUT"
    CLIMATOLOGY_OR_GENERIC_PROXY = "CLIMATOLOGY_OR_GENERIC_PROXY"


class EnvironmentUseRole(str, Enum):
    NO_ENVIRONMENT_BASELINE = "NO_ENVIRONMENT_BASELINE"
    OPTIONAL_PHYSICS_SENSITIVITY = "OPTIONAL_PHYSICS_SENSITIVITY"


@dataclass(frozen=True)
class EnvironmentObservation:
    venue_id: str
    evidence_kind: EnvironmentEvidenceKind
    observation_timestamp: str
    capture_timestamp: str
    decision_timestamp: str
    source_url: str
    source_class: str
    provenance_sha: str
    venue_station_mapping_source: str | None
    wind_speed_mps: float | None = None
    wind_direction: str | None = None
    temperature_c: float | None = None
    precipitation_mm: float | None = None

    def __post_init__(self) -> None:
        if self.evidence_kind not in {
            EnvironmentEvidenceKind.OBSERVED_OFFICIAL_STATION,
            EnvironmentEvidenceKind.OBSERVED_VENUE_SENSOR,
        }:
            raise RealityEnvironmentError("forecast/model/proxy environment is not an observation and is prohibited")

        obs = _dt(self.observation_timestamp)
        capture = _dt(self.capture_timestamp)
        decision = _dt(self.decision_timestamp)
        if obs > decision:
            raise RealityEnvironmentError("environment observation occurs after decision cutoff")
        if capture < obs:
            raise RealityEnvironmentError("capture_timestamp cannot precede observation_timestamp")
        if capture > decision:
            raise RealityEnvironmentError("environment was not decision-available: captured after cutoff")

        if not self.venue_id or not self.source_url or not self.source_class or not self.provenance_sha:
            raise RealityEnvironmentError("environment provenance is required")
        if self.evidence_kind is EnvironmentEvidenceKind.OBSERVED_OFFICIAL_STATION and not self.venue_station_mapping_source:
            raise RealityEnvironmentError("official-station observation requires venue-to-station mapping provenance")

        if self.wind_speed_mps is not None:
            v = float(self.wind_speed_mps)
            if not isfinite(v) or v < 0:
                raise RealityEnvironmentError("wind_speed_mps must be finite and >= 0")
        if (self.wind_speed_mps is None) != (self.wind_direction is None):
            raise RealityEnvironmentError("wind speed and direction must be present together or both missing")
        if self.temperature_c is not None and not isfinite(float(self.temperature_c)):
            raise RealityEnvironmentError("temperature_c must be finite")
        if self.precipitation_mm is not None:
            p = float(self.precipitation_mm)
            if not isfinite(p) or p < 0:
                raise RealityEnvironmentError("precipitation_mm must be finite and >= 0")


def validate_environment_use(
    role: EnvironmentUseRole,
    observation: EnvironmentObservation | None,
    *,
    venue_is_indoor_or_wind_shielded: bool,
    max_observation_age_seconds: int | None = None,
) -> None:
    if role is EnvironmentUseRole.NO_ENVIRONMENT_BASELINE:
        if observation is not None:
            raise RealityEnvironmentError("no-environment baseline must not carry environment inputs")
        return

    if role is not EnvironmentUseRole.OPTIONAL_PHYSICS_SENSITIVITY:
        raise RealityEnvironmentError("unsupported environment use role")
    if observation is None:
        raise RealityEnvironmentError("optional physics sensitivity requires an admitted observation")
    if venue_is_indoor_or_wind_shielded and observation.wind_speed_mps is not None:
        raise RealityEnvironmentError("outdoor wind must not be injected into an indoor/wind-shielded venue without a venue-sensor contract")
    if max_observation_age_seconds is None or max_observation_age_seconds < 0:
        raise RealityEnvironmentError("observation age limit must be prespecified for each sensitivity test")
    age = (_dt(observation.decision_timestamp) - _dt(observation.observation_timestamp)).total_seconds()
    if age > max_observation_age_seconds:
        raise RealityEnvironmentError("environment observation is too stale for the prespecified test")


def weather_is_required_for_reality_baseline() -> bool:
    """Frozen policy: environment is not required unless future governed evidence changes it."""
    return False
