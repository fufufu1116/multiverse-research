from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

POST_TERMS = (
    "result", "payout", "harai", "払戻", "配当", "結果", "着順", "確定",
    "raceresult", "harailist",
)
RID_RE = re.compile(r"/racedetail/(\d{16})/")
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
PARSER_VERSION = "v3-fresh-universe-discovery-preflight-v1"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def reject_post(url: str) -> None:
    low = url.lower()
    if any(tok.lower() in low for tok in POST_TERMS):
        raise RuntimeError(f"HARD_SAFETY_POST_URL_PROHIBITED: {url}")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def fetch(session: requests.Session, url: str, *, retries: int = 2, timeout: int = 30):
    reject_post(url)
    last = None
    for attempt in range(retries + 1):
        try:
            r = session.get(url, timeout=timeout, allow_redirects=True)
            reject_post(r.url)
            if r.status_code == 200 and r.content:
                return r
            if r.status_code in {404, 429, 500, 502, 503, 504}:
                last = RuntimeError(f"RECOVERABLE_HTTP_{r.status_code}")
            else:
                raise RuntimeError(f"HARD_HTTP_{r.status_code}")
        except (requests.Timeout, requests.ConnectionError) as e:
            last = RuntimeError(f"RECOVERABLE_NETWORK: {e!r}")
        if attempt < retries:
            time.sleep(1.0 + attempt)
    raise last or RuntimeError("RECOVERABLE_UNKNOWN")


