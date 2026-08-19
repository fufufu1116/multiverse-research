from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
import math
import random
from typing import Dict, List, Mapping, Tuple

Top3 = Tuple[int, int, int]


@dataclass(frozen=True)
class Rider:
    car_no: int
    rider_class: str
    latent_skill: float
    observed_score: float
    style: str
    H: float
    B: float
    S: float
    nige: float
    makuri: float
    sashi: float
    mark: float
    line_id: int
    line_position: int
    line_size: int


@dataclass(frozen=True)
class Race:
    race_id: str
    regime: str
    race_band: str
    bank_length_m: int
    wind_speed_mps: float
    riders: Tuple[Rider, ...]


def _softmax(values: Mapping[int, float]) -> Dict[int, float]:
    m = max(values.values())
    ex = {k: math.exp(v - m) for k, v in values.items()}
    z = sum(ex.values())
    return {k: v / z for k, v in ex.items()}


def _line_templates(n: int, rng: random.Random) -> List[List[int]]:
    """Synthetic line structures; shapes are scenario motifs, not claimed frequencies."""
    cars = list(range(1, n + 1))
    rng.shuffle(cars)
    if n == 9:
        shapes = [[3, 3, 3], [3, 2, 2, 1, 1], [3, 3, 2, 1]]
    elif n == 7:
        shapes = [[3, 2, 2], [3, 3, 1], [2, 2, 2, 1]]
    else:
        shape: List[int] = []
        left = n
        while left:
            k = min(3, left)
            shape.append(k)
            left -= k
        shapes = [shape]

    shape = rng.choice(shapes)
    out: List[List[int]] = []
    p = 0
    for size in shape:
        out.append(cars[p:p + size])
        p += size
    return out


def _class_for_band(race_band: str, rng: random.Random) -> str:
    if race_band == "S":
        return rng.choices(["S1", "S2"], weights=[0.35, 0.65], k=1)[0]
    if race_band == "A12":
        return rng.choices(["A1", "A2"], weights=[0.48, 0.52], k=1)[0]
    if race_band == "A3":
        return "A3"
    raise ValueError(race_band)


def _style_for_position(line_position: int, line_size: int, rng: random.Random) -> str:
    # Head riders are more often self-powered; followers are more often chasing types.
    # These are synthetic scenario priors, not empirical frequency claims.
    if line_size == 1:
        weights = [0.24, 0.46, 0.30]
    elif line_position == 0:
        weights = [0.42, 0.38, 0.20]
    else:
        weights = [0.08, 0.28, 0.64]
    return rng.choices(["逃", "両", "追"], weights=weights, k=1)[0]


def generate_race(seed: int, race_index: int, n_riders: int | None = None) -> Race:
    """Generate one synthetic PRE race with hidden truth separated from observable PRE."""
    rng = random.Random(f"keirin-dt:{seed}:{race_index}")
    n = n_riders or rng.choice([7, 9])
    if n < 3:
        raise ValueError("race requires >=3 riders")

    race_band = rng.choices(["S", "A12", "A3"], weights=[0.32, 0.43, 0.25], k=1)[0]
    bank = rng.choice([333, 400, 500])
    wind = max(0.0, rng.gauss(2.2, 1.4))
    regime = "STANDARD_ORIGINAL_LINE_KEIRIN"
    lines = _line_templates(n, rng)

    membership: Dict[int, Tuple[int, int, int]] = {}
    for line_id, members in enumerate(lines, start=1):
        size = len(members)
        for pos, car in enumerate(members):
            membership[car] = (line_id, pos, size)

    riders: List[Rider] = []
    for car in range(1, n + 1):
        rider_class = _class_for_band(race_band, rng)
        line_id, line_pos, line_size = membership[car]
        style = _style_for_position(line_pos, line_size, rng)

        latent = rng.gauss(0.0, 1.0)
        observed = latent + rng.gauss(0.0, 0.55)

        if style == "逃":
            tactical = (1.2, 1.0, 0.35, 1.1, 0.65, 0.25, 0.20)
        elif style == "両":
            tactical = (0.65, 0.65, 0.45, 0.55, 1.05, 0.60, 0.30)
        else:
            tactical = (0.25, 0.25, 0.60, 0.15, 0.35, 1.00, 0.95)

        vals = [max(0.0, rng.gauss(mu, 0.28)) for mu in tactical]
        riders.append(
            Rider(
                car_no=car,
                rider_class=rider_class,
                latent_skill=latent,
                observed_score=observed,
                style=style,
                H=vals[0],
                B=vals[1],
                S=vals[2],
                nige=vals[3],
                makuri=vals[4],
                sashi=vals[5],
                mark=vals[6],
                line_id=line_id,
                line_position=line_pos,
                line_size=line_size,
            )
        )

    return Race(
        race_id=f"SYN_{seed}_{race_index}",
        regime=regime,
        race_band=race_band,
        bank_length_m=bank,
        wind_speed_mps=wind,
        riders=tuple(riders),
    )


