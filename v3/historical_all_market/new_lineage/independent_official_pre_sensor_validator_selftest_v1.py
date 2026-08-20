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


def _race(source_url: str, scheduled: str = "2026-08-21T20:50:00+09:00") -> dict:
    return {
        "race_date": "2026-08-21",
        "venue": "大垣",
        "race_number": 1,
        "scheduled_start": scheduled,
        "field_size": 7,
        "source_url": source_url,
        "source_class": "FIRST_PARTY_OFFICIAL",
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

        # A third-party HTTPS URL must never become a scientific race source.
        third_party = _write(
            root,
            "third_party.json",
            _base("2026-08-21T19:00:00+09:00", [_race("https://example.com/race")]),
        )
        _must_fail(third_party, "third_party_https")

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

        # Prospective central-official admission inside the window is allowed.
        good = _write(
            root,
            "good.json",
            _base(
                "2026-08-21T19:00:00+09:00",
                [_race("https://keirin.jp/pc/dfw/dataplaza/guest/raceprogram?KCD=44&KST=20260821")],
            ),
        )
        out = validate(PREREG, [good])
        assert out["status"] == "PASS"
        assert out["admitted_races"] == 1
        assert out["admitted_venues"] == 1

    print("INDEPENDENT_OFFICIAL_PRE_SENSOR_VALIDATOR_SELFTEST_PASS")


if __name__ == "__main__":
    run()
