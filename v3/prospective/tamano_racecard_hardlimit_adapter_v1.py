#!/usr/bin/env python3
import argparse, hashlib, json, sys, time
from urllib.parse import unquote, urljoin, urlparse

import fitz
import requests
from bs4 import BeautifulSoup

HOST = "www.tamano-keirin.jp"
DISCOVERY_PREFIX = "/racepdf/"
PDF_PREFIX = "/wp-content/uploads/"
MIN_SPACING_SECONDS = 10.0
MAX_DISCOVERY_PER_EVENT_DAY = 2
MAX_PDF_BYTES = 10_000_000
TIMEOUT_SECONDS = 20
W, H, TOL = 1190.55, 841.88, 1.0
CLIPS = [fitz.Rect(610,0,W,H), fitz.Rect(0,0,W,720)]
ANCHORS = [
    {"得点":1,"連対率":1,"ギヤ":1,"班別":1,"締切":4,"発走":4,"（７車立）":4},
    {"得点":2,"連対率":2,"ギヤ":2,"班別":2,"締切":8,"発走":8,"（７車立）":8},
]
POST_SENTINELS = ["成績表","払戻","発売金額","２車単","2車単","３連単","3連単","ワイド","着順","風速","合計"]

class FailClosed(RuntimeError): pass
class PersistentHalt(RuntimeError): pass

def _origin(url):
    u = urlparse(url)
    if u.scheme != "https" or u.netloc != HOST or u.fragment:
        raise FailClosed("REJECT origin")
    return u

def validate_discovery_url(url):
    u = _origin(url)
    if not u.path.startswith(DISCOVERY_PREFIX):
        raise FailClosed("REJECT discovery path")
    return url

def validate_pdf_url(url, discovered_exact_hrefs):
    u = _origin(url)
    if not u.path.startswith(PDF_PREFIX) or not u.path.lower().endswith(".pdf") or u.query:
        raise FailClosed("REJECT pdf path")
    if url not in set(discovered_exact_hrefs):
        raise FailClosed("REJECT guessed/non-session PDF")
    return url

def select_pdf_for_event_day(discovered_exact_hrefs, event_day):
    yyyymmdd = str(event_day).replace("-", "")
    if len(yyyymmdd) != 8 or not yyyymmdd.isdigit():
        raise FailClosed("REJECT invalid event day")
    candidates = []
    for href in discovered_exact_hrefs:
        validate_pdf_url(href, discovered_exact_hrefs)
        basename = unquote(urlparse(href).path.rsplit("/", 1)[-1])
        if basename.startswith(yyyymmdd) and basename.lower().endswith(".pdf"):
            candidates.append(href)
    if len(candidates) != 1:
        raise FailClosed(f"REJECT event-day PDF cardinality={len(candidates)}")
    return candidates[0]

class RuntimeLimiter:
    def __init__(self):
        self.last_request_monotonic = None
        self.discovery_counts = {}
        self.halted = False

    def before(self, event_day, kind, now=None):
        if self.halted:
            raise PersistentHalt("HALTED")
        now = time.monotonic() if now is None else float(now)
        if self.last_request_monotonic is not None and now - self.last_request_monotonic < MIN_SPACING_SECONDS:
            raise FailClosed("REJECT spacing <10s")
        if kind == "discovery":
            n = self.discovery_counts.get(event_day, 0)
            if n >= MAX_DISCOVERY_PER_EVENT_DAY:
                raise FailClosed("REJECT >2 discovery checks/event day")
            self.discovery_counts[event_day] = n + 1
        elif kind != "pdf":
            raise FailClosed("REJECT unknown request kind")
        self.last_request_monotonic = now

    def status(self, code):
        code = int(code)
        if code in (403, 429):
            self.halted = True
            raise PersistentHalt(f"HALT provider status {code}")
        if code != 200:
            raise FailClosed(f"REJECT HTTP {code}")


def compact(text):
    return "".join(ch for ch in text if not ch.isspace())

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def validate_pdf_bytes(pdf_bytes):
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise FailClosed("REJECT PDF too large")
    raw_sha = sha256_bytes(pdf_bytes)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if len(doc) != 2:
        raise FailClosed("REJECT_TEMPLATE_MISMATCH pages")
    for p in doc:
        if abs(p.rect.width-W) > TOL or abs(p.rect.height-H) > TOL:
            raise FailClosed("REJECT_TEMPLATE_MISMATCH dimensions")
    page_receipts = []
    for i, (page, clip, expected) in enumerate(zip(doc, CLIPS, ANCHORS), start=1):
        text = compact(page.get_text("text", clip=clip))
        got = {k:text.count(k) for k in expected}
        if got != expected:
            raise FailClosed(f"REJECT_ANCHOR page={i} got={got}")
        post = {k:text.count(k) for k in POST_SENTINELS}
        if any(post.values()):
            raise PersistentHalt(f"HALT_POST_SENTINEL page={i} hits={post}")
        page_receipts.append({"page":i,"anchor_counts":got,"post_hits":post})
    return {"raw_pdf_sha256":raw_sha,"byte_size":len(pdf_bytes),"pages":page_receipts}


