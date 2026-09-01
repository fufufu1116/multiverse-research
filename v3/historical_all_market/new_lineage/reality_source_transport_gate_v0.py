from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse
import re


class SourceTransportError(ValueError):
    """Fail-closed source transport/admission error."""


SOURCE_CLASSES = {
    "OFFICIAL_RULE",
    "OFFICIAL_PROGRAM",
    "OFFICIAL_MASTER",
    "OFFICIAL_PUBLIC_VIEW_ONLY",
    "PRE_EMPIRICAL_AUTHORIZED",
    "AUTHORIZED_THIRD_PARTY_FEED",
    "ASSUMPTION_RANGE",
}

CAPTURE_MODES = {
    "MANUAL_FOUNDATION_RESEARCH",
    "PROSPECTIVE_POINT_IN_TIME_SNAPSHOT",
    "AUTHORIZED_FEED",
}

FIELD_STATUS = {
    "race_grade/program_family/field_size eligibility": "GREEN_STATIC_OFFICIAL",
    "venue bank circumference": "GREEN_STATIC_OFFICIAL",
    "rider identity/profile current state": "YELLOW_PROSPECTIVE_SNAPSHOT_ONLY",
    "competition_score/win_rate/quinella_rate/trio_rate/H/B/current maneuver summaries": "YELLOW_PROSPECTIVE_SNAPSHOT_ONLY",
    "historical point-in-time rider PRE statistics": "RED_NO_PROVEN_ARCHIVE_TRANSPORT",
    "PRE_EVENT_EXPECTED_LINE structured snapshot": "RED_TRANSPORT_UNPROVEN",
    "LEGSHOW_OBSERVED_LINE structured snapshot": "RED_TRANSPORT_UNPROVEN",
    "line-shape frequency / formation probabilities": "RED_UNCALIBRATED",
    "weather/wind point-in-time observation": "RED_SOURCE_AND_TIMESTAMP_TRANSPORT_NOT_YET_BOUND",
    "home straight/cant full venue master": "RED_MASTER_INCOMPLETE_IN_CURRENT_REVIEW",
    "tactical/line effect sizes": "RED_UNCALIBRATED",
}

ALLOWED_OFFICIAL_HOSTS = {"keirin.jp", "www.keirin.jp"}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class SourceCaptureRecord:
    source_id: str
    url: str
    source_class: str
    capture_mode: str
    retrieved_at: str
    payload_sha256: str
    rights_basis: str
    source_update_timestamp: str | None = None
    decision_timestamp: str | None = None


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise SourceTransportError(f"{name}:empty")


def _ts(name: str, value: str) -> datetime:
    _nonempty(name, value)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceTransportError(f"{name}:invalid_iso8601") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise SourceTransportError(f"{name}:timezone_required")
    return dt


def validate_capture(record: SourceCaptureRecord) -> None:
    for name, value in (
        ("source_id", record.source_id),
        ("url", record.url),
        ("rights_basis", record.rights_basis),
    ):
        _nonempty(name, value)

    if record.source_class not in SOURCE_CLASSES:
        raise SourceTransportError(f"source_class:unknown:{record.source_class}")
    if record.capture_mode not in CAPTURE_MODES:
        raise SourceTransportError(f"capture_mode:unknown:{record.capture_mode}")
    if not _SHA256_RE.match(record.payload_sha256):
        raise SourceTransportError("payload_sha256:invalid")

    parsed = urlparse(record.url)
    if parsed.scheme != "https":
        raise SourceTransportError("url:https_required")

    if record.source_class.startswith("OFFICIAL_"):
        if parsed.hostname not in ALLOWED_OFFICIAL_HOSTS:
            raise SourceTransportError("official_source:host_mismatch")

    retrieved = _ts("retrieved_at", record.retrieved_at)
    if record.source_update_timestamp is not None:
        updated = _ts("source_update_timestamp", record.source_update_timestamp)
        if updated > retrieved:
            raise SourceTransportError("source_update_timestamp:after_retrieval")

    if record.capture_mode == "PROSPECTIVE_POINT_IN_TIME_SNAPSHOT":
        if record.decision_timestamp is None:
            raise SourceTransportError("decision_timestamp:required_for_prospective_snapshot")
        decision = _ts("decision_timestamp", record.decision_timestamp)
        if retrieved > decision:
            raise SourceTransportError("retrieved_at:after_decision")

    if record.capture_mode == "AUTHORIZED_FEED" and record.source_class not in {
        "PRE_EMPIRICAL_AUTHORIZED",
        "AUTHORIZED_THIRD_PARTY_FEED",
    }:
        raise SourceTransportError("authorized_feed:source_class_mismatch")


def field_status(field: str) -> str:
    try:
        return FIELD_STATUS[field]
    except KeyError as exc:
        raise SourceTransportError(f"field:unregistered:{field}") from exc


def may_use_as_reality_point_parameter(field: str) -> bool:
    """Return True only for already-green static official calibration targets.

    YELLOW prospective snapshot fields are intentionally False until a separate
    capture protocol is approved and mechanically bound. RED fields are False.
    """
    return field_status(field) == "GREEN_STATIC_OFFICIAL"


def require_reality_point_parameter_admission(field: str) -> None:
    status = field_status(field)
    if status != "GREEN_STATIC_OFFICIAL":
        raise SourceTransportError(f"reality_point_parameter:not_admitted:{field}:{status}")


def may_backfill_current_profile_into_historical_race() -> bool:
    return False


def may_use_post_race_reconstructed_line_as_pre() -> bool:
    return False


def automated_bulk_collection_authorized() -> bool:
    return False


def truth_generator_ready() -> bool:
    return False
