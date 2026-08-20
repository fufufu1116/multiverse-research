from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from independent_official_pre_sensor_validator_v1 import PREREG, validate


def _write(root: Path, name: str, payload: dict) -> Path:
    path = root / name
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _base(captured: str, races: list[dict]) -> dict:
    return {
        "record": "TEST_CAPTURE",
        "captured_at_jst": captured,
        "admitted_race_count": len(races),
        "admitted_races": races,
        "policy_observed": {
            "first_party_only": True,
            "bypass": False,
            "third_party_completion": False,
            "result_or_payout_access": False,
            "post_race_backfill": False,
            "external_contact": False,
        },
    }


def _riders() -> list[dict]:
    return [
        {
            "rider_slot": slot,
            "rider_class": "A1" if slot <= 3 else "A2",
            "competition_score": 90.0 - slot,
            "B": slot % 4,
        }
        for slot in range(1, 8)
    ]


def _race(
    source_url: str,
    scheduled: str = "2026-08-21T20:50:00+09:00",
    riders: list[dict] | None = None,
) -> dict:
    return {
        "race_date": "2026-08-21",
        "venue": "大垣",
        "race_number": 1,
        "scheduled_start": scheduled,
        "field_size": 7,
        "source_url": source_url,
        "source_class": "FIRST_PARTY_OFFICIAL",
        "source_document_type": "OFFICIAL_RACECARD_PAGE_OR_FILE",
        "rider_pre": _riders() if riders is None else riders,
    }


def _must_fail(path: Path, label: str) -> None:
    try:
        validate(PREREG, [path])
    except ValueError:
        return
    raise AssertionError(f"expected_failure_not_raised:{label}")


def run() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)

        # Zero-admission preflight before 19:15 is allowed.
        preflight = _write(root, "preflight.json", _base("2026-08-20T19:02:00+09:00", []))
        out = validate(PREREG, [preflight])
        assert out["admitted_races"] == 0

        # Scientific admission before the locked window must fail.
        early = _write(
            root,
            "early.json",
            _base("2026-08-20T19:02:00+09:00", [_race("https://keirin.jp/pc/dfw/dataplaza/guest/raceprogram?KCD=44&KST=20260821")]),
        )
        _must_fail(early, "pre_window_admission")

        # Scientific admission after window start but before the quality amendment must fail.
        pre_quality = _write(
            root,
            "pre_quality.json",
            _base("2026-08-20T19:18:00+09:00", [_race("https://keirin.jp/pc/dfw/dataplaza/guest/raceprogram?KCD=44&KST=20260821")]),
        )
        _must_fail(pre_quality, "pre_quality_amendment_admission")

        # A third-party HTTPS URL must never become a scientific race source.
        third_party = _write(
            root,
            "third_party.json",
            _base("2026-08-21T19:00:00+09:00", [_race("https://example.com/race")]),
        )
        _must_fail(third_party, "third_party_https")

        # Schedule-only structure is now discovery-only and cannot consume a sample slot.
        schedule_only_race = _race(
            "https://www.ogakikeirin.com/midnight",
            riders=[],
        )
        schedule_only_race["source_document_type"] = "OFFICIAL_SCHEDULE_PAGE"
        schedule_only = _write(
            root,
            "schedule_only.json",
            _base("2026-08-21T19:00:00+09:00", [schedule_only_race]),
        )
        _must_fail(schedule_only, "schedule_only_not_scientific_sample")

        # Every rider needs class, score and at least one directly measured tactical field.
        no_tactical_riders = [
            {"rider_slot": i, "rider_class": "A1", "competition_score": 88.0}
            for i in range(1, 8)
        ]
        no_tactical = _write(
            root,
            "no_tactical.json",
            _base(
                "2026-08-21T19:00:00+09:00",
                [_race("https://keirin.jp/pc/dfw/dataplaza/guest/raceprogram?KCD=44&KST=20260821", riders=no_tactical_riders)],
            ),
        )
        _must_fail(no_tactical, "tactical_payload_required")

        # Raw identity storage is unnecessary for the realism comparison and must fail closed.
        identity_riders = _riders()
        identity_riders[0]["name"] = "TEST NAME"
        identity = _write(
            root,
            "identity.json",
            _base(
                "2026-08-21T19:00:00+09:00",
                [_race("https://keirin.jp/pc/dfw/dataplaza/guest/raceprogram?KCD=44&KST=20260821", riders=identity_riders)],
            ),
        )
        _must_fail(identity, "raw_identity_storage")

        # Post-start capture must fail even on central official URL.
        late = _write(
            root,
            "late.json",
            _base(
                "2026-08-21T21:00:00+09:00",
                [_race("https://keirin.jp/pc/dfw/dataplaza/guest/raceprogram?KCD=44&KST=20260821", "2026-08-21T20:50:00+09:00")],
            ),
        )
        _must_fail(late, "post_start_capture")

        # Prospective central-official full PRE admission inside the window is allowed.
        good_central = _write(
            root,
            "good_central.json",
            _base(
                "2026-08-21T19:00:00+09:00",
                [_race("https://keirin.jp/pc/dfw/dataplaza/guest/raceprogram?KCD=44&KST=20260821")],
            ),
        )
        out = validate(PREREG, [good_central])
        assert out["status"] == "PASS"
        assert out["admitted_races"] == 1
        assert out["admitted_venues"] == 1

        # A pre-allowlisted first-party venue racecard file is also permitted by the original
        # first-party-source prereg, but only with the same full rider-level quality contract.
        good_venue = _write(
            root,
            "good_venue.json",
            _base(
                "2026-08-21T19:00:00+09:00",
                [_race("https://www.ogakikeirin.com/files/official-racecard.pdf")],
            ),
        )
        out = validate(PREREG, [good_venue])
        assert out["status"] == "PASS"
        assert out["admitted_races"] == 1

    print("INDEPENDENT_OFFICIAL_PRE_SENSOR_VALIDATOR_SELFTEST_PASS")


if __name__ == "__main__":
    run()