def pre_view(race: Race) -> Dict[str, object]:
    """Only the synthetic information visible to a PRE-only prediction model."""
    line_ids = {r.line_id for r in race.riders}
    return {
        "race_id": race.race_id,
        "race_regime": race.regime,
        "race_band": race.race_band,
        "bank_length_m": race.bank_length_m,
        "wind_speed_mps": race.wind_speed_mps,
        "num_lines": len(line_ids),
        "riders": [
            {
                "car_no": r.car_no,
                "class": r.rider_class,
                "score": r.observed_score,
                "style": r.style,
                "H": r.H,
                "B": r.B,
                "S": r.S,
                "nige": r.nige,
                "makuri": r.makuri,
                "sashi": r.sashi,
                "mark": r.mark,
                "line_group_id": r.line_id,
                "line_position": r.line_position,
                "line_size": r.line_size,
                "is_singleton": r.line_size == 1,
            }
            for r in race.riders
        ],
    }


def _class_term(rider_class: str) -> float:
    return {
        "S1": 0.08,
        "S2": -0.03,
        "A1": 0.05,
        "A2": -0.03,
        "A3": 0.0,
    }[rider_class]


def _base_utility(r: Rider, race: Race) -> float:
    style_term = {"逃": 0.06, "両": 0.04, "追": 0.0}[r.style]
    wind_penalty = 0.035 * race.wind_speed_mps * (1.0 if r.style == "逃" else 0.25)
    bank_term = 0.04 if (race.bank_length_m <= 333 and r.style in {"逃", "両"}) else 0.0
    return r.latent_skill + _class_term(r.rider_class) + style_term + bank_term - wind_penalty


def _line_strengths(race: Race) -> Dict[int, float]:
    groups: Dict[int, List[float]] = {}
    for r in race.riders:
        groups.setdefault(r.line_id, []).append(r.latent_skill)
    return {line: sum(vals) / len(vals) for line, vals in groups.items()}


def _static_utilities(race: Race, use_line: bool) -> Dict[int, float]:
    line_strength = _line_strengths(race)
    out: Dict[int, float] = {}
    for r in race.riders:
        value = _base_utility(r, race)
        if use_line:
            pos_bonus = {0: 0.04, 1: 0.10, 2: 0.05}.get(r.line_position, 0.0)
            size_bonus = 0.025 * max(0, r.line_size - 1)
            value += 0.16 * line_strength[r.line_id] + pos_bonus + size_bonus
        out[r.car_no] = value
    return out


def _joint_from_utilities(
    race: Race,
    util: Mapping[int, float],
    relation_strength: float,
) -> Dict[Top3, float]:
    cars = [r.car_no for r in race.riders]
    rider = {r.car_no: r for r in race.riders}
    p1 = _softmax(util)
    joint: Dict[Top3, float] = {}

    for i, j, k in permutations(cars, 3):
        rem2 = [c for c in cars if c != i]
        if relation_strength <= 0.0:
            p2 = _softmax({c: util[c] for c in rem2})
            rem3 = [c for c in rem2 if c != j]
            p3 = _softmax({c: util[c] for c in rem3})
        else:
            ri = rider[i]
            u2: Dict[int, float] = {}
            for c in rem2:
                rc = rider[c]
                same = 1.0 if rc.line_id == ri.line_id else 0.0
                follower = 1.0 if same and rc.line_position == ri.line_position + 1 else 0.0
                u2[c] = util[c] + relation_strength * (0.30 * same + 0.28 * follower)
            p2 = _softmax(u2)

            rem3 = [c for c in rem2 if c != j]
            rj = rider[j]
            u3: Dict[int, float] = {}
            for c in rem3:
                rc = rider[c]
                same_i = 1.0 if rc.line_id == ri.line_id else 0.0
                same_j = 1.0 if rc.line_id == rj.line_id else 0.0
                chain = 1.0 if (
                    ri.line_id == rj.line_id == rc.line_id
                    and ri.line_position < rj.line_position < rc.line_position
                ) else 0.0
                u3[c] = util[c] + relation_strength * (
                    0.17 * same_i + 0.14 * same_j + 0.30 * chain
                )
            p3 = _softmax(u3)

        joint[(i, j, k)] = p1[i] * p2[j] * p3[k]

    z = sum(joint.values())
    return {key: value / z for key, value in joint.items()}


