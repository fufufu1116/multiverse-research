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
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

POST_TERMS = (
    "result", "payout", "harai", "払戻", "配当", "結果", "着順", "確定",
    "raceresult", "harailist",
)
RID_RE = re.compile(r"/racedetail/(\d{16})/")
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
PARSER_VERSION = "v3-fresh-universe-discovery-preflight-v2"
JST = ZoneInfo("Asia/Tokyo")


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


def fetch(session: requests.Session, url: str, *, retries: int = 3, timeout: int = 30):
    reject_post(url)
    last = None
    for attempt in range(retries + 1):
        try:
            r = session.get(url, timeout=timeout, allow_redirects=True)
            reject_post(r.url)
            if r.status_code == 200 and r.content:
                return r
            if r.status_code in {404, 408, 429, 500, 502, 503, 504}:
                last = RuntimeError(f"RECOVERABLE_HTTP_{r.status_code}")
            else:
                raise RuntimeError(f"HARD_HTTP_{r.status_code}")
        except (requests.Timeout, requests.ConnectionError) as e:
            last = RuntimeError(f"RECOVERABLE_NETWORK: {e!r}")
        if attempt < retries:
            time.sleep(min(16.0, float(2 ** attempt)))
    raise last or RuntimeError("RECOVERABLE_UNKNOWN")


def race_id_identity(rid: str) -> dict:
    if len(rid) != 16 or not rid.isdigit():
        raise ValueError(f"invalid 16-digit race_id: {rid}")
    venue_code = rid[:2]
    start = date(int(rid[2:6]), int(rid[6:8]), int(rid[8:10]))
    day_no = int(rid[10:12])
    race_no = int(rid[12:16])
    if day_no < 1:
        raise ValueError(f"invalid meeting day number: {day_no}")
    if race_no < 1:
        raise ValueError(f"invalid race number: {race_no}")
    actual = start + timedelta(days=day_no - 1)
    return {
        "venue_code": venue_code,
        "event_start_date": start.isoformat(),
        "meeting_day_no": day_no,
        "race_no": race_no,
        "derived_actual_race_date": actual.isoformat(),
    }


