from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path
import random
from typing import Dict, Iterable, Mapping

from digital_twin_v1 import Race, Rider, generate_race, pre_view

HERE = Path(__file__).resolve().parent
DEFAULT_PARAMS_PATH = HERE.parent / "governance" / "KEIRIN_DT_EMPIRICAL_GENERATOR_PARAMS_v1.json"
STYLES = ("逃", "両", "追")
SENSOR_FIELDS = ("class", "score", "style", "B", "S", "nige", "makuri", "sashi", "mark")
ASSUMPTION_FIELDS = ("H", "line_group_id", "line_position", "line_size", "bank_length_m", "wind_speed_mps", "race_regime")


def load_params(path: str | Path | None = None) -> dict:
    p = Path(path) if path is not None else DEFAULT_PARAMS_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("record") != "KEIRIN_DT_EMPIRICAL_GENERATOR_PARAMS_v1":
        raise ValueError("unexpected_empirical_generator_params_record")
    if data.get("status") != "DERIVED_SENSOR_ONLY_GENERATOR_PARAMS_NOT_REALITY_TRUTH":
        raise ValueError("empirical_generator_params_status_drift")
    if data.get("use_boundary") != "SYNTHETIC_PRE_ENGINEERING_ONLY":
        raise ValueError("empirical_generator_params_use_boundary_drift")
    return data


def _choice_from_probs(probs: Mapping[str, float], rng: random.Random) -> str:
    keys = list(probs)
    weights = [float(probs[k]) for k in keys]
    if any(w < 0 for w in weights) or sum(weights) <= 0:
        raise ValueError("invalid_probability_weights")
    return rng.choices(keys, weights=weights, k=1)[0]


def _base_style_weights(r: Rider) -> Dict[str, float]:
    if r.line_size == 1:
        values = (0.24, 0.46, 0.30)
    elif r.line_position == 0:
        values = (0.42, 0.38, 0.20)
    else:
        values = (0.08, 0.28, 0.64)
    return dict(zip(STYLES, values))


def _balanced_style_probabilities(
    riders: Iterable[Rider],
    target: Mapping[str, float],
    max_iter: int = 200,
) -> Dict[int, Dict[str, float]]:
    """Preserve current line-position motif while matching a target style marginal in expectation.

    The position/style coupling itself remains an assumption. Multiplicative balancing only
    reweights the existing synthetic motif so its race-average expected marginal tracks the
    staged empirical sensor target for the selected race band.
    """
    riders = tuple(riders)
    if not riders:
        raise ValueError("no_riders")
    if set(target) != set(STYLES):
        raise ValueError("unexpected_style_target")
    if abs(sum(float(target[s]) for s in STYLES) - 1.0) > 1e-6:
        raise ValueError("style_target_not_unit_mass")

    multipliers = {s: 1.0 for s in STYLES}
    probs: Dict[int, Dict[str, float]] = {}
    for _ in range(max_iter):
        probs = {}
        aggregate = {s: 0.0 for s in STYLES}
        for r in riders:
            base = _base_style_weights(r)
            raw = {s: base[s] * multipliers[s] for s in STYLES}
            z = sum(raw.values())
            q = {s: raw[s] / z for s in STYLES}
            probs[r.car_no] = q
            for s in STYLES:
                aggregate[s] += q[s] / len(riders)
        err = max(abs(aggregate[s] - float(target[s])) for s in STYLES)
        if err < 1e-10:
            break
        for s in STYLES:
            multipliers[s] *= (float(target[s]) / max(aggregate[s], 1e-12)) ** 0.7
    return probs


def _zero_inflated_beta(spec: Mapping[str, float], rng: random.Random) -> float:
    p0 = float(spec["p0"])
    alpha = float(spec["alpha"])
    beta = float(spec["beta"])
    if not (0 <= p0 < 1) or alpha <= 0 or beta <= 0:
        raise ValueError("invalid_zero_inflated_beta_spec")
    if rng.random() < p0:
        return 0.0
    return rng.betavariate(alpha, beta)


