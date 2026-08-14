from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

EXPECTED_UNIVERSE_SHA256 = "95754e7ac17cb91b12f619504d1be5e8a4ddc4f0e3734fa59671aea2e17eb043"
EXPECTED_PREDICTION_LOCK_SHA256 = "bbabe47f75ee809cda2a2e9124be364b2213bbf343a4508c1be85039ecb85ca0"
EXPECTED_RACE_COUNT = 100
TARGET_TYPES = ("exacta", "quinella", "trio")

INPUT_ROOT = Path(os.environ.get("RESULT_CAPTURE_DIR", "INPUT_RESULT/SIM100_RESULT_CAPTURE_ARTIFACT"))
OUT = Path("SIM100_SCORING_ARTIFACT")
STRUCT = OUT / "10_structured"
SCORE = OUT / "20_scoring"
AUDIT = OUT / "audit"
for d in (STRUCT, SCORE, AUDIT):
    d.mkdir(parents=True, exist_ok=True)


def hbytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hfile(path: Path) -> str:
    return hbytes(path.read_bytes())


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def immutable_csv(df: pd.DataFrame, path: Path) -> None:
    if path.exists():
        raise RuntimeError(f"immutable output already exists: {path}")
    tmp = Path(str(path) + ".tmp")
    df.to_csv(tmp, index=False, lineterminator="\n")
    os.replace(tmp, path)
    Path(str(path) + ".sha256").write_text(
        f"{hfile(path)}  {path.name}\n", encoding="utf-8"
    )


def verify_manifest(root: Path) -> None:
    manifest_path = root / "ARTIFACT_MANIFEST.sha256"
    if not manifest_path.exists():
        raise RuntimeError("capture artifact manifest missing")
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            expected, rel = line.split("  ", 1)
        except ValueError as exc:
            raise RuntimeError(f"invalid manifest line: {line}") from exc
        p = root / rel
        if not p.is_file():
            raise RuntimeError(f"manifest file missing: {rel}")
        observed = hfile(p)
        if observed != expected:
            raise RuntimeError(f"manifest SHA mismatch: {rel}")


def parse_payout_cell(cell, ticket_type: str):
    rows = []
    for dl in cell.find_all("dl"):
        dt, dd = dl.find("dt"), dl.find("dd")
        if not dt or not dd:
            continue
        combo_raw = norm(dt.get_text(" ", strip=True))
        if combo_raw == "未発売":
            continue
        money = re.search(r"([\d,]+)円", dd.get_text(" ", strip=True))
        if not money:
            continue
        payout = int(money.group(1).replace(",", ""))
        nums = [int(x) for x in re.findall(r"[1-9]", combo_raw)]
        if ticket_type == "exacta" and len(nums) == 2:
            combo = "-".join(map(str, nums))
        elif ticket_type == "quinella" and len(nums) == 2:
            combo = "-".join(map(str, sorted(nums)))
        elif ticket_type == "trio" and len(nums) == 3:
            combo = "-".join(map(str, sorted(nums)))
        else:
            continue
        rows.append(
            {
                "ticket_type": ticket_type,
                "combination": combo,
                "payout_per_100_yen": payout,
            }
        )
    return rows


