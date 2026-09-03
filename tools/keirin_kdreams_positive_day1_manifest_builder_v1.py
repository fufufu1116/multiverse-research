#!/usr/bin/env python3
"""Research-only positive-link Day1 manifest builder v1 for KDreamS.

The builder fetches exactly one caller-supplied KDreamS racecard day URL, keeps
raw HTML in memory only, and emits only event metadata plus racedetail hrefs
that are positively observed as anchor hrefs in that racecard DOM. It never
opens racedetail, RESULT, payout, odds, forecast, or other downstream pages and
never constructs a race ID arithmetically.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import date, datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

HOST = "keirin.kdreams.jp"
MAX_BYTES = 8 * 1024 * 1024
UA = "Mozilla/5.0 (compatible; MultiverseKeirinResearch/PositiveDay1ManifestBuilder1.0; PRE-only)"


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", unescape(s or "")).strip()


def norm(s: str) -> str:
    return unicodedata.normalize("NFKC", clean(s))


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def parse_cutoff(x: str) -> datetime:
    d = datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("FAIL_CLOSED_CUTOFF_TZ_REQUIRED")
    return d.astimezone(timezone.utc)


def validate_racecard_url(url: str) -> tuple[str, str]:
    p = urlparse(url)
    if p.scheme != "https" or p.hostname != HOST or p.query or p.fragment:
        raise ValueError("FAIL_CLOSED_RACECARD_URL")
    m = re.fullmatch(r"/([^/]+)/racecard/(\d+)/?", p.path)
    if not m:
        raise ValueError("FAIL_CLOSED_NOT_EXACT_RACECARD_DAY_URL")
    return m.group(1), m.group(2)


def validate_detail_url(url: str, venue_slug: str) -> str:
    p = urlparse(url)
    if p.scheme != "https" or p.hostname != HOST or p.query or p.fragment:
        raise ValueError("FAIL_CLOSED_DETAIL_URL")
    if not re.fullmatch(rf"/{re.escape(venue_slug)}/racedetail/\d+/?", p.path):
        raise ValueError("FAIL_CLOSED_DETAIL_URL_VENUE_OR_PATH")
    return url


def fetch_racecard(url: str, timeout: int = 25) -> bytes:
    validate_racecard_url(url)
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
    with urlopen(req, timeout=timeout) as r:
        final = r.geturl()
        validate_racecard_url(final)
        if final != url:
            raise ValueError("FAIL_CLOSED_RACECARD_REDIRECT")
        ctype = (r.headers.get("Content-Type") or "").lower()
        if "text/html" not in ctype and "application/xhtml" not in ctype:
            raise ValueError("FAIL_CLOSED_NON_HTML")
        data = r.read(MAX_BYTES + 1)
    if not 500 <= len(data) <= MAX_BYTES:
        raise ValueError("FAIL_CLOSED_RACECARD_SIZE")
    return data


def parse_date(text: str) -> str | None:
    t = norm(text)
    m = re.search(r"(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日", t)
    if not m:
        m = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", t)
    if not m:
        return None
    try:
        return date(*map(int, m.groups())).isoformat()
    except ValueError:
        return None


def parse_venue_from_title(title: str) -> str | None:
    t = clean(title)
    if "競輪" not in t:
        return None
    v = t.split("競輪", 1)[0].strip()
    return v or None


def day_category(text: str) -> str:
    t = norm(text)
    if "初日" in t or re.search(r"(^|\D)1日目($|\D)", t) or re.search(r"第1日($|\D)", t):
        return "INITIAL_DAY_EXPLICIT"
    if "最終日" in t:
        return "FINAL_DAY_EXPLICIT"
    m = re.search(r"([2-9])日目", t)
    return f"DAY_{m.group(1)}_EXPLICIT" if m else "NO_EXPLICIT_DAY_STATUS"


def active_day_categories(soup: BeautifulSoup) -> list[str]:
    cats: list[str] = []
    for e in soup.find_all(True):
        classes = " ".join(e.get("class", []))
        aria = clean(str(e.get("aria-current", "")))
        if not (
            re.search(r"(?:^|\s)(?:active|current|selected|on)(?:\s|$)", classes, re.I)
            or aria in {"page", "true"}
        ):
            continue
        c = day_category(e.get_text(" ", strip=True))
        if c != "NO_EXPLICIT_DAY_STATUS":
            cats.append(c)
    return sorted(set(cats))


def extract_positive_detail_urls(data: bytes, racecard_url: str, venue_slug: str) -> tuple[list[str], int, int]:
    soup = BeautifulSoup(data.decode("utf-8", errors="replace"), "html.parser")
    ordered: list[str] = []
    seen: set[str] = set()
    duplicate_count = 0
    suspicious_invalid: list[str] = []

    for a in soup.find_all("a", href=True):
        raw_href = str(a.get("href") or "").strip()
        if "racedetail" not in raw_href.lower():
            continue
        candidate = urljoin(racecard_url, raw_href)
        try:
            validate_detail_url(candidate, venue_slug)
        except Exception:
            suspicious_invalid.append(raw_href[:240])
            continue
        if candidate in seen:
            duplicate_count += 1
            continue
        seen.add(candidate)
        ordered.append(candidate)

    if suspicious_invalid:
        raise ValueError(f"FAIL_CLOSED_INVALID_RACEDETAIL_ANCHOR_{len(suspicious_invalid)}")
    return ordered, len(ordered) + duplicate_count, duplicate_count


def build_manifest_from_bytes(
    data: bytes,
    racecard_url: str,
    expected_venue: str,
    expected_date: str,
    circumference_m: float,
    pit_cutoff_utc: str,
    *,
    captured_utc: datetime | None = None,
) -> dict:
    venue_slug, _ = validate_racecard_url(racecard_url)
    cutoff = parse_cutoff(pit_cutoff_utc)
    captured = captured_utc or datetime.now(timezone.utc)
    if captured.tzinfo is None:
        raise ValueError("FAIL_CLOSED_CAPTURE_TZ_REQUIRED")
    captured = captured.astimezone(timezone.utc)
    if captured >= cutoff:
        raise ValueError("FAIL_CLOSED_CAPTURE_AT_OR_AFTER_PIT_CUTOFF")
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", expected_date):
        raise ValueError("FAIL_CLOSED_EXPECTED_DATE_FORMAT")
    try:
        circumference = float(circumference_m)
    except Exception as exc:
        raise ValueError("FAIL_CLOSED_CIRCUMFERENCE") from exc
    if circumference <= 0:
        raise ValueError("FAIL_CLOSED_CIRCUMFERENCE")

    soup = BeautifulSoup(data.decode("utf-8", errors="replace"), "html.parser")
    title = clean(soup.title.get_text(" ", strip=True)) if soup.title else ""
    observed_date = parse_date(title)
    observed_venue = parse_venue_from_title(title)
    if observed_date != expected_date:
        raise ValueError(f"FAIL_CLOSED_RACECARD_DATE_{observed_date}")
    if norm(observed_venue or "") != norm(expected_venue):
        raise ValueError(f"FAIL_CLOSED_RACECARD_VENUE_{observed_venue}")

    title_cat = day_category(title)
    active_cats = active_day_categories(soup)
    explicit = {c for c in [title_cat, *active_cats] if c != "NO_EXPLICIT_DAY_STATUS"}
    if explicit != {"INITIAL_DAY_EXPLICIT"}:
        raise ValueError(f"FAIL_CLOSED_DAY1_NOT_UNAMBIGUOUS_{sorted(explicit)}")

    detail_urls, matched_anchor_count, duplicate_count = extract_positive_detail_urls(data, racecard_url, venue_slug)
    if not 5 <= len(detail_urls) <= 12:
        raise ValueError(f"FAIL_CLOSED_DETAIL_URL_COUNT_{len(detail_urls)}")

    return {
        "record": "KEIRIN_KDREAMS_POSITIVE_DAY1_MANIFEST_v1",
        "status": "POSITIVE_DAY1_RACEDETAIL_HREF_MANIFEST_CAPTURED_PRE_ONLY",
        "generated_utc": captured.isoformat(),
        "source_racecard_url": racecard_url,
        "source_racecard_sha256": sha256_bytes(data),
        "event": {
            "race_date": expected_date,
            "venue": expected_venue,
            "circumference_m": circumference,
            "day": "Day1",
        },
        "observed": {
            "race_date": observed_date,
            "venue": observed_venue,
            "title_day_category": title_cat,
            "active_day_categories": active_cats,
        },
        "pit_cutoff_utc": cutoff.isoformat(),
        "captured_before_pit_cutoff": True,
        "day1_confirmed": True,
        "detail_urls": detail_urls,
        "observed_racedetail_anchor_count": matched_anchor_count,
        "unique_detail_url_count": len(detail_urls),
        "duplicate_detail_url_count": duplicate_count,
        "detail_pages_opened": False,
        "race_id_guessed": False,
        "racecard_day_id_arithmetic_used": False,
        "raw_html_persisted": False,
        "raw_html_printed": False,
        "result_accessed": False,
        "result_page_opened": False,
        "payout_accessed": False,
        "odds_accessed": False,
        "forecast_accessed": False,
        "human_comment_accessed": False,
        "support_increment_authorized_now": 0,
        "model_fit_authorized": False,
        "result_join_authorized": False,
        "main_or_runtime_mutation": False,
    }


def build_manifest(
    racecard_url: str,
    expected_venue: str,
    expected_date: str,
    circumference_m: float,
    pit_cutoff_utc: str,
    timeout: int = 25,
) -> dict:
    raw = fetch_racecard(racecard_url, timeout)
    return build_manifest_from_bytes(raw, racecard_url, expected_venue, expected_date, circumference_m, pit_cutoff_utc)


def synthetic_page(*, title: str = "川崎競輪 2026年09月10日", active: str = "初日", anchors: list[str] | None = None) -> bytes:
    anchors = anchors or [
        "/kawasaki/racedetail/3420260910010001/",
        "https://keirin.kdreams.jp/kawasaki/racedetail/3420260910010002/",
        "/kawasaki/racedetail/3420260910010003/",
        "/kawasaki/racedetail/3420260910010004/",
        "/kawasaki/racedetail/3420260910010005/",
        "/kawasaki/racedetail/3420260910010001/",
    ]
    body = "".join(f"<a href='{h}'>race</a>" for h in anchors)
    return (
        f"<html><head><title>{title}</title></head><body>"
        f"<div class='day active'>{active}</div>{body}"
        "<div>結果 払戻 オッズ 予想 コメント 並び予想</div>"
        "</body></html>"
    ).encode("utf-8")


def selftest() -> dict:
    now = datetime(2026, 9, 9, 0, 0, tzinfo=timezone.utc)
    cutoff = "2026-09-10T00:00:00+00:00"
    base_url = "https://keirin.kdreams.jp/kawasaki/racecard/34202609100100/"
    manifest = build_manifest_from_bytes(
        synthetic_page(), base_url, "川崎", "2026-09-10", 400, cutoff, captured_utc=now
    )
    failures: dict[str, bool] = {}

    bad_cases = {
        "off_host_rejected": [
            "https://evil.example/kawasaki/racedetail/123/",
            "/kawasaki/racedetail/3420260910010002/",
            "/kawasaki/racedetail/3420260910010003/",
            "/kawasaki/racedetail/3420260910010004/",
            "/kawasaki/racedetail/3420260910010005/",
        ],
        "query_rejected": [
            "/kawasaki/racedetail/123/?pageType=result",
            "/kawasaki/racedetail/3420260910010002/",
            "/kawasaki/racedetail/3420260910010003/",
            "/kawasaki/racedetail/3420260910010004/",
            "/kawasaki/racedetail/3420260910010005/",
        ],
        "wrong_venue_path_rejected": [
            "/nara/racedetail/123/",
            "/kawasaki/racedetail/3420260910010002/",
            "/kawasaki/racedetail/3420260910010003/",
            "/kawasaki/racedetail/3420260910010004/",
            "/kawasaki/racedetail/3420260910010005/",
        ],
    }
    for key, anchors in bad_cases.items():
        try:
            build_manifest_from_bytes(
                synthetic_page(anchors=anchors), base_url, "川崎", "2026-09-10", 400, cutoff, captured_utc=now
            )
            failures[key] = False
        except ValueError:
            failures[key] = True

    try:
        build_manifest_from_bytes(
            synthetic_page(title="川崎競輪 2026年09月11日"), base_url, "川崎", "2026-09-10", 400, cutoff, captured_utc=now
        )
        failures["wrong_date_fail_closed"] = False
    except ValueError:
        failures["wrong_date_fail_closed"] = True

    try:
        build_manifest_from_bytes(
            synthetic_page(title="奈良競輪 2026年09月10日"), base_url, "川崎", "2026-09-10", 400, cutoff, captured_utc=now
        )
        failures["wrong_venue_fail_closed"] = False
    except ValueError:
        failures["wrong_venue_fail_closed"] = True

    try:
        build_manifest_from_bytes(
            synthetic_page(active="2日目"), base_url, "川崎", "2026-09-10", 400, cutoff, captured_utc=now
        )
        failures["non_day1_fail_closed"] = False
    except ValueError:
        failures["non_day1_fail_closed"] = True

    serialized = json.dumps(manifest, ensure_ascii=False)
    tests = {
        "five_unique_exact_links": manifest["unique_detail_url_count"] == 5,
        "relative_href_resolved": manifest["detail_urls"][0].startswith("https://keirin.kdreams.jp/kawasaki/racedetail/"),
        "document_order_preserved": manifest["detail_urls"][0].endswith("0001/"),
        "duplicate_deduplicated": manifest["duplicate_detail_url_count"] == 1,
        "day1_explicit_required": manifest["day1_confirmed"] is True,
        "no_detail_page_opened": manifest["detail_pages_opened"] is False,
        "no_race_id_guessing": manifest["race_id_guessed"] is False,
        "no_forbidden_mixed_text_persisted": not any(x in serialized for x in ["結果", "払戻", "オッズ", "予想", "コメント", "並び予想"]),
        **failures,
    }
    return {
        "record": "KEIRIN_KDREAMS_POSITIVE_DAY1_MANIFEST_BUILDER_SELFTEST_v1",
        "status": "PASS" if all(tests.values()) else "FAIL",
        "tests": tests,
        "network_access": False,
        "race_id_guessing": False,
        "result_accessed": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    p = sub.add_parser("build")
    p.add_argument("--racecard-url", required=True)
    p.add_argument("--expected-venue", required=True)
    p.add_argument("--expected-date", required=True)
    p.add_argument("--circumference-m", required=True, type=float)
    p.add_argument("--pit-cutoff-utc", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--timeout", type=int, default=25)
    args = ap.parse_args()

    if args.cmd == "selftest":
        out = selftest()
        print(json.dumps(out, ensure_ascii=False, sort_keys=True))
        return 0 if out["status"] == "PASS" else 2

    try:
        out = build_manifest(
            args.racecard_url,
            args.expected_venue,
            args.expected_date,
            args.circumference_m,
            args.pit_cutoff_utc,
            args.timeout,
        )
        Path(args.out).write_text(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "record": out["record"],
            "status": out["status"],
            "unique_detail_url_count": out["unique_detail_url_count"],
            "day1_confirmed": out["day1_confirmed"],
            "captured_before_pit_cutoff": out["captured_before_pit_cutoff"],
            "race_id_guessed": out["race_id_guessed"],
            "result_accessed": out["result_accessed"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:
        fail = {
            "record": "KEIRIN_KDREAMS_POSITIVE_DAY1_MANIFEST_v1",
            "status": "FAIL_CLOSED_DAY1_MANIFEST_NOT_CAPTURED",
            "fatal_error": f"{type(exc).__name__}: {str(exc)[:500]}",
            "detail_pages_opened": False,
            "race_id_guessed": False,
            "racecard_day_id_arithmetic_used": False,
            "raw_html_persisted": False,
            "raw_html_printed": False,
            "result_accessed": False,
            "result_page_opened": False,
            "payout_accessed": False,
            "odds_accessed": False,
            "forecast_accessed": False,
            "support_increment_authorized_now": 0,
            "model_fit_authorized": False,
            "result_join_authorized": False,
            "main_or_runtime_mutation": False,
        }
        Path(args.out).write_text(json.dumps(fail, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(fail, ensure_ascii=False, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
