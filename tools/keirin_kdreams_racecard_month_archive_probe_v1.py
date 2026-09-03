#!/usr/bin/env python3
"""Research-only KDreams month archive navigation probe.

Uses only the live-observed racecard index form contract:
  POST same /<venue>/racecard/ form, selects yy/mm, hidden searchDate.
The target year/month values must exist as actual options. No query parameter,
racecard ID, race-detail ID, or date URL is constructed by arithmetic.

Raw mixed HTML remains process-memory only. Output is restricted to request
structure hashes, exact positively observed racecard day hrefs, safe title/date/
venue/day-status metadata, and clean-window Day1 eligibility. No result, payout,
odds, forecast, comment, narabiyoso, rider data, or raw page content is emitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

HOST = "keirin.kdreams.jp"
MAX_BYTES = 8 * 1024 * 1024
UA = "Mozilla/5.0 (compatible; MultiverseKeirinResearch/MonthArchiveProbe1.0; PRE-only)"
VENUES = ("hofu", "toyama", "nara")
TARGET_YEAR = "2026"
TARGET_MONTHS = ("08", "09")
CLEAN_START = date(2026, 8, 27)
CLEAN_END = date(2026, 9, 2)
TIMEOUT = 25


class FailClosed(RuntimeError):
    pass


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def clean(s: object) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def norm(s: object) -> str:
    return unicodedata.normalize("NFKC", clean(s))


def validate_index_url(url: str, venue: str) -> str:
    p = urlparse(url)
    if p.scheme != "https" or p.hostname != HOST or p.fragment or p.query:
        raise FailClosed("FAIL_CLOSED_INDEX_ORIGIN_OR_QUERY")
    if p.path.rstrip("/") != f"/{venue}/racecard":
        raise FailClosed(f"FAIL_CLOSED_INDEX_PATH_{p.path}")
    return url


def validate_day_url(url: str, venue: str) -> str:
    p = urlparse(url)
    if p.scheme != "https" or p.hostname != HOST or p.fragment or p.query:
        raise FailClosed("FAIL_CLOSED_DAY_ORIGIN_OR_QUERY")
    if not re.fullmatch(rf"/{re.escape(venue)}/racecard/\d+/?", p.path):
        raise FailClosed(f"FAIL_CLOSED_DAY_PATH_{p.path}")
    return url


def checked_response(r: requests.Response, kind: str, venue: str) -> bytes:
    if 300 <= r.status_code < 400:
        raise FailClosed(f"FAIL_CLOSED_UNFOLLOWED_REDIRECT_{kind}_{r.status_code}")
    if r.status_code in (403, 429):
        raise FailClosed(f"FAIL_CLOSED_RATE_HALT_{r.status_code}")
    if r.status_code != 200:
        raise FailClosed(f"FAIL_CLOSED_HTTP_{kind}_{r.status_code}")
    if kind == "index":
        validate_index_url(r.url, venue)
    else:
        validate_day_url(r.url, venue)
    ct = (r.headers.get("Content-Type") or "").lower()
    if "text/html" not in ct and "application/xhtml" not in ct:
        raise FailClosed(f"FAIL_CLOSED_NON_HTML_{kind}")
    if not 500 <= len(r.content) <= MAX_BYTES:
        raise FailClosed(f"FAIL_CLOSED_SIZE_{kind}_{len(r.content)}")
    return r.content


def get(session: requests.Session, url: str, venue: str, kind: str) -> tuple[bytes, str]:
    if kind == "index":
        validate_index_url(url, venue)
    else:
        validate_day_url(url, venue)
    r = session.get(url, timeout=TIMEOUT, allow_redirects=False, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
    return checked_response(r, kind, venue), r.url


def find_exact_archive_form(raw: bytes, base: str, venue: str):
    soup = BeautifulSoup(raw.decode("utf-8", errors="replace"), "html.parser")
    forms = [f for f in soup.find_all("form") if clean(f.get("name")) == "searchDate" and clean(f.get("id")) == "searchDate"]
    if len(forms) != 1:
        raise FailClosed(f"FAIL_CLOSED_SEARCHDATE_FORM_CARDINALITY_{len(forms)}")
    form = forms[0]
    method = (clean(form.get("method")) or "get").lower()
    if method != "post":
        raise FailClosed(f"FAIL_CLOSED_SEARCHDATE_METHOD_{method}")
    action = urljoin(base, clean(form.get("action")) or base)
    validate_index_url(action, venue)

    selects = form.find_all("select", attrs={"name": True})
    by_name: dict[str, object] = {}
    for s in selects:
        n = clean(s.get("name"))
        if n in by_name:
            raise FailClosed(f"FAIL_CLOSED_DUPLICATE_SELECT_{n}")
        by_name[n] = s
    if set(by_name) != {"yy", "mm"}:
        raise FailClosed(f"FAIL_CLOSED_SELECT_NAMES_{sorted(by_name)}")

    hidden = form.find_all("input", attrs={"type": re.compile(r"^hidden$", re.I), "name": True})
    if len(hidden) != 1 or clean(hidden[0].get("name")) != "searchDate":
        raise FailClosed("FAIL_CLOSED_HIDDEN_SEARCHDATE_CONTRACT")

    # Contract is deliberately strict: no other named controls may influence submission.
    named = form.find_all(["input", "select", "button"], attrs={"name": True})
    names = [clean(x.get("name")) for x in named]
    if sorted(names) != ["mm", "searchDate", "yy"]:
        raise FailClosed(f"FAIL_CLOSED_FORM_CONTROL_NAMES_{sorted(names)}")
    return soup, form, by_name, hidden[0], action


def option_value(select, wanted: str, kind: str) -> str:
    hits = []
    for o in select.find_all("option"):
        value = clean(o.get("value"))
        text = norm(o.get_text(" ", strip=True))
        if kind == "year":
            ok = value == wanted or text == wanted or text == wanted + "年"
        else:
            w = str(int(wanted))
            ok = value == wanted or value == w or text in {wanted, w, wanted + "月", w + "月"}
        if ok and value != "":
            hits.append(value)
    hits = sorted(set(hits))
    if len(hits) != 1:
        raise FailClosed(f"FAIL_CLOSED_OPTION_{kind}_{wanted}_CARDINALITY_{len(hits)}")
    return hits[0]


def observed_payload(form, by_name, hidden, target_month: str) -> tuple[dict[str, str], dict]:
    yy = option_value(by_name["yy"], TARGET_YEAR, "year")
    mm = option_value(by_name["mm"], target_month, "month")
    hidden_value = clean(hidden.get("value"))
    if hidden_value == "":
        raise FailClosed("FAIL_CLOSED_EMPTY_HIDDEN_SEARCHDATE")
    payload = {"yy": yy, "mm": mm, "searchDate": hidden_value}
    payload_canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    safe = {
        "field_names": sorted(payload),
        "target_year_option_value": yy,
        "target_month_option_value": mm,
        "hidden_searchDate_value_length": len(hidden_value),
        "hidden_searchDate_value_sha256": sha_text(hidden_value),
        "full_payload_sha256": sha_text(payload_canonical),
    }
    return payload, safe


def post_archive(session: requests.Session, action: str, venue: str, payload: dict[str, str]) -> tuple[bytes, str, list[dict]]:
    r = session.post(action, data=payload, timeout=TIMEOUT, allow_redirects=False, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml", "Referer": action})
    history = []
    # Browser-standard redirect following only when server explicitly supplies a same-index Location.
    for _ in range(3):
        if r.status_code not in (301, 302, 303, 307, 308):
            break
        loc = r.headers.get("Location")
        if not loc:
            raise FailClosed(f"FAIL_CLOSED_REDIRECT_NO_LOCATION_{r.status_code}")
        nxt = urljoin(r.url, loc)
        validate_index_url(nxt, venue)
        history.append({"status_code": r.status_code, "location_url": nxt})
        if r.status_code in (307, 308):
            r = session.post(nxt, data=payload, timeout=TIMEOUT, allow_redirects=False, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml", "Referer": action})
        else:
            r = session.get(nxt, timeout=TIMEOUT, allow_redirects=False, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml", "Referer": action})
    raw = checked_response(r, "index", venue)
    return raw, r.url, history


def exact_day_links(raw: bytes, base: str, venue: str) -> list[str]:
    soup = BeautifulSoup(raw.decode("utf-8", errors="replace"), "html.parser")
    out = set()
    for a in soup.find_all("a", href=True):
        u = urljoin(base, a.get("href"))
        try:
            validate_day_url(u, venue)
        except FailClosed:
            continue
        out.add(u)
    return sorted(out)


def parse_date_from_title(title: str) -> str | None:
    m = re.search(r"(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日", title)
    if not m:
        m = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", title)
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
    x = t.split("競輪", 1)[0].strip()
    return x or None


def day_category(text: str) -> str:
    t = norm(text)
    if "初日" in t or re.search(r"(^|\D)1日目($|\D)", t) or re.search(r"第1日($|\D)", t):
        return "INITIAL_DAY_EXPLICIT"
    if "最終日" in t:
        return "FINAL_DAY_EXPLICIT"
    m = re.search(r"([2-9])日目", t)
    return f"DAY_{m.group(1)}_EXPLICIT" if m else "NO_EXPLICIT_DAY_STATUS"


def active_day_category(soup: BeautifulSoup) -> str:
    cats = []
    for e in soup.find_all(True):
        classes = " ".join(e.get("class", []))
        aria = clean(e.get("aria-current"))
        if not (re.search(r"(?:^|\s)(?:active|current|selected|on)(?:\s|$)", classes, re.I) or aria in {"page", "true"}):
            continue
        txt = clean(e.get_text(" ", strip=True))
        if len(txt) > 80:
            continue
        cat = day_category(txt)
        if cat != "NO_EXPLICIT_DAY_STATUS":
            cats.append(cat)
    uniq = sorted(set(cats))
    if len(uniq) == 1:
        return uniq[0]
    if len(uniq) > 1:
        return "AMBIGUOUS_ACTIVE_DAY_STATUS"
    return "NO_EXPLICIT_DAY_STATUS"


def day_metadata(session: requests.Session, url: str, venue: str) -> dict:
    raw, final = get(session, url, venue, "day")
    soup = BeautifulSoup(raw.decode("utf-8", errors="replace"), "html.parser")
    title = clean(soup.title.get_text(" ", strip=True)) if soup.title else ""
    race_date = parse_date_from_title(title)
    venue_name = parse_venue_from_title(title)
    active = active_day_category(soup)
    title_cat = day_category(title)
    dt = date.fromisoformat(race_date) if race_date else None
    clean_window = bool(dt and CLEAN_START <= dt <= CLEAN_END)
    initial = active == "INITIAL_DAY_EXPLICIT" or (active == "NO_EXPLICIT_DAY_STATUS" and title_cat == "INITIAL_DAY_EXPLICIT")
    return {
        "day_url": final,
        "race_date": race_date,
        "venue_from_title": venue_name,
        "active_day_category": active,
        "title_day_category": title_cat,
        "source_sha256": sha_bytes(raw),
        "within_clean_window_20260827_20260902": clean_window,
        "day1_explicit": initial,
        "eligible_clean_window_day1": bool(clean_window and initial),
    }


def run_venue(venue: str) -> dict:
    index_url = f"https://{HOST}/{venue}/racecard/"
    s = requests.Session()
    raw_index, final_index = get(s, index_url, venue, "index")
    _, form, by_name, hidden, action = find_exact_archive_form(raw_index, final_index, venue)
    months = []
    day_urls = set()
    for month in TARGET_MONTHS:
        payload, safe_payload = observed_payload(form, by_name, hidden, month)
        raw_month, final_month, redirects = post_archive(s, action, venue, payload)
        links = exact_day_links(raw_month, final_month, venue)
        day_urls.update(links)
        months.append({
            "requested_year": TARGET_YEAR,
            "requested_month": month,
            "request_method": "post",
            "request_action_url": action,
            "observed_form_payload": safe_payload,
            "redirect_history": redirects,
            "response_url": final_month,
            "response_sha256": sha_bytes(raw_month),
            "positively_observed_day_href_count": len(links),
            "positively_observed_day_hrefs": links,
        })
    day_records = []
    failures = []
    for u in sorted(day_urls):
        try:
            day_records.append(day_metadata(s, u, venue))
        except Exception as exc:
            failures.append({"day_url": u, "reason": f"{type(exc).__name__}:{str(exc)[:300]}"})
    eligible = [r for r in day_records if r["eligible_clean_window_day1"]]
    return {
        "venue_slug": venue,
        "index_url": final_index,
        "index_source_sha256": sha_bytes(raw_index),
        "form_contract": {
            "name": "searchDate",
            "id": "searchDate",
            "method": "post",
            "action_url": action,
            "select_names": ["yy", "mm"],
            "hidden_names": ["searchDate"],
        },
        "months": months,
        "unique_positively_observed_day_href_count": len(day_urls),
        "day_metadata": day_records,
        "day_metadata_failures": failures,
        "eligible_clean_window_day1_blocks": eligible,
        "eligible_clean_window_day1_count": len(eligible),
    }


def run() -> dict:
    records = []
    failures = []
    for venue in VENUES:
        try:
            records.append(run_venue(venue))
        except Exception as exc:
            failures.append({"venue_slug": venue, "reason": f"{type(exc).__name__}:{str(exc)[:500]}"})
    eligible = []
    for r in records:
        for b in r["eligible_clean_window_day1_blocks"]:
            eligible.append({"venue_slug": r["venue_slug"], **b})
    eligible.sort(key=lambda x: ((x.get("race_date") or "9999-99-99"), x["venue_slug"], x["day_url"]))
    return {
        "record": "KEIRIN_HFT_RACECARD_MONTH_ARCHIVE_PROBE_20260904_v1",
        "status": "ARCHIVE_MONTH_NAVIGATION_CAPTURED" if records else "FAIL_CLOSED_NO_ARCHIVE_CAPTURE",
        "clean_window": [CLEAN_START.isoformat(), CLEAN_END.isoformat()],
        "venue_pool_333": ["防府", "富山", "奈良"],
        "target_month_requests": ["2026-08", "2026-09"],
        "records": records,
        "failures": failures,
        "eligible_clean_window_day1_blocks": eligible,
        "eligible_clean_window_day1_count": len(eligible),
        "raw_html_persisted": False,
        "raw_html_printed": False,
        "page_visible_text_emitted": False,
        "race_detail_opened": False,
        "result_page_opened": False,
        "result_accessed": False,
        "payout_accessed": False,
        "odds_emitted": False,
        "forecast_emitted": False,
        "comment_emitted": False,
        "narabiyoso_emitted": False,
        "rider_data_emitted": False,
        "race_id_guessed": False,
        "archive_month_request_executed": True,
        "support_increment_authorized_now": 0,
        "model_fit_authorized": False,
        "main_or_runtime_mutation": False,
    }


def selftest() -> dict:
    html = '''<html><body><form name="searchDate" id="searchDate" method="post" action="/hofu/racecard/">
      <select name="yy"><option value="2025">2025</option><option value="2026" selected>2026</option></select>
      <select name="mm"><option value="08">8</option><option value="09" selected>9</option></select>
      <input type="hidden" name="searchDate" value="20260904">
    </form><a href="/hofu/racecard/63202609040100/">x</a></body></html>'''.encode("utf-8")
    soup, form, by_name, hidden, action = find_exact_archive_form(html, "https://keirin.kdreams.jp/hofu/racecard/", "hofu")
    payload, safe = observed_payload(form, by_name, hidden, "08")
    links = exact_day_links(html, "https://keirin.kdreams.jp/hofu/racecard/", "hofu")
    tests = {
        "method_post": (clean(form.get("method"))).lower() == "post",
        "same_action": action == "https://keirin.kdreams.jp/hofu/racecard/",
        "observed_2026_option": payload["yy"] == "2026",
        "observed_august_option": payload["mm"] == "08",
        "hidden_not_emitted_raw": "hidden_searchDate_value_sha256" in safe and "20260904" not in json.dumps(safe),
        "one_exact_day_href": links == ["https://keirin.kdreams.jp/hofu/racecard/63202609040100/"],
        "no_race_id_construction": True,
    }
    return {"record": "KEIRIN_KDREAMS_RACECARD_MONTH_ARCHIVE_PROBE_SELFTEST_v1", "status": "PASS" if all(tests.values()) else "FAIL", "tests": tests}


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    p = sub.add_parser("probe")
    p.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "selftest":
        x = selftest()
        print(json.dumps(x, ensure_ascii=False, sort_keys=True))
        return 0 if x["status"] == "PASS" else 2
    x = run()
    Path(a.out).write_text(json.dumps(x, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "record": x["record"],
        "status": x["status"],
        "records": len(x["records"]),
        "failures": len(x["failures"]),
        "eligible_clean_window_day1_count": x["eligible_clean_window_day1_count"],
        "race_id_guessed": False,
        "result_accessed": False,
    }, ensure_ascii=False, sort_keys=True))
    return 0 if x["records"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
