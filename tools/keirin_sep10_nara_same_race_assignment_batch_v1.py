#!/usr/bin/env python3
"""Research-only Sep10 Nara official same-race assignment batch v1.

Consumes the frozen Nara pending-support survivor resolver output and runs the
existing KEIRIN.JP same-race assignment probe sequentially for each survivor.
It is identity/assignment evidence only: support remains unauthorized until a
separate cross-circumference support receipt is assembled and validated.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import subprocess
import time
from datetime import datetime, timezone
from types import SimpleNamespace

CHILD = pathlib.Path("tools/keirinjp_same_race_assignment_probe_v1.py")
EXPECTED_CHILD_BLOB = "01b6a024e190142bab3bd8bc723193e145899459"
RESOLVER_RECORD = "KEIRIN_SEP10_NARA_PENDING_SUPPORT_CANDIDATE_RESOLVER_v1"
RESOLVER_STATUS = "FINAL_PRE_PENDING_CANDIDATE_INTERSECTION_RESOLVED_ASSIGNMENT_PROBES_REQUIRED"
EXPECTED_EVENT = {"race_date":"2026-09-10","venue":"奈良","circumference_m":333.33,"day":"Day1"}


def git_blob(path: pathlib.Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], text=True).strip()


def load_child():
    got = git_blob(CHILD)
    if got != EXPECTED_CHILD_BLOB:
        raise ValueError(f"FAIL_CLOSED_ASSIGNMENT_CHILD_BLOB_{got}")
    spec = importlib.util.spec_from_file_location("same_race_assignment_probe_v1", CHILD)
    if not spec or not spec.loader:
        raise ValueError("FAIL_CLOSED_ASSIGNMENT_CHILD_IMPORT")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, got


def parse_utc(value: str) -> datetime:
    d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("FAIL_CLOSED_CUTOFF_TZ_REQUIRED")
    return d.astimezone(timezone.utc)


def validate_resolver(obj: dict, now: datetime | None = None) -> tuple[list[dict], datetime]:
    if obj.get("record") != RESOLVER_RECORD or obj.get("status") != RESOLVER_STATUS:
        raise ValueError("FAIL_CLOSED_RESOLVER_RECORD_OR_STATUS")
    if obj.get("support_increment_authorized_now") not in (0, False):
        raise ValueError("FAIL_CLOSED_RESOLVER_SUPPORT_AUTHORITY")
    if obj.get("support_receipt_authorized_now") is not False:
        raise ValueError("FAIL_CLOSED_RESOLVER_RECEIPT_AUTHORITY")
    if obj.get("result_accessed") is not False or obj.get("result_join_authorized") is not False:
        raise ValueError("FAIL_CLOSED_RESOLVER_RESULT_FLAG")
    ev = obj.get("event") or {}
    for k in ("race_date","venue","day"):
        if ev.get(k) != EXPECTED_EVENT[k]:
            raise ValueError(f"FAIL_CLOSED_RESOLVER_EVENT_{k}")
    if abs(float(ev.get("circumference_m")) - EXPECTED_EVENT["circumference_m"]) > 1e-9:
        raise ValueError("FAIL_CLOSED_RESOLVER_EVENT_CIRCUMFERENCE")
    cutoff = parse_utc(obj.get("pit_cutoff_utc"))
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if now >= cutoff:
        raise ValueError("FAIL_CLOSED_ASSIGNMENT_BATCH_AT_OR_AFTER_PIT_CUTOFF")
    survivors = obj.get("survivors")
    if not isinstance(survivors, list):
        raise ValueError("FAIL_CLOSED_RESOLVER_SURVIVORS")
    if int(obj.get("survivor_count_ready_for_official_assignment", -1)) != len(survivors):
        raise ValueError("FAIL_CLOSED_RESOLVER_SURVIVOR_COUNT")
    regs = []
    for s in survivors:
        if s.get("status") != "FINAL_PRE_PRESENT_READY_FOR_OFFICIAL_SAME_RACE_ASSIGNMENT":
            raise ValueError("FAIL_CLOSED_SURVIVOR_STATUS")
        a = s.get("same_race_assignment_probe_args") or {}
        required = {
            "registration-number","name","prefecture","term","venue","race-date",
            "race-no","circumference-m","day","pit-cutoff-utc"
        }
        if set(a) != required:
            raise ValueError("FAIL_CLOSED_ASSIGNMENT_ARG_SCHEMA")
        if a["registration-number"] != s.get("official_registration_number"):
            raise ValueError("FAIL_CLOSED_ASSIGNMENT_REG_BINDING")
        if a["venue"] != EXPECTED_EVENT["venue"] or a["race-date"] != EXPECTED_EVENT["race_date"] or a["day"] != "Day1":
            raise ValueError("FAIL_CLOSED_ASSIGNMENT_EVENT_BINDING")
        if parse_utc(a["pit-cutoff-utc"]) != cutoff:
            raise ValueError("FAIL_CLOSED_ASSIGNMENT_CUTOFF_BINDING")
        regs.append(a["registration-number"])
    if len(regs) != len(set(regs)):
        raise ValueError("FAIL_CLOSED_DUPLICATE_SURVIVOR_REGISTRATION")
    return survivors, cutoff


def to_namespace(args: dict) -> SimpleNamespace:
    return SimpleNamespace(
        registration_number=args["registration-number"],
        name=args["name"],
        prefecture=args["prefecture"],
        term=args["term"],
        venue=args["venue"],
        race_date=args["race-date"],
        race_no=args["race-no"],
        circumference_m=args["circumference-m"],
        day=args["day"],
        pit_cutoff_utc=args["pit-cutoff-utc"],
    )


def run_batch(resolver: dict, spacing_seconds: float = 5.2) -> dict:
    child, child_blob = load_child()
    survivors, cutoff = validate_resolver(resolver)
    started = datetime.now(timezone.utc)
    records = []
    halted = False

    for idx, survivor in enumerate(survivors):
        if datetime.now(timezone.utc) >= cutoff:
            halted = True
            reason = "FAIL_CLOSED_BATCH_REACHED_PIT_CUTOFF"
            for rest in survivors[idx:]:
                records.append({
                    "official_registration_number":rest["official_registration_number"],
                    "rider_name":rest["rider_name"],
                    "status":"NOT_ATTEMPTED_AFTER_BATCH_HALT",
                    "halt_reason":reason,
                })
            break
        if halted:
            break

        rec = child.run(to_namespace(survivor["same_race_assignment_probe_args"]))
        wrapped = {
            "official_registration_number":survivor["official_registration_number"],
            "rider_name":survivor["rider_name"],
            "final_pre":survivor["final_pre"],
            "historical_sources":survivor["historical_sources"],
            "assignment":rec,
        }
        records.append(wrapped)
        err = str(rec.get("fatal_error") or "")
        if "RATE_HALT" in err:
            halted = True
            for rest in survivors[idx+1:]:
                records.append({
                    "official_registration_number":rest["official_registration_number"],
                    "rider_name":rest["rider_name"],
                    "status":"NOT_ATTEMPTED_AFTER_BATCH_HALT",
                    "halt_reason":"FAIL_CLOSED_RATE_HALT",
                })
            break
        if idx + 1 < len(survivors):
            time.sleep(max(0.0, float(spacing_seconds)))

    passed = [
        r for r in records
        if isinstance(r.get("assignment"), dict)
        and r["assignment"].get("status") == "EXACT_SINGLE_MATCH_EVENT_CORROBORATED"
        and r["assignment"].get("captured_before_pit_cutoff") is True
        and r["assignment"].get("event_assignment_eligible_for_frozen_mapper") is True
    ]
    failed = len(survivors) - len(passed)

    return {
        "record":"KEIRIN_SEP10_NARA_SAME_RACE_ASSIGNMENT_BATCH_v1",
        "status":"BATCH_COMPLETED_ASSIGNMENT_EVIDENCE_READY_FOR_SUPPORT_ACCOUNTING" if not halted else "BATCH_HALTED_FAIL_CLOSED_PARTIAL_ASSIGNMENT_EVIDENCE_ONLY",
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "started_utc":started.isoformat(),
        "event":EXPECTED_EVENT,
        "pit_cutoff_utc":cutoff.isoformat(),
        "child_probe_path":str(CHILD),
        "child_probe_git_blob":child_blob,
        "survivor_input_count":len(survivors),
        "official_assignment_pass_count":len(passed),
        "official_assignment_fail_or_unattempted_count":failed,
        "records":records,
        "support_increment_authorized_now":0,
        "support_receipt_authorized_now":False,
        "next_gate":"ASSEMBLE_CROSS_CIRCUMFERENCE_SUPPORT_RECEIPTS_ONLY_FOR_ASSIGNMENT_PASS_RECORDS_AND_REVALIDATE_FROZEN_ADEQUACY_GATE",
        "result_accessed":False,
        "payout_accessed":False,
        "odds_accessed":False,
        "human_forecast_accessed":False,
        "raw_html_persisted":False,
        "race_id_guessed":False,
        "result_join_authorized":False,
        "formula_fit_authorized":False,
        "main_or_runtime_mutation":False,
    }


def selftest() -> dict:
    child, blob = load_child()
    child_self = child.selftest()
    future = "2099-01-01T00:00:00+00:00"
    resolver = {
        "record":RESOLVER_RECORD,
        "status":RESOLVER_STATUS,
        "event":EXPECTED_EVENT,
        "pit_cutoff_utc":future,
        "survivor_count_ready_for_official_assignment":1,
        "survivors":[{
            "rider_name":"テスト 太郎",
            "official_registration_number":"012345",
            "status":"FINAL_PRE_PRESENT_READY_FOR_OFFICIAL_SAME_RACE_ASSIGNMENT",
            "historical_sources":[{"venue":"川崎","race_date":"2026-08-30","circumference_m":400.0,"race_no":1,"car_no":1}],
            "final_pre":{"race_no":7,"car_no":2,"prefecture":"奈良","term":100,"race_id":"synthetic","source_url":"https://keirin.kdreams.jp/nara/racedetail/1/","source_file_sha256":"a"*64},
            "same_race_assignment_probe_args":{
                "registration-number":"012345","name":"テスト 太郎","prefecture":"奈良","term":"100",
                "venue":"奈良","race-date":"2026-09-10","race-no":"7","circumference-m":"333.33",
                "day":"Day1","pit-cutoff-utc":future
            },
            "support_increment_authorized_now":0,
        }],
        "support_increment_authorized_now":0,
        "support_receipt_authorized_now":False,
        "result_accessed":False,
        "result_join_authorized":False,
    }
    survivors, cutoff = validate_resolver(
        resolver,
        now=datetime(2098, 12, 31, tzinfo=timezone.utc),
    )
    bad = dict(resolver)
    bad["support_increment_authorized_now"] = 1
    try:
        validate_resolver(bad, now=datetime(2098,12,31,tzinfo=timezone.utc))
        bad_support_rejected = False
    except ValueError:
        bad_support_rejected = True

    tests = {
        "child_blob_pinned":blob == EXPECTED_CHILD_BLOB,
        "child_selftest_pass":child_self.get("status") == "PASS",
        "one_survivor_validated":len(survivors) == 1,
        "cutoff_preserved":cutoff.isoformat() == future,
        "nonzero_support_authority_rejected":bad_support_rejected,
        "no_network_in_batch_selftest":True,
    }
    return {
        "record":"KEIRIN_SEP10_NARA_SAME_RACE_ASSIGNMENT_BATCH_SELFTEST_v1",
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
    p = sub.add_parser("run")
    p.add_argument("--resolver", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--spacing-seconds", type=float, default=5.2)
    a = ap.parse_args()

    if a.cmd == "selftest":
        x = selftest()
        print(json.dumps(x, ensure_ascii=False, sort_keys=True))
        return 0 if x["status"] == "PASS" else 2

    try:
        resolver = json.loads(pathlib.Path(a.resolver).read_text(encoding="utf-8"))
        x = run_batch(resolver, a.spacing_seconds)
        pathlib.Path(a.out).write_text(json.dumps(x, ensure_ascii=False, sort_keys=True, indent=2)+"\n", encoding="utf-8")
        print(json.dumps({
            "record":x["record"],
            "status":x["status"],
            "survivor_input_count":x["survivor_input_count"],
            "official_assignment_pass_count":x["official_assignment_pass_count"],
            "support_increment_authorized_now":0,
            "result_join_authorized":False,
        }, ensure_ascii=False, sort_keys=True))
        return 0 if x["status"].startswith("BATCH_COMPLETED") else 3
    except Exception as exc:
        fail = {
            "record":"KEIRIN_SEP10_NARA_SAME_RACE_ASSIGNMENT_BATCH_v1",
            "status":"FAIL_CLOSED_ASSIGNMENT_BATCH_INCOMPLETE",
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
        pathlib.Path(a.out).write_text(json.dumps(fail, ensure_ascii=False, sort_keys=True, indent=2)+"\n", encoding="utf-8")
        print(json.dumps(fail, ensure_ascii=False, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