def discover_pdf_hrefs(html_bytes, discovery_url):
    soup = BeautifulSoup(html_bytes, "html.parser")
    found = []
    for a in soup.find_all("a", href=True):
        absolute = urljoin(discovery_url, a["href"])
        try:
            u = _origin(absolute)
        except FailClosed:
            continue
        if u.path.startswith(PDF_PREFIX) and u.path.lower().endswith(".pdf") and not u.query:
            found.append(absolute)
    return sorted(set(found))


def _get(session, limiter, event_day, kind, url):
    limiter.before(event_day, kind)
    r = session.get(url, timeout=TIMEOUT_SECONDS, allow_redirects=False, headers={"User-Agent":"Multiverse-Private-Research/1.0"})
    limiter.status(r.status_code)
    if 300 <= r.status_code < 400:
        raise FailClosed("REJECT redirect")
    return r


def smoke(discovery_url, event_day):
    validate_discovery_url(discovery_url)
    limiter = RuntimeLimiter()
    s = requests.Session()
    discovery = _get(s, limiter, event_day, "discovery", discovery_url)
    if "text/html" not in discovery.headers.get("content-type", "").lower():
        raise FailClosed("REJECT discovery content-type")
    hrefs = discover_pdf_hrefs(discovery.content, discovery_url)
    selected_pdf_url = select_pdf_for_event_day(hrefs, event_day)
    time.sleep(MIN_SPACING_SECONDS)
    pdf = _get(s, limiter, event_day, "pdf", selected_pdf_url)
    ctype = pdf.headers.get("content-type", "").lower()
    if "application/pdf" not in ctype and not pdf.content.startswith(b"%PDF-"):
        raise FailClosed("REJECT PDF content-type/magic")
    receipt = validate_pdf_bytes(pdf.content)
    return {
        "record":"TAMANO_RACECARD_RUNTIME_SMOKE_PASS_v1",
        "status":"PASS",
        "discovery_url":discovery_url,
        "pdf_url":selected_pdf_url,
        "event_day":event_day,
        "capture_timestamp_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "discovery_content_hash":sha256_bytes(discovery.content),
        "pdf_raw_sha256":receipt["raw_pdf_sha256"],
        "pdf_byte_size":receipt["byte_size"],
        "region_anchor_receipt":receipt["pages"],
        "raw_html_persisted":False,
        "raw_pdf_persisted":False,
        "shadow250_collected":0,
        "scientific_trial_consumed":False,
    }


def synthetic():
    race = "https://www.tamano-keirin.jp/racepdf/example/"
    pdf = "https://www.tamano-keirin.jp/wp-content/uploads/example.pdf"
    assert validate_discovery_url(race)
    for bad in ["http://www.tamano-keirin.jp/racepdf/x/","https://evil.example/racepdf/x/","https://www.tamano-keirin.jp/wp-admin/x/"]:
        try: validate_discovery_url(bad); raise AssertionError("not rejected")
        except FailClosed: pass
    assert validate_pdf_url(pdf, [pdf])
    try: validate_pdf_url(pdf, []); raise AssertionError("guessed PDF not rejected")
    except FailClosed: pass
    p1 = "https://www.tamano-keirin.jp/wp-content/uploads/2026/07/20260729-%E7%8E%89%E9%87%8E.pdf"
    p2 = "https://www.tamano-keirin.jp/wp-content/uploads/2026/07/20260728%E3%80%80%E7%8E%89%E9%87%8E.pdf"
    assert select_pdf_for_event_day([p1,p2], "2026-07-29") == p1
    try: select_pdf_for_event_day([p1,"https://www.tamano-keirin.jp/wp-content/uploads/2026/07/20260729-other.pdf"], "2026-07-29"); raise AssertionError("ambiguous day not rejected")
    except FailClosed: pass
    lim = RuntimeLimiter(); lim.before("2026-08-19","discovery",100)
    try: lim.before("2026-08-19","discovery",105); raise AssertionError("spacing not rejected")
    except FailClosed: pass
    lim.before("2026-08-19","discovery",110)
    try: lim.before("2026-08-19","discovery",120); raise AssertionError("third discovery not rejected")
    except FailClosed: pass
    lim2 = RuntimeLimiter()
    try: lim2.status(403); raise AssertionError("403 not halted")
    except PersistentHalt: pass
    try: lim2.before("2026-08-19","pdf",200); raise AssertionError("halt not persistent")
    except PersistentHalt: pass
    return {"status":"PASS","network_used":False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--discovery-url")
    ap.add_argument("--event-day")
    args = ap.parse_args()
    if args.synthetic:
        print(json.dumps(synthetic(), ensure_ascii=False)); return 0
    if args.smoke:
        if not all([args.discovery_url,args.event_day]):
            raise SystemExit("FAIL_CLOSED smoke requires discovery-url/event-day")
        print(json.dumps(smoke(args.discovery_url,args.event_day), ensure_ascii=False)); return 0
    raise SystemExit("FAIL_CLOSED no mode")

if __name__ == "__main__":
    sys.exit(main())
