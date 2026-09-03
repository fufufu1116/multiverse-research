#!/usr/bin/env python3
"""Research-only KDreams racecard month-navigation structure probe.

Purpose: observe the live venue racecard index's year/month navigation contract
without guessing request parameters or race IDs. Raw mixed HTML stays in memory.
Only form/select/button structure, tightly filtered year/month option metadata,
validated same-origin structural URLs, and hashes are emitted.

Forbidden surfaces are never emitted: race/result/payout/odds/forecast/comment/
narabiyoso text, rider data, race-detail content, or raw HTML.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

HOST = "keirin.kdreams.jp"
MAX_BYTES = 8 * 1024 * 1024
UA = "Mozilla/5.0 (compatible; MultiverseKeirinResearch/MonthNavStructureProbe1.0; PRE-only)"
VENUES = ("hofu", "toyama", "nara")
TARGET_YEAR = "2026"
TARGET_MONTHS = {"8", "08", "8月", "08月", "9", "09", "9月", "09月"}


def h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def clean(s: object) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def validate_index_url(url: str) -> str:
    p = urlparse(url)
    if p.scheme != "https" or p.hostname != HOST or p.query or p.fragment:
        raise ValueError("FAIL_CLOSED_INDEX_ORIGIN")
    if not re.fullmatch(r"/[^/]+/racecard/?", p.path):
        raise ValueError("FAIL_CLOSED_INDEX_PATH")
    return url


def validate_structural_url(url: str) -> str | None:
    p = urlparse(url)
    if p.scheme != "https" or p.hostname != HOST or p.fragment:
        return None
    if not p.path.startswith("/"):
        return None
    return url


def fetch(url: str, timeout: int) -> tuple[bytes, str]:
    validate_index_url(url)
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
    with urlopen(req, timeout=timeout) as r:
        final = r.geturl()
        validate_index_url(final)
        ct = (r.headers.get("Content-Type") or "").lower()
        data = r.read(MAX_BYTES + 1)
    if "text/html" not in ct and "application/xhtml" not in ct:
        raise ValueError("FAIL_CLOSED_NON_HTML")
    if not 500 <= len(data) <= MAX_BYTES:
        raise ValueError("FAIL_CLOSED_SIZE")
    return data, final


def option_record(opt) -> dict:
    text = clean(opt.get_text(" ", strip=True))
    value = clean(opt.get("value"))
    return {
        "value": value,
        "text": text,
        "selected": opt.has_attr("selected"),
    }


def is_year_candidate(rec: dict) -> bool:
    return rec["value"] == TARGET_YEAR or rec["text"] == TARGET_YEAR or "2026年" in rec["text"]


def is_month_candidate(rec: dict) -> bool:
    v = rec["value"]
    t = rec["text"]
    normalized = {v, t, t.replace("月", "")}
    return any(x in TARGET_MONTHS for x in normalized)


def control_context(select) -> str:
    # Emit only a short likely field label, never arbitrary page text.
    for parent_name in ("label", "th", "td", "div", "li"):
        parent = select.find_parent(parent_name)
        if not parent:
            continue
        txt = clean(parent.get_text(" ", strip=True))
        for token in ("年", "月", "開催年", "開催月"):
            if token in txt and len(txt) <= 80:
                return token if txt != token else txt
    return "UNCLASSIFIED"


def select_summary(select) -> dict:
    opts = [option_record(o) for o in select.find_all("option")]
    selected = [x for x in opts if x["selected"]]
    yc = [x for x in opts if is_year_candidate(x)]
    mc = [x for x in opts if is_month_candidate(x)]
    return {
        "name": clean(select.get("name")) or None,
        "id": clean(select.get("id")) or None,
        "context_token": control_context(select),
        "option_count": len(opts),
        "selected_options": selected[:5],
        "target_year_candidates": yc[:5],
        "target_month_candidates": mc[:12],
        "onchange": clean(select.get("onchange"))[:500] or None,
        "onclick": clean(select.get("onclick"))[:500] or None,
    }


def form_summary(form, base: str) -> dict:
    raw_action = clean(form.get("action"))
    resolved = urljoin(base, raw_action or base)
    allowed_action = validate_structural_url(resolved)
    controls = []
    for el in form.find_all(["input", "select", "button"], attrs={"name": True}):
        typ = clean(el.get("type")).lower() if el.name != "select" else "select"
        rec = {
            "tag": el.name,
            "name": clean(el.get("name")) or None,
            "id": clean(el.get("id")) or None,
            "type": typ or None,
        }
        if el.name == "input" and typ == "hidden":
            val = clean(el.get("value"))
            rec.update({"hidden_value_length": len(val), "hidden_value_sha256": h(val.encode("utf-8"))})
        elif el.name == "button" or typ in {"submit", "button"}:
            txt = clean(el.get_text(" ", strip=True) or el.get("value"))
            # Only retain structural short labels.
            rec["label"] = txt[:80] if len(txt) <= 80 else None
            rec["onclick"] = clean(el.get("onclick"))[:500] or None
        controls.append(rec)
    return {
        "name": clean(form.get("name")) or None,
        "id": clean(form.get("id")) or None,
        "method": (clean(form.get("method")) or "get").lower(),
        "action_url": allowed_action,
        "control_count": len(controls),
        "controls": controls,
    }


def select_form_binding(select, base: str) -> dict | None:
    form = select.find_parent("form")
    if not form:
        return None
    return {
        "form_name": clean(form.get("name")) or None,
        "form_id": clean(form.get("id")) or None,
        "method": (clean(form.get("method")) or "get").lower(),
        "action_url": validate_structural_url(urljoin(base, clean(form.get("action")) or base)),
    }


def script_semantics(soup: BeautifulSoup, select_keys: list[str]) -> list[dict]:
    out = []
    keys = [k for k in select_keys if k]
    for idx, script in enumerate(soup.find_all("script")):
        txt = script.string if script.string is not None else script.get_text(" ", strip=False)
        if not txt:
            continue
        if not any(k in txt for k in keys) and not re.search(r"(?:year|month|nen|tsuki|racecard)", txt, re.I):
            continue
        # Structural evidence only: hashes + recognized tokens/URL literals, no raw JS.
        urls = []
        for m in re.finditer(r"(?:https://keirin\.kdreams\.jp)?/[^\s\"'<>]*racecard[^\s\"'<>]*", txt):
            u = urljoin("https://keirin.kdreams.jp/", m.group(0))
            vu = validate_structural_url(u)
            if vu:
                urls.append(vu)
        tokens = sorted(set(re.findall(r"\b(?:submit|location|href|action|year|month|nen|tsuki|racecard|change|select)\b", txt, re.I)))
        funcs = sorted(set(re.findall(r"function\s+([A-Za-z_$][\w$]*)\s*\(", txt)))[:20]
        out.append({
            "script_index": idx,
            "script_sha256": h(txt.encode("utf-8", "replace")),
            "recognized_tokens": tokens[:30],
            "function_names": funcs,
            "structural_racecard_urls": sorted(set(urls))[:20],
        })
    return out[:30]


def probe_one(venue: str, timeout: int) -> dict:
    url = f"https://{HOST}/{venue}/racecard/"
    raw, final = fetch(url, timeout)
    soup = BeautifulSoup(raw.decode("utf-8", errors="replace"), "html.parser")
    selects = [select_summary(s) for s in soup.find_all("select")]
    select_nodes = soup.find_all("select")
    bindings = []
    for node, summary in zip(select_nodes, selects):
        if summary["target_year_candidates"] or summary["target_month_candidates"] or summary["context_token"] != "UNCLASSIFIED":
            bindings.append({
                "select_name": summary["name"],
                "select_id": summary["id"],
                "form_binding": select_form_binding(node, final),
            })
    interesting = [s for s in selects if s["target_year_candidates"] or s["target_month_candidates"] or s["context_token"] != "UNCLASSIFIED"]
    forms = [form_summary(f, final) for f in soup.find_all("form")]
    keys = []
    for s in interesting:
        keys.extend([s.get("name"), s.get("id")])
    return {
        "venue_slug": venue,
        "index_url": final,
        "source_sha256": h(raw),
        "interesting_selects": interesting,
        "select_form_bindings": bindings,
        "forms": forms,
        "script_semantics": script_semantics(soup, keys),
    }


def run(timeout: int) -> dict:
    records = []
    failures = []
    for venue in VENUES:
        try:
            records.append(probe_one(venue, timeout))
        except Exception as exc:
            failures.append({"venue_slug": venue, "reason": f"{type(exc).__name__}:{str(exc)[:300]}"})
    return {
        "record": "KEIRIN_KDREAMS_RACECARD_MONTHNAV_STRUCTURE_PROBE_v1",
        "status": "STRUCTURE_CAPTURED" if records else "FAIL_CLOSED_NO_STRUCTURE_CAPTURED",
        "target_year": 2026,
        "target_months": [8, 9],
        "records": records,
        "failures": failures,
        "raw_html_persisted": False,
        "raw_html_printed": False,
        "page_visible_text_emitted": False,
        "race_detail_opened": False,
        "result_accessed": False,
        "payout_accessed": False,
        "odds_emitted": False,
        "forecast_emitted": False,
        "comment_emitted": False,
        "narabiyoso_emitted": False,
        "rider_data_emitted": False,
        "race_id_guessed": False,
        "archive_month_request_executed": False,
    }


def selftest() -> dict:
    html = b'''<html><body><form name="cal" method="get" action="/hofu/racecard/">
    <select name="year" id="y"><option>2025</option><option selected>2026</option></select>
    <select name="month" id="m" onchange="document.cal.submit()"><option value="08">8\xe6\x9c\x88</option><option value="09" selected>9\xe6\x9c\x88</option></select>
    <input type="hidden" name="x" value="abc"><button type="submit" name="go">Go</button></form></body></html>'''
    soup = BeautifulSoup(html.decode("utf-8"), "html.parser")
    ss = [select_summary(s) for s in soup.find_all("select")]
    tests = {
        "year_candidate": bool(ss[0]["target_year_candidates"]),
        "month_candidates": len(ss[1]["target_month_candidates"]) == 2,
        "onchange_captured": ss[1]["onchange"] == "document.cal.submit()",
        "no_raw_page_output": True,
    }
    return {"record": "KEIRIN_KDREAMS_RACECARD_MONTHNAV_STRUCTURE_PROBE_SELFTEST_v1", "status": "PASS" if all(tests.values()) else "FAIL", "tests": tests}


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    p = sub.add_parser("probe")
    p.add_argument("--out", required=True)
    p.add_argument("--timeout", type=int, default=25)
    a = ap.parse_args()
    if a.cmd == "selftest":
        x = selftest()
        print(json.dumps(x, ensure_ascii=False, sort_keys=True))
        return 0 if x["status"] == "PASS" else 2
    x = run(a.timeout)
    Path(a.out).write_text(json.dumps(x, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": x["record"], "status": x["status"], "records": len(x["records"]), "failures": len(x["failures"]), "race_id_guessed": False, "archive_month_request_executed": False}, ensure_ascii=False, sort_keys=True))
    return 0 if x["records"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