def parse_racedetail_links(index_url: str, payload: bytes, scan_date: str, run_jst_date: date):
    soup = BeautifulSoup(payload, "lxml")
    found = {}
    rejected = []
    for a in soup.find_all("a", href=True):
        full = urljoin(index_url, a["href"])
        m = RID_RE.search(full)
        if not m:
            continue
        reject_post(full)
        rid = m.group(1)
        try:
            ident = race_id_identity(rid)
        except Exception as e:
            rejected.append({
                "race_id": rid,
                "source_url": index_url,
                "reason": "INVALID_RACE_ID_IDENTITY",
                "error": repr(e),
            })
            continue
        if ident["derived_actual_race_date"] != scan_date:
            rejected.append({
                "race_id": rid,
                "source_url": index_url,
                "reason": "RACE_ID_DERIVED_DATE_MISMATCH",
                "scan_date": scan_date,
                "derived_actual_race_date": ident["derived_actual_race_date"],
            })
            continue
        if date.fromisoformat(ident["derived_actual_race_date"]) <= run_jst_date:
            rejected.append({
                "race_id": rid,
                "source_url": index_url,
                "reason": "NOT_STRICTLY_PROSPECTIVE_AT_RUN_TIME",
                "run_jst_date": run_jst_date.isoformat(),
                "derived_actual_race_date": ident["derived_actual_race_date"],
            })
            continue
        found[rid] = {
            "race_id": rid,
            "race_date": scan_date,
            "venue_code": ident["venue_code"],
            "event_start_date": ident["event_start_date"],
            "meeting_day_no": ident["meeting_day_no"],
            "race_no": ident["race_no"],
            "race_id_derived_date": ident["derived_actual_race_date"],
            "url": full,
            "discovery_source": index_url,
            "data_status": "DISCOVERED_STRICTLY_PROSPECTIVE_CANDIDATE",
        }
    return list(found.values()), rejected


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = [
        "candidate_index", "race_id", "race_date", "venue_code", "event_start_date",
        "meeting_day_no", "race_no", "race_id_derived_date", "url", "discovery_source", "data_status",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def load_holdout_guard(path: Path) -> dict:
    x = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "source_universe_sha256", "race_count", "unique_race_ids", "min_race_date",
        "max_race_date", "sorted_race_id_set_sha256",
    }
    if not required.issubset(x):
        raise RuntimeError(f"FAIL-CLOSED: HOLDOUT membership guard missing keys {required - set(x)}")
    if int(x["race_count"]) != 1000 or int(x["unique_race_ids"]) != 1000:
        raise RuntimeError("FAIL-CLOSED: HOLDOUT membership guard cardinality")
    return x


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="YYYY-MM-DD; strictly future JST scan start")
    ap.add_argument("--horizon-days", type=int, default=45)
    ap.add_argument("--target", type=int, default=1000)
    ap.add_argument("--out", default="V3_FRESH_UNIVERSE_DISCOVERY")
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--holdout-guard", default="v3/holdout_membership_guard_v1.json")
    args = ap.parse_args()

    if args.horizon_days < 1 or args.horizon_days > 90:
        raise SystemExit("FAIL-CLOSED: horizon-days must be 1..90")
    if args.target != 1000:
        raise SystemExit("FAIL-CLOSED: frozen v3 target must remain exactly 1000")
    if args.sleep < 1.0:
        raise SystemExit("FAIL-CLOSED: request interval must be >=1.0 second")

    run_jst_date = datetime.now(JST).date()
    start = date.fromisoformat(args.start)
    if start <= run_jst_date:
        raise SystemExit(
            f"FAIL-CLOSED: prospective start must be strictly later than run JST date {run_jst_date.isoformat()}"
        )
    end = start + timedelta(days=args.horizon_days - 1)

    holdout_guard_path = Path(args.holdout_guard)
    holdout_guard = load_holdout_guard(holdout_guard_path)
    holdout_max_date = date.fromisoformat(holdout_guard["max_race_date"])
    if start <= holdout_max_date:
        raise SystemExit("FAIL-CLOSED: fresh prospective start is not temporally disjoint from HOLDOUT membership")

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
                got, link_rejects = parse_racedetail_links(url, payload, ds, run_jst_date)
                quarantine.extend(link_rejects)
                retrieved = utcnow()
                provenance.append({
                    "race_date": ds,
                    "source_url": url,
                    "final_url": r.url,
                    "retrieved_at_utc": retrieved,
                    "run_jst_date": run_jst_date.isoformat(),
                    "http_status": r.status_code,
                    "payload_sha256": digest,
                    "byte_length": len(payload),
                    "accepted_candidate_count": len(got),
                    "rejected_link_count": len(link_rejects),
                    "parser_version": PARSER_VERSION,
                    "acquisition_run_id": RUN_ID,
                    "post_access": False,
                    "result_access": False,
                    "payout_access": False,
                })
                for row in got:
                    if date.fromisoformat(row["race_id_derived_date"]) <= holdout_max_date:
                        raise RuntimeError(f"HARD_HOLDOUT_TEMPORAL_GUARD_BREACH: {row['race_id']}")
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
    first_1000_sha = None
    if enough:
        first_path = root / "FRESH_FIRST1000_CANDIDATE.csv"
        write_csv(first_path, first_1000)
        first_1000_sha = sha256_bytes(first_path.read_bytes())

    report = {
        "status": "PASS_DISCOVERY_TARGET_REACHED" if enough else "INSUFFICIENT_FUTURE_PUBLICATION",
        "mode": "DISCOVERY_ONLY_NOT_UNIVERSE_FREEZE",
        "run_jst_date": run_jst_date.isoformat(),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "horizon_days": args.horizon_days,
        "request_interval_seconds": args.sleep,
        "max_concurrency": 1,
        "target": args.target,
        "unique_race_ids_discovered": len(ordered),
        "dates_with_candidates": len(date_counts),
        "candidate_date_counts": date_counts,
        "earliest_candidate_date": ordered[0]["race_date"] if ordered else None,
        "latest_candidate_date": ordered[-1]["race_date"] if ordered else None,
        "first_1000_last_date": first_1000[-1]["race_date"] if first_1000 else None,
        "candidate_csv_sha256": sha256_bytes(candidate_csv.read_bytes()),
        "first_1000_candidate_sha256": first_1000_sha,
        "race_id_date_identity_required": True,
        "all_accepted_candidates_strictly_future_at_run": all(
            date.fromisoformat(r["race_date"]) > run_jst_date for r in ordered
        ),
        "holdout_membership_temporal_guard": {
            "guard_file": str(holdout_guard_path),
            "guard_file_sha256": sha256_bytes(holdout_guard_path.read_bytes()),
            "membership_count": holdout_guard["race_count"],
            "membership_set_sha256": holdout_guard["sorted_race_id_set_sha256"],
            "holdout_max_race_date": holdout_guard["max_race_date"],
            "fresh_dates_strictly_after_holdout": all(
                date.fromisoformat(r["race_date"]) > holdout_max_date for r in ordered
            ),
            "price_accessed": False,
            "payout_accessed": False,
            "result_accessed": False,
        },
        "fresh_result_accessed": False,
        "fresh_payout_accessed": False,
        "scoring_performed": False,
        "scientific_trial_added": 0,
        "holdout_price_payout_result_accessed": False,
        "freeze_authorized": False,
        "next": (
            "If >=1000, independently audit prospectiveness, race_id-derived dates, provenance and temporal membership guard, "
            "then build exact FRESH_ECON_VALID1000_v1. If <1000, do NOT guess race IDs and do NOT partially freeze."
        ),
    }
    (root / "DISCOVERY_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    files = [p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"]
    (root / "SHA256SUMS.txt").write_text(
        "\n".join(f"{sha256_bytes(p.read_bytes())}  {p.relative_to(root).as_posix()}" for p in sorted(files)) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
