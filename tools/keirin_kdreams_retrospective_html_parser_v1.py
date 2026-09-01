#!/usr/bin/env python3
"""Offline parser for saved KDreams race-detail HTML.

Research-only. No network access. Consumes lawfully saved HTML files and emits:
- PRE rider rows (race-local features available before the race)
- outcome labels (finish order only)

It never emits payout/settlement/EV/ROI fields and refuses pages that cannot be
unambiguously identified as KDreams race-detail pages.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

FORBIDDEN_OUTPUT_TOKENS = {"払戻", "payout", "refund", "settlement", "roi", "ev"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def txt(node) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip() if node else ""


def parse_meta(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    title = txt(soup.title)
    canonical = soup.find("link", rel="canonical")
    canonical_url = canonical.get("href") if canonical else None
    m = re.search(r"/(?:racedetail|racecard)/(\d{12,})/", canonical_url or "")
    if not m:
        raise ValueError("FAIL-CLOSED: no canonical KDreams race-detail id")
    rid = m.group(1)
    dm = re.search(r"(20\d{2})年(\d{2})月(\d{2})日", title + " " + txt(soup))
    if not dm:
        raise ValueError("FAIL-CLOSED: race date missing")
    race_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
    rm = re.search(r"\b(\d{1,2})R\b", title)
    race_no = int(rm.group(1)) if rm else None
    venue = title.split("競輪")[0].strip() if "競輪" in title else None
    return {"race_id": rid, "race_date": race_date, "race_no": race_no, "venue": venue, "canonical_url": canonical_url}


def find_rider_table(soup: BeautifulSoup):
    # KDreams uses a table whose headers include these stable labels.
    for table in soup.find_all("table"):
        t = txt(table)
        if all(k in t for k in ("競走得点", "脚質", "S", "B", "逃", "捲", "差", "マ")):
            return table
    raise ValueError("FAIL-CLOSED: PRE rider table not found")


def parse_pre_rows(soup: BeautifulSoup, meta: dict) -> list[dict]:
    table = find_rider_table(soup)
    rows = []
    # Robust heuristic: each competitor row contains car no, rider, class/style and score.
    for tr in table.find_all("tr"):
        cells = [txt(x) for x in tr.find_all(["th", "td"])]
        if len(cells) < 8:
            continue
        joined = " | ".join(cells)
        # Prefer explicit car number near the start of a competitor row.
        car_candidates = [int(x) for x in re.findall(r"(?<!\d)([1-9])(?!\d)", " ".join(cells[:6]))]
        score_candidates = [float(x) for x in re.findall(r"\b(\d{2,3}\.\d{2})\b", joined)]
        if not car_candidates or not score_candidates:
            continue
        car_no = car_candidates[-1]
        score = score_candidates[0]
        class_m = re.search(r"\b([SA][123])\b", joined)
        style_m = re.search(r"\b(逃|追|両)\b", joined)
        # Six integer tactical/support fields immediately following score are parsed conservatively.
        after_score = joined.split(f"{score:.2f}", 1)[1] if f"{score:.2f}" in joined else ""
        nums = [int(x) for x in re.findall(r"(?<![\d.])(\d{1,2})(?![\d.])", after_score)]
        s_val = b_val = nige = makuri = sashi = mark = None
        if len(nums) >= 6:
            s_val, b_val, nige, makuri, sashi, mark = nums[:6]
        # Rider name heuristic: Japanese text before class token, excluding labels.
        rider = None
        for c in cells:
            if re.search(r"[一-龥ぁ-んァ-ン]", c) and not any(k in c for k in ("競走得点", "脚質", "予想", "府県", "級班")):
                if class_m and class_m.group(1) in c:
                    continue
                if len(c) <= 24:
                    rider = c
                    break
        rows.append({
            "race_id": meta["race_id"], "race_date": meta["race_date"], "venue": meta["venue"], "race_no": meta["race_no"],
            "car_no": car_no, "rider_name_raw": rider, "class": class_m.group(1) if class_m else None,
            "style": style_m.group(1) if style_m else None, "competition_score": score,
            "S": s_val, "B": b_val, "nige": nige, "makuri": makuri, "sashi": sashi, "mark": mark,
            "source_url": meta["canonical_url"], "evidence_role": "RETROSPECTIVE_PRE_DEVELOPMENT_ONLY"
        })
    # Deduplicate by car and reject ambiguity.
    by_car = {}
    for r in rows:
        c = r["car_no"]
        if c in by_car and by_car[c] != r:
            raise ValueError(f"FAIL-CLOSED: ambiguous duplicate car {c}")
        by_car[c] = r
    out = [by_car[c] for c in sorted(by_car)]
    if len(out) < 5:
        raise ValueError(f"FAIL-CLOSED: too few PRE riders parsed ({len(out)})")
    return out


def parse_finish_order(soup: BeautifulSoup, active_cars: set[int]) -> list[int]:
    # Search result-oriented tables/blocks only; do not parse payout amounts.
    candidates = []
    for table in soup.find_all("table"):
        t = txt(table)
        if any(k in t for k in ("着順", "順位", "着 車番")):
            pairs = re.findall(r"(?:^|\s)([1-9])\s*(?:着|位)?\s*([1-9])(?:\s|$)", t)
            if pairs:
                order = []
                for pos, car in pairs:
                    p, c = int(pos), int(car)
                    if p <= 9 and c in active_cars:
                        order.append((p, c))
                order = [c for p, c in sorted(set(order))]
                if len(order) >= 3:
                    candidates.append(order)
    if not candidates:
        # Last-resort text pattern such as 1着 3, 2着 4, 3着 5.
        body = txt(soup)
        found = []
        for p in (1, 2, 3):
            m = re.search(fr"{p}\s*着[^0-9]{{0,20}}([1-9])", body)
            if m and int(m.group(1)) in active_cars:
                found.append(int(m.group(1)))
        if len(found) == 3 and len(set(found)) == 3:
            return found
        raise ValueError("FAIL-CLOSED: finish order not identified")
    # Require top3 agreement if multiple representations exist.
    top3 = {tuple(x[:3]) for x in candidates}
    if len(top3) != 1:
        raise ValueError(f"FAIL-CLOSED: conflicting finish orders {sorted(top3)}")
    return list(next(iter(top3)))


def parse_file(path: Path) -> tuple[list[dict], dict]:
    html = path.read_text(encoding="utf-8", errors="replace")
    if "keirin.kdreams.jp" not in html:
        raise ValueError("FAIL-CLOSED: not KDreams HTML")
    soup = BeautifulSoup(html, "html.parser")
    meta = parse_meta(html)
    pre = parse_pre_rows(soup, meta)
    active = {r["car_no"] for r in pre}
    finish = parse_finish_order(soup, active)
    outcome = {
        "race_id": meta["race_id"], "race_date": meta["race_date"], "venue": meta["venue"], "race_no": meta["race_no"],
        "finish_1": finish[0], "finish_2": finish[1], "finish_3": finish[2],
        "source_url": meta["canonical_url"], "evidence_role": "RETROSPECTIVE_OUTCOME_LABEL_ONLY",
        "payout_fields_included": False
    }
    for d in [*pre, outcome]:
        keys = " ".join(map(str, d.keys())).lower()
        if any(tok.lower() in keys for tok in FORBIDDEN_OUTPUT_TOKENS):
            raise ValueError("FAIL-CLOSED: forbidden economic output field")
    return pre, outcome


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_dir")
    ap.add_argument("pre_csv")
    ap.add_argument("outcome_jsonl")
    ap.add_argument("receipt_json")
    a = ap.parse_args()
    inp = Path(a.input_dir)
    files = sorted(inp.glob("*.html"))
    if not files:
        raise SystemExit("FAIL-CLOSED: no HTML files")
    pre_rows, outcomes, failures = [], [], []
    for p in files:
        try:
            pre, out = parse_file(p)
            for r in pre:
                r["source_file_sha256"] = sha256_file(p)
            out["source_file_sha256"] = sha256_file(p)
            pre_rows.extend(pre); outcomes.append(out)
        except Exception as e:
            failures.append({"file": p.name, "error": str(e)})
    # One race per source file and no duplicate race ids among successes.
    rids = [x["race_id"] for x in outcomes]
    if len(rids) != len(set(rids)):
        raise SystemExit("FAIL-CLOSED: duplicate successful race ids")
    fields = ["race_id","race_date","venue","race_no","car_no","rider_name_raw","class","style","competition_score","S","B","nige","makuri","sashi","mark","source_url","source_file_sha256","evidence_role"]
    Path(a.pre_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(a.pre_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(pre_rows)
    with open(a.outcome_jsonl, "w", encoding="utf-8", newline="\n") as f:
        for r in outcomes:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    receipt = {
        "record": "KEIRIN_KDREAMS_RETROSPECTIVE_HTML_PARSE_RECEIPT_v1",
        "status": "PASS_WITH_REJECTIONS" if failures else "PASS",
        "input_html_files": len(files), "successful_races": len(outcomes), "rejected_files": len(failures),
        "pre_rows": len(pre_rows), "failure_examples": failures[:20],
        "network_access": False, "result_used_as_feature": False, "payout_access_required": False,
        "ev_roi_computed": False
    }
    Path(a.receipt_json).write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