def _deterministic_shock_utilities(
    race: Race,
    base_util: Mapping[int, float],
    sigma: float,
    temperature: float,
    tag: str,
) -> Dict[int, float]:
    out: Dict[int, float] = {}
    for car_no, value in base_util.items():
        rng = random.Random(f"{tag}:{race.race_id}:{car_no}")
        shock = rng.gauss(0.0, sigma)
        out[car_no] = value / temperature + shock
    return out


def _mix_joint(a: Mapping[Top3, float], b: Mapping[Top3, float], weight_b: float) -> Dict[Top3, float]:
    keys = set(a) | set(b)
    out = {k: (1.0 - weight_b) * a.get(k, 0.0) + weight_b * b.get(k, 0.0) for k in keys}
    z = sum(out.values())
    return {k: v / z for k, v in out.items()}


def world_joint_distribution(race: Race, world: str) -> Dict[Top3, float]:
    """Exact ordered-top3 truth distribution for five distinct synthetic worlds.

    W0: individual ability/context dominates; no line effect.
    W1: static line strength/position matters but ordering remains PL-like.
    W2: rank-2/rank-3 explicitly depend on line relations after earlier finishers are known.
    W3: W2-like race with meaningful probability of line disruption / performance shock.
    W4: high-uncertainty upset world; favorite/line structure is less reliable.

    These worlds are stress scenarios, not claims about real-keirin frequencies.
    """
    if world not in {"W0", "W1", "W2", "W3", "W4"}:
        raise ValueError(f"unknown world {world}")

    if world == "W0":
        return _joint_from_utilities(race, _static_utilities(race, use_line=False), relation_strength=0.0)

    stable_util = _static_utilities(race, use_line=True)
    if world == "W1":
        return _joint_from_utilities(race, stable_util, relation_strength=0.0)

    stable_joint = _joint_from_utilities(race, stable_util, relation_strength=1.0)
    if world == "W2":
        return stable_joint

    if world == "W3":
        disrupted_util = _deterministic_shock_utilities(
            race,
            _static_utilities(race, use_line=False),
            sigma=0.50,
            temperature=1.10,
            tag="W3-disruption",
        )
        disrupted_joint = _joint_from_utilities(race, disrupted_util, relation_strength=0.15)
        return _mix_joint(stable_joint, disrupted_joint, weight_b=0.28)

    upset_util = _deterministic_shock_utilities(
        race,
        _static_utilities(race, use_line=False),
        sigma=0.85,
        temperature=1.65,
        tag="W4-upset",
    )
    upset_joint = _joint_from_utilities(race, upset_util, relation_strength=0.0)
    return _mix_joint(stable_joint, upset_joint, weight_b=0.42)


def sample_top3(joint: Mapping[Top3, float], rng: random.Random) -> Top3:
    x = rng.random()
    acc = 0.0
    last: Top3 | None = None
    for outcome, p in joint.items():
        last = outcome
        acc += p
        if x <= acc:
            return outcome
    if last is None:
        raise ValueError("empty joint")
    return last


def generate_world_batch(seed: int, n_races: int, world: str) -> List[Dict[str, object]]:
    """Generate PRE + hidden synthetic outcome + exact oracle joint for stress testing."""
    offsets = {"W0": 1000, "W1": 2000, "W2": 3000, "W3": 4000, "W4": 5000}
    if world not in offsets:
        raise ValueError(world)

    out: List[Dict[str, object]] = []
    rng = random.Random(seed + offsets[world])
    for idx in range(n_races):
        race = generate_race(seed=seed, race_index=idx)
        joint = world_joint_distribution(race, world)
        outcome = sample_top3(joint, rng)
        out.append(
            {
                "world": world,
                "pre": pre_view(race),
                "outcome_top3": outcome,
                "oracle_joint": joint,
            }
        )
    return out
