#!/usr/bin/env python3
"""Deterministic workload-shape cost normalizer for Make vs n8n.

Research-only utility. No network access, publication, monetization, or account action.
It deliberately preserves unknowns instead of pretending dynamic AI/API/self-host costs are known.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class MakeEstimate:
    state: str
    ordinary_credits_estimate: Optional[int]
    notes: List[str]


@dataclass
class N8nEstimate:
    state: str
    executions_estimate: int
    notes: List[str]


def normalize_workload(
    monthly_runs: int,
    ordinary_make_steps_per_run: int,
    make_dynamic_ai: bool = False,
    n8n_external_ai_or_api: bool = False,
) -> Dict[str, Any]:
    if monthly_runs < 0:
        raise ValueError("monthly_runs must be >= 0")
    if ordinary_make_steps_per_run < 1:
        raise ValueError("ordinary_make_steps_per_run must be >= 1")

    common_notes = [
        "Billing cadence, currency, tax and checked-date must remain visible near any price.",
        "Retries/redelivery, bundles/items, branch firing and polling can change real workload economics.",
        "Third-party model/API charges are separate from SaaS platform billing unless explicitly included by current terms.",
    ]

    if make_dynamic_ai:
        make = MakeEstimate(
            state="REQUIRES_DYNAMIC_AI_USAGE_MODEL",
            ordinary_credits_estimate=None,
            notes=[
                "Do not estimate Make dynamic-AI credit usage from runs x ordinary steps alone.",
                *common_notes,
            ],
        )
    else:
        credits = monthly_runs * ordinary_make_steps_per_run
        if credits <= 1_000:
            state = "FREE_1K_CAPACITY"
        elif credits <= 10_000:
            state = "10K_BUCKET_CAPACITY"
        else:
            state = "ABOVE_10K_SELECT_HIGHER_BUCKET"
        make = MakeEstimate(
            state=state,
            ordinary_credits_estimate=credits,
            notes=[
                "Estimate assumes ordinary one-credit module actions only; actual scenario design can differ.",
                *common_notes,
            ],
        )

    executions = monthly_runs
    if executions <= 2_500:
        n8n_state = "STARTER_2_5K_CAPACITY"
    elif executions <= 10_000:
        n8n_state = "PRO1_10K_CAPACITY"
    elif executions <= 50_000:
        n8n_state = "PRO2_50K_CAPACITY"
    else:
        n8n_state = "ABOVE_PRO2_SELF_SERVE_OR_ENTERPRISE_CHECK"

    n8n_notes = [
        "Cloud execution count is modeled at workflow-run level; step count is not multiplied into the execution count.",
        "Separate n8n AI-credit allowances and current plan-generation details must be checked before claiming AI cost coverage.",
        *common_notes,
    ]
    if n8n_external_ai_or_api:
        n8n_notes.insert(0, "External AI/API usage cost is explicitly unresolved and must be modeled separately.")

    n8n = N8nEstimate(
        state=n8n_state,
        executions_estimate=executions,
        notes=n8n_notes,
    )

    return {
        "input": {
            "monthly_runs": monthly_runs,
            "ordinary_make_steps_per_run": ordinary_make_steps_per_run,
            "make_dynamic_ai": make_dynamic_ai,
            "n8n_external_ai_or_api": n8n_external_ai_or_api,
        },
        "make": asdict(make),
        "n8n": asdict(n8n),
        "decision_rule": "NO_GENERIC_WINNER_RECOMPUTE_WITH_EXACT_WORKLOAD_AND_CURRENT_TERMS",
    }


def _self_test() -> None:
    cases = [
        (100, 4, "FREE_1K_CAPACITY", "STARTER_2_5K_CAPACITY", 400),
        (1_000, 4, "10K_BUCKET_CAPACITY", "STARTER_2_5K_CAPACITY", 4_000),
        (2_500, 4, "10K_BUCKET_CAPACITY", "STARTER_2_5K_CAPACITY", 10_000),
        (5_000, 4, "ABOVE_10K_SELECT_HIGHER_BUCKET", "PRO1_10K_CAPACITY", 20_000),
        (1_000, 20, "ABOVE_10K_SELECT_HIGHER_BUCKET", "STARTER_2_5K_CAPACITY", 20_000),
    ]
    for runs, steps, make_state, n8n_state, make_credits in cases:
        result = normalize_workload(runs, steps)
        assert result["make"]["state"] == make_state
        assert result["make"]["ordinary_credits_estimate"] == make_credits
        assert result["n8n"]["state"] == n8n_state
        assert result["n8n"]["executions_estimate"] == runs

    dynamic = normalize_workload(1_000, 4, make_dynamic_ai=True)
    assert dynamic["make"]["state"] == "REQUIRES_DYNAMIC_AI_USAGE_MODEL"
    assert dynamic["make"]["ordinary_credits_estimate"] is None

    external = normalize_workload(500, 3, n8n_external_ai_or_api=True)
    assert external["n8n"]["notes"][0].startswith("External AI/API")

    print("SELF_TEST_PASS")


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        _self_test()
        return
    if len(sys.argv) not in (3, 4, 5):
        print(
            "usage: automation_cost_normalizer_v1.py RUNS_PER_MONTH MAKE_ORDINARY_STEPS [MAKE_DYNAMIC_AI 0|1] [N8N_EXTERNAL_AI_API 0|1]",
            file=sys.stderr,
        )
        raise SystemExit(2)

    runs = int(sys.argv[1])
    steps = int(sys.argv[2])
    make_ai = bool(int(sys.argv[3])) if len(sys.argv) >= 4 else False
    n8n_ext = bool(int(sys.argv[4])) if len(sys.argv) >= 5 else False
    print(json.dumps(normalize_workload(runs, steps, make_ai, n8n_ext), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
