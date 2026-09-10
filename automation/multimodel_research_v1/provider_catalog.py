from __future__ import annotations

import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from automation.multimodel_research_v1.model import (
    NONAUTHORITY_KEYS,
    require,
    sha256_json,
)

CATALOG_SCHEMA = "MULTIVERSE_PROVIDER_MODEL_CATALOG_SNAPSHOT_v1"
CATALOG_PATH = Path(__file__).with_name(
    "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
)

CATALOG_KEYS = {
    "schema",
    "snapshot_id",
    "observed_at",
    "currency",
    "pricing_basis",
    "entries",
    "nonauthority",
}

ENTRY_KEYS = {
    "provider",
    "model_id",
    "classification",
    "lifecycle",
    "structured_json",
    "input_usd_micros_per_million_tokens",
    "output_usd_micros_per_million_tokens",
    "pricing_valid_through",
    "official_evidence_refs",
}

EXPECTED_PROVIDERS = {
    "GOOGLE_GEMINI",
    "ANTHROPIC_CLAUDE",
}


def _parse_utc(value: Any, code: str) -> datetime:
    require(
        isinstance(value, str)
        and bool(
            re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
                value,
            )
        ),
        code,
    )
    return datetime.fromisoformat(value[:-1] + "+00:00")


def validate_provider_catalog(
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(snapshot, dict)
        and set(snapshot) == CATALOG_KEYS,
        "CATALOG_SCHEMA_KEYS",
    )
    require(
        snapshot["schema"] == CATALOG_SCHEMA,
        "CATALOG_SCHEMA_VERSION",
    )

    snapshot_id = snapshot["snapshot_id"]
    snapshot_match = (
        re.fullmatch(
            r"provider-model-catalog-(\d{8})",
            snapshot_id,
        )
        if isinstance(snapshot_id, str)
        else None
    )
    require(snapshot_match is not None, "CATALOG_SNAPSHOT_ID")
    observed_at = _parse_utc(
        snapshot["observed_at"],
        "CATALOG_OBSERVED_AT",
    )
    require(
        observed_at.strftime("%Y%m%d")
        == snapshot_match.group(1),
        "CATALOG_SNAPSHOT_ID_DATE_MISMATCH",
    )

    require(
        snapshot["currency"] == "USD",
        "CATALOG_CURRENCY",
    )
    require(
        snapshot["pricing_basis"] == "PER_MILLION_TOKENS",
        "CATALOG_PRICING_BASIS",
    )

    entries = snapshot["entries"]
    require(
        isinstance(entries, list) and len(entries) == 2,
        "CATALOG_ENTRIES_COUNT",
    )

    seen: set[str] = set()
    for entry in entries:
        require(
            isinstance(entry, dict)
            and set(entry) == ENTRY_KEYS,
            "CATALOG_ENTRY_SCHEMA",
        )
        provider = entry["provider"]
        require(
            provider in EXPECTED_PROVIDERS,
            "CATALOG_PROVIDER",
        )
        require(
            provider not in seen,
            "CATALOG_DUPLICATE_PROVIDER",
        )
        seen.add(provider)

        require(
            isinstance(entry["model_id"], str)
            and len(entry["model_id"]) >= 3,
            "CATALOG_MODEL_ID",
        )
        require(
            entry["classification"] == "PINNED_OR_STABLE",
            "CATALOG_MODEL_NOT_STABLE",
        )
        require(
            entry["lifecycle"] in {"GA", "CURRENT"},
            "CATALOG_LIFECYCLE",
        )
        require(
            entry["structured_json"] is True,
            "CATALOG_STRUCTURED_JSON_REQUIRED",
        )

        for key in (
            "input_usd_micros_per_million_tokens",
            "output_usd_micros_per_million_tokens",
        ):
            value = entry[key]
            require(
                isinstance(value, int)
                and not isinstance(value, bool)
                and value > 0,
                f"CATALOG_PRICE:{key}",
            )

        pricing_valid_through = entry["pricing_valid_through"]
        require(
            pricing_valid_through is None
            or (
                isinstance(pricing_valid_through, str)
                and bool(
                    re.fullmatch(
                        r"\d{4}-\d{2}-\d{2}",
                        pricing_valid_through,
                    )
                )
            ),
            "CATALOG_PRICING_VALID_THROUGH",
        )

        refs = entry["official_evidence_refs"]
        require(
            isinstance(refs, list) and bool(refs),
            "CATALOG_EVIDENCE_REFS",
        )
        for ref in refs:
            require(
                isinstance(ref, str)
                and ref.startswith("https://"),
                "CATALOG_EVIDENCE_REF_URL",
            )
            if provider == "GOOGLE_GEMINI":
                require(
                    "ai.google.dev/" in ref,
                    "CATALOG_GEMINI_EVIDENCE_DOMAIN",
                )
            else:
                require(
                    "platform.claude.com/" in ref,
                    "CATALOG_CLAUDE_EVIDENCE_DOMAIN",
                )

    require(
        seen == EXPECTED_PROVIDERS,
        "CATALOG_PROVIDER_SET",
    )

    nonauthority = snapshot["nonauthority"]
    require(
        isinstance(nonauthority, dict)
        and set(nonauthority) == NONAUTHORITY_KEYS,
        "CATALOG_NONAUTHORITY_SCHEMA",
    )
    for key, value in nonauthority.items():
        require(
            value is False,
            f"CATALOG_NONAUTHORITY_NOT_FALSE:{key}",
        )
    return snapshot


