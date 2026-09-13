from __future__ import annotations

import hashlib
import inspect
import json
import math
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from statistics import mean

from digital_twin_v1 import generate_race, pre_view, world_joint_distribution

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PREREG = ROOT / "research_candidates" / "KEIRIN_SYNTHETIC_PRE_IDENTIFIABILITY_AUDIT_PREREG_20260913_v3.json"
OUT = ROOT / "research_candidates" / "synthetic_pre_identifiability_audit_v3"
EXPECTED_PREREG_SHA256 = "992fe53f6d09cda1f3c205ea7e0aeba5b98e76ff6e36759a5aca1c5f173dd07e"
WORLDS = ("W0","W1","W2","W3","W4")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(name: str, obj: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def canonical_pre_hash(pre: dict) -> str:
    raw = json.dumps(pre, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def entropy_from_counts(counts: Counter) -> float:
    total = sum(counts.values())
    return -sum((n/total)*math.log(n/total) for n in counts.values() if n)


def tv(a: dict, b: dict) -> float:
    if set(a) != set(b):
        raise RuntimeError("oracle_support_mismatch")
    return 0.5 * sum(abs(float(a[k]) - float(b[k])) for k in a)


def main() -> int:
    if sha256_file(PREREG) != EXPECTED_PREREG_SHA256:
        raise RuntimeError("prereg_sha256_mismatch")
    rule=json.loads(PREREG.read_text(encoding="utf-8"))
    if rule.get("evidence_class") != "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY":
        raise RuntimeError("evidence_class_invalid")
    cfg=rule["batch"]
    seed=int(cfg["seed"]); races=int(cfg["races"])
    worlds=tuple(cfg["worlds"])
    if worlds != WORLDS:
        raise RuntimeError("world_binding_invalid")

    dump("00_GOVERNANCE_AUDIT.json", {
        "record":"KEIRIN_SYNTHETIC_PRE_IDENTIFIABILITY_GOVERNANCE_AUDIT_v3",
        "status":"PASS_SYNTHETIC_ONLY",
        "prereg_sha256":EXPECTED_PREREG_SHA256,
        "generate_race_parameters":list(inspect.signature(generate_race).parameters),
        "generate_race_has_world_parameter":"world" in inspect.signature(generate_race).parameters,
        "real_historical_input":False,
        "RESULT_PAYOUT":"NOT_ACCESSED",
        "ECON_HOLDOUT1000":"SEALED_NOT_ACCESSED",
        "DEV2000_RESULT_PAYOUT":"NOT_ACCESSED",
        "odds":"NOT_USED",
        "economics":"NOT_COMPUTED",
        "roi":"NOT_COMPUTED",
        "runtime":"OFF",
        "automatic_betting":False,
        "real_money":False,
        "spend":False,
        "credential":False,
    })

    groups=defaultdict(Counter)
    matched_equal=0
    pair_tv=defaultdict(list)
    sample_count=0
    for idx in range(races):
        race=generate_race(seed=seed, race_index=idx, event_format=cfg["event_format"])
        hashes=[]
        oracle={w:world_joint_distribution(race,w) for w in worlds}
        for w in worlds:
            pre=pre_view(race)
            h=canonical_pre_hash(pre)
            hashes.append(h)
            groups[h][w]+=1
            sample_count+=1
        if len(set(hashes)) == 1:
            matched_equal+=1
        for a,b in combinations(worlds,2):
            pair_tv[f"{a}__{b}"].append(tv(oracle[a],oracle[b]))

    world_counts=Counter({w:races for w in worlds})
    h_world=entropy_from_counts(world_counts)
    total=sample_count
    h_cond=0.0
    all_five=0
    exact_once=0
    for counts in groups.values():
        n=sum(counts.values())
        h_cond += (n/total)*entropy_from_counts(counts)
        if set(counts)==set(worlds):
            all_five += 1
        if all(counts.get(w,0)==1 for w in worlds):
            exact_once += 1
    mi=h_world-h_cond

    pair_means={k:mean(v) for k,v in sorted(pair_tv.items())}
    metrics={
        "races":races,
        "world_labeled_samples":sample_count,
        "unique_PRE_groups":len(groups),
        "matched_PRE_hash_equality_rate_across_worlds":matched_equal/races,
        "unique_PRE_groups_with_all_five_world_labels_rate":all_five/len(groups),
        "unique_PRE_groups_with_each_world_exactly_once_rate":exact_once/len(groups),
        "empirical_world_entropy_nats":h_world,
        "empirical_conditional_world_entropy_given_PRE_nats":h_cond,
        "empirical_mutual_information_PRE_world_nats":mi,
        "pairwise_oracle_TV_mean_by_pair":pair_means,
        "mean_pairwise_oracle_total_variation_distance":mean(pair_means.values()),
        "minimum_pairwise_oracle_total_variation_distance":min(pair_means.values()),
    }
    passed=(
        metrics["matched_PRE_hash_equality_rate_across_worlds"] == 1.0
        and metrics["unique_PRE_groups_with_each_world_exactly_once_rate"] == 1.0
        and abs(mi) <= 1e-12
        and metrics["mean_pairwise_oracle_total_variation_distance"] > 0.02
    )
    result={
        "record":"KEIRIN_SYNTHETIC_PRE_IDENTIFIABILITY_AUDIT_RESULT_v3",
        "status":"PASS_CURRENT_W0_W4_PRE_NONIDENTIFIABILITY_CONFIRMED" if passed else "NO_NONIDENTIFIABILITY_CLAIM",
        "evidence_class":"SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "metrics":metrics,
        "interpretation":(
            "Current W0-W4 assigns materially different hidden outcome mechanisms to exactly matched PRE support. "
            "Therefore prediction-time PRE cannot identify the world label in this twin; W0-W4 can test universal robustness "
            "but cannot fairly test a learned PRE-only regime selector."
        ) if passed else "Predeclared nonidentifiability conditions were not all met.",
        "real_keirin_claim":False,
        "model_promotion":False,
        "protected_boundaries":rule["protected_boundaries"],
    }
    dump("01_RESULT.json",result)
    print(json.dumps({"status":result["status"],"metrics":metrics,"runtime":"OFF","automatic_betting":False},sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
