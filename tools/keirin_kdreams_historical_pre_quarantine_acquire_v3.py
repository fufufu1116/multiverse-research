#!/usr/bin/env python3
"""Research-only HFT PRE acquirer v3 for an already-frozen exact Day1 manifest.

This is intentionally narrower than the discovery fetchers: it performs no
archive discovery and no race-ID construction. It accepts only exact KDreams
racedetail hrefs already present in a frozen Day1 manifest, keeps raw mixed HTML
in memory only, and emits the unchanged strict PRE allowlist plus provenance.

Parser delta from v2 is prespecified in
KEIRIN_HFT_L1_PRE_PARSER_SCHEMA_DELTA_PRESPEC_20260904_v1.json: recognize L1
in the same class-token position as S1/S2/A1/A2/A3. Unknown classes fail closed.
"""
from __future__ import annotations

import argparse, csv, hashlib, json, re
from datetime import date
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

HOST = "keirin.kdreams.jp"
UA = "Mozilla/5.0 (compatible; MultiverseKeirinResearch/3.0; PRE-only)"
MAX_BYTES = 8 * 1024 * 1024
EVIDENCE_ROLE = "HISTORICAL_PIT_PRE_SUPPORT_CANDIDATE_ONLY"
CLASS_RE = re.compile(r"(?:[SA][123]|L1)")
ALLOWED_PRE_FIELDS = [
    "race_id","race_date","venue","race_no","car_no","rider_name_raw",
    "class","style","competition_score","S","B","nige","makuri",
    "sashi","mark","source_url","source_file_sha256","evidence_role"
]
FORBIDDEN_OUTPUT_KEYS = {
    "result","finish","finish_1","finish_2","finish_3","payout",
    "settlement","odds","forecast","prediction","tips","comment",
    "narabiyoso","roi","ev"
}


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", unescape(s or "")).strip()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def validate_detail_url(url: str) -> str:
    p = urlparse(url)
    if p.scheme != "https" or p.hostname != HOST:
        raise ValueError("FAIL-CLOSED:non_kdreams_https_url")
    if p.query or p.fragment:
        raise ValueError("FAIL-CLOSED:query_or_fragment_forbidden")
    if not re.fullmatch(r"/[^/]+/racedetail/\d+/?", p.path):
        raise ValueError("FAIL-CLOSED:not_exact_racedetail_href")
    return url


def fetch_bytes(url: str, timeout: int = 25) -> tuple[bytes, str]:
    validate_detail_url(url)
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
    with urlopen(req, timeout=timeout) as r:
        final = r.geturl()
        validate_detail_url(final)
        if final != url:
            raise ValueError("FAIL-CLOSED:detail_redirect")
        ctype = (r.headers.get("Content-Type") or "").lower()
        if "text/html" not in ctype and "application/xhtml" not in ctype:
            raise ValueError("FAIL-CLOSED:non_html_content_type")
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("FAIL-CLOSED:html_too_large")
    if len(data) < 500:
        raise ValueError("FAIL-CLOSED:html_too_small")
    return data, final


def soup_from_bytes(data: bytes) -> BeautifulSoup:
    return BeautifulSoup(data.decode("utf-8", errors="replace"), "html.parser")


def parse_date(text: str) -> str | None:
    m = re.search(r"(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日", text)
    if not m:
        return None
    y, mo, d = map(int, m.groups())
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


