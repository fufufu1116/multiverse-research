from reality_repeated_expected_line_v0 import (
    ExpectedLinePointInTime,
    ExpectedLineSeries,
    RepeatedExpectedLineError,
    validate_series_collection,
)


def snap(ts: str, groups: tuple[tuple[int, ...], ...]) -> ExpectedLinePointInTime:
    return ExpectedLinePointInTime(
        race_id="RACE_X",
        active_car_numbers=(1,2,3,4,5,6,7),
        groups=groups,
        capture_timestamp=ts,
        decision_timestamp="2026-09-01T18:00:00+09:00",
        source_url="https://example.invalid/pre",
        provider_name="PROVIDER",
        provenance_sha="abc123",
    )


s1 = snap("2026-09-01T16:00:00+09:00", ((1,2,3),(4,5),(6,7)))
s2 = snap("2026-09-01T16:15:00+09:00", ((6,7),(1,2,3),(4,5)))
s3 = snap("2026-09-01T16:30:00+09:00", ((1,2),(3,4,5),(6,7)))
series = ExpectedLineSeries("RACE_X", (s1,s2,s3))
assert s1.signature == s2.signature
assert series.unchanged_intervals() == 1
changes = series.changes()
assert len(changes) == 1
assert changes[0].later_capture_timestamp == "2026-09-01T16:30:00+09:00"
assert series.latest_available_by("2026-09-01T16:20:00+09:00") == s2
validate_series_collection((series,))

try:
    snap("2026-09-01T18:01:00+09:00", ((1,2,3),(4,5),(6,7)))
    raise AssertionError("post-cutoff capture should fail")
except RepeatedExpectedLineError:
    pass

try:
    snap("2026-09-01T16:00:00+09:00", ((1,2,3),(4,5)))
    raise AssertionError("incomplete partition should fail")
except RepeatedExpectedLineError:
    pass

try:
    ExpectedLineSeries("RACE_X", (s2,s1))
    raise AssertionError("out-of-order series should fail")
except RepeatedExpectedLineError:
    pass

print("PASS repeated expected-line foundation selftest")
