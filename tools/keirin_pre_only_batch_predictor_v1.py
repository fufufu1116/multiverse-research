#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize_name(value):
    return " ".join(str(value).split())


def softmax(logits):
    m = max(logits)
    exps = [math.exp(x - m) for x in logits]
    total = sum(exps)
    return [x / total for x in exps]


def main():
    ap = argparse.ArgumentParser(description="Batch PRE-only S0 vs Rider x Circumference predictor.")
    ap.add_argument("--model", required=True)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--circumference", required=True, choices=["333_OR_333_33", "400"])
    ap.add_argument("--out")
    args = ap.parse_args()

    model = load_json(args.model)
    snap = load_json(args.snapshot)
    beta = float(model["baseline"]["beta"])
    q = 1.0 if args.circumference == "333_OR_333_33" else -1.0

    by_name = {
        normalize_name(x["rider_name"]): {
            "registration": x["official_registration_number"],
            "delta": float(x["delta_logit"]),
        }
        for x in model["frozen_rider_lookup"]
    }

    cols = snap["columns"]
    rows = [dict(zip(cols, raw)) for raw in snap["rows"]]
    races = {}
    for row in rows:
        races.setdefault(int(row["race_no"]), []).append(row)

    out_races = []
    supported_appearances = 0
    rank_change_races = 0
    top1_change_races = 0

    for race_no in sorted(races):
        race_rows = sorted(races[race_no], key=lambda x: int(x["car_no"]))
        records = []
        for row in race_rows:
            name = normalize_name(row["rider_name_raw"])
            support = by_name.get(name)
            score = float(row["competition_score"])
            delta = support["delta"] if support else 0.0
            records.append({
                "car_no": int(row["car_no"]),
                "rider_name": name,
                "official_registration_number": support["registration"] if support else None,
                "competition_score": score,
                "supported": support is not None,
                "delta_logit": delta,
                "s0_logit": beta * score,
                "challenger_logit": beta * score + q * delta,
            })

        s0p = softmax([x["s0_logit"] for x in records])
        chp = softmax([x["challenger_logit"] for x in records])
        for i, rec in enumerate(records):
            rec["s0_probability"] = s0p[i]
            rec["challenger_probability"] = chp[i]
            rec["change_percentage_points"] = (chp[i] - s0p[i]) * 100.0

        s0_order = sorted(records, key=lambda x: x["s0_probability"], reverse=True)
        ch_order = sorted(records, key=lambda x: x["challenger_probability"], reverse=True)
        s0_rank = {x["car_no"]: i + 1 for i, x in enumerate(s0_order)}
        ch_rank = {x["car_no"]: i + 1 for i, x in enumerate(ch_order)}
        for rec in records:
            rec["s0_rank"] = s0_rank[rec["car_no"]]
            rec["challenger_rank"] = ch_rank[rec["car_no"]]

        rank_changed = any(x["s0_rank"] != x["challenger_rank"] for x in records)
        top1_changed = s0_order[0]["car_no"] != ch_order[0]["car_no"]
        supported = sum(1 for x in records if x["supported"])
        supported_appearances += supported
        rank_change_races += int(rank_changed)
        top1_change_races += int(top1_changed)

        out_races.append({
            "race_no": race_no,
            "supported_riders": supported,
            "rank_changed": rank_changed,
            "top1_changed": top1_changed,
            "s0_top1": s0_order[0]["rider_name"],
            "challenger_top1": ch_order[0]["rider_name"],
            "riders": records,
        })

    output = {
        "model": model["model_name"],
        "snapshot_record": snap.get("record"),
        "circumference_bucket": args.circumference,
        "result_accessed": False,
        "summary": {
            "races": len(out_races),
            "rider_rows": sum(len(x["riders"]) for x in out_races),
            "supported_rider_appearances": supported_appearances,
            "rank_change_races": rank_change_races,
            "top1_change_races": top1_change_races,
        },
        "races": out_races,
    }

    rendered = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
