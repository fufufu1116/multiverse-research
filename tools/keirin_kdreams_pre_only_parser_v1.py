#!/usr/bin/env python3
"""Research-only PRE-only parser for saved KDreams racedetail HTML.

This parser deliberately ignores every post-event/market/forecast region.
It extracts only the pre-race rider table headed by:
  直近4ヶ月の成績 / 競走得点 / 2連 対率

Designed for prospective, result-blind capture. It never requires or parses
result tables, payout, odds, forecast marks/comments, or narabiyoso.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


EVIDENCE_ROLE = "PROSPECTIVE_PRE_ONLY"


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_pre_only_file(p: Path) -> list[dict[str, Any]]:
    html = p.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    title = clean(soup.title.get_text(" ", strip=True)) if soup.title else ""
    canonical = soup.find("link", rel="canonical")
    url = canonical.get("href") if canonical else ""

    m = re.search(r"/racedetail/(\d+)/", url)
    if not m:
        raise ValueError("FAIL-CLOSED:no_race_id")
    race_id = m.group(1)

    dm = re.search(r"(20\d{2})年(\d{2})月(\d{2})日", title)
    rm = re.search(r"(?:^|\s)(\d{1,2})R(?:\s|$)", title)
    if not dm or not rm:
        raise ValueError("FAIL-CLOSED:race_metadata")

    race_date = "-".join(dm.groups())
    race_no = int(rm.group(1))
    venue = title.split("競輪")[0].strip() if "競輪" in title else ""
    if not venue:
        raise ValueError("FAIL-CLOSED:venue_metadata")

    pre_table = None
    for t in soup.find_all("table"):
        tt = clean(t.get_text(" ", strip=True))
        if "直近4ヶ月の成績" in tt and "競走得点" in tt and "2連 対率" in tt:
            pre_table = t
            break
    if pre_table is None:
        raise ValueError("FAIL-CLOSED:no_pre_table")

    rows: list[dict[str, Any]] = []
    seen_cars: set[int] = set()
    for tr in pre_table.find_all("tr"):
        cells = [clean(x.get_text(" ", strip=True)) for x in tr.find_all(["th", "td"])]
        ci = next((i for i, c in enumerate(cells) if re.fullmatch(r"[SA][123]", c)), None)
        if ci is None or ci < 1:
            continue

        cars = [int(c) for c in cells[:ci-1] if re.fullmatch(r"[1-9]", c)]
        if not cars:
            continue
        car_no = cars[-1]
        if car_no in seen_cars:
            raise ValueError(f"FAIL-CLOSED:duplicate_car={car_no}")

        rider = cells[ci - 1]
        if not rider:
            raise ValueError(f"FAIL-CLOSED:missing_rider:car={car_no}")

        style = cells[ci + 1] if ci + 1 < len(cells) and cells[ci + 1] in ("逃", "追", "両") else None
        si = next(
            (i for i in range(ci + 1, len(cells)) if re.fullmatch(r"\d{1,3}\.\d{2}", cells[i])),
            None,
        )
        if si is None:
            raise ValueError(f"FAIL-CLOSED:missing_competition_score:car={car_no}")

        score = float(cells[si])
        if score == 0.0:
            raise ValueError(f"FAIL-CLOSED:zero_competition_score:car={car_no}")

        vals: list[int] = []
        for c in cells[si + 1 :]:
            if re.fullmatch(r"\d{1,2}", c):
                vals.append(int(c))
                if len(vals) == 6:
                    break
        if len(vals) != 6:
            raise ValueError(f"FAIL-CLOSED:missing_tactical_counts:car={car_no}")
        S, B, nige, makuri, sashi, mark = vals

        rows.append(
            {
                "race_id": race_id,
                "race_date": race_date,
                "venue": venue,
                "race_no": race_no,
                "car_no": car_no,
                "rider_name_raw": rider,
                "class": cells[ci],
                "style": style,
                "competition_score": score,
                "S": S,
                "B": B,
                "nige": nige,
                "makuri": makuri,
                "sashi": sashi,
                "mark": mark,
                "source_url": url,
                "evidence_role": EVIDENCE_ROLE,
            }
        )
        seen_cars.add(car_no)

    if len(rows) < 5:
        raise ValueError(f"FAIL-CLOSED:pre_rows={len(rows)}")

    return sorted(rows, key=lambda x: x["car_no"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_dir")
    ap.add_argument("pre_csv")
    ap.add_argument("receipt_json")
    args = ap.parse_args()

    files = sorted(Path(args.input_dir).glob("*.html"))
    pre_rows: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    rejects: list[dict[str, str]] = []

    for p in files:
        try:
            rows = parse_pre_only_file(p)
            h = sha256(p)
            for r in rows:
                r["source_file_sha256"] = h
            pre_rows.extend(rows)
            accepted.append(
                {
                    "file": p.name,
                    "race_id": rows[0]["race_id"],
                    "race_date": rows[0]["race_date"],
                    "venue": rows[0]["venue"],
                    "race_no": rows[0]["race_no"],
                    "pre_rows": len(rows),
                    "source_file_sha256": h,
                }
            )
        except Exception as exc:
            rejects.append({"file": p.name, "reason": str(exc)})

    fields = [
        "race_id",
        "race_date",
        "venue",
        "race_no",
        "car_no",
        "rider_name_raw",
        "class",
        "style",
        "competition_score",
        "S",
        "B",
        "nige",
        "makuri",
        "sashi",
        "mark",
        "source_url",
        "source_file_sha256",
        "evidence_role",
    ]
    with open(args.pre_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(pre_rows)

    receipt = {
        "record": "KEIRIN_KDREAMS_PRE_ONLY_PARSE_RECEIPT_v1",
        "input_files": len(files),
        "successful_races": len(accepted),
        "rejected_files": len(rejects),
        "pre_rows": len(pre_rows),
        "accepted": accepted,
        "rejects": rejects[:50],
        "evidence_role": EVIDENCE_ROLE,
        "result_table_required": False,
        "result_fields_emitted": False,
        "payout_fields_emitted": False,
        "odds_fields_emitted": False,
        "forecast_fields_emitted": False,
        "narabiyoso_fields_emitted": False,
        "postrace_pre_reconstruction": False,
        "network_access": False,
    }
    Path(args.receipt_json).write_text(
        json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