def catalog_entry(
    snapshot: dict[str, Any],
    provider: str,
) -> dict[str, Any]:
    validate_provider_catalog(snapshot)
    for entry in snapshot["entries"]:
        if entry["provider"] == provider:
            return entry
    raise RuntimeError("CATALOG_PROVIDER_NOT_FOUND")


def catalog_entry_sha256(
    snapshot: dict[str, Any],
    provider: str,
) -> str:
    return sha256_json(catalog_entry(snapshot, provider))


def estimate_smoke_cost_usd_micros(
    snapshot: dict[str, Any],
    provider: str,
    input_tokens: int,
    output_tokens: int,
) -> int:
    require(
        isinstance(input_tokens, int)
        and not isinstance(input_tokens, bool)
        and input_tokens >= 0,
        "CATALOG_INPUT_TOKENS",
    )
    require(
        isinstance(output_tokens, int)
        and not isinstance(output_tokens, bool)
        and output_tokens >= 0,
        "CATALOG_OUTPUT_TOKENS",
    )
    entry = catalog_entry(snapshot, provider)
    numerator = (
        input_tokens
        * entry["input_usd_micros_per_million_tokens"]
        + output_tokens
        * entry["output_usd_micros_per_million_tokens"]
    )
    return math.ceil(numerator / 1_000_000)


def validate_first_smoke_candidate(
    snapshot: dict[str, Any],
    provider: str,
    *,
    max_input_tokens: int = 32768,
    max_output_tokens: int = 4096,
    max_cost_usd_micros: int = 1_000_000,
) -> dict[str, Any]:
    entry = catalog_entry(snapshot, provider)
    estimated = estimate_smoke_cost_usd_micros(
        snapshot,
        provider,
        max_input_tokens,
        max_output_tokens,
    )
    require(
        estimated <= max_cost_usd_micros,
        "CATALOG_SMOKE_COST_EXCEEDS_CEILING",
    )
    return {
        "provider": provider,
        "model_id": entry["model_id"],
        "classification": entry["classification"],
        "structured_json": entry["structured_json"],
        "catalog_entry_sha256":
            catalog_entry_sha256(snapshot, provider),
        "estimated_max_cost_usd_micros": estimated,
        "spend_authority": False,
    }
