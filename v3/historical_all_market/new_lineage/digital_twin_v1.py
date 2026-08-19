from __future__ import annotations

from dataclasses import dataclass, asdict
from itertools import permutations
import math
import random
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

Top3 = Tuple[int, int, int]


@dataclass(frozen=True)
class Rider:
    car_no: int
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


@dataclass(frozen=True)
class Race:
    race_id: str
    regime: str
    bank_length_m: int
    wind_speed_mps: float
    riders: Tuple[Rider, ...]


def _softmax(values: Mapping[int, float]) -> Dict[int, float]:
    m = max(values.values())
    ex = {k: math.exp(v - m) for k, v in values.items()}
    z = sum(ex.values())
    return {k: v / z for k, v in ex.items()}


def _line_templates(n: int, rng: random.Random) -> List[List[int]]:
    """Return within-race line member car numbers. Synthetic only.

    Uses common structural motifs rather than claiming exact real-world frequencies.
    """
    cars = list(range(1, n + 1))
    rng.shuffle(cars)
    if n == 9:
        choices = [[3, 3, 3], [3, 2, 2, 1, 1], [3, 3, 2, 1]]
    elif n == 7:
        choices = [[3, 2, 2], [3, 3, 1], [2, 2, 2, 1]]
    else:
        # fail-safe generic partition into 1-3 rider units
        choices = []
        left = n
        shape = []
        while left:
            k = min(3, left)
            shape.append(k)
            left -= k
        choices.append(shape)
    shape = rng.choice(choices)
    out: List[List[int]] = []
    p = 0
    for size in shape:
        out.append(cars[p:p + size])
        p += size
    return out


def generate_race(seed: int, race_index: int, n_riders: int | None = None) -> Race:
    """Generate a synthetic PRE race while keeping latent truth hidden from PRE fields."""
    rng = random.Random((seed, race_index).__hash__())
    n = n_riders or rng.choice([7, 9])
    if n < 3:
        raise ValueError("race requires >=3 riders")

    bank = rng.choice([333, 400, 500])
    wind = max(0.0, rng.gauss(2.2, 1.4))
    regime = "STANDARD_ORIGINAL_LINE_KEIRIN"
    lines = _line_templates(n, rng)

    membership: Dict[int, Tuple[int, int]] = {}
    for line_id, members in enumerate(lines, start=1):
        for pos, car in enumerate(members):
            membership[car] = (line_id, pos)

    riders: List[Rider] = []
    for car in range(1, n + 1):
        latent = rng.gauss(0.0, 1.0)
        # PRE score is informative but noisy; simulator retains hidden performance variance.
        observed = latent + rng.gauss(0.0, 0.55)
        style = rng.choices(["逃", "両", "追"], weights=[0.24, 0.31, 0.45], k=1)[0]

        if style == "逃":
            tactical = (1.2, 1.0, 0.35, 1.1, 0.65, 0.25, 0.20)
        elif style == "両":
            tactical = (0.65, 0.65, 0.45, 0.55, 1.05, 0.60, 0.30)
        else:
            tactical = (0.25, 0.25, 0.60, 0.15, 0.35, 1.00, 0.95)

        vals = [max(0.0, rng.gauss(mu, 0.28)) for mu in tactical]
        line_id, line_pos = membership[car]
        riders.append(
            Rider(
                car_no=car,
                latent_skill=latent,
                observed_score=observed,
                style=style,
                H=vals[0], B=vals[1], S=vals[2],
                nige=vals[3], makuri=vals[4], sashi=vals[5], mark=vals[6],
                line_id=line_id,
                line_position=line_pos,
            )
        )

    return Race(
        race_id=f"SYN_{seed}_{race_index}",
        regime=regime,
        bank_length_m=bank,
        wind_speed_mps=wind,
        riders=tuple(riders),
    )


def pre_view(race: Race) -> Dict[str, object]:
    """Return only information a model is allowed to see in the synthetic PRE layer."""
    return {
        "race_id": race.race_id,
        "race_regime": race.regime,
        "bank_length_m": race.bank_length_m,
        "wind_speed_mps": race.wind_speed_mps,
        "riders": [
            {
                "car_no": r.car_no,
                "score": r.observed_score,
                "style": r.style,
                "H": r.H, "B": r.B, "S": r.S,
                "nige": r.nige, "makuri": r.makuri,
                "sashi": r.sashi, "mark": r.mark,
                "line_group_id": r.line_id,
                "line_position": r.line_position,
            }
            for r in race.riders
        ],
    }


