from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
from typing import Dict, Iterable, Mapping, Sequence

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from digital_twin_empirical_pre_adapter_v1 import (
    generate_empirical_candidate_bundle,
    realistic_pre_view,
)
from digital_twin_v1 import generate_race, pre_view

EXPECTED_PRE_SHA256 = "4fb0a2e9ede9aa343fa7828a65099beb2e4ce8ee76522c9952331ad536b0db84"
EXPECTED_REAL_CANDIDATE_RACES = 1539
LOCKED_SEED = 20260820
TACTICAL_FIELDS = ("B", "S", "nige", "makuri", "sashi", "mark")
CLASSES = ("S1", "S2", "A1", "A2", "A3")
STYLES = ("逃", "両", "追")
BANDS = ("S", "A12", "A3")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_real_candidate(path: Path) -> list[dict]:
    if _sha256(path) != EXPECTED_PRE_SHA256:
        raise ValueError("pre_structured_sha256_mismatch")
    out = []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row.get("data_status") != "STAGED_UNPROVEN_HISTORICAL_PRE":
                raise ValueError("unexpected_source_status")
            if row.get("training_eligibility") is not False:
                raise ValueError("training_eligibility_boundary_drift")
            entrants = row.get("entrants", [])
            if len(entrants) != 7:
                continue
            if any(e.get("class") in {"L1", "SS"} for e in entrants):
                continue
            out.append(row)
    if len(out) != EXPECTED_REAL_CANDIDATE_RACES:
        raise ValueError(f"candidate_race_count_mismatch:{len(out)}")
    return out


def _band_from_classes(classes: Iterable[str]) -> str:
    values = set(classes)
    if values <= {"S1", "S2"}:
        return "S"
    if values <= {"A1", "A2"}:
        return "A12"
    if values <= {"A3"}:
        return "A3"
    raise ValueError(f"mixed_or_unsupported_band_classes:{sorted(values)}")


def _zscore(values: Sequence[float]) -> np.ndarray:
    x = np.asarray(values, dtype=float)
    sd = float(x.std(ddof=0))
    if not np.isfinite(sd) or sd <= 1e-12:
        return np.zeros_like(x)
    return (x - float(x.mean())) / sd


def _feature_vector(
    band: str,
    entrants: Sequence[Mapping[str, object]],
    score_values: Sequence[float],
    tactical_rates: Mapping[str, Sequence[float]],
    view: str,
) -> tuple[list[str], np.ndarray]:
    if band not in BANDS or len(entrants) != 7:
        raise ValueError("unsupported_feature_race")
    if view not in {"AUDIT_REALISM_VIEW", "SCALE_NEUTRAL_VIEW"}:
        raise ValueError(f"unknown_view:{view}")

    scores = np.asarray(score_values, dtype=float)
    if view == "SCALE_NEUTRAL_VIEW":
        scores = _zscore(scores)

    names: list[str] = []
    vals: list[float] = []
    for b in BANDS:
        names.append(f"race_band_{b}")
        vals.append(float(band == b))

    class_counts = Counter(str(e["class"]) for e in entrants)
    for cls in CLASSES:
        names.append(f"class_fraction_{cls}")
        vals.append(class_counts[cls] / 7.0)

    style_counts = Counter(str(e["style"]) for e in entrants)
    for style in STYLES:
        names.append(f"style_fraction_{style}")
        vals.append(style_counts[style] / 7.0)

    names += ["score_mean", "score_std", "score_range"]
    vals += [float(scores.mean()), float(scores.std(ddof=0)), float(scores.max() - scores.min())]

    for field in TACTICAL_FIELDS:
        x = np.asarray(tactical_rates[field], dtype=float)
        if len(x) != 7 or not np.all(np.isfinite(x)):
            raise ValueError(f"invalid_tactical_rates:{field}")
        names.append(f"mean_{field}_per_start")
        vals.append(float(x.mean()))
        names.append(f"zero_fraction_{field}_per_start")
        vals.append(float(np.mean(x == 0.0)))

    return names, np.asarray(vals, dtype=float)


def _real_features(rows: Sequence[dict], view: str) -> tuple[list[str], np.ndarray]:
    matrix = []
    feature_names = None
    for row in rows:
        entrants = row["entrants"]
        band = _band_from_classes(str(e["class"]) for e in entrants)
        scores = [float(e["score"]) for e in entrants]
        rates: Dict[str, list[float]] = {f: [] for f in TACTICAL_FIELDS}
        for entrant in entrants:
            starts = sum(float(entrant[k]) for k in ("wins", "seconds", "thirds", "outs"))
            for field in TACTICAL_FIELDS:
                rates[field].append(float(entrant[field]) / starts if starts > 0 else 0.0)
        names, vec = _feature_vector(band, entrants, scores, rates, view)
        if feature_names is None:
            feature_names = names
        elif feature_names != names:
            raise AssertionError("feature_contract_drift")
        matrix.append(vec)
    return feature_names or [], np.vstack(matrix)


