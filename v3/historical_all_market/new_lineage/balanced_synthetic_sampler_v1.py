from __future__ import annotations

from dataclasses import replace
from typing import Dict, List, Tuple

from digital_twin_v1 import Race, generate_race

RaceBand = str
LineShape = Tuple[int, ...]
Stratum = Tuple[RaceBand, LineShape]

RACE_BANDS: Tuple[RaceBand, ...] = ("S", "A12", "A3")
LINE_SHAPES_7: Tuple[LineShape, ...] = (
    (3, 2, 2),
    (3, 3, 1),
    (2, 2, 2, 1),
)
BANK_CYCLE_M = (333, 400, 500)
WIND_CYCLE_MPS = (0.0, 1.5, 3.0, 5.0)
TARGET_STRATA: Tuple[Stratum, ...] = tuple(
    (band, shape) for band in RACE_BANDS for shape in LINE_SHAPES_7
)


def line_shape(race: Race) -> LineShape:
    groups: Dict[int, int] = {}
    for rider in race.riders:
        groups[rider.line_id] = groups.get(rider.line_id, 0) + 1
    return tuple(sorted(groups.values(), reverse=True))


def balanced_races(
    seed: int,
    repeats_per_stratum: int = 12,
    max_scan: int = 100_000,
) -> List[Race]:
    """Deterministically construct a balanced synthetic PRE sample by rejection selection.

    This does not claim that race bands or line shapes are equally frequent in real keirin.
    Equality here is an engineering control that prevents uncalibrated generator priors from
    deciding an architecture comparison.

    The underlying generator is unchanged. We select an equal number from each of the nine
    race-band x line-shape strata, then give every stratum the same bank/wind stress cycle.
    No RESULT/PAYOUT or protected validation data is used.
    """
    if repeats_per_stratum <= 0:
        raise ValueError("repeats_per_stratum_must_be_positive")

    counts: Dict[Stratum, int] = {key: 0 for key in TARGET_STRATA}
    out: List[Race] = []

    for race_index in range(max_scan):
        if all(v >= repeats_per_stratum for v in counts.values()):
            break

        race = generate_race(
            seed=seed,
            race_index=race_index,
            event_format="STANDARD_FI_FII_7",
        )
        key = (race.race_band, line_shape(race))
        if key not in counts or counts[key] >= repeats_per_stratum:
            continue

        rep = counts[key]
        race = replace(
            race,
            bank_length_m=BANK_CYCLE_M[rep % len(BANK_CYCLE_M)],
            wind_speed_mps=WIND_CYCLE_MPS[rep % len(WIND_CYCLE_MPS)],
        )
        counts[key] += 1
        out.append(race)
    else:
        raise RuntimeError("balanced_sample_max_scan_exhausted")

    if any(v != repeats_per_stratum for v in counts.values()):
        raise RuntimeError(f"balanced_sample_incomplete:{counts}")
    if len(out) != len(TARGET_STRATA) * repeats_per_stratum:
        raise RuntimeError("balanced_sample_size_mismatch")

    # Fail closed if the constructed sample is not exactly balanced.
    observed: Dict[Stratum, int] = {key: 0 for key in TARGET_STRATA}
    for race in out:
        observed[(race.race_band, line_shape(race))] += 1
    if observed != counts:
        raise RuntimeError(f"balanced_sample_verification_failed:{observed}")

    return out


def stratum_counts(races: List[Race]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for race in races:
        band, shape = race.race_band, line_shape(race)
        key = f"{band}|{'-'.join(str(x) for x in shape)}"
        counts[key] = counts.get(key, 0) + 1
    return counts
