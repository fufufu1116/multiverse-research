#!/usr/bin/env python3
"""Strict evidence-sufficiency diagnostics for prospective longshot validation v2."""

from datetime import date
from math import isfinite
import re
from typing import Iterable, Dict, Mapping

BANDS = ("MID_HOLE", "LONGSHOT", "EXTREME_LONGSHOT")
MIN_EXPECTED_HITS = 5.0
MIN_ACTUAL_HITS = 5
MIN_WEEKS = 8


class EvidenceSufficiencyError(ValueError):
    pass


def _finite(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceSufficiencyError(f"{label}_must_be_numeric")
    x = float(value)
    if not isfinite(x):
        raise EvidenceSufficiencyError(f"{label}_must_be_finite")
    return x


def _probability(value) -> float:
    x = _finite(value, "conservative_probability")
    if not (0.0 <= x <= 1.0):
        raise EvidenceSufficiencyError("conservative_probability_must_be_in_[0,1]")
    return x


def _iso_week(value) -> str:
    if not isinstance(value, str):
        raise EvidenceSufficiencyError("iso_week_must_be_string")
    m = re.fullmatch(r"(\d{4})-W(\d{2})", value)
    if not m:
        raise EvidenceSufficiencyError("invalid_iso_week_format")
    year, week = int(m.group(1)), int(m.group(2))
    try:
        date.fromisocalendar(year, week, 1)
    except ValueError as exc:
        raise EvidenceSufficiencyError("invalid_iso_week_value") from exc
    return value


def _normalize_rows(rows: Iterable[Dict]) -> list[dict]:
    out = []
    for i, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise EvidenceSufficiencyError(f"row_must_be_mapping:{i}")
        band = raw.get("band")
        if band not in BANDS:
            raise EvidenceSufficiencyError(f"unsupported_band:{band}")
        p = _probability(raw.get("conservative_probability"))
        ret = _finite(raw.get("return_units", 0.0), "return_units")
        if ret < 0.0:
            raise EvidenceSufficiencyError("return_units_must_be_nonnegative")
        week = _iso_week(raw.get("iso_week"))
        row = dict(raw)
        row["conservative_probability"] = p
        row["return_units"] = ret
        row["iso_week"] = week
        out.append(row)
    return out


def evaluate(rows: Iterable[Dict]) -> Dict:
    xs = _normalize_rows(rows)
    out = []
    for band in BANDS:
        bs = [x for x in xs if x["band"] == band]
        expected_hits = sum(x["conservative_probability"] for x in bs)
        actual_hits = sum(1 for x in bs if x["return_units"] > 0.0)
        weeks = len({x["iso_week"] for x in bs})
        out.append({
            "band": band,
            "decisions": len(bs),
            "expected_hits_under_frozen_conservative_probability": expected_hits,
            "actual_hits": actual_hits,
            "calendar_weeks": weeks,
            "minimum_expected_hits": MIN_EXPECTED_HITS,
            "minimum_actual_hits": MIN_ACTUAL_HITS,
            "minimum_weeks": MIN_WEEKS,
            "evidence_sufficient": (
                expected_hits >= MIN_EXPECTED_HITS
                and actual_hits >= MIN_ACTUAL_HITS
                and weeks >= MIN_WEEKS
            ),
        })
    return {
        "status": "PROPOSED_EVIDENCE_SUFFICIENCY_ONLY_V2",
        "bands": out,
        "all_bands_sufficient": all(x["evidence_sufficient"] for x in out),
        "real_money_authorized": False,
    }


def required_decisions_for_expected_hits(
    avg_probability: float,
    expected_hits: float = MIN_EXPECTED_HITS,
) -> float:
    p = _finite(avg_probability, "avg_probability")
    target = _finite(expected_hits, "expected_hits")
    if not (0.0 < p <= 1.0):
        raise EvidenceSufficiencyError("avg_probability_must_be_in_(0,1]")
    if target <= 0.0:
        raise EvidenceSufficiencyError("expected_hits_must_be_positive")
    return target / p