def parse_result_and_payout(race_id: str, payload: bytes):
    soup = BeautifulSoup(payload, "lxml")

    result_table = soup.find("table", class_="result_table")
    if result_table is None:
        raise RuntimeError(f"{race_id}: result_table missing")

    result_rows = []
    for tr in result_table.find_all("tr")[1:]:
        cells = tr.find_all(["td", "th"], recursive=False)
        if len(cells) < 4:
            continue
        rank_raw = norm(cells[1].get_text(" ", strip=True))
        car_raw = norm(cells[2].get_text(" ", strip=True))
        m = re.search(r"([1-9])", car_raw)
        if not m:
            continue
        result_rows.append(
            {
                "race_id": race_id,
                "rank_raw": rank_raw,
                "car_no": int(m.group(1)),
                "rider_name": " ".join(cells[3].stripped_strings),
            }
        )
    if not 5 <= len(result_rows) <= 9:
        raise RuntimeError(f"{race_id}: invalid result row count {len(result_rows)}")

    refund = soup.find("table", class_="refund_table")
    if refund is None:
        raise RuntimeError(f"{race_id}: refund_table missing")
    trs = refund.find_all("tr", recursive=False)
    if len(trs) < 2:
        raise RuntimeError(f"{race_id}: refund_table row structure invalid")

    row0 = trs[0].find_all(["th", "td"], recursive=False)
    row1 = trs[1].find_all(["th", "td"], recursive=False)

    headers = [
        (norm(c.get_text(" ", strip=True)), i)
        for i, c in enumerate(row0)
        if c.name == "th"
    ]
    header_index = dict(headers)
    if "2車連" not in header_index or "3連勝" not in header_index:
        raise RuntimeError(f"{race_id}: target payout headers missing: {headers}")

    payout_rows = []
    payout_rows += parse_payout_cell(
        row0[header_index["2車連"] + 2], "quinella"
    )
    payout_rows += parse_payout_cell(
        row0[header_index["3連勝"] + 2], "trio"
    )

    ordered_groups = [
        h for h, _ in headers if h in ("2枠連", "2車連", "3連勝")
    ]
    group_index = ordered_groups.index("2車連")
    exacta_cell_index = 2 * group_index + 1
    if exacta_cell_index >= len(row1):
        raise RuntimeError(f"{race_id}: exacta payout cell missing")
    payout_rows += parse_payout_cell(row1[exacta_cell_index], "exacta")

    counts = {}
    for t in TARGET_TYPES:
        counts[t] = sum(x["ticket_type"] == t for x in payout_rows)
        if counts[t] < 1:
            raise RuntimeError(f"{race_id}: no official payout for {t}")

    for x in payout_rows:
        x["race_id"] = race_id

    return result_rows, payout_rows


# ---- Constitutional verification ----
if not INPUT_ROOT.is_dir():
    raise RuntimeError(f"RESULT capture artifact root missing: {INPUT_ROOT}")

verify_manifest(INPUT_ROOT)

races_path = INPUT_ROOT / "races.csv"
lock_path = INPUT_ROOT / "SIM100_PREDICTION_LOCK.csv"
report_path = INPUT_ROOT / "SIM100_RESULT_CAPTURE_REPORT.json"
prov_path = INPUT_ROOT / "audit" / "provenance.jsonl"

if hfile(races_path) != EXPECTED_UNIVERSE_SHA256:
    raise RuntimeError("frozen Universe SHA mismatch")
if hfile(lock_path) != EXPECTED_PREDICTION_LOCK_SHA256:
    raise RuntimeError("approved Prediction Lock SHA mismatch")

capture_report = json.loads(report_path.read_text(encoding="utf-8"))
required_capture_state = {
    "status": "PASS",
    "phase": "RESULT_PAYOUT_RAW_CAPTURE",
    "universe_count": 100,
    "successful_races": 100,
    "failed_races": 0,
    "replacement_races": 0,
    "result_access": True,
    "payout_access": True,
    "result_parsing_performed": False,
    "payout_parsing_performed": False,
    "scoring_performed": False,
}
for key, expected in required_capture_state.items():
    if capture_report.get(key) != expected:
        raise RuntimeError(
            f"capture report state mismatch {key}: "
            f"{capture_report.get(key)!r} != {expected!r}"
        )

races = list(csv.DictReader(races_path.read_text(encoding="utf-8").splitlines()))
race_ids = [r["race_id"] for r in races]
if len(race_ids) != EXPECTED_RACE_COUNT or len(set(race_ids)) != EXPECTED_RACE_COUNT:
    raise RuntimeError("frozen Universe must contain exactly 100 unique races")

provenance = [
    json.loads(line)
    for line in prov_path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]
if len(provenance) != EXPECTED_RACE_COUNT:
    raise RuntimeError(f"provenance count {len(provenance)} != 100")
prov_by_race = {x["race_id"]: x for x in provenance}
if set(prov_by_race) != set(race_ids):
    raise RuntimeError("provenance race_id set differs from frozen Universe")

result_rows, payout_rows = [], []
parse_audit = []

