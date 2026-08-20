from __future__ import annotations

from dataclasses import dataclass, replace
import json
import math
from pathlib import Path
import random
from typing import Dict, Mapping

from digital_twin_v1 import Race, Rider, generate_race, pre_view


HERE = Path(__file__).resolve().parent
GOV = HERE.parent / "governance"
PARAMS_PATH = GOV / "KEIRIN_DT_EMPIRICAL_GENERATOR_PARAMS_v1.json"

STYLES = ("逃", "両", "追")
BASE_POSITION_STYLE = {
    "singleton": {"逃": 0.24, "両": 0.46, "追": 0.30},
    "head": {"逃": 0.42, "両": 0.38, "追": 0.20},
    "follower": {"逃": 0.08, "両": 0.28, "追": 0.64},
}
OBSERVED_LATENT_RHO = 1.0 / math.sqrt(1.0 + 0.55**2)
HIDDEN_RESIDUAL_WEIGHT = math.sqrt(1.0 - OBSERVED_LATENT_RHO**2)


@dataclass(frozen=True)
class EmpiricalRaceBundle:
    race: Race
    raw_scores: Mapping[int, float]
    source_status: str
    source_envelope: str


def _load_params(path: Path = PARAMS_PATH) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("record") != "KEIRIN_DT_EMPIRICAL_GENERATOR_PARAMS_v1":
        raise ValueError("empirical_generator_params_identity_drift")
    if data.get("status") != "DERIVED_SENSOR_ONLY_GENERATOR_PARAMS_NOT_REALITY_TRUTH":
        raise ValueError("empirical_generator_params_status_drift")
    if data.get("use_boundary") != "SYNTHETIC_PRE_ENGINEERING_ONLY":
        raise ValueError("empirical_generator_params_use_boundary_drift")
    required_unmeasured = {
        "H",
        "LINE_SHAPE_FREQUENCY",
        "BANK_FREQUENCY_PER_RACE",
        "WIND_DISTRIBUTION",
        "RACE_REGIME_FREQUENCY",
    }
    if not required_unmeasured.issubset(set(data.get("unmeasured", []))):
        raise ValueError("empirical_generator_unmeasured_boundary_drift")
    return data


def _weighted_choice(rng: random.Random, weights: Mapping[str, float]) -> str:
    keys = list(weights)
    vals = [float(weights[k]) for k in keys]
    if any(v < 0.0 for v in vals) or sum(vals) <= 0.0:
        raise ValueError("invalid_choice_weights")
    return rng.choices(keys, weights=vals, k=1)[0]


def _position_category(rider: Rider) -> str:
    if rider.line_size == 1:
        return "singleton"
    if rider.line_position == 0:
        return "head"
    return "follower"


def _style_conditionals_for_race(
    race: Race,
    target: Mapping[str, float],
) -> Dict[str, Dict[str, float]]:
    """Preserve target style marginal while retaining bounded position coupling.

    The existing hand-authored position/style probabilities are treated only as an
    assumption-shaped deviation.  For the selected line shape we subtract their
    weighted marginal, then add the zero-mean deviation back to the sensor target.
    Coupling strength is reduced automatically only as far as required to keep every
    conditional probability in [0, 1].  Therefore the race-level expected style
    marginal remains exactly the sensor target for any supported line shape.
    """
    target_total = sum(float(target[s]) for s in STYLES)
    if target_total <= 0.0:
        raise ValueError("invalid_style_target_mass")
    target_norm = {s: float(target[s]) / target_total for s in STYLES}

    categories = [_position_category(r) for r in race.riders]
    n = len(categories)
    cat_weight = {c: categories.count(c) / n for c in set(categories)}
    base_marginal = {
        s: sum(cat_weight[c] * BASE_POSITION_STYLE[c][s] for c in cat_weight)
        for s in STYLES
    }

    max_lambda = 1.0
    for category in cat_weight:
        for style in STYLES:
            delta = BASE_POSITION_STYLE[category][style] - base_marginal[style]
            t = target_norm[style]
            if delta < 0.0:
                max_lambda = min(max_lambda, t / (-delta))
            elif delta > 0.0:
                max_lambda = min(max_lambda, (1.0 - t) / delta)
    coupling = max(0.0, min(1.0, max_lambda * 0.999999))

    cond: Dict[str, Dict[str, float]] = {}
    for category in cat_weight:
        cond[category] = {}
        for style in STYLES:
            delta = BASE_POSITION_STYLE[category][style] - base_marginal[style]
            value = target_norm[style] + coupling * delta
            if value < -1e-12 or value > 1.0 + 1e-12:
                raise ValueError("style_coupling_probability_out_of_bounds")
            cond[category][style] = min(1.0, max(0.0, value))
        z = sum(cond[category].values())
        if abs(z - 1.0) > 1e-12:
            raise ValueError("style_conditional_mass_drift")

    marginal = {
        s: sum(cat_weight[c] * cond[c][s] for c in cat_weight)
        for s in STYLES
    }
    if max(abs(marginal[s] - target_norm[s]) for s in STYLES) > 1e-12:
        raise ValueError("style_target_marginal_drift")
    return cond


