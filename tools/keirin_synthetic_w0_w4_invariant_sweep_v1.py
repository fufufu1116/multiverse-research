#!/usr/bin/env python3
from __future__ import annotations

from itertools import permutations
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
NEW_LINEAGE = ROOT / "v3" / "historical_all_market" / "new_lineage"
sys.path.insert(0, str(NEW_LINEAGE))

from digital_twin_v1 import generate_race, pre_view, world_joint_distribution

WORLDS = ("W0", "W1", "W2", "W3", "W4")
CASE_COUNT = 128
EXPECTED_SUPPORT = len(list(permutations(range(1, 8), 3)))


def main() -> None:
    max_mass_error = 0.0
    min_probability = 1.0
    deterministic_checks = 0
    bank_lengths = set()
    observed_formats = set()

    for case in range(CASE_COUNT):
        seed = 20260821 + case
        race_index = case % 32
        race = generate_race(seed=seed, race_index=race_index)
        if race.event_format != "STANDARD_FI_FII_7" or len(race.riders) != 7:
            raise AssertionError(f"unexpected_standard_format:{case}")

        bank_lengths.add(race.bank_length_m)
        observed_formats.add(race.event_format)
        pre = pre_view(race)
        if pre.get("field_size") != 7 or pre.get("event_format") != "STANDARD_FI_FII_7":
            raise AssertionError(f"pre_format_failed:{case}")
        if any("latent_skill" in rider for rider in pre["riders"]):
            raise AssertionError(f"latent_skill_leak:{case}")

        for world in WORLDS:
            joint = world_joint_distribution(race, world)
            if len(joint) != EXPECTED_SUPPORT:
                raise AssertionError(f"support_failed:{case}:{world}:{len(joint)}")
            mass_error = abs(sum(joint.values()) - 1.0)
            max_mass_error = max(max_mass_error, mass_error)
            if mass_error > 1e-10:
                raise AssertionError(f"mass_failed:{case}:{world}:{mass_error}")
            for (first, second, third), p in joint.items():
                if first == second or first == third or second == third:
                    raise AssertionError(f"duplicate_finisher:{case}:{world}")
                if not math.isfinite(p) or p < 0.0:
                    raise AssertionError(f"invalid_probability:{case}:{world}:{p}")
                min_probability = min(min_probability, p)

            if case < 8:
                repeat = world_joint_distribution(race, world)
                if repeat != joint:
                    raise AssertionError(f"nondeterministic_world:{case}:{world}")
                deterministic_checks += 1

    result = {
        "record": "KEIRIN_SYNTHETIC_W0_W4_INVARIANT_SWEEP_v1",
        "status": "PASS",
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "cases": CASE_COUNT,
        "worlds": list(WORLDS),
        "world_evaluations": CASE_COUNT * len(WORLDS),
        "expected_support_per_world": EXPECTED_SUPPORT,
        "max_probability_mass_error": max_mass_error,
        "minimum_observed_probability": min_probability,
        "deterministic_repeat_checks": deterministic_checks,
        "observed_event_formats": sorted(observed_formats),
        "observed_bank_lengths_m": sorted(bank_lengths),
        "real_live_input_collection": False,
        "economics": False,
        "real_world_validation": False,
        "protected_or_quarantined_input": False,
        "result_payout_access": False,
        "holdout_access": False,
        "pr15_metrics_access": False,
        "scientific_segment_c_scoring_count": 0,
        "model_promotion": False,
        "external_provider_contact": False,
        "real_money_wagering": False,
        "real_world_edge_or_roi_evidence": False,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    print("KEIRIN_SYNTHETIC_W0_W4_INVARIANT_SWEEP_PASS")


if __name__ == "__main__":
    main()