def parse_detail_pre(data: bytes, exact_url: str) -> list[dict[str, Any]]:
    validate_detail_url(exact_url)
    s = soup_from_bytes(data)
    title = clean(s.title.get_text(" ", strip=True)) if s.title else ""
    canonical = s.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        c = canonical.get("href")
        validate_detail_url(c)
        if c != exact_url:
            raise ValueError("FAIL-CLOSED:canonical_url_mismatch")

    m = re.search(r"/racedetail/(\d+)/", exact_url)
    race_date = parse_date(title)
    rm = re.search(r"(?:^|\s)(\d{1,2})R(?:\s|$)", title)
    venue = title.split("競輪", 1)[0].strip() if "競輪" in title else ""
    if not m or not race_date or not rm or not venue:
        raise ValueError("FAIL-CLOSED:race_metadata")
    rid = m.group(1)
    race_no = int(rm.group(1))

    table = None
    for t in s.find_all("table"):
        tt = clean(t.get_text(" ", strip=True))
        if "直近4ヶ月の成績" in tt and "競走得点" in tt and "2連 対率" in tt:
            table = t
            break
    if table is None:
        raise ValueError("FAIL-CLOSED:no_pre_table")

    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    source_hash = sha256_bytes(data)
    for tr in table.find_all("tr"):
        cells = [clean(x.get_text(" ", strip=True)) for x in tr.find_all(["th", "td"])]
        ci = next((i for i, c in enumerate(cells) if CLASS_RE.fullmatch(c)), None)
        if ci is None or ci < 1:
            continue
        cls = cells[ci]
        if cls not in {"S1","S2","A1","A2","A3","L1"}:
            raise ValueError("FAIL-CLOSED:unknown_class")
        cars = [int(c) for c in cells[:ci-1] if re.fullmatch(r"[1-9]", c)]
        if not cars:
            continue
        car = cars[-1]
        if car in seen:
            raise ValueError(f"FAIL-CLOSED:duplicate_car={car}")
        rider = cells[ci - 1]
        if not rider:
            raise ValueError(f"FAIL-CLOSED:missing_rider={car}")
        style = cells[ci + 1] if ci + 1 < len(cells) and cells[ci + 1] in {"逃","追","両"} else None
        si = next((i for i in range(ci + 1, len(cells)) if re.fullmatch(r"\d{1,3}\.\d{2}", cells[i])), None)
        if si is None:
            raise ValueError(f"FAIL-CLOSED:missing_competition_score={car}")
        score = float(cells[si])
        if score == 0.0:
            raise ValueError(f"FAIL-CLOSED:zero_competition_score={car}")
        vals: list[int] = []
        for c in cells[si + 1:]:
            if re.fullmatch(r"\d{1,2}", c):
                vals.append(int(c))
            if len(vals) == 6:
                break
        if len(vals) != 6:
            raise ValueError(f"FAIL-CLOSED:missing_tactical_counts={car}")
        S, B, nige, makuri, sashi, mark = vals
        row = {
            "race_id":rid,"race_date":race_date,"venue":venue,"race_no":race_no,
            "car_no":car,"rider_name_raw":rider,"class":cls,"style":style,
            "competition_score":score,"S":S,"B":B,"nige":nige,"makuri":makuri,
            "sashi":sashi,"mark":mark,"source_url":exact_url,
            "source_file_sha256":source_hash,"evidence_role":EVIDENCE_ROLE
        }
        if set(row) != set(ALLOWED_PRE_FIELDS):
            raise ValueError("FAIL-CLOSED:output_schema_drift")
        if any(k.lower() in FORBIDDEN_OUTPUT_KEYS for k in row):
            raise ValueError("FAIL-CLOSED:forbidden_output_key")
        rows.append(row)
        seen.add(car)

    rows.sort(key=lambda x: x["car_no"])
    if len(rows) < 5:
        raise ValueError(f"FAIL-CLOSED:pre_rows={len(rows)}")
    if [r["car_no"] for r in rows] != list(range(1, max(r["car_no"] for r in rows) + 1)):
        raise ValueError("FAIL-CLOSED:active_car_continuity")
    return rows


