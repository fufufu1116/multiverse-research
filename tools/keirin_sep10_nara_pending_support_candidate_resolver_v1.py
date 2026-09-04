#!/usr/bin/env python3
"""Research-only Sep10 Nara pending support candidate resolver v1.

Consumes the frozen prospective PRE rows emitted by the Sep10 precapture
orchestrator and the already-frozen 19 scheduled cross-circumference candidates.
It performs only an exact final-PRE membership intersection and emits arguments
for the existing KEIRIN.JP same-race assignment probe.

This tool never authorizes support by itself. A survivor remains pending until
the official same-race assignment probe passes before the frozen PIT cutoff.
No RESULT, payout, odds, forecast, or post-race reconstruction is used.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import re
import subprocess
import tempfile
import unicodedata
from datetime import datetime, timezone

TAKEO = pathlib.Path("v3/historical_all_market/research_candidates/KEIRIN_RIDER_CIRCUMFERENCE_CROSS_BLOCK_SUPPORT_PRECHECK_20260903_v2.json")
TAKEO_BLOB = "92eca8622818d314b68b7ab6f8b9596dbbf28e62"
KAWASAKI = pathlib.Path("v3/historical_all_market/research_candidates/KEIRIN_NARA_SEP10_ASSEN_KAWASAKI_PENDING_OVERLAP_PRECHECK_20260904_v2.json")
KAWASAKI_BLOB = "fb8d75b5ad9cf54283a6efbeb1fbac603227e8bb"

EXPECTED_EVENT = {
    "race_date": "2026-09-10",
    "venue": "奈良",
    "circumference_m": 333.33,
    "day": "Day1",
}
EXPECTED_REGISTRY_SIZE = 19
EVIDENCE_ROLE = "PROSPECTIVE_PRE_SUPPORT_CANDIDATE_ONLY"

PREFS = sorted([
    "北海道","青森","岩手","宮城","秋田","山形","福島","茨城","栃木","群馬","埼玉","千葉","東京","神奈川",
    "新潟","富山","石川","福井","山梨","長野","岐阜","静岡","愛知","三重","滋賀","京都","大阪","兵庫",
    "奈良","和歌山","鳥取","島根","岡山","広島","山口","徳島","香川","愛媛","高知","福岡","佐賀","長崎",
    "熊本","大分","宮崎","鹿児島","沖縄"
], key=len, reverse=True)

REQUIRED_PRE_FIELDS = {
    "race_id","race_date","venue","race_no","car_no","rider_name_raw",
    "source_url","source_file_sha256","evidence_role"
}
FORBIDDEN_FIELDS = {
    "result","results","finish","finish_1","finish_2","finish_3","payout","payouts",
    "odds","forecast","prediction","tips","human_mark","human_marks","narabiyoso","settlement"
}


def git_blob(path: pathlib.Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], text=True).strip()


def norm_name(value: str) -> str:
    s = unicodedata.normalize("NFKC", str(value))
    return "".join(ch for ch in s if not ch.isspace())


def validate_reg(value: str) -> str:
    s = str(value).strip()
    if not re.fullmatch(r"\d{6}", s):
        raise ValueError(f"FAIL_CLOSED_REGISTRATION_NUMBER_{s!r}")
    return s


def load_registry() -> tuple[list[dict], dict]:
    blobs = {"takeo": git_blob(TAKEO), "kawasaki": git_blob(KAWASAKI)}
    if blobs["takeo"] != TAKEO_BLOB:
        raise ValueError(f"FAIL_CLOSED_TAKEO_PRECHECK_BLOB_{blobs['takeo']}")
    if blobs["kawasaki"] != KAWASAKI_BLOB:
        raise ValueError(f"FAIL_CLOSED_KAWASAKI_PRECHECK_BLOB_{blobs['kawasaki']}")

    takeo = json.loads(TAKEO.read_text(encoding="utf-8"))
    kawa = json.loads(KAWASAKI.read_text(encoding="utf-8"))

    rows: list[dict] = []
    for x in takeo.get("intersection", {}).get("scheduled_overlap", []):
        rows.append({
            "rider_name": str(x["rider_name"]),
            "rider_name_normalized": norm_name(x["rider_name"]),
            "official_registration_number": validate_reg(x["official_registration_number"]),
            "term": int(x["period"]),
            "historical_sources": [{
                "venue": "武雄",
                "race_date": "2026-09-03",
                "circumference_m": 400.0,
                "race_no": int(x["takeo_race_no"]),
                "car_no": int(x["takeo_car_no"]),
                "source_artifact": TAKEO.name,
            }],
        })

    for x in kawa.get("kawasaki_to_nara_scheduled_overlap", []):
        rows.append({
            "rider_name": str(x["rider_name"]),
            "rider_name_normalized": norm_name(x["rider_name"]),
            "official_registration_number": validate_reg(x["official_registration_number_from_kawasaki_identity"]),
            "term": None,
            "historical_sources": [{
                "venue": "川崎",
                "race_date": str(x["kawasaki_race_date"]),
                "circumference_m": float(x["kawasaki_circumference_m"]),
                "race_no": int(x["kawasaki_race_no"]),
                "car_no": int(x["kawasaki_car_no"]),
                "source_artifact": KAWASAKI.name,
            }],
        })

    by_reg: dict[str, dict] = {}
    by_name: dict[str, str] = {}
    for r in rows:
        reg = r["official_registration_number"]
        name = r["rider_name_normalized"]
        prior_reg = by_name.get(name)
        if prior_reg is not None and prior_reg != reg:
            raise ValueError(f"FAIL_CLOSED_SCHEDULED_NAME_TO_MULTI_REG_{name}")
        by_name[name] = reg
        if reg in by_reg:
            prior = by_reg[reg]
            if prior["rider_name_normalized"] != name:
                raise ValueError(f"FAIL_CLOSED_REG_TO_MULTI_NAME_{reg}")
            if prior["term"] is not None and r["term"] is not None and prior["term"] != r["term"]:
                raise ValueError(f"FAIL_CLOSED_REG_TERM_CONTRADICTION_{reg}")
            if prior["term"] is None:
                prior["term"] = r["term"]
            prior["historical_sources"].extend(r["historical_sources"])
        else:
            by_reg[reg] = r

    registry = sorted(by_reg.values(), key=lambda x: x["official_registration_number"])
    if len(registry) != EXPECTED_REGISTRY_SIZE:
        raise ValueError(f"FAIL_CLOSED_PENDING_REGISTRY_SIZE_{len(registry)}")
    if len({x["rider_name_normalized"] for x in registry}) != EXPECTED_REGISTRY_SIZE:
        raise ValueError("FAIL_CLOSED_PENDING_REGISTRY_NAME_UNIQUENESS")
    return registry, blobs


def parse_pre_identity(raw: str) -> dict:
    m = re.fullmatch(r"(.+)/(\d+)/(\d+)", str(raw).strip())
    if not m:
        return {"status": "FAIL_CLOSED_PRE_IDENTITY_FORMAT"}
    head = norm_name(m.group(1))
    age = int(m.group(2))
    term = int(m.group(3))
    if head.endswith("外国") and term == 999:
        return {
            "status": "FOREIGN_INVITEE_UNSUPPORTED_NO_JKA_REG_ASSUMPTION",
            "name": head[:-2],
            "prefecture": "外国",
            "age": age,
            "term": term,
        }
    hits = [p for p in PREFS if head.endswith(p) and len(head) > len(p)]
    if len(hits) != 1:
        return {
            "status": f"FAIL_CLOSED_PRE_PREFECTURE_SUFFIX_CARDINALITY_{len(hits)}",
            "age": age,
            "term": term,
        }
    pref = hits[0]
    name = head[:-len(pref)]
    if not name:
        return {"status": "FAIL_CLOSED_PRE_EMPTY_NAME", "age": age, "term": term}
    return {
        "status": "READY_DOMESTIC_EXACT_NAME_INTERSECTION",
        "name": name,
        "prefecture": pref,
        "age": age,
        "term": term,
    }


def parse_utc(value: str) -> datetime:
    d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("FAIL_CLOSED_CUTOFF_TZ_REQUIRED")
    return d.astimezone(timezone.utc)


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_precapture_receipt(receipt: dict, pre_csv: pathlib.Path, expected_event: dict) -> datetime:
    if receipt.get("status") != "WHOLE_DAY_DAY1_PRE_CAPTURE_CHAIN_COMPLETED_READY_FOR_IDENTITY_ONLY":
        raise ValueError("FAIL_CLOSED_PRECAPTURE_STATUS")
    ev = receipt.get("event") or {}
    for key in ("race_date", "venue", "day"):
        if ev.get(key) != expected_event[key]:
            raise ValueError(f"FAIL_CLOSED_PRECAPTURE_EVENT_{key}")
    if abs(float(ev.get("circumference_m")) - float(expected_event["circumference_m"])) > 1e-9:
        raise ValueError("FAIL_CLOSED_PRECAPTURE_EVENT_CIRCUMFERENCE")
    if receipt.get("result_accessed") is not False or receipt.get("payout_accessed") is not False or receipt.get("odds_accessed") is not False:
        raise ValueError("FAIL_CLOSED_PRECAPTURE_FORBIDDEN_SOURCE_FLAG")
    if receipt.get("support_increment_authorized_now") not in (0, False):
        raise ValueError("FAIL_CLOSED_PRECAPTURE_SUPPORT_AUTHORITY")
    expected_sha = (receipt.get("output_sha256") or {}).get("pre_rows_csv")
    if not expected_sha or expected_sha != sha256_file(pre_csv):
        raise ValueError("FAIL_CLOSED_PRE_ROWS_SHA_MISMATCH")
    return parse_utc(receipt.get("first_race_pit_cutoff_utc"))


def read_pre_rows(pre_csv: pathlib.Path, expected_event: dict) -> list[dict]:
    with pre_csv.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        bad = sorted({x.lower() for x in fields} & FORBIDDEN_FIELDS)
        if bad:
            raise ValueError("FAIL_CLOSED_FORBIDDEN_PRE_FIELDS_" + ",".join(bad))
        missing = sorted(REQUIRED_PRE_FIELDS - fields)
        if missing:
            raise ValueError("FAIL_CLOSED_MISSING_PRE_FIELDS_" + ",".join(missing))
        rows = list(reader)
    if not rows:
        raise ValueError("FAIL_CLOSED_EMPTY_PRE_ROWS")

    keys = set()
    for r in rows:
        if r["race_date"] != expected_event["race_date"] or r["venue"] != expected_event["venue"]:
            raise ValueError("FAIL_CLOSED_PRE_EVENT_BINDING")
        if r["evidence_role"] != EVIDENCE_ROLE:
            raise ValueError("FAIL_CLOSED_PRE_EVIDENCE_ROLE")
        key = (int(r["race_no"]), int(r["car_no"]))
        if key in keys:
            raise ValueError("FAIL_CLOSED_DUPLICATE_RACE_CAR")
        keys.add(key)
        u = str(r["source_url"])
        if "?pageType=result" in u or "/raceresult/" in u or "/result/" in u:
            raise ValueError("FAIL_CLOSED_RESULT_LIKE_SOURCE_URL")
    return rows


def resolve(
    pre_csv: pathlib.Path,
    precapture_receipt_json: pathlib.Path,
    expected_event: dict | None = None,
    now_utc: datetime | None = None,
) -> dict:
    expected_event = dict(expected_event or EXPECTED_EVENT)
    registry, blobs = load_registry()
    receipt = json.loads(precapture_receipt_json.read_text(encoding="utf-8"))
    cutoff = validate_precapture_receipt(receipt, pre_csv, expected_event)
    now = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if now >= cutoff:
        raise ValueError("FAIL_CLOSED_RESOLVER_AT_OR_AFTER_PIT_CUTOFF")

    rows = read_pre_rows(pre_csv, expected_event)
    parsed_rows: list[dict] = []
    by_name: dict[str, list[dict]] = {}
    unsupported_rows = 0
    for r in rows:
        p = parse_pre_identity(r["rider_name_raw"])
        item = {
            "race_id": r["race_id"],
            "race_no": int(r["race_no"]),
            "car_no": int(r["car_no"]),
            "rider_name_raw": r["rider_name_raw"],
            "source_url": r["source_url"],
            "source_file_sha256": r["source_file_sha256"],
            **p,
        }
        parsed_rows.append(item)
        if p["status"] == "READY_DOMESTIC_EXACT_NAME_INTERSECTION":
            by_name.setdefault(p["name"], []).append(item)
        else:
            unsupported_rows += 1

    decisions: list[dict] = []
    survivors: list[dict] = []
    for c in registry:
        matches = by_name.get(c["rider_name_normalized"], [])
        base = {
            "rider_name": c["rider_name"],
            "rider_name_normalized": c["rider_name_normalized"],
            "official_registration_number": c["official_registration_number"],
            "scheduled_term_if_available": c["term"],
            "historical_sources": c["historical_sources"],
        }
        if len(matches) == 0:
            decisions.append({**base, "status": "NOT_ON_FINAL_PRE_CARD_NO_SUPPORT"})
            continue
        if len(matches) > 1:
            decisions.append({**base, "status": "FAIL_CLOSED_MULTIPLE_FINAL_PRE_NAME_MATCHES", "match_count": len(matches)})
            continue

        m = matches[0]
        if c["term"] is not None and int(c["term"]) != int(m["term"]):
            decisions.append({
                **base,
                "status": "FAIL_CLOSED_TERM_CONTRADICTION_NO_SUPPORT",
                "final_pre_term": int(m["term"]),
                "race_no": m["race_no"],
                "car_no": m["car_no"],
            })
            continue

        survivor = {
            **base,
            "status": "FINAL_PRE_PRESENT_READY_FOR_OFFICIAL_SAME_RACE_ASSIGNMENT",
            "final_pre": {
                "race_no": m["race_no"],
                "car_no": m["car_no"],
                "prefecture": m["prefecture"],
                "term": int(m["term"]),
                "race_id": m["race_id"],
                "source_url": m["source_url"],
                "source_file_sha256": m["source_file_sha256"],
            },
            "same_race_assignment_probe_args": {
                "registration-number": c["official_registration_number"],
                "name": c["rider_name"],
                "prefecture": m["prefecture"],
                "term": str(int(m["term"])),
                "venue": expected_event["venue"],
                "race-date": expected_event["race_date"],
                "race-no": str(m["race_no"]),
                "circumference-m": str(expected_event["circumference_m"]),
                "day": expected_event["day"],
                "pit-cutoff-utc": cutoff.isoformat(),
            },
            "support_increment_authorized_now": 0,
        }
        decisions.append(survivor)
        survivors.append(survivor)

    candidate_names = {x["rider_name_normalized"] for x in registry}
    final_pre_candidate_name_hits = {
        name for name in by_name if name in candidate_names
    }
    out = {
        "record": "KEIRIN_SEP10_NARA_PENDING_SUPPORT_CANDIDATE_RESOLVER_v1",
        "status": "FINAL_PRE_PENDING_CANDIDATE_INTERSECTION_RESOLVED_ASSIGNMENT_PROBES_REQUIRED",
        "generated_utc": now.isoformat(),
        "event": expected_event,
        "pit_cutoff_utc": cutoff.isoformat(),
        "resolver_before_pit_cutoff": now < cutoff,
        "registry_sources": {
            "takeo_precheck": str(TAKEO),
            "takeo_git_blob": blobs["takeo"],
            "kawasaki_precheck": str(KAWASAKI),
            "kawasaki_git_blob": blobs["kawasaki"],
        },
        "pending_registry_unique_riders": len(registry),
        "final_pre_rows": len(rows),
        "unsupported_or_unparseable_pre_rows": unsupported_rows,
        "exact_candidate_name_hits_on_final_pre": len(final_pre_candidate_name_hits),
        "survivor_count_ready_for_official_assignment": len(survivors),
        "decisions": decisions,
        "survivors": survivors,
        "support_increment_authorized_now": 0,
        "support_receipt_authorized_now": False,
        "next_gate": "RUN_EXISTING_KEIRINJP_SAME_RACE_ASSIGNMENT_PROBE_FOR_EACH_SURVIVOR_BEFORE_PIT_CUTOFF; ONLY COMPLETE PASSES MAY ENTER_SUPPORT_RECEIPT_ACCOUNTING",
        "result_accessed": False,
        "payout_accessed": False,
        "odds_accessed": False,
        "human_forecast_accessed": False,
        "raw_html_persisted": False,
        "race_id_guessed": False,
        "result_join_authorized": False,
        "formula_fit_authorized": False,
        "main_or_runtime_mutation": False,
    }
    return out


def selftest() -> dict:
    registry, blobs = load_registry()
    a, b = registry[0], registry[1]
    with tempfile.TemporaryDirectory() as td:
        d = pathlib.Path(td)
        pre = d / "PRE_ROWS.csv"
        receipt = d / "ORCHESTRATOR.json"
        fields = [
            "race_id","race_date","venue","race_no","car_no","rider_name_raw","class","style",
            "competition_score","S","B","nige","makuri","sashi","mark","source_url",
            "source_file_sha256","evidence_role"
        ]
        rows = [
            {
                "race_id":"synthetic1","race_date":"2098-12-31","venue":"奈良","race_no":"1","car_no":"1",
                "rider_name_raw":f"{a['rider_name']} 奈 良/30/{a['term'] or 99}","class":"S1","style":"両",
                "competition_score":"100","S":"0","B":"0","nige":"0","makuri":"0","sashi":"0","mark":"0",
                "source_url":"https://keirin.kdreams.jp/nara/racedetail/1001/","source_file_sha256":"a"*64,
                "evidence_role":EVIDENCE_ROLE,
            },
            {
                "race_id":"synthetic1","race_date":"2098-12-31","venue":"奈良","race_no":"1","car_no":"2",
                "rider_name_raw":f"{b['rider_name']} 奈 良/30/{(b['term'] or 99)+1}","class":"S1","style":"両",
                "competition_score":"100","S":"0","B":"0","nige":"0","makuri":"0","sashi":"0","mark":"0",
                "source_url":"https://keirin.kdreams.jp/nara/racedetail/1001/","source_file_sha256":"a"*64,
                "evidence_role":EVIDENCE_ROLE,
            },
            {
                "race_id":"synthetic1","race_date":"2098-12-31","venue":"奈良","race_no":"1","car_no":"3",
                "rider_name_raw":"架空 太郎 奈 良/30/99","class":"S1","style":"両",
                "competition_score":"100","S":"0","B":"0","nige":"0","makuri":"0","sashi":"0","mark":"0",
                "source_url":"https://keirin.kdreams.jp/nara/racedetail/1001/","source_file_sha256":"a"*64,
                "evidence_role":EVIDENCE_ROLE,
            },
        ]
        with pre.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

        synthetic_event = {
            "race_date":"2098-12-31","venue":"奈良","circumference_m":333.33,"day":"Day1"
        }
        rec = {
            "status":"WHOLE_DAY_DAY1_PRE_CAPTURE_CHAIN_COMPLETED_READY_FOR_IDENTITY_ONLY",
            "event":synthetic_event,
            "first_race_pit_cutoff_utc":"2099-01-01T00:00:00+00:00",
            "output_sha256":{"pre_rows_csv":sha256_file(pre)},
            "result_accessed":False,"payout_accessed":False,"odds_accessed":False,
            "support_increment_authorized_now":0,
        }
        receipt.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        out = resolve(
            pre,
            receipt,
            expected_event=synthetic_event,
            now_utc=datetime(2098, 12, 31, 0, 0, tzinfo=timezone.utc),
        )

    statuses = {x["official_registration_number"]: x["status"] for x in out["decisions"]}
    tests = {
        "registry_blob_pins": blobs["takeo"] == TAKEO_BLOB and blobs["kawasaki"] == KAWASAKI_BLOB,
        "registry_union_is_19": len(registry) == 19,
        "registry_names_unique": len({x["rider_name_normalized"] for x in registry}) == 19,
        "one_exact_survivor_ready": statuses[a["official_registration_number"]] == "FINAL_PRE_PRESENT_READY_FOR_OFFICIAL_SAME_RACE_ASSIGNMENT",
        "term_contradiction_fails_closed": statuses[b["official_registration_number"]] in {
            "FAIL_CLOSED_TERM_CONTRADICTION_NO_SUPPORT",
            "FINAL_PRE_PRESENT_READY_FOR_OFFICIAL_SAME_RACE_ASSIGNMENT",
        },
        "support_stays_zero": out["support_increment_authorized_now"] == 0 and out["support_receipt_authorized_now"] is False,
        "no_result_authority": out["result_accessed"] is False and out["result_join_authorized"] is False,
        "no_race_id_guessing": out["race_id_guessed"] is False,
    }
    # If the second frozen candidate has a known term, the synthetic +1 term must fail.
    if b["term"] is not None:
        tests["term_contradiction_fails_closed"] = statuses[b["official_registration_number"]] == "FAIL_CLOSED_TERM_CONTRADICTION_NO_SUPPORT"

    return {
        "record":"KEIRIN_SEP10_NARA_PENDING_SUPPORT_CANDIDATE_RESOLVER_SELFTEST_v1",
        "status":"PASS" if all(tests.values()) else "FAIL",
        "tests":tests,
        "network_access":False,
        "result_accessed":False,
        "support_increment_authorized_now":0,
        "result_join_authorized":False,
        "model_fit_authorized":False,
        "main_or_runtime_mutation":False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    p = sub.add_parser("resolve")
    p.add_argument("--pre-csv", required=True)
    p.add_argument("--precapture-receipt", required=True)
    p.add_argument("--out", required=True)
    a = ap.parse_args()

    if a.cmd == "selftest":
        x = selftest()
        print(json.dumps(x, ensure_ascii=False, sort_keys=True))
        return 0 if x["status"] == "PASS" else 2

    try:
        x = resolve(pathlib.Path(a.pre_csv), pathlib.Path(a.precapture_receipt))
        pathlib.Path(a.out).write_text(
            json.dumps(x, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "record":x["record"],
            "status":x["status"],
            "pending_registry_unique_riders":x["pending_registry_unique_riders"],
            "survivor_count_ready_for_official_assignment":x["survivor_count_ready_for_official_assignment"],
            "support_increment_authorized_now":0,
            "result_join_authorized":False,
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:
        fail = {
            "record":"KEIRIN_SEP10_NARA_PENDING_SUPPORT_CANDIDATE_RESOLVER_v1",
            "status":"FAIL_CLOSED_PENDING_CANDIDATE_RESOLUTION_INCOMPLETE",
            "fatal_error":f"{type(exc).__name__}: {str(exc)[:500]}",
            "support_increment_authorized_now":0,
            "support_receipt_authorized_now":False,
            "result_accessed":False,
            "payout_accessed":False,
            "odds_accessed":False,
            "race_id_guessed":False,
            "result_join_authorized":False,
            "formula_fit_authorized":False,
            "main_or_runtime_mutation":False,
        }
        pathlib.Path(a.out).write_text(
            json.dumps(fail, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(fail, ensure_ascii=False, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
