#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def bucket_from_input(obj):
    if "circumference_bucket" in obj:
        bucket = obj["circumference_bucket"]
        if bucket in ("333_OR_333_33", "400"):
            return bucket
    m = float(obj["circumference_m"])
    if abs(m - 400.0) < 1e-6:
        return "400"
    if abs(m - 333.0) < 1.0 or abs(m - 333.33) < 1.0:
        return "333_OR_333_33"
    raise ValueError(f"unsupported circumference_m={m}")


def predict(model, race):
    beta = float(model["baseline"]["beta"])
    lookup = {
        row["official_registration_number"]: float(row["delta_logit"])
        for row in model["frozen_rider_lookup"]
    }
    bucket = bucket_from_input(race)
    q = 1.0 if bucket == "333_OR_333_33" else -1.0

    scored = []
    for row in race["riders"]:
        reg = str(row["official_registration_number"])
        score = float(row["competition_score"])
        supported = reg in lookup
        delta = lookup.get(reg, 0.0)
        logit = beta * score + q * delta
        scored.append({
            "official_registration_number": reg,
            "rider_name": row.get("rider_name"),
            "competition_score": score,
            "supported_rider_delta": supported,
            "delta_logit": delta if supported else 0.0,
            "logit": logit
        })

    if len(scored) < 2:
        raise ValueError("race must contain at least two riders")

    max_logit = max(row["logit"] for row in scored)
    denominator = sum(math.exp(row["logit"] - max_logit) for row in scored)
    for row in scored:
        row["win_probability"] = math.exp(row["logit"] - max_logit) / denominator

    scored.sort(key=lambda row: row["win_probability"], reverse=True)
    return {
        "model": model["model_name"],
        "circumference_bucket": bucket,
        "result_accessed": False,
        "riders": scored,
        "probability_sum": sum(row["win_probability"] for row in scored)
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run the frozen PRE-only rider x circumference challenger."
    )
    parser.add_argument("--model", required=True, help="Frozen model JSON path")
    parser.add_argument("--race", required=True, help="PRE-only race JSON path")
    parser.add_argument("--out", help="Optional output JSON path")
    args = parser.parse_args()

    result = predict(load_json(args.model), load_json(args.race))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