def generate_reality_calibrated_race(
    seed: int,
    race_index: int,
    params: Mapping[str, object] | None = None,
) -> Race:
    """Generate a 7-rider synthetic race whose observable PRE layer uses staged sensor constraints.

    Unmeasured line/bank/wind/H/regime quantities remain inherited synthetic assumptions.
    This function does not make a real-world equivalence claim and does not use RESULT/PAYOUT.
    """
    cfg = dict(params) if params is not None else load_params()
    base = generate_race(seed=seed, race_index=race_index, event_format="STANDARD_FI_FII_7")
    rng = random.Random(f"keirin-dt-empirical-envelope-v1:{seed}:{race_index}")

    band = _choice_from_probs(cfg["band_probs"], rng)
    score_cfg = cfg["score_hierarchy"][band]
    race_mean = rng.gauss(float(score_cfg["race_mean_mu"]), float(score_cfg["race_mean_sd"]))
    race_sd = math.exp(rng.gauss(float(score_cfg["log_race_sd_mu"]), float(score_cfg["log_race_sd_sd"])))
    race_sd = min(12.0, max(0.5, race_sd))

    style_prob = _balanced_style_probabilities(base.riders, cfg["style_probs"][band])
    new_riders = []
    obs_noise_scale = math.sqrt(1.0 + 0.55 * 0.55)
    for r in base.riders:
        rider_class = _choice_from_probs(cfg["class_probs"][band], rng)
        style = _choice_from_probs(style_prob[r.car_no], rng)
        observed_z = (r.latent_skill + rng.gauss(0.0, 0.55)) / obs_noise_scale
        raw_score = race_mean + race_sd * observed_z
        tactical = {
            field: _zero_inflated_beta(cfg["tactical_zero_inflated_beta"][style][field], rng)
            for field in ("B", "S", "nige", "makuri", "sashi", "mark")
        }
        new_riders.append(
            replace(
                r,
                rider_class=rider_class,
                observed_score=raw_score,
                style=style,
                B=tactical["B"],
                S=tactical["S"],
                nige=tactical["nige"],
                makuri=tactical["makuri"],
                sashi=tactical["sashi"],
                mark=tactical["mark"],
            )
        )

    return replace(
        base,
        race_id=f"SYN_CAL_PRE_{seed}_{race_index}",
        race_band=band,
        riders=tuple(new_riders),
    )


def reality_pre_view(race: Race) -> Dict[str, object]:
    out = pre_view(race)
    out["calibration_layer"] = {
        "status": "STAGED_SENSOR_CALIBRATED_SYNTHETIC_PRE_NOT_REALITY_TRUTH",
        "source_params": "KEIRIN_DT_EMPIRICAL_GENERATOR_PARAMS_v1",
        "sensor_derived_fields": list(SENSOR_FIELDS),
        "assumption_fields": list(ASSUMPTION_FIELDS),
        "result_payout_used": False,
        "real_world_equivalence_claim": False,
    }
    return out


def architecture_pre_view(race: Race) -> Dict[str, object]:
    """Return the same PRE with score standardized only for synthetic architecture proxies.

    Raw competition-score scale is retained in raw_competition_score. This avoids feeding
    70-110 scale values into proxy models that were written around roughly unit-scale scores.
    """
    out = reality_pre_view(race)
    riders = out["riders"]
    raw = [float(r["score"]) for r in riders]
    mean = sum(raw) / len(raw)
    variance = sum((x - mean) ** 2 for x in raw) / len(raw)
    sd = math.sqrt(variance)
    if sd <= 1e-12:
        raise ValueError("zero_within_race_score_sd")
    for r in riders:
        raw_score = float(r["score"])
        r["raw_competition_score"] = raw_score
        r["score"] = (raw_score - mean) / sd
    out["architecture_score_transform"] = {
        "method": "WITHIN_RACE_ZSCORE_FOR_SYNTHETIC_PROXY_ONLY",
        "raw_field": "raw_competition_score",
        "model_field": "score",
        "real_model_training_claim": False,
    }
    return out
