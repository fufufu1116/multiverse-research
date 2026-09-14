#!/usr/bin/env python3
"""Conservative no-inventory resale break-even screen.

Research only. This utility does not scrape, buy, reserve, list, contact sellers,
or decide legal/permit status. Feed it independently verified sold-price samples and
current cost assumptions.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from typing import Any, Dict, Iterable, List


def nearest_rank_q25(values: List[float]) -> float:
    """Conservative lower quartile using nearest-rank definition."""
    if not values:
        raise ValueError("sold_prices must not be empty")
    ordered = sorted(values)
    index = max(0, math.ceil(0.25 * len(ordered)) - 1)
    return ordered[index]


def max_buy_price(
    sale_price: float,
    fee_rate: float,
    shipping: float,
    packaging: float,
    expected_return_loss: float,
    markdown_reserve: float,
    payout_cost: float,
    target_net_profit: float,
) -> float:
    return (
        sale_price * (1.0 - fee_rate)
        - shipping
        - packaging
        - expected_return_loss
        - markdown_reserve
        - payout_cost
        - target_net_profit
    )


def screen(
    sold_prices: Iterable[float],
    fee_rate: float,
    shipping: float,
    packaging: float,
    expected_return_loss: float,
    markdown_reserve: float,
    payout_cost: float,
    target_net_profit: float,
    observed_repeatable_sources_below_q25_break_even: int = 0,
) -> Dict[str, Any]:
    prices = [float(v) for v in sold_prices]
    if len(prices) < 1:
        raise ValueError("sold_prices must not be empty")
    if not 0 <= fee_rate < 1:
        raise ValueError("fee_rate must be in [0, 1)")
    for name, value in {
        "shipping": shipping,
        "packaging": packaging,
        "expected_return_loss": expected_return_loss,
        "markdown_reserve": markdown_reserve,
        "payout_cost": payout_cost,
        "target_net_profit": target_net_profit,
    }.items():
        if value < 0:
            raise ValueError(f"{name} must be >= 0")

    median_sale = float(statistics.median(prices))
    q25_sale = float(nearest_rank_q25(prices))
    median_buy_ceiling = max_buy_price(
        median_sale, fee_rate, shipping, packaging, expected_return_loss,
        markdown_reserve, payout_cost, target_net_profit,
    )
    q25_buy_ceiling = max_buy_price(
        q25_sale, fee_rate, shipping, packaging, expected_return_loss,
        markdown_reserve, payout_cost, target_net_profit,
    )

    sample_ok = len(prices) >= 20
    source_ok = observed_repeatable_sources_below_q25_break_even >= 5
    economics_possible = q25_buy_ceiling > 0

    if not sample_ok:
        state = "INSUFFICIENT_COMPLETED_SALES_SAMPLE"
    elif not economics_possible:
        state = "FAIL_Q25_BREAK_EVEN_NONPOSITIVE"
    elif not source_ok:
        state = "SOURCE_REPEATABILITY_NOT_PROVEN"
    else:
        state = "DESK_ECONOMICS_SURVIVES_REQUIRES_LEGAL_TOS_DEFECT_REVIEW"

    return {
        "state": state,
        "sample_count": len(prices),
        "median_sale_price": round(median_sale, 2),
        "lower_quartile_sale_price": round(q25_sale, 2),
        "max_buy_price_at_median": round(median_buy_ceiling, 2),
        "max_buy_price_at_lower_quartile": round(q25_buy_ceiling, 2),
        "repeatable_sources_below_q25_break_even": observed_repeatable_sources_below_q25_break_even,
        "thresholds": {
            "minimum_exact_model_completed_sales": 20,
            "minimum_repeatable_sources_below_q25_break_even": 5,
        },
        "cost_assumptions": {
            "fee_rate": fee_rate,
            "shipping": shipping,
            "packaging": packaging,
            "expected_return_loss": expected_return_loss,
            "markdown_reserve": markdown_reserve,
            "payout_cost": payout_cost,
            "target_net_profit": target_net_profit,
        },
        "guardrail": "PASS_IS_NOT_BUY_AUTHORITY_CHECK_PERMIT_TOS_CONDITION_AND_SOURCE_BEFORE_ANY_ACTION",
    }


def _self_test() -> None:
    base = [3500, 3600, 3700, 3800, 3900, 4000, 4100, 4200, 4300, 4400,
            4500, 4600, 4700, 4800, 4900, 5000, 5100, 5200, 5300, 5400]
    r = screen(base, 0.05, 750, 100, 300, 300, 0, 1000, 5)
    assert r["sample_count"] == 20
    assert r["state"] == "DESK_ECONOMICS_SURVIVES_REQUIRES_LEGAL_TOS_DEFECT_REVIEW"

    few = screen(base[:8], 0.05, 750, 100, 300, 300, 0, 1000, 5)
    assert few["state"] == "INSUFFICIENT_COMPLETED_SALES_SAMPLE"

    no_sources = screen(base, 0.05, 750, 100, 300, 300, 0, 1000, 2)
    assert no_sources["state"] == "SOURCE_REPEATABILITY_NOT_PROVEN"

    impossible = screen([1000] * 20, 0.10, 750, 100, 300, 300, 0, 1000, 5)
    assert impossible["state"] == "FAIL_Q25_BREAK_EVEN_NONPOSITIVE"

    print("SELF_TEST_PASS")


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        _self_test()
        return
    if len(sys.argv) != 2:
        print("usage: resale_break_even_screen_v0.py INPUT.json | --self-test", file=sys.stderr)
        raise SystemExit(2)
    with open(sys.argv[1], encoding="utf-8") as f:
        payload = json.load(f)
    print(json.dumps(screen(**payload), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
