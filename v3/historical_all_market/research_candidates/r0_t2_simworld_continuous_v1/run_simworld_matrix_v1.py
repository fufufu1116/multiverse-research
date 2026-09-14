#!/usr/bin/env python3
import json, math
from collections import defaultdict
import numpy as np

SEED = 20260915
RACES_PER_WORLD = 1200
TEMPERATURES = [0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]


def pl_sample(latent, rng):
    remaining = list(range(len(latent)))
    order = []
    for _ in range(len(latent)):
        vals = np.array([latent[i] for i in remaining], dtype=float)
        vals -= vals.max()
        p = np.exp(vals)
        p /= p.sum()
        j = rng.choice(len(remaining), p=p)
        order.append(remaining.pop(j))
    return order


def ordered_top3_nll(scores, order, temperature):
    remaining = list(range(len(scores)))
    nll = 0.0
    for winner in order[:3]:
        vals = np.array([scores[i] / temperature for i in remaining], dtype=float)
        vals -= vals.max()
        logden = math.log(np.exp(vals).sum())
        idx = remaining.index(winner)
        nll += -(vals[idx] - logden)
        remaining.pop(idx)
    return nll


def worlds():
    return {
        "baseline_T2": lambda s, r: s / 2.0,
        "sharp_T1": lambda s, r: s / 1.0,
        "flat_T4": lambda s, r: s / 4.0,
        "measurement_noise_sd0_75": lambda s, r: (s + r.normal(0, 0.75, len(s))) / 2.0,
        "measurement_noise_sd1_5": lambda s, r: (s + r.normal(0, 1.5, len(s))) / 2.0,
        "nonlinear_tanh": lambda s, r: np.tanh(s / 1.5) * 1.5,
        "heavy_tail_latent": lambda s, r: s / 2.0 + r.standard_t(df=3, size=len(s)) * 0.55,
        "heteroskedastic": lambda s, r: s / 2.0 + r.normal(0, 0.25 + 0.18 * np.abs(s), len(s)),
        "rank_compression": lambda s, r: np.sign(s) * np.sqrt(np.abs(s) + 1e-9) / 1.5,
        "partial_rank_reversal_20pct": lambda s, r: np.where(r.random(len(s)) < 0.2, -s / 2.0, s / 2.0),
        "outlier_upset": lambda s, r: s / 2.0 + (r.random(len(s)) < 0.12) * r.normal(0, 2.2, len(s)),
        "distribution_shift_mixture": lambda s, r: (s / 1.2 if r.random() < 0.5 else s / 4.5),
    }


def run():
    master = np.random.default_rng(SEED)
    world_defs = worlds()
    race_seeds = master.integers(0, 2**32 - 1, size=(len(world_defs), RACES_PER_WORLD), dtype=np.uint64)
    out = {
        "record": "R0_T2_SIMWORLD_MATRIX_RESULT_v1",
        "seed": SEED,
        "races_per_world": RACES_PER_WORLD,
        "temperatures_compared": TEMPERATURES,
        "interpretation_guard": "Simulation-only engineering evidence. Never promotion evidence and never a substitute for independent real predictive validation.",
        "worlds": {},
    }
    for wi, (name, transform) in enumerate(world_defs.items()):
        nlls = {t: [] for t in TEMPERATURES}
        top1 = {t: 0 for t in TEMPERATURES}
        field_counts = defaultdict(int)
        r0_vs_uniform = []
        for k in range(RACES_PER_WORLD):
            rng = np.random.default_rng(int(race_seeds[wi, k]))
            n = int(rng.integers(5, 10))
            field_counts[n] += 1
            scores = rng.normal(0, 1.4, n)
            latent = np.array(transform(scores, rng), dtype=float)
            order = pl_sample(latent, rng)
            for t in TEMPERATURES:
                nll = ordered_top3_nll(scores, order, t)
                nlls[t].append(nll)
                top1[t] += int(int(np.argmax(scores / t)) == order[0])
            uniform_nll = math.log(n) + math.log(n - 1) + math.log(n - 2)
            r0_vs_uniform.append(uniform_nll - nlls[2.0][-1])
        means = {str(t): float(np.mean(nlls[t])) for t in TEMPERATURES}
        best_t = min(TEMPERATURES, key=lambda t: means[str(t)])
        out["worlds"][name] = {
            "races": RACES_PER_WORLD,
            "field_size_counts": {str(k): v for k, v in sorted(field_counts.items())},
            "mean_ordered_top3_nll_by_temperature": means,
            "best_simulation_temperature": best_t,
            "r0_t2_mean_ordered_top3_nll": means["2.0"],
            "r0_t2_mean_improvement_vs_sequential_uniform": float(np.mean(r0_vs_uniform)),
            "r0_t2_top1_accuracy": top1[2.0] / RACES_PER_WORLD,
            "r0_t2_regret_vs_best_temp_nll": means["2.0"] - means[str(best_t)],
        }
    return out


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, sort_keys=True))