def acquire_manifest(manifest: dict[str, Any], timeout: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for block in manifest.get("blocks", []):
        if block.get("day1_confirmed") is not True:
            continue
        details = block.get("detail_urls", [])
        if not 5 <= len(details) <= 12:
            raise ValueError("FAIL-CLOSED:manifest_detail_count")
        for u in details:
            try:
                validate_detail_url(u)
                raw, final = fetch_bytes(u, timeout)
                pr = parse_detail_pre(raw, final)
                rows.extend(pr)
                accepted.append({
                    "race_id":pr[0]["race_id"],"race_date":pr[0]["race_date"],
                    "venue":pr[0]["venue"],"race_no":pr[0]["race_no"],
                    "pre_rows":len(pr),"class_tokens":sorted({r["class"] for r in pr}),
                    "source_file_sha256":pr[0]["source_file_sha256"]
                })
            except Exception as exc:
                rejected.append({"url":u,"reason":str(exc)})
    keys = [(x["race_date"],x["venue"],x["race_no"]) for x in accepted]
    if len(keys) != len(set(keys)):
        raise ValueError("FAIL-CLOSED:duplicate_accepted_race")
    receipt = {
        "record":"KEIRIN_KDREAMS_HISTORICAL_PRE_QUARANTINE_ACQUIRE_RECEIPT_v3",
        "successful_races":len(accepted),"pre_rows":len(rows),"accepted":accepted,
        "rejected":rejected[:100],"allowed_class_tokens":["S1","S2","A1","A2","A3","L1"],
        "raw_html_written_to_disk":False,"raw_html_printed":False,
        "result_fields_emitted":False,"payout_fields_emitted":False,
        "odds_fields_emitted":False,"forecast_fields_emitted":False,
        "narabiyoso_fields_emitted":False,"race_id_guessed":False,
        "support_increment_authorized_by_tool":False
    }
    return rows, receipt


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ALLOWED_PRE_FIELDS)
        w.writeheader(); w.writerows(rows)


def synthetic_detail(classes: list[str]) -> bytes:
    rs=[]
    for i, cls in enumerate(classes,1):
        rs.append(f"<tr><td>{i}</td><td>選手{i}</td><td>{cls}</td><td>両</td><td>55.{i:02d}</td><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td><td>6</td></tr>")
    return ("<html><head><title>川崎競輪 2026年08月30日 6R test</title><link rel='canonical' href='https://keirin.kdreams.jp/kawasaki/racedetail/3420260830010006/'></head><body><table><tr><th>直近4ヶ月の成績</th><th>競走得点</th><th>2連 対率</th></tr>"+"".join(rs)+"</table><div>結果 払戻 オッズ 予想 コメント 並び予想</div></body></html>").encode("utf-8")


def selftest() -> dict[str, Any]:
    tests={}
    l=parse_detail_pre(synthetic_detail(["L1"]*5),"https://keirin.kdreams.jp/kawasaki/racedetail/3420260830010006/")
    a=parse_detail_pre(synthetic_detail(["A1"]*5),"https://keirin.kdreams.jp/kawasaki/racedetail/3420260830010006/")
    tests["l1_rows_5"] = len(l)==5 and {r["class"] for r in l}=={"L1"}
    tests["a1_rows_5"] = len(a)==5 and {r["class"] for r in a}=={"A1"}
    tests["schema_unchanged"] = all(set(r)==set(ALLOWED_PRE_FIELDS) for r in l+a)
    blob=json.dumps(l+a,ensure_ascii=False)
    tests["forbidden_mixed_text_not_emitted"] = not any(x in blob for x in ["結果","払戻","オッズ","予想","コメント","並び予想"])
    try:
        validate_detail_url("https://keirin.kdreams.jp/kawasaki/racedetail/3420260830010006/?pageType=result")
        tests["query_rejected"]=False
    except ValueError:
        tests["query_rejected"]=True
    return {"record":"KEIRIN_KDREAMS_HISTORICAL_PRE_QUARANTINE_ACQUIRE_SELFTEST_v3","status":"PASS" if all(tests.values()) else "FAIL","tests":tests,"network_access":False,"race_id_guessing":False}


def main() -> int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True); sub.add_parser("selftest")
    a=sub.add_parser("acquire"); a.add_argument("--manifest",required=True); a.add_argument("--pre-csv",required=True); a.add_argument("--receipt",required=True); a.add_argument("--timeout",type=int,default=25)
    args=ap.parse_args()
    if args.cmd=="selftest":
        out=selftest(); print(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)); return 0 if out["status"]=="PASS" else 2
    manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    rows,receipt=acquire_manifest(manifest,args.timeout); write_csv(rows,Path(args.pre_csv)); Path(args.receipt).write_text(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in receipt.items() if k not in {"accepted","rejected"}},ensure_ascii=False,sort_keys=True)); return 0 if not receipt["rejected"] else 3

if __name__=="__main__": raise SystemExit(main())
