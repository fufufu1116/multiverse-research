#!/usr/bin/env python3
"""Research-only KDreamS PIT cutoff extractor v1.

Starting from an exact positively-observed Day1 racecard URL, this tool follows
only a raceprogram href positively observed in that racecard DOM. It emits only
race numbers, KDreamS `締切時間` (PIT cutoff) and `発走時間` plus source hashes.
Raw mixed HTML stays in memory. No rider values, RESULT, payout, odds, forecast,
or guessed meeting/race identifiers are emitted or used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

HOST = "keirin.kdreams.jp"
JST = ZoneInfo("Asia/Tokyo")
MAX_BYTES = 8 * 1024 * 1024
UA = "MultiverseKeirinResearch/PITCutoffExtractor1.0 PRE-only"


def clean(x: object) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(x))).strip()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def parse_date_text(text: str) -> str | None:
    t = clean(text)
    m = re.search(r"(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日", t)
    if not m:
        return None
    try:
        return date(*map(int, m.groups())).isoformat()
    except ValueError:
        return None


def parse_venue_title(title: str) -> str | None:
    t = clean(title)
    if "競輪" not in t:
        return None
    v = t.split("競輪", 1)[0].strip()
    return v or None


def validate_racecard_url(url: str) -> tuple[str, str]:
    p = urlparse(url)
    if p.scheme != "https" or p.hostname != HOST or p.query or p.fragment:
        raise ValueError("FAIL_CLOSED_RACECARD_URL")
    m = re.fullmatch(r"/([^/]+)/racecard/(\d+)/?", p.path)
    if not m:
        raise ValueError("FAIL_CLOSED_NOT_EXACT_RACECARD_DAY_URL")
    return m.group(1), m.group(2)


def validate_program_url(url: str, slug: str) -> str:
    p = urlparse(url)
    if p.scheme != "https" or p.hostname != HOST or p.query or p.fragment:
        raise ValueError("FAIL_CLOSED_PROGRAM_URL")
    if not re.fullmatch(rf"/{re.escape(slug)}/raceprogram/\d+/?", p.path):
        raise ValueError("FAIL_CLOSED_PROGRAM_URL_PATH")
    return url


def fetch_exact(url: str, validator, *validator_args, timeout: int = 25) -> bytes:
    validator(url, *validator_args)
    r = requests.get(url, timeout=timeout, allow_redirects=False, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml", "Cache-Control": "no-cache"})
    if 300 <= r.status_code < 400:
        raise ValueError(f"FAIL_CLOSED_REDIRECT_{r.status_code}")
    if r.status_code != 200:
        raise ValueError(f"FAIL_CLOSED_HTTP_{r.status_code}")
    if not 500 <= len(r.content) <= MAX_BYTES:
        raise ValueError("FAIL_CLOSED_RESPONSE_SIZE")
    if "html" not in (r.headers.get("Content-Type") or "").lower():
        raise ValueError("FAIL_CLOSED_CONTENT_TYPE")
    return r.content


def active_day_categories(soup: BeautifulSoup) -> list[str]:
    out = []
    for e in soup.find_all(True):
        classes = " ".join(e.get("class", []))
        aria = clean(e.get("aria-current", ""))
        if not (re.search(r"(?:^|\s)(?:active|current|selected|on)(?:\s|$)", classes, re.I) or aria in {"page", "true"}):
            continue
        t = clean(e.get_text(" ", strip=True))
        if "初日" in t or re.search(r"(^|\D)1日目($|\D)", t) or re.search(r"第1日($|\D)", t):
            out.append("INITIAL_DAY_EXPLICIT")
        elif "最終日" in t:
            out.append("FINAL_DAY_EXPLICIT")
        else:
            m = re.search(r"([2-9])日目", t)
            if m:
                out.append(f"DAY_{m.group(1)}_EXPLICIT")
    return sorted(set(out))


def validate_racecard_binding(data: bytes, expected_venue: str, expected_date: str) -> BeautifulSoup:
    soup = BeautifulSoup(data.decode("utf-8", "replace"), "html.parser")
    title = clean(soup.title.get_text(" ", strip=True)) if soup.title else ""
    if parse_date_text(title) != expected_date:
        raise ValueError("FAIL_CLOSED_RACECARD_DATE")
    if clean(parse_venue_title(title) or "") != clean(expected_venue):
        raise ValueError("FAIL_CLOSED_RACECARD_VENUE")
    cats = active_day_categories(soup)
    if cats != ["INITIAL_DAY_EXPLICIT"]:
        raise ValueError(f"FAIL_CLOSED_RACECARD_DAY1_{cats}")
    return soup


def extract_positive_program_href(soup: BeautifulSoup, racecard_url: str, slug: str) -> tuple[str, int]:
    urls: list[str] = []
    raw_matches = 0
    for a in soup.find_all("a", href=True):
        raw = str(a.get("href") or "").strip()
        if "raceprogram" not in raw.lower():
            continue
        raw_matches += 1
        u = urljoin(racecard_url, raw)
        validate_program_url(u, slug)
        if u not in urls:
            urls.append(u)
    if len(urls) != 1:
        raise ValueError(f"FAIL_CLOSED_UNIQUE_PROGRAM_HREF_{len(urls)}")
    return urls[0], raw_matches


def parse_time_value(x: str) -> str:
    t = clean(x)
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", t):
        raise ValueError(f"FAIL_CLOSED_TIME_FORMAT_{t}")
    return t


def jst_dt(event_date: str, hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    d = date.fromisoformat(event_date)
    return datetime(d.year, d.month, d.day, h, m, tzinfo=JST)


def parse_program_schedule(data: bytes, expected_venue: str, expected_date: str) -> list[dict]:
    soup = BeautifulSoup(data.decode("utf-8", "replace"), "html.parser")
    title = clean(soup.title.get_text(" ", strip=True)) if soup.title else ""
    if parse_date_text(title) != expected_date:
        raise ValueError("FAIL_CLOSED_PROGRAM_DATE")
    if clean(parse_venue_title(title) or "") != clean(expected_venue):
        raise ValueError("FAIL_CLOSED_PROGRAM_VENUE")

    rows = []
    for tr in soup.find_all("tr"):
        race_markers = []
        for th in tr.find_all("th"):
            t = clean(th.get_text(" ", strip=True))
            m = re.fullmatch(r"(\d{1,2})R", t)
            if m:
                race_markers.append(int(m.group(1)))
        if not race_markers:
            continue
        if len(set(race_markers)) != 1:
            raise ValueError("FAIL_CLOSED_RACE_MARKER_AMBIGUOUS")
        race_no = race_markers[0]
        pre_cells = tr.select("td.pre")
        if len(pre_cells) != 1:
            raise ValueError(f"FAIL_CLOSED_PRE_CELL_{race_no}_{len(pre_cells)}")
        deadline = []
        start = []
        for dl in pre_cells[0].find_all("dl"):
            dts = [clean(x.get_text(" ", strip=True)) for x in dl.find_all("dt")]
            dds = [clean(x.get_text(" ", strip=True)) for x in dl.find_all("dd")]
            for label in dts:
                if label == "締切時間":
                    deadline.extend(parse_time_value(x) for x in dds if re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", clean(x)))
                elif label == "発走時間":
                    start.extend(parse_time_value(x) for x in dds if re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", clean(x)))
        if len(deadline) != 1 or len(start) != 1:
            raise ValueError(f"FAIL_CLOSED_TIMING_CARDINALITY_{race_no}_{len(deadline)}_{len(start)}")
        deadline_dt = jst_dt(expected_date, deadline[0])
        start_dt = jst_dt(expected_date, start[0])
        if not deadline_dt < start_dt:
            raise ValueError(f"FAIL_CLOSED_DEADLINE_NOT_BEFORE_START_{race_no}")
        rows.append({
            "race_no": race_no,
            "pit_cutoff_label": "締切時間",
            "pit_cutoff_hhmm_jst": deadline[0],
            "pit_cutoff_jst": deadline_dt.isoformat(),
            "pit_cutoff_utc": deadline_dt.astimezone(timezone.utc).isoformat(),
            "scheduled_start_label": "発走時間",
            "scheduled_start_hhmm_jst": start[0],
            "scheduled_start_jst": start_dt.isoformat(),
            "scheduled_start_utc": start_dt.astimezone(timezone.utc).isoformat(),
        })
    rows.sort(key=lambda x: x["race_no"])
    if not 5 <= len(rows) <= 12:
        raise ValueError(f"FAIL_CLOSED_RACE_COUNT_{len(rows)}")
    if [x["race_no"] for x in rows] != list(range(1, len(rows) + 1)):
        raise ValueError("FAIL_CLOSED_RACE_NUMBER_CONTINUITY")
    return rows


def extract(racecard_url: str, expected_venue: str, expected_date: str, timeout: int = 25, captured_utc: datetime | None = None) -> dict:
    slug, _ = validate_racecard_url(racecard_url)
    racecard_raw = fetch_exact(racecard_url, validate_racecard_url, timeout=timeout)
    soup = validate_racecard_binding(racecard_raw, expected_venue, expected_date)
    program_url, program_anchor_count = extract_positive_program_href(soup, racecard_url, slug)
    program_raw = fetch_exact(program_url, validate_program_url, slug, timeout=timeout)
    schedule = parse_program_schedule(program_raw, expected_venue, expected_date)
    captured = (captured_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    first_cutoff = datetime.fromisoformat(schedule[0]["pit_cutoff_utc"])
    if captured >= first_cutoff:
        raise ValueError("FAIL_CLOSED_CAPTURE_AT_OR_AFTER_FIRST_RACE_PIT_CUTOFF")
    return {
        "record": "KEIRIN_KDREAMS_PIT_CUTOFF_EXTRACT_v1",
        "status": "POSITIVE_RACECARD_TO_RACEPROGRAM_PIT_CUTOFF_CAPTURED_PRE_ONLY",
        "generated_utc": captured.isoformat(),
        "event": {"race_date": expected_date, "venue": expected_venue, "day": "Day1"},
        "source_racecard_url": racecard_url,
        "source_racecard_sha256": sha256_bytes(racecard_raw),
        "program_href_positively_observed_on_racecard": True,
        "program_anchor_occurrence_count": program_anchor_count,
        "source_program_url": program_url,
        "source_program_sha256": sha256_bytes(program_raw),
        "pit_cutoff_semantics": "KDreamS 締切時間; distinct from later 発走時間",
        "first_race_pit_cutoff_jst": schedule[0]["pit_cutoff_jst"],
        "first_race_pit_cutoff_utc": schedule[0]["pit_cutoff_utc"],
        "captured_before_first_race_pit_cutoff": True,
        "races": schedule,
        "race_count": len(schedule),
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


def synthetic_racecard(program_hrefs: list[str] | None = None, active: str = "初日", title: str = "防府競輪 2026年09月04日") -> bytes:
    hrefs = program_hrefs or ["/hofu/raceprogram/6320260904/", "/hofu/raceprogram/6320260904/"]
    anchors = "".join(f"<a href='{h}'>program</a>" for h in hrefs)
    return f"<html><head><title>{title}</title></head><body><div class='active'>{active}</div>{anchors}</body></html>".encode()


def synthetic_program(deadline_label: str = "締切時間", title: str = "防府競輪 2026年09月04日") -> bytes:
    times = [("08:35","08:40"),("08:55","09:00"),("09:15","09:20"),("09:35","09:40"),("09:55","10:00")]
    rows=[]
    for i,(d,s) in enumerate(times,1):
        rows.append(f"<tr><th>{i}R</th><td class='pre'><dl><dt>{deadline_label}</dt><dd>{d}</dd></dl><dl><dt>発走時間</dt><dd>{s}</dd></dl></td><td>選手など混在情報</td></tr>")
    return (f"<html><head><title>{title}</title></head><body><table>{''.join(rows)}</table><div>結果 払戻 オッズ 予想 コメント</div></body></html>").encode()


def selftest() -> dict:
    rc = synthetic_racecard()
    soup = validate_racecard_binding(rc, "防府", "2026-09-04")
    program_url, occurrences = extract_positive_program_href(soup, "https://keirin.kdreams.jp/hofu/racecard/63202609040100/", "hofu")
    schedule = parse_program_schedule(synthetic_program(), "防府", "2026-09-04")
    tests = {
        "positive_program_href": program_url == "https://keirin.kdreams.jp/hofu/raceprogram/6320260904/",
        "duplicate_same_program_href_deduped": occurrences == 2,
        "deadline_label_used": schedule[0]["pit_cutoff_label"] == "締切時間" and schedule[0]["pit_cutoff_hhmm_jst"] == "08:35",
        "start_kept_distinct": schedule[0]["scheduled_start_label"] == "発走時間" and schedule[0]["scheduled_start_hhmm_jst"] == "08:40",
        "utc_conversion": schedule[0]["pit_cutoff_utc"] == "2026-09-03T23:35:00+00:00",
        "five_races": len(schedule) == 5,
        "no_rider_values_emitted": "選手など混在情報" not in json.dumps(schedule, ensure_ascii=False),
        "no_forbidden_mixed_text_emitted": not any(x in json.dumps(schedule,ensure_ascii=False) for x in ["結果","払戻","オッズ","予想","コメント"]),
    }
    fail_cases = {}
    try:
        soup2 = validate_racecard_binding(synthetic_racecard(["/hofu/raceprogram/1/","/hofu/raceprogram/2/"]), "防府", "2026-09-04")
        extract_positive_program_href(soup2, "https://keirin.kdreams.jp/hofu/racecard/63202609040100/", "hofu")
        fail_cases["multiple_unique_programs_fail_closed"] = False
    except ValueError:
        fail_cases["multiple_unique_programs_fail_closed"] = True
    try:
        validate_racecard_binding(synthetic_racecard(active="2日目"), "防府", "2026-09-04")
        fail_cases["non_day1_fail_closed"] = False
    except ValueError:
        fail_cases["non_day1_fail_closed"] = True
    try:
        parse_program_schedule(synthetic_program(deadline_label="受付時間"), "防府", "2026-09-04")
        fail_cases["wrong_deadline_label_fail_closed"] = False
    except ValueError:
        fail_cases["wrong_deadline_label_fail_closed"] = True
    tests.update(fail_cases)
    return {"record":"KEIRIN_KDREAMS_PIT_CUTOFF_EXTRACTOR_SELFTEST_v1","status":"PASS" if all(tests.values()) else "FAIL","tests":tests,"network_access":False,"result_accessed":False,"raceprogram_url_guessing":False,"race_id_guessing":False}


def main() -> int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True); sub.add_parser("selftest")
    p=sub.add_parser("extract"); p.add_argument("--racecard-url",required=True); p.add_argument("--expected-venue",required=True); p.add_argument("--expected-date",required=True); p.add_argument("--out",required=True); p.add_argument("--timeout",type=int,default=25)
    a=ap.parse_args()
    if a.cmd=="selftest":
        x=selftest(); print(json.dumps(x,ensure_ascii=False,sort_keys=True)); return 0 if x["status"]=="PASS" else 2
    try:
        x=extract(a.racecard_url,a.expected_venue,a.expected_date,a.timeout)
        Path(a.out).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"record":x["record"],"status":x["status"],"race_count":x["race_count"],"first_race_pit_cutoff_jst":x["first_race_pit_cutoff_jst"],"captured_before_first_race_pit_cutoff":True,"result_accessed":False},ensure_ascii=False,sort_keys=True)); return 0
    except Exception as e:
        x={"record":"KEIRIN_KDREAMS_PIT_CUTOFF_EXTRACT_v1","status":"FAIL_CLOSED_PIT_CUTOFF_NOT_CAPTURED","fatal_error":f"{type(e).__name__}: {str(e)[:500]}","raceprogram_url_guessed":False,"race_id_guessed":False,"detail_pages_opened":False,"raw_html_persisted":False,"raw_html_printed":False,"rider_values_persisted":False,"result_accessed":False,"payout_accessed":False,"odds_accessed":False,"forecast_accessed":False,"support_increment_authorized_now":0,"model_fit_authorized":False,"result_join_authorized":False,"main_or_runtime_mutation":False}
        Path(a.out).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8"); print(json.dumps(x,ensure_ascii=False,sort_keys=True)); return 3

if __name__ == "__main__":
    raise SystemExit(main())