for i, rid in enumerate(race_ids, 1):
    print(f"[STRUCTURE RESULT/PAYOUT {i:03d}/100] {rid}", flush=True)
    p = prov_by_race[rid]
    raw_rel = Path(p["raw_blob_path"])
    try:
        rel_inside = raw_rel.relative_to("SIM100_RESULT_CAPTURE_ARTIFACT")
    except ValueError:
        rel_inside = raw_rel
    raw_path = INPUT_ROOT / rel_inside

    if not raw_path.is_file():
        raise RuntimeError(f"{rid}: raw payload missing: {raw_path}")
    if hfile(raw_path) != p["payload_sha256"]:
        raise RuntimeError(f"{rid}: raw payload SHA mismatch")

    rr, pp = parse_result_and_payout(rid, raw_path.read_bytes())
    result_rows.extend(rr)
    payout_rows.extend(pp)
    parse_audit.append(
        {
            "race_id": rid,
            "result_rows": len(rr),
            "payout_rows": len(pp),
            "raw_payload_sha256": p["payload_sha256"],
            "parser_version": "sim100-result-payout-parser-v1",
            "status": "PASS",
        }
    )

results = pd.DataFrame(result_rows)
payouts = pd.DataFrame(payout_rows)

if results["race_id"].nunique() != EXPECTED_RACE_COUNT:
    raise RuntimeError("RESULT_TABLE does not cover exactly 100 races")
if payouts["race_id"].nunique() != EXPECTED_RACE_COUNT:
    raise RuntimeError("PAYOUT_TABLE does not cover exactly 100 races")

coverage = payouts.groupby(["race_id", "ticket_type"]).size().unstack(fill_value=0)
for t in TARGET_TYPES:
    if t not in coverage.columns or (coverage[t] < 1).any():
        raise RuntimeError(f"PAYOUT_TABLE lacks complete {t} coverage")

immutable_csv(results, STRUCT / "RESULT_TABLE.csv")
immutable_csv(payouts, STRUCT / "PAYOUT_TABLE.csv")
(AUDIT / "parse_audit.json").write_text(
    json.dumps(parse_audit, ensure_ascii=False, indent=2), encoding="utf-8"
)

# ---- Fixed Prediction Lock scoring; no recalculation permitted ----
pred = pd.read_csv(lock_path, dtype={"combination": str})
required_cols = {
    "race_id", "ticket_type", "combination", "probability", "fair_odds",
    "required_odds", "market_odds", "ev", "value_score", "gate_result",
    "virtual_stake", "price_type", "price_timestamp"
}
if set(pred.columns) != required_cols:
    raise RuntimeError(
        f"Prediction Lock schema changed: {sorted(set(pred.columns) ^ required_cols)}"
    )
if pred["race_id"].nunique() != EXPECTED_RACE_COUNT:
    raise RuntimeError("Prediction Lock does not cover exactly 100 races")
if set(pred["race_id"]) != set(race_ids):
    raise RuntimeError("Prediction Lock race set differs from frozen Universe")
if not set(pred["ticket_type"]).issubset(set(TARGET_TYPES)):
    raise RuntimeError("Prediction Lock contains unsupported ticket types")

bad_gate = pred[
    ((pred["gate_result"] == "BET") & (pred["virtual_stake"] <= 0))
    | ((pred["gate_result"] == "NO_BET") & (pred["virtual_stake"] != 0))
    | (~pred["gate_result"].isin(["BET", "NO_BET"]))
]
if not bad_gate.empty:
    raise RuntimeError("Prediction Lock gate/stake integrity violation")

payout_lookup = {}
for x in payouts.itertuples(index=False):
    key = (str(x.race_id), str(x.ticket_type), str(x.combination))
    if key in payout_lookup:
        raise RuntimeError(f"duplicate official payout key: {key}")
    payout_lookup[key] = int(x.payout_per_100_yen)

score = pred.copy()
official_payout = []
event_hit = []
actual_return = []
actual_profit = []

for x in score.itertuples(index=False):
    key = (str(x.race_id), str(x.ticket_type), str(x.combination))
    payout = payout_lookup.get(key, 0)
    hit = payout > 0
    stake = float(x.virtual_stake)
    ret = payout * (stake / 100.0) if x.gate_result == "BET" and hit else 0.0
    profit = ret - stake
    official_payout.append(payout)
    event_hit.append(hit)
    actual_return.append(ret)
    actual_profit.append(profit)

score["official_payout_per_100_yen"] = official_payout
score["event_hit"] = event_hit
score["actual_return_yen"] = actual_return
score["actual_profit_yen"] = actual_profit

immutable_csv(score, SCORE / "SCORING_TABLE.csv")

bets = score[score["gate_result"] == "BET"].copy()
total_stake = float(bets["virtual_stake"].sum())
total_return = float(bets["actual_return_yen"].sum())
total_profit = total_return - total_stake