def _sample_scores(
    rng: random.Random,
    band: str,
    params: Mapping[str, object],
    n: int,
) -> tuple[list[float], list[float]]:
    score = params["score_hierarchy"][band]
    center = float(score["race_mean_mu"])
    race_mean = rng.gauss(center, float(score["race_mean_sd"]))
    race_sd = math.exp(
        rng.gauss(float(score["log_race_sd_mu"]), float(score["log_race_sd_sd"]))
    )

    z = [rng.gauss(0.0, 1.0) for _ in range(n)]
    z_mean = sum(z) / n
    z_var = sum((x - z_mean) ** 2 for x in z) / (n - 1)
    z_sd = math.sqrt(max(z_var, 1e-15))
    raw = [race_mean + race_sd * (x - z_mean) / z_sd for x in z]

    # Total rider-score scale implied by the staged hierarchical summary. This is
    # a unit transform only, fixed before synthetic stress execution.
    expected_within_var = math.exp(
        2.0 * float(score["log_race_sd_mu"])
        + 2.0 * float(score["log_race_sd_sd"]) ** 2
    )
    total_sd = math.sqrt(float(score["race_mean_sd"]) ** 2 + expected_within_var)
    model_z = [(x - center) / total_sd for x in raw]
    return raw, model_z


def _sample_tactical_rates(
    rng: random.Random,
    style: str,
    params: Mapping[str, object],
) -> Dict[str, float]:
    spec = params["tactical_zero_inflated_beta"][style]
    out: Dict[str, float] = {}
    for field in ("B", "S", "nige", "makuri", "sashi", "mark"):
        p = spec[field]
        if rng.random() < float(p["p0"]):
            out[field] = 0.0
        else:
            out[field] = rng.betavariate(float(p["alpha"]), float(p["beta"]))
    return out


def generate_empirical_candidate_bundle(
    seed: int,
    race_index: int,
    params_path: Path = PARAMS_PATH,
) -> EmpiricalRaceBundle:
    """Generate one seven-rider candidate reality-shaped synthetic PRE race.

    Admitted official structure remains in digital_twin_v1. Only the observable PRE
    marginals listed in the sensor-only parameter file are reshaped here. Missing
    line/bank/wind/H calibration is never silently invented as measured reality.
    """
    params = _load_params(params_path)
    base = generate_race(
        seed=seed,
        race_index=race_index,
        event_format="STANDARD_FI_FII_7",
    )
    rng = random.Random(f"keirin-dt-empirical-v1:{seed}:{race_index}")

    band = _weighted_choice(rng, params["band_probs"])
    style_cond = _style_conditionals_for_race(base, params["style_probs"][band])
    raw_scores, model_scores = _sample_scores(rng, band, params, len(base.riders))

    new_riders = []
    raw_score_map: Dict[int, float] = {}
    for idx, original in enumerate(base.riders):
        rider_class = _weighted_choice(rng, params["class_probs"][band])
        category = _position_category(original)
        style = _weighted_choice(rng, style_cond[category])
        tactical = _sample_tactical_rates(rng, style, params)

        # Hidden sporting truth is still synthetic. Preserve the original Twin's
        # observed/latent correlation scale while linking it to the reality-shaped
        # score view; this is an assumption, never a real-effect calibration.
        latent = (
            OBSERVED_LATENT_RHO * model_scores[idx]
            + HIDDEN_RESIDUAL_WEIGHT * original.latent_skill
        )
        new_rider = replace(
            original,
            rider_class=rider_class,
            latent_skill=latent,
            observed_score=model_scores[idx],
            style=style,
            B=tactical["B"],
            S=tactical["S"],
            nige=tactical["nige"],
            makuri=tactical["makuri"],
            sashi=tactical["sashi"],
            mark=tactical["mark"],
            # H intentionally remains the base synthetic assumption because it is
            # absent from the staged PRE artifact.
        )
        new_riders.append(new_rider)
        raw_score_map[new_rider.car_no] = raw_scores[idx]

    race = replace(
        base,
        race_id=f"SYN_EMP_{seed}_{race_index}",
        race_band=band,
        riders=tuple(new_riders),
    )
    return EmpiricalRaceBundle(
        race=race,
        raw_scores=raw_score_map,
        source_status="CANDIDATE_SENSOR_ENVELOPE_NOT_REALITY_ADMISSION",
        source_envelope="KEIRIN_DT_EMPIRICAL_ENVELOPE_COMPACT_v1",
    )


def model_pre_view(bundle: EmpiricalRaceBundle) -> Dict[str, object]:
    """PRE view for fixed synthetic proxy models after preregistered score scaling."""
    out = pre_view(bundle.race)
    out["calibration_status"] = bundle.source_status
    out["score_semantics"] = "BAND_SCALED_MODEL_Z_FROM_SENSOR_ONLY_RAW_SCORE"
    return out


def realistic_pre_view(bundle: EmpiricalRaceBundle) -> Dict[str, object]:
    """Human/audit PRE view on the staged real-like score scale.

    The original model-z score is retained separately for reproducibility. Source
    labels make the unmeasured fields explicit instead of presenting them as real.
    """
    out = pre_view(bundle.race)
    for rider in out["riders"]:
        car = int(rider["car_no"])
        rider["score_model_z"] = rider["score"]
        rider["score"] = bundle.raw_scores[car]
        rider["H_source"] = "ASSUMPTION_UNMEASURED"
        rider["line_source_class"] = "ASSUMPTION_RANGE_NOT_SENSOR_CALIBRATED"
    out["calibration_status"] = bundle.source_status
    out["calibration_source"] = bundle.source_envelope
    out["bank_source_class"] = "ASSUMPTION_RANGE_NOT_SENSOR_CALIBRATED"
    out["wind_source_class"] = "ASSUMPTION_RANGE_NOT_SENSOR_CALIBRATED"
    out["race_regime_source_class"] = "OFFICIAL_RULE_STRUCTURAL_ASSUMPTION_FOR_STANDARD_WORLD"
    return out
