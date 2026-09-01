"""Reality-calibrated keirin physics foundation v0.

Research-only foundation. This module supplies transparent mechanical equations and
interfaces; it does NOT generate race truth, choose tactics, evaluate C0/C1/N1/PEER,
or claim calibrated Japanese-keirin coefficients.

Design anchors:
- Official active bank-length support: 333/335/400/500 m
  https://www.keirin.jp/pc/dfw/portal/guest/data/bankrecord/bankrecord.html
- Velodrome/cycling physics literature includes aerodynamic drag, rolling resistance,
  drivetrain losses, banking/curve mechanics and multi-rider drafting.

All rider- and race-specific physical parameters must be supplied explicitly or by a
future governed calibration range. No W0-W4 engineering coefficient is inherited.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import atan, degrees, isfinite

STANDARD_GRAVITY_MPS2 = 9.80665
OFFICIAL_ACTIVE_TRACK_LENGTH_SUPPORT_M = frozenset({333, 335, 400, 500})


class PhysicsInputError(ValueError):
    """Raised when a physics input is missing, impossible, or outside the v0 contract."""


def _require_finite_positive(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value <= 0.0:
        raise PhysicsInputError(f"{name} must be finite and > 0")
    return value


def _require_finite_nonnegative(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value < 0.0:
        raise PhysicsInputError(f"{name} must be finite and >= 0")
    return value


@dataclass(frozen=True)
class TrackGeometry:
    venue_id: str
    track_length_m: int
    home_straight_m: float | None = None
    max_cant_deg: float | None = None
    indoor: bool | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        if not self.venue_id:
            raise PhysicsInputError("venue_id is required")
        if int(self.track_length_m) != self.track_length_m or self.track_length_m <= 0:
            raise PhysicsInputError("track_length_m must be a positive integer")
        if self.home_straight_m is not None:
            _require_finite_positive("home_straight_m", self.home_straight_m)
        if self.max_cant_deg is not None:
            cant = float(self.max_cant_deg)
            if not isfinite(cant) or not (0.0 < cant < 90.0):
                raise PhysicsInputError("max_cant_deg must be finite in (0, 90)")

    @property
    def official_length_class_supported(self) -> bool:
        return self.track_length_m in OFFICIAL_ACTIVE_TRACK_LENGTH_SUPPORT_M


@dataclass(frozen=True)
class Environment:
    air_density_kg_m3: float
    relative_air_speed_mps: float

    def __post_init__(self) -> None:
        _require_finite_positive("air_density_kg_m3", self.air_density_kg_m3)
        _require_finite_nonnegative("relative_air_speed_mps", self.relative_air_speed_mps)


@dataclass(frozen=True)
class RiderPhysics:
    total_mass_kg: float
    cda_m2: float
    crr: float
    drivetrain_efficiency: float

    def __post_init__(self) -> None:
        _require_finite_positive("total_mass_kg", self.total_mass_kg)
        _require_finite_positive("cda_m2", self.cda_m2)
        _require_finite_nonnegative("crr", self.crr)
        efficiency = float(self.drivetrain_efficiency)
        if not isfinite(efficiency) or not (0.0 < efficiency <= 1.0):
            raise PhysicsInputError("drivetrain_efficiency must be finite in (0, 1]")


@dataclass(frozen=True)
class KinematicState:
    ground_speed_mps: float
    acceleration_mps2: float = 0.0

    def __post_init__(self) -> None:
        _require_finite_nonnegative("ground_speed_mps", self.ground_speed_mps)
        acceleration = float(self.acceleration_mps2)
        if not isfinite(acceleration):
            raise PhysicsInputError("acceleration_mps2 must be finite")


@dataclass(frozen=True)
class DraftingContext:
    """Externally supplied drag multiplier.

    1.0 means no drag reduction. Values below 1.0 represent a lower aerodynamic
    drag exposure for this rider. v0 deliberately does not infer the multiplier from
    line membership or hard-code a drafting percentage.
    """

    aero_drag_multiplier: float
    provenance_class: str

    def __post_init__(self) -> None:
        multiplier = _require_finite_positive("aero_drag_multiplier", self.aero_drag_multiplier)
        if multiplier > 2.0:
            raise PhysicsInputError("aero_drag_multiplier > 2 is outside the v0 guardrail")
        if not self.provenance_class:
            raise PhysicsInputError("provenance_class is required")


@dataclass(frozen=True)
class PowerBreakdown:
    aerodynamic_force_n: float
    rolling_force_n: float
    inertial_force_n: float
    wheel_mechanical_power_w: float
    rider_input_power_w: float


def aerodynamic_drag_force_n(
    environment: Environment,
    rider: RiderPhysics,
    drafting: DraftingContext,
) -> float:
    """Return aerodynamic drag force using F = 0.5 * rho * CdA * v_rel^2 * multiplier."""

    return (
        0.5
        * environment.air_density_kg_m3
        * rider.cda_m2
        * environment.relative_air_speed_mps**2
        * drafting.aero_drag_multiplier
    )


def rolling_resistance_force_n(
    rider: RiderPhysics,
    normal_force_n: float | None = None,
) -> float:
    """Return Crr * normal force.

    If a future curve module has a better normal-force estimate it must pass it
    explicitly. Otherwise v0 uses body+bicycle weight as a level-ground reference.
    """

    normal = (
        rider.total_mass_kg * STANDARD_GRAVITY_MPS2
        if normal_force_n is None
        else _require_finite_positive("normal_force_n", normal_force_n)
    )
    return rider.crr * normal


def centripetal_force_required_n(total_mass_kg: float, speed_mps: float, curve_radius_m: float) -> float:
    mass = _require_finite_positive("total_mass_kg", total_mass_kg)
    speed = _require_finite_nonnegative("speed_mps", speed_mps)
    radius = _require_finite_positive("curve_radius_m", curve_radius_m)
    return mass * speed**2 / radius


def ideal_bank_angle_deg(speed_mps: float, curve_radius_m: float) -> float:
    """Ideal no-lateral-friction bank angle for a point-mass reference model.

    This is a mechanical reference quantity, NOT a claim that a keirin rider follows
    the ideal-bank condition or a full tyre/steering model.
    """

    speed = _require_finite_nonnegative("speed_mps", speed_mps)
    radius = _require_finite_positive("curve_radius_m", curve_radius_m)
    return degrees(atan(speed**2 / (radius * STANDARD_GRAVITY_MPS2)))


def power_breakdown(
    environment: Environment,
    rider: RiderPhysics,
    kinematics: KinematicState,
    drafting: DraftingContext,
    normal_force_n: float | None = None,
) -> PowerBreakdown:
    """Compute a transparent short-horizon mechanical power breakdown.

    Positive acceleration adds inertial demand. Negative acceleration is retained as a
    signed inertial term, while rider_input_power is floored at zero because v0 does not
    model regenerative braking or detailed dissipative braking work.
    """

    aero = aerodynamic_drag_force_n(environment, rider, drafting)
    rolling = rolling_resistance_force_n(rider, normal_force_n=normal_force_n)
    inertial = rider.total_mass_kg * kinematics.acceleration_mps2
    wheel_power = (aero + rolling + inertial) * kinematics.ground_speed_mps
    rider_input = max(0.0, wheel_power) / rider.drivetrain_efficiency
    return PowerBreakdown(
        aerodynamic_force_n=aero,
        rolling_force_n=rolling,
        inertial_force_n=inertial,
        wheel_mechanical_power_w=wheel_power,
        rider_input_power_w=rider_input,
    )


__all__ = [
    "STANDARD_GRAVITY_MPS2",
    "OFFICIAL_ACTIVE_TRACK_LENGTH_SUPPORT_M",
    "PhysicsInputError",
    "TrackGeometry",
    "Environment",
    "RiderPhysics",
    "KinematicState",
    "DraftingContext",
    "PowerBreakdown",
    "aerodynamic_drag_force_n",
    "rolling_resistance_force_n",
    "centripetal_force_required_n",
    "ideal_bank_angle_deg",
    "power_breakdown",
]
