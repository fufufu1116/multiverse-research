from __future__ import annotations

from dataclasses import replace
import base64
import hashlib
import json
import math
from pathlib import Path
import random
from typing import Dict, Mapping
import zlib

from digital_twin_v1 import generate_race, pre_view
from digital_twin_empirical_pre_adapter_v1 import (
    EmpiricalRaceBundle,
    HIDDEN_RESIDUAL_WEIGHT,
    OBSERVED_LATENT_RHO,
    PARAMS_PATH as V1_PARAMS_PATH,
    _load_params,
    _position_category,
    _style_conditionals_for_race,
    _weighted_choice,
)

HERE = Path(__file__).resolve().parent
V2_PAYLOAD_PATH = HERE / "fixtures" / "keirin_dt_joint_dependence_params_v2.json.zlib.b85"
V2_DECODED_SHA256 = "0f23a54cc4af204c83bfb47d8bb272e5eec0a7d5e210233900e0435ff7fffbd9"
TACTICAL = ("B", "S", "nige", "makuri", "sashi", "mark")


def _load_v2(path: Path = V2_PAYLOAD_PATH) -> dict:
    encoded = path.read_bytes().strip()
    raw = zlib.decompress(base64.b85decode(encoded))
    if hashlib.sha256(raw).hexdigest() != V2_DECODED_SHA256:
        raise ValueError("v2_joint_params_sha256_drift")
    data = json.loads(raw.decode("utf-8"))
    if data.get("record") != "KEIRIN_DT_JOINT_DEPENDENCE_GENERATOR_PARAMS_v2":
        raise ValueError("v2_joint_params_identity_drift")
    if data.get("use_boundary") != "SYNTHETIC_PRE_ENGINEERING_ONLY_NO_SOURCE_ADMISSION":
        raise ValueError("v2_joint_params_boundary_drift")
    if len(data.get("cells", {})) != 15:
        raise ValueError("v2_joint_params_cell_count_drift")
    return data


def _normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _quantile_interp(grid: list[float], values: list[float], u: float) -> float:
    u = min(1.0, max(0.0, float(u)))
    if u <= grid[0]:
        return float(values[0])
    if u >= grid[-1]:
        return float(values[-1])
    for i in range(1, len(grid)):
        if u <= grid[i]:
            q0, q1 = float(grid[i - 1]), float(grid[i])
            v0, v1 = float(values[i - 1]), float(values[i])
            if q1 <= q0:
                return v1
            w = (u - q0) / (q1 - q0)
            return v0 + w * (v1 - v0)
    return float(values[-1])


def _sample_score_latents(rng: random.Random, n: int) -> tuple[list[float], list[float]]:
    raw = [rng.gauss(0.0, 1.0) for _ in range(n)]
    mean = sum(raw) / n
    var = sum((x - mean) ** 2 for x in raw) / (n - 1)
    sd = math.sqrt(max(var, 1e-15))
    return raw, [(x - mean) / sd for x in raw]


def _sample_race_score_context(
    rng: random.Random,
    band: str,
    v1: Mapping[str, object],
) -> tuple[float, float, float, float]:
    spec = v1["score_hierarchy"][band]
    center = float(spec["race_mean_mu"])
    race_mean = rng.gauss(center, float(spec["race_mean_sd"]))
    race_sd = math.exp(
        rng.gauss(float(spec["log_race_sd_mu"]), float(spec["log_race_sd_sd"]))
    )
    expected_within_var = math.exp(
        2.0 * float(spec["log_race_sd_mu"])
        + 2.0 * float(spec["log_race_sd_sd"]) ** 2
    )
    total_sd = math.sqrt(float(spec["race_mean_sd"]) ** 2 + expected_within_var)
    return center, race_mean, race_sd, total_sd


def _sample_joint_tactical(
    rng: random.Random,
    z_score: float,
    cell: Mapping[str, object],
    grid: list[float],
) -> Dict[str, float]:
    rho = [float(x) for x in cell["score_tactical_gaussian_rho"]]
    chol = [[float(x) for x in row] for row in cell["conditional_cholesky"]]
    eps = [rng.gauss(0.0, 1.0) for _ in TACTICAL]
    z = []
    for i in range(len(TACTICAL)):
        residual = sum(chol[i][k] * eps[k] for k in range(i + 1))
        z.append(rho[i] * z_score + residual)

    out: Dict[str, float] = {}
    for i, field in enumerate(TACTICAL):
        u = _normal_cdf(z[i])
        value = _quantile_interp(grid, cell["quantiles"][field], u)
        out[field] = min(1.0, max(0.0, value))
    return out


