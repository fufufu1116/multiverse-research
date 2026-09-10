#!/usr/bin/env python3
"""B1a_MKT50_v1 preregistered ticket-probability transform.

Winner layer: B1a_RECONSTITUTED_v1 unchanged.
Ticket layer, within each race+market:
  q_raw(ticket) = sqrt(max(p_model, 1e-15) * max(p_market, 1e-15))
  q(ticket) = q_raw(ticket) / sum(q_raw)

The 0.50/0.50 weights and epsilon are fixed by preregistration and are not configurable.
"""
from __future__ import annotations
import math
from typing import Mapping

MODEL_NAME = "B1a_MKT50_v1"
POOL_WEIGHT_MODEL = 0.50
POOL_WEIGHT_MARKET = 0.50
EPS = 1e-15
SUPPORTED_MARKETS = ("3rentan", "2shatan")

class FailClosed(ValueError):
    pass

def _clean_distribution(d: Mapping[str, float], label: str) -> dict[str, float]:
    if not isinstance(d, Mapping) or not d:
        raise FailClosed(f"{label}: empty/non-mapping distribution")
    out: dict[str, float] = {}
    total = 0.0
    for k, raw in d.items():
        key = str(k)
        try:
            v = float(raw)
        except Exception as e:
            raise FailClosed(f"{label}/{key}: non-numeric probability") from e
        if not math.isfinite(v) or v < 0.0:
            raise FailClosed(f"{label}/{key}: probability must be finite and >= 0")
        out[key] = v
        total += v
    if not math.isfinite(total) or total <= 0.0:
        raise FailClosed(f"{label}: invalid total")
    return {k: v / total for k, v in out.items()}

def pool_ticket_distribution(model_probability: Mapping[str, float], market_shape_probability: Mapping[str, float]) -> dict[str, float]:
    pm = _clean_distribution(model_probability, "model")
    pq = _clean_distribution(market_shape_probability, "market")
    if set(pm) != set(pq):
        raise FailClosed("ticket-universe mismatch")
    raw = {k: math.sqrt(max(pm[k], EPS) * max(pq[k], EPS)) for k in pm}
    z = sum(raw.values())
    if not math.isfinite(z) or z <= 0.0:
        raise FailClosed("pooled normalization constant invalid")
    out = {k: v / z for k, v in raw.items()}
    if abs(sum(out.values()) - 1.0) > 1e-12:
        raise FailClosed("pooled probabilities do not sum to one")
    return out

def market_shape_from_decimal_odds(odds: Mapping[str, float]) -> dict[str, float]:
    if not isinstance(odds, Mapping) or not odds:
        raise FailClosed("odds: empty/non-mapping")
    inv: dict[str, float] = {}
    for k, raw in odds.items():
        try:
            v = float(raw)
        except Exception as e:
            raise FailClosed(f"odds/{k}: non-numeric") from e
        if not math.isfinite(v) or v <= 1.0:
            raise FailClosed(f"odds/{k}: decimal odds must be finite and > 1")
        inv[str(k)] = 1.0 / v
    z = sum(inv.values())
    return {k: v / z for k, v in inv.items()}

def transform_race_market(market: str, model_probability: Mapping[str, float], market_shape_probability: Mapping[str, float]) -> dict[str, float]:
    if market not in SUPPORTED_MARKETS:
        raise FailClosed(f"unsupported market={market}")
    return pool_ticket_distribution(model_probability, market_shape_probability)
