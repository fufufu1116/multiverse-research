from __future__ import annotations

from dataclasses import replace

from reality_source_transport_gate_v0 import (
    SourceCaptureRecord,
    SourceTransportError,
    automated_bulk_collection_authorized,
    may_backfill_current_profile_into_historical_race,
    may_use_as_reality_point_parameter,
    may_use_post_race_reconstructed_line_as_pre,
    require_reality_point_parameter_admission,
    truth_generator_ready,
    validate_capture,
)


def expect_fail(fn, contains: str) -> None:
    try:
        fn()
    except SourceTransportError as exc:
        assert contains in str(exc), (contains, str(exc))
    else:
        raise AssertionError(f"expected SourceTransportError containing {contains!r}")


def main() -> None:
    static = SourceCaptureRecord(
        source_id="KEIRIN_2026_PROGRAM_MASTER",
        url="https://www.keirin.jp/pc/dfw/portal/guest/data/prize/2026/2026.html",
        source_class="OFFICIAL_PROGRAM",
        capture_mode="MANUAL_FOUNDATION_RESEARCH",
        retrieved_at="2026-09-01T15:00:00+09:00",
        payload_sha256="a" * 64,
        rights_basis="manual foundation research; no bulk reuse claim",
    )
    validate_capture(static)

    prospective = SourceCaptureRecord(
        source_id="KEIRIN_RACER_PROFILE_CURRENT",
        url="https://www.keirin.jp/pc/racerprofile?snum=015045",
        source_class="OFFICIAL_PUBLIC_VIEW_ONLY",
        capture_mode="PROSPECTIVE_POINT_IN_TIME_SNAPSHOT",
        retrieved_at="2026-09-01T14:00:00+09:00",
        payload_sha256="b" * 64,
        rights_basis="narrow prospective snapshot candidate only",
        source_update_timestamp="2026-09-01T02:36:00+09:00",
        decision_timestamp="2026-09-01T14:30:00+09:00",
    )
    validate_capture(prospective)

    expect_fail(
        lambda: validate_capture(replace(prospective, retrieved_at="2026-09-01T15:00:00+09:00")),
        "retrieved_at:after_decision",
    )
    expect_fail(
        lambda: validate_capture(replace(static, url="http://www.keirin.jp/test")),
        "url:https_required",
    )
    expect_fail(
        lambda: validate_capture(replace(static, url="https://example.com/test")),
        "official_source:host_mismatch",
    )

    assert may_use_as_reality_point_parameter("race_grade/program_family/field_size eligibility")
    assert may_use_as_reality_point_parameter("venue bank circumference")
    assert not may_use_as_reality_point_parameter("competition_score/win_rate/quinella_rate/trio_rate/H/B/current maneuver summaries")
    assert not may_use_as_reality_point_parameter("LEGSHOW_OBSERVED_LINE structured snapshot")

    expect_fail(
        lambda: require_reality_point_parameter_admission("line-shape frequency / formation probabilities"),
        "reality_point_parameter:not_admitted",
    )

    assert may_backfill_current_profile_into_historical_race() is False
    assert may_use_post_race_reconstructed_line_as_pre() is False
    assert automated_bulk_collection_authorized() is False
    assert truth_generator_ready() is False

    print("PASS reality_source_transport_gate_selftest_v0")


if __name__ == "__main__":
    main()