def generate_empirical_joint_v2_bundle(seed: int, race_index: int) -> EmpiricalRaceBundle:
    """Generate one staged-candidate-shaped PRE race with joint tactical dependence.

    This is an engineering-only synthetic adapter. The third-party staged source is not
    admitted as real-world truth. H, line shape, bank, wind and sporting effect sizes are
    not upgraded by this adapter.
    """
    v1 = _load_params(V1_PARAMS_PATH)
    v2 = _load_v2()
    base = generate_race(
        seed=seed,
        race_index=race_index,
        event_format="STANDARD_FI_FII_7",
    )
    rng = random.Random(f"keirin-dt-empirical-joint-v2:{seed}:{race_index}")
    band = _weighted_choice(rng, v1["band_probs"])
    style_cond = _style_conditionals_for_race(base, v1["style_probs"][band])

    classes = []
    styles = []
    for original in base.riders:
        classes.append(_weighted_choice(rng, v1["class_probs"][band]))
        styles.append(_weighted_choice(rng, style_cond[_position_category(original)]))

    z_raw, z_std = _sample_score_latents(rng, len(base.riders))
    center, race_mean, race_sd, total_sd = _sample_race_score_context(rng, band, v1)
    offsets = [
        float(v2["class_score_within_race_residual_mean"][rider_class])
        for rider_class in classes
    ]
    offset_mean = sum(offsets) / len(offsets)
    centered_offsets = [x - offset_mean for x in offsets]
    raw_scores = [
        race_mean + race_sd * z_std[i] + centered_offsets[i]
        for i in range(len(base.riders))
    ]
    model_scores = [(x - center) / total_sd for x in raw_scores]
    grid = [float(x) for x in v2["quantile_grid"]]

    riders = []
    raw_score_map: Dict[int, float] = {}
    for i, original in enumerate(base.riders):
        rider_class = classes[i]
        style = styles[i]
        cell = v2["cells"][f"{rider_class}|{style}"]
        tactical = _sample_joint_tactical(rng, z_raw[i], cell, grid)
        latent = (
            OBSERVED_LATENT_RHO * model_scores[i]
            + HIDDEN_RESIDUAL_WEIGHT * original.latent_skill
        )
        rider = replace(
            original,
            rider_class=rider_class,
            latent_skill=latent,
            observed_score=model_scores[i],
            style=style,
            B=tactical["B"],
            S=tactical["S"],
            nige=tactical["nige"],
            makuri=tactical["makuri"],
            sashi=tactical["sashi"],
            mark=tactical["mark"],
        )
        riders.append(rider)
        raw_score_map[rider.car_no] = raw_scores[i]

    race = replace(
        base,
        race_id=f"SYN_EMP_JOINT_V2_{seed}_{race_index}",
        race_band=band,
        riders=tuple(riders),
    )
    return EmpiricalRaceBundle(
        race=race,
        raw_scores=raw_score_map,
        source_status="CANDIDATE_SENSOR_JOINT_V2_NOT_REALITY_ADMISSION",
        source_envelope="KEIRIN_DT_JOINT_DEPENDENCE_GENERATOR_PARAMS_v2",
    )


def model_pre_view_v2(bundle: EmpiricalRaceBundle) -> Dict[str, object]:
    out = pre_view(bundle.race)
    out["calibration_status"] = bundle.source_status
    out["score_semantics"] = (
        "BAND_SCALED_MODEL_Z_FROM_SENSOR_ONLY_RAW_SCORE_WITH_CLASS_OFFSET_V2"
    )
    return out


def realistic_pre_view_v2(bundle: EmpiricalRaceBundle) -> Dict[str, object]:
    out = pre_view(bundle.race)
    for rider in out["riders"]:
        car = int(rider["car_no"])
        rider["score_model_z"] = rider["score"]
        rider["score"] = bundle.raw_scores[car]
        rider["H_source"] = "ASSUMPTION_UNMEASURED"
        rider["line_source_class"] = "ASSUMPTION_RANGE_NOT_SENSOR_CALIBRATED"
    out["calibration_status"] = bundle.source_status
    out["calibration_source"] = bundle.source_envelope
    out["tactical_dependence_source"] = (
        "STAGED_CANDIDATE_DERIVED_CLASS_X_STYLE_COPULA_NOT_REALITY_TRUTH"
    )
    out["bank_source_class"] = "ASSUMPTION_RANGE_NOT_SENSOR_CALIBRATED"
    out["wind_source_class"] = "ASSUMPTION_RANGE_NOT_SENSOR_CALIBRATED"
    return out