def _base_utility(r: Rider, race: Race) -> float:
    style_term = {"逃": 0.06, "両": 0.04, "追": 0.0}[r.style]
    # Hidden race-performance truth may depend weakly on bank/wind interaction.
    wind_penalty = 0.035 * race.wind_speed_mps * (1.0 if r.style == "逃" else 0.25)
    bank_term = 0.04 if (race.bank_length_m <= 333 and r.style in {"逃", "両"}) else 0.0
    return r.latent_skill + style_term + bank_term - wind_penalty


def _line_strengths(race: Race) -> Dict[int, float]:
    groups: Dict[int, List[float]] = {}
    for r in race.riders:
        groups.setdefault(r.line_id, []).append(r.latent_skill)
    return {line: sum(vals) / len(vals) for line, vals in groups.items()}


def world_joint_distribution(race: Race, world: str) -> Dict[Top3, float]:
    """Exact ordered-top3 distribution for the first three simulator worlds.

    W0: context-light PL-like world.
    W1: static line benefit modifies utilities but PL ordering remains.
    W2: explicit rank-2/rank-3 conditional line relations.
    """
    cars = [r.car_no for r in race.riders]
    rider = {r.car_no: r for r in race.riders}
    line_strength = _line_strengths(race)

    if world not in {"W0", "W1", "W2"}:
        raise ValueError(f"unknown world {world}")

    base = {c: _base_utility(rider[c], race) for c in cars}

    if world == "W0":
        util = base
    else:
        util = {}
        for c in cars:
            r = rider[c]
            pos_bonus = {0: 0.04, 1: 0.10, 2: 0.05}.get(r.line_position, 0.0)
            line_bonus = 0.16 * line_strength[r.line_id] + pos_bonus
            util[c] = base[c] + line_bonus

    p1 = _softmax(util)
    joint: Dict[Top3, float] = {}

    for i, j, k in permutations(cars, 3):
        rem2 = [c for c in cars if c != i]
        if world in {"W0", "W1"}:
            p2 = _softmax({c: util[c] for c in rem2})
            rem3 = [c for c in rem2 if c != j]
            p3 = _softmax({c: util[c] for c in rem3})
        else:
            ri = rider[i]
            u2: Dict[int, float] = {}
            for c in rem2:
                rc = rider[c]
                same = 1.0 if rc.line_id == ri.line_id else 0.0
                # Bante/follower relation matters after first is known.
                follower = 1.0 if same and rc.line_position == ri.line_position + 1 else 0.0
                u2[c] = util[c] + 0.30 * same + 0.28 * follower
            p2 = _softmax(u2)

            rem3 = [c for c in rem2 if c != j]
            rj = rider[j]
            u3: Dict[int, float] = {}
            for c in rem3:
                rc = rider[c]
                same_i = 1.0 if rc.line_id == ri.line_id else 0.0
                same_j = 1.0 if rc.line_id == rj.line_id else 0.0
                chain = 1.0 if (ri.line_id == rj.line_id == rc.line_id and ri.line_position < rj.line_position < rc.line_position) else 0.0
                u3[c] = util[c] + 0.17 * same_i + 0.14 * same_j + 0.30 * chain
            p3 = _softmax(u3)

        joint[(i, j, k)] = p1[i] * p2[j] * p3[k]

    z = sum(joint.values())
    return {k: v / z for k, v in joint.items()}


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
    """Generate synthetic races with PRE, hidden truth outcome and exact oracle joint."""
    out: List[Dict[str, object]] = []
    rng = random.Random(seed + {"W0": 1000, "W1": 2000, "W2": 3000}[world])
    for idx in range(n_races):
        race = generate_race(seed=seed, race_index=idx)
        joint = world_joint_distribution(race, world)
        outcome = sample_top3(joint, rng)
        out.append({
            "world": world,
            "pre": pre_view(race),
            "outcome_top3": outcome,
            "oracle_joint": joint,
        })
    return out