def parse_racedetail_links(index_url: str, payload: bytes, race_date: str):
    soup = BeautifulSoup(payload, "lxml")
    found = {}
    for a in soup.find_all("a", href=True):
        full = urljoin(index_url, a["href"])
        m = RID_RE.search(full)
        if not m:
            continue
        reject_post(full)
        rid = m.group(1)
        # Structural guard: 2-digit venue prefix + 8-digit event start date + 2-digit day + 4-digit race no.
        if len(rid) != 16 or not rid.isdigit():
            raise RuntimeError(f"HARD_INVALID_RACE_ID: {rid}")
        found[rid] = {
            "race_id": rid,
            "race_date": race_date,
            "venue_code": rid[:2],
            "url": full,
            "discovery_source": index_url,
            "data_status": "DISCOVERED_PREOUTCOME_CANDIDATE",
        }
    return list(found.values())


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = ["candidate_index", "race_id", "race_date", "venue_code", "url", "discovery_source", "data_status"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="YYYY-MM-DD; prospective scan start")
    ap.add_argument("--horizon-days", type=int, default=45)
    ap.add_argument("--target", type=int, default=1000)
    ap.add_argument("--out", default="V3_FRESH_UNIVERSE_DISCOVERY")
    ap.add_argument("--sleep", type=float, default=0.35)
    args = ap.parse_args()

    if args.horizon_days < 1 or args.horizon_days > 90:
        raise SystemExit("FAIL-CLOSED: horizon-days must be 1..90")
    if args.target != 1000:
        raise SystemExit("FAIL-CLOSED: frozen v3 target must remain exactly 1000")

    start = date.fromisoformat(args.start)
    end = start + timedelta(days=args.horizon_days - 1)
    root = Path(args.out)
    raw = root / "00_raw_index" / "sha256"
    audit = root / "audit"
    root.mkdir(parents=True, exist_ok=True)
    raw.mkdir(parents=True, exist_ok=True)
    audit.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 MultiverseResearch-v3-FreshDiscovery/1.0",
        "Accept-Language": "ja,en;q=0.5",
    })

    candidates: dict[str, dict] = {}
    provenance = []
    quarantine = []

    d = start
    while d <= end:
        ds = d.isoformat()
        # Two PRE-only index families. We only accept explicit /racedetail/<16digit>/ links.
        urls = [
            f"https://keirin.kdreams.jp/racecard/{d.year:04d}/{d.month:02d}/{d.day:02d}/",
            f"https://keirin.kdreams.jp/kaisai/{d.year:04d}/{d.month:02d}/{d.day:02d}/",
        ]
        for url in urls:
            print(f"[DISCOVERY] {ds} {url} unique={len(candidates)}", flush=True)
            try:
                r = fetch(session, url)
                payload = bytes(r.content)
                digest = sha256_bytes(payload)
                blob = raw / digest[:2] / f"{digest}.bin"
                if not blob.exists():
                    atomic_write(blob, payload)
                if sha256_bytes(blob.read_bytes()) != digest:
                    raise RuntimeError("HARD_RAW_SHA_MISMATCH")
                got = parse_racedetail_links(url, payload, ds)
                retrieved = utcnow()
                provenance.append({
                    "race_date": ds,
                    "source_url": url,
                    "final_url": r.url,
                    "retrieved_at_utc": retrieved,
                    "http_status": r.status_code,
                    "payload_sha256": digest,
                    "byte_length": len(payload),
                    "candidate_count": len(got),
                    "parser_version": PARSER_VERSION,
                    "acquisition_run_id": RUN_ID,
                    "post_access": False,
                    "result_access": False,
                    "payout_access": False,
                })
                for row in got:
                    old = candidates.get(row["race_id"])
                    if old is not None and old["race_date"] != row["race_date"]:
                        raise RuntimeError(
                            f"HARD_RACE_ID_DATE_CONFLICT: {row['race_id']} {old['race_date']} vs {row['race_date']}"
                        )
                    candidates.setdefault(row["race_id"], row)
            except RuntimeError as e:
                if str(e).startswith("HARD"):
                    raise
                quarantine.append({
                    "race_date": ds,
                    "source_url": url,
                    "status": "QUARANTINED",
                    "error": repr(e),
                })
            time.sleep(args.sleep)
        d += timedelta(days=1)

    ordered = sorted(candidates.values(), key=lambda r: (r["race_date"], r["venue_code"], r["race_id"]))
    for i, row in enumerate(ordered, 1):
        row["candidate_index"] = i

    candidate_csv = root / "FRESH_CANDIDATE_DISCOVERY.csv"
    write_csv(candidate_csv, ordered)

    (audit / "provenance.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in provenance),
        encoding="utf-8",
    )
    (audit / "quarantine.json").write_text(
        json.dumps(quarantine, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    date_counts = {}
    for row in ordered:
        date_counts[row["race_date"]] = date_counts.get(row["race_date"], 0) + 1

    enough = len(ordered) >= args.target
    first_1000 = ordered[: args.target] if enough else []
    report = {
        "status": "PASS_DISCOVERY_TARGET_REACHED" if enough else "PASS_DISCOVERY_TARGET_NOT_REACHED",
        "mode": "DISCOVERY_ONLY_NOT_UNIVERSE_FREEZE",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "horizon_days": args.horizon_days,
        "target": args.target,
        "unique_race_ids_discovered": len(ordered),
        "dates_with_candidates": len(date_counts),
        "candidate_date_counts": date_counts,
        "earliest_candidate_date": ordered[0]["race_date"] if ordered else None,
        "latest_candidate_date": ordered[-1]["race_date"] if ordered else None,
        "first_1000_last_date": first_1000[-1]["race_date"] if first_1000 else None,
        "candidate_csv_sha256": sha256_bytes(candidate_csv.read_bytes()),
        "fresh_result_accessed": False,
        "fresh_payout_accessed": False,
        "scoring_performed": False,
        "scientific_trial_added": 0,
        "holdout_accessed": False,
        "freeze_authorized": False,
        "next": (
            "If >=1000, independently audit prospectiveness/timestamps then build exact FRESH_ECON_VALID1000_v1. "
            "If <1000, do NOT guess race IDs; investigate a farther-ahead PRE-only schedule source or governance amendment."
        ),
    }
    (root / "DISCOVERY_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    files = [p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"]
    (root / "SHA256SUMS.txt").write_text(
        "\n".join(f"{sha256_bytes(p.read_bytes())}  {p.relative_to(root).as_posix()}" for p in sorted(files)) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    # Target-not-reached is a valid preflight observation, not a workflow failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
