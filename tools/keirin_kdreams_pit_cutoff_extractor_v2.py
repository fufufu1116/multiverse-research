#!/usr/bin/env python3
"""Research-only KDreamS PIT cutoff extractor v2.

v1 failed closed on a live PRE raceprogram href because KDreamS appended the
navigation-only query key `l-id`. v2 preserves the positively observed href
exactly and allows only one non-empty `l-id` query parameter on the same exact
KDreamS raceprogram path. All other query keys, fragments, hosts, paths, and
identifier construction remain fail closed.

The parser and PRE-only guarantees are inherited from the pinned v1 extractor.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import subprocess
from urllib.parse import parse_qsl, urlparse

BASE = pathlib.Path("tools/keirin_kdreams_pit_cutoff_extractor_v1.py")
EXPECTED_BASE_GIT_BLOB = "ba9f2114647038139b54eae0843302c8781729da"
HOST = "keirin.kdreams.jp"


def validate_program_url_v2(url: str, slug: str) -> str:
    p = urlparse(url)
    if p.scheme != "https" or p.hostname != HOST or p.fragment:
        raise ValueError("FAIL_CLOSED_PROGRAM_URL")
    import re
    if not re.fullmatch(rf"/{re.escape(slug)}/raceprogram/\d+/?", p.path):
        raise ValueError("FAIL_CLOSED_PROGRAM_URL_PATH")
    pairs = parse_qsl(p.query, keep_blank_values=True)
    if pairs:
        if len(pairs) != 1 or pairs[0][0] != "l-id" or not pairs[0][1]:
            raise ValueError("FAIL_CLOSED_PROGRAM_QUERY")
        if len(pairs[0][1]) > 256:
            raise ValueError("FAIL_CLOSED_PROGRAM_QUERY_VALUE")
    return url


def base_module():
    got = subprocess.check_output(["git", "hash-object", str(BASE)], text=True).strip()
    if got != EXPECTED_BASE_GIT_BLOB:
        raise ValueError(f"FAIL_CLOSED_BASE_EXTRACTOR_BLOB_{got}")
    spec = importlib.util.spec_from_file_location("pit_cutoff_extractor_v1", BASE)
    if not spec or not spec.loader:
        raise ValueError("FAIL_CLOSED_BASE_IMPORT")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    # Patch only the program-URL policy. Every other v1 parser/binding guard stays pinned.
    m.validate_program_url = validate_program_url_v2
    return m, got


def extract(racecard_url: str, expected_venue: str, expected_date: str, timeout: int = 25):
    base, blob = base_module()
    out = base.extract(racecard_url, expected_venue, expected_date, timeout)
    out["record"] = "KEIRIN_KDREAMS_PIT_CUTOFF_EXTRACT_v2"
    out["base_extractor_file"] = str(BASE)
    out["base_extractor_git_blob"] = blob
    out["program_query_policy"] = "ALLOW_NONE_OR_SINGLE_NONEMPTY_L_ID_ONLY_ON_EXACT_POSITIVELY_OBSERVED_PROGRAM_HREF"
    out["positive_program_href_preserved_exactly"] = True
    return out


def selftest():
    base, blob = base_module()
    tests = {}

    clean = "https://keirin.kdreams.jp/hofu/raceprogram/6320260904/"
    observed = clean + "?l-id=l-pc-srci-srpi-raceinfo_kaisai_detail_nav_btn"
    tests["base_blob_pinned"] = blob == EXPECTED_BASE_GIT_BLOB
    tests["clean_program_url_allowed"] = validate_program_url_v2(clean, "hofu") == clean
    tests["observed_single_l_id_allowed"] = validate_program_url_v2(observed, "hofu") == observed

    rc = base.synthetic_racecard(program_hrefs=[
        "/hofu/raceprogram/6320260904/?l-id=l-pc-srci-srpi-raceinfo_kaisai_detail_nav_btn",
        "/hofu/raceprogram/6320260904/?l-id=l-pc-srci-srpi-raceinfo_kaisai_detail_nav_btn",
    ])
    soup = base.validate_racecard_binding(rc, "防府", "2026-09-04")
    got, occurrences = base.extract_positive_program_href(
        soup,
        "https://keirin.kdreams.jp/hofu/racecard/63202609040100/",
        "hofu",
    )
    tests["positive_observed_href_preserved_exactly"] = got == observed
    tests["duplicate_same_observed_href_deduped"] = occurrences == 2

    bad = {
        "other_query_rejected": clean + "?foo=bar",
        "multiple_query_keys_rejected": observed + "&foo=bar",
        "blank_l_id_rejected": clean + "?l-id=",
        "fragment_rejected": clean + "#x",
        "off_host_rejected": "https://example.com/hofu/raceprogram/6320260904/?l-id=x",
        "wrong_venue_path_rejected": "https://keirin.kdreams.jp/nara/raceprogram/6320260904/?l-id=x",
    }
    for name, url in bad.items():
        try:
            validate_program_url_v2(url, "hofu")
            tests[name] = False
        except ValueError:
            tests[name] = True

    schedule = base.parse_program_schedule(base.synthetic_program(), "防府", "2026-09-04")
    tests["deadline_semantics_inherited"] = schedule[0]["pit_cutoff_label"] == "締切時間"
    tests["start_semantics_distinct"] = schedule[0]["scheduled_start_label"] == "発走時間"
    tests["no_rider_values_emitted"] = "選手など混在情報" not in json.dumps(schedule, ensure_ascii=False)
    tests["no_forbidden_mixed_text_emitted"] = not any(
        x in json.dumps(schedule, ensure_ascii=False)
        for x in ["結果", "払戻", "オッズ", "予想", "コメント"]
    )

    return {
        "record": "KEIRIN_KDREAMS_PIT_CUTOFF_EXTRACTOR_SELFTEST_v2",
        "status": "PASS" if all(tests.values()) else "FAIL",
        "tests": tests,
        "network_access": False,
        "live_pre_validation": False,
        "live_pre_validation_reason": "Hofu Sep4 first-race PIT cutoff already passed before v2 creation; do not reconstruct PRE after cutoff.",
        "base_extractor_git_blob": blob,
        "result_accessed": False,
        "raceprogram_url_guessing": False,
        "race_id_guessing": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    p = sub.add_parser("extract")
    p.add_argument("--racecard-url", required=True)
    p.add_argument("--expected-venue", required=True)
    p.add_argument("--expected-date", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--timeout", type=int, default=25)
    a = ap.parse_args()

    if a.cmd == "selftest":
        x = selftest()
        print(json.dumps(x, ensure_ascii=False, sort_keys=True))
        return 0 if x["status"] == "PASS" else 2

    try:
        x = extract(a.racecard_url, a.expected_venue, a.expected_date, a.timeout)
        pathlib.Path(a.out).write_text(
            json.dumps(x, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "record": x["record"],
            "status": x["status"],
            "race_count": x["race_count"],
            "first_race_pit_cutoff_jst": x["first_race_pit_cutoff_jst"],
            "captured_before_first_race_pit_cutoff": x["captured_before_first_race_pit_cutoff"],
            "program_query_policy": x["program_query_policy"],
            "result_accessed": False,
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as e:
        x = {
            "record": "KEIRIN_KDREAMS_PIT_CUTOFF_EXTRACT_v2",
            "status": "FAIL_CLOSED_PIT_CUTOFF_NOT_CAPTURED",
            "fatal_error": f"{type(e).__name__}: {str(e)[:500]}",
            "base_extractor_git_blob": EXPECTED_BASE_GIT_BLOB,
            "program_query_policy": "ALLOW_NONE_OR_SINGLE_NONEMPTY_L_ID_ONLY_ON_EXACT_POSITIVELY_OBSERVED_PROGRAM_HREF",
            "raceprogram_url_guessed": False,
            "race_id_guessed": False,
            "detail_pages_opened": False,
            "raw_html_persisted": False,
            "raw_html_printed": False,
            "rider_values_persisted": False,
            "result_accessed": False,
            "payout_accessed": False,
            "odds_accessed": False,
            "forecast_accessed": False,
            "support_increment_authorized_now": 0,
            "model_fit_authorized": False,
            "result_join_authorized": False,
            "main_or_runtime_mutation": False,
        }
        pathlib.Path(a.out).write_text(
            json.dumps(x, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(x, ensure_ascii=False, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