ticket_summary = {}
for t in TARGET_TYPES:
    b = bets[bets["ticket_type"] == t]
    stake = float(b["virtual_stake"].sum())
    ret = float(b["actual_return_yen"].sum())
    ticket_summary[t] = {
        "bet_lines": int(len(b)),
        "hit_lines": int(b["event_hit"].sum()),
        "hit_rate_percent": (float(b["event_hit"].mean()) * 100.0 if len(b) else None),
        "stake_yen": stake,
        "return_yen": ret,
        "profit_yen": ret - stake,
        "return_rate_percent": (ret / stake * 100.0 if stake else None),
        "net_roi_percent": ((ret - stake) / stake * 100.0 if stake else None),
    }

race_financial = (
    bets.groupby("race_id", as_index=False)
    .agg(
        stake_yen=("virtual_stake", "sum"),
        return_yen=("actual_return_yen", "sum"),
        hit_lines=("event_hit", "sum"),
        bet_lines=("event_hit", "size"),
    )
)
race_financial["profit_yen"] = race_financial["return_yen"] - race_financial["stake_yen"]
immutable_csv(race_financial, SCORE / "RACE_FINANCIAL_SUMMARY.csv")

final_report = {
    "status": "PASS",
    "phase": "SIM100_SCORING_COMPLETE",
    "universe_sha256": EXPECTED_UNIVERSE_SHA256,
    "prediction_lock_sha256": EXPECTED_PREDICTION_LOCK_SHA256,
    "race_count": EXPECTED_RACE_COUNT,
    "prediction_rows": int(len(score)),
    "bet_lines": int(len(bets)),
    "no_bet_lines": int((score["gate_result"] == "NO_BET").sum()),
    "bet_races": int(bets["race_id"].nunique()),
    "winning_bet_lines": int(bets["event_hit"].sum()),
    "bet_line_hit_rate_percent": float(bets["event_hit"].mean() * 100.0),
    "total_stake_yen": total_stake,
    "total_return_yen": total_return,
    "total_profit_yen": total_profit,
    "return_rate_percent": (total_return / total_stake * 100.0 if total_stake else None),
    "net_roi_percent": (total_profit / total_stake * 100.0 if total_stake else None),
    "profitable_races": int((race_financial["profit_yen"] > 0).sum()),
    "losing_races": int((race_financial["profit_yen"] < 0).sum()),
    "flat_races": int((race_financial["profit_yen"] == 0).sum()),
    "ticket_summary": ticket_summary,
    "result_parsing_performed": True,
    "payout_parsing_performed": True,
    "scoring_performed": True,
    "prediction_recalculated": False,
    "prediction_lock_modified": False,
    "price_quality": "B_CLOSING_PRICE",
    "evaluation_note": (
        "This is a historical scoring of the frozen Prediction Lock using official "
        "payouts. The lock used B_CLOSING_PRICE; treat this as backtest evidence, "
        "not proof of live pre-bet executability."
    ),
}

report_path = SCORE / "SIM100_FINAL_REPORT.json"
report_path.write_text(
    json.dumps(final_report, ensure_ascii=False, indent=2), encoding="utf-8"
)

# Hash every core output after it is final.
core_hashes = {
    "result_table_sha256": hfile(STRUCT / "RESULT_TABLE.csv"),
    "payout_table_sha256": hfile(STRUCT / "PAYOUT_TABLE.csv"),
    "scoring_table_sha256": hfile(SCORE / "SCORING_TABLE.csv"),
    "race_financial_summary_sha256": hfile(SCORE / "RACE_FINANCIAL_SUMMARY.csv"),
    "final_report_sha256": hfile(report_path),
}
(AUDIT / "CORE_OUTPUT_SHA256.json").write_text(
    json.dumps(core_hashes, ensure_ascii=False, indent=2), encoding="utf-8"
)

print(json.dumps(final_report, ensure_ascii=False, indent=2))
print(json.dumps(core_hashes, ensure_ascii=False, indent=2))

manifest = []
for p in sorted(
    x for x in OUT.rglob("*")
    if x.is_file() and x.name != "ARTIFACT_MANIFEST.sha256"
):
    manifest.append(f"{hfile(p)}  {p.relative_to(OUT).as_posix()}")
(OUT / "ARTIFACT_MANIFEST.sha256").write_text(
    "\n".join(manifest) + "\n", encoding="utf-8"
)
