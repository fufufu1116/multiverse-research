#!/usr/bin/env python3
import argparse, json, math
from pathlib import Path

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def bucket(race):
    b = race.get("circumference_bucket")
    if b in ("333_OR_333_33", "400"):
        return b
    m = float(race["circumference_m"])
    if abs(m - 400.0) < 1e-6:
        return "400"
    if abs(m - 333.0) < 1.0 or abs(m - 333.33) < 1.0:
        return "333_OR_333_33"
    raise ValueError("unsupported circumference")

def predict(model, race):
    beta = float(model["baseline"]["beta"])
    rider_lookup = {
        x["official_registration_number"]: float(x["delta_logit"])
        for x in model["rider_level"]["lookup"]
    }
    style_lookup = {
        k: float(v["delta_logit"])
        for k, v in model["style_fallback"]["lookup"].items()
    }
    b = bucket(race)
    q = 1.0 if b == "333_OR_333_33" else -1.0
    rows = []
    for r in race["riders"]:
        reg = str(r.get("official_registration_number") or "")
        style = r.get("style")
        if reg and reg in rider_lookup:
            delta, source = rider_lookup[reg], "RIDER"
        elif style in style_lookup:
            delta, source = style_lookup[style], "STYLE"
        else:
            delta, source = 0.0, "S0"
        score = float(r["competition_score"])
        rows.append({
            "car_no": r.get("car_no"),
            "rider_name": r.get("rider_name"),
            "official_registration_number": reg or None,
            "style": style,
            "competition_score": score,
            "correction_source": source,
            "delta_logit": delta,
            "s0_logit": beta * score,
            "challenger_logit": beta * score + q * delta,
        })

    def probs(key):
        m = max(x[key] for x in rows)
        exps = [math.exp(x[key] - m) for x in rows]
        d = sum(exps)
        return [x / d for x in exps]

    s0 = probs("s0_logit")
    ch = probs("challenger_logit")
    for i, row in enumerate(rows):
        row["s0_probability"] = s0[i]
        row["challenger_probability"] = ch[i]
        row["change_percentage_points"] = (ch[i] - s0[i]) * 100.0

    s0_order = sorted(range(len(rows)), key=lambda i: s0[i], reverse=True)
    ch_order = sorted(range(len(rows)), key=lambda i: ch[i], reverse=True)
    s0_rank = {idx: rank + 1 for rank, idx in enumerate(s0_order)}
    ch_rank = {idx: rank + 1 for rank, idx in enumerate(ch_order)}
    for i, row in enumerate(rows):
        row["s0_rank"] = s0_rank[i]
        row["challenger_rank"] = ch_rank[i]

    return {
        "model": model["record"],
        "circumference_bucket": b,
        "target_result_accessed": False,
        "rank_changed": any(r["s0_rank"] != r["challenger_rank"] for r in rows),
        "top1_changed": s0_order[0] != ch_order[0],
        "riders": sorted(rows, key=lambda r: r["challenger_rank"]),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--race", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()
    out = predict(load_json(args.model), load_json(args.race))
    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text, end="")

if __name__ == "__main__":
    main()