def _synthetic_features(kind: str, n_races: int, view: str) -> tuple[list[str], np.ndarray]:
    matrix = []
    feature_names = None
    for race_index in range(n_races):
        if kind == "CURRENT_DIGITAL_TWIN":
            pre = pre_view(generate_race(LOCKED_SEED, race_index, event_format="STANDARD_FI_FII_7"))
        elif kind == "EMPIRICAL_ADAPTER_TWIN":
            pre = realistic_pre_view(generate_empirical_candidate_bundle(LOCKED_SEED, race_index))
        else:
            raise ValueError(f"unknown_synthetic_kind:{kind}")

        entrants = pre["riders"]
        scores = [float(e["score"]) for e in entrants]
        rates = {field: [float(e[field]) for e in entrants] for field in TACTICAL_FIELDS}
        names, vec = _feature_vector(str(pre["race_band"]), entrants, scores, rates, view)
        if feature_names is None:
            feature_names = names
        elif feature_names != names:
            raise AssertionError("feature_contract_drift")
        matrix.append(vec)
    return feature_names or [], np.vstack(matrix)


def _oof_metrics(X: np.ndarray, y: np.ndarray, classifier: str) -> dict:
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=LOCKED_SEED)
    probability = np.zeros(len(y), dtype=float)
    if classifier == "HIST_GRADIENT_BOOSTING":
        def build():
            return HistGradientBoostingClassifier(
                max_iter=200,
                learning_rate=0.05,
                max_leaf_nodes=15,
                l2_regularization=1.0,
                random_state=LOCKED_SEED,
            )
    elif classifier == "LOGISTIC_REGRESSION":
        def build():
            return Pipeline([
                ("scale", StandardScaler()),
                ("model", LogisticRegression(C=1.0, max_iter=2000, solver="lbfgs")),
            ])
    else:
        raise ValueError(f"unknown_classifier:{classifier}")

    for train_idx, test_idx in cv.split(X, y):
        model = build()
        model.fit(X[train_idx], y[train_idx])
        probability[test_idx] = model.predict_proba(X[test_idx])[:, 1]
    auc = float(roc_auc_score(y, probability))
    balanced = float(balanced_accuracy_score(y, probability >= 0.5))
    return {
        "out_of_fold_ROC_AUC": auc,
        "out_of_fold_balanced_accuracy_at_0_5": balanced,
        "AUC_distance_from_0_5": abs(auc - 0.5),
    }


def evaluate(pre_structured_path: Path) -> dict:
    real_rows = _load_real_candidate(pre_structured_path)
    comparisons = {}
    for view in ("AUDIT_REALISM_VIEW", "SCALE_NEUTRAL_VIEW"):
        real_names, X_real = _real_features(real_rows, view)
        comparisons[view] = {}
        for kind in ("CURRENT_DIGITAL_TWIN", "EMPIRICAL_ADAPTER_TWIN"):
            syn_names, X_syn = _synthetic_features(kind, len(real_rows), view)
            if real_names != syn_names:
                raise AssertionError("real_synthetic_feature_contract_mismatch")
            X = np.vstack([X_real, X_syn])
            y = np.concatenate([np.ones(len(X_real), dtype=int), np.zeros(len(X_syn), dtype=int)])
            result = {
                "HIST_GRADIENT_BOOSTING": _oof_metrics(X, y, "HIST_GRADIENT_BOOSTING"),
                "LOGISTIC_REGRESSION": _oof_metrics(X, y, "LOGISTIC_REGRESSION"),
            }
            comparisons[view][kind] = result

    deltas = {}
    for view, by_kind in comparisons.items():
        deltas[view] = {}
        for classifier in ("HIST_GRADIENT_BOOSTING", "LOGISTIC_REGRESSION"):
            old_distance = by_kind["CURRENT_DIGITAL_TWIN"][classifier]["AUC_distance_from_0_5"]
            new_distance = by_kind["EMPIRICAL_ADAPTER_TWIN"][classifier]["AUC_distance_from_0_5"]
            deltas[view][classifier] = {
                "current_AUC_distance_from_0_5": old_distance,
                "empirical_adapter_AUC_distance_from_0_5": new_distance,
                "distance_reduction_positive_is_desired": old_distance - new_distance,
            }

    return {
        "record": "KEIRIN_DT_CANDIDATE_SOURCE_DISCRIMINATOR_RESULT_v1",
        "status": "STAGED_SOURCE_RESEMBLANCE_DIAGNOSTIC_ONLY_NOT_REALITY_VALIDATION",
        "source_sha256": EXPECTED_PRE_SHA256,
        "source_status": "STAGED_UNPROVEN_HISTORICAL_PRE",
        "training_eligibility": False,
        "population_representativeness": "NOT_PROVEN",
        "real_candidate_races": len(real_rows),
        "synthetic_races_each": len(real_rows),
        "seed": LOCKED_SEED,
        "feature_count": len(real_names),
        "raw_identity_features_used": False,
        "result_payout_used": False,
        "hyperparameter_search": False,
        "comparisons": comparisons,
        "distance_reduction": deltas,
        "claim_limit": (
            "This measures distinguishability from the same staged candidate PRE source used "
            "to derive the empirical envelope. It cannot establish real-world equivalence, "
            "population truth, source admission, predictive edge, ROI, or model promotion."
        ),
        "scientific_firewall": {
            "ECON_HOLDOUT1000": "SEALED",
            "DEV2000_C_new_lineage_rescue": "PROHIBITED",
            "same_lineage_B_C_rescue_tuning": "PROHIBITED",
            "RESULT_PAYOUT_access": "UNAUTHORIZED",
            "new_untouched_validation_opened": False,
            "model_promotion": "PROHIBITED",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre-structured", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.pre_structured), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
