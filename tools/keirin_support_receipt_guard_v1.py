#!/usr/bin/env python3
"""Research-only duplicate/provenance guard for cross-circumference support receipts.

Validates receipt-shaped JSON against the frozen duplicate/provenance prespec,
derives canonical row keys, de-duplicates rider/row accounting, and reports
eligibility diagnostics. It never increments support by itself and never uses
RESULT/payout/odds/forecast evidence.
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib, re

PRESPEC = pathlib.Path("v3/historical_all_market/research_candidates/KEIRIN_SUPPORT_RECEIPT_DUPLICATE_PROVENANCE_PRESPEC_20260906_v1.json")
PRESPEC_BLOB = "26a0fedd2a8b1a000b8bdba294c4e9a47f704e54"
REQ_ROW = {"race_date","venue","circumference_m","day","race_no","car_no","pre_artifact","source_file_sha256","registration_number","valid_pre_row_for_support"}
FORBIDDEN_TRUE = {"result_accessed","target_result_accessed","payout_accessed","odds_accessed","human_forecast_accessed"}


def sha1_git_blob(path: pathlib.Path) -> str:
    data = path.read_bytes()
    head = f"blob {len(data)}\0".encode()
    return hashlib.sha1(head + data).hexdigest()


def load_prespec() -> dict:
    got = sha1_git_blob(PRESPEC)
    if got != PRESPEC_BLOB:
        raise ValueError(f"FAIL_CLOSED_PRESPEC_BLOB_{got}")
    p = json.loads(PRESPEC.read_text(encoding="utf-8"))
    if p.get("status") != "FROZEN_RESEARCH_PRE_ONLY_NO_RESULT_NO_SUPPORT_AUTO_AUTHORITY":
        raise ValueError("FAIL_CLOSED_PRESPEC_STATUS")
    return p


def reg6(x) -> str:
    s = str(x).strip()
    if not re.fullmatch(r"\d{6}", s):
        raise ValueError("FAIL_CLOSED_REGISTRATION_NUMBER")
    return s


def bucket(c) -> str:
    x = float(c)
    if abs(x-333.0) < 1e-6 or abs(x-333.33) < 0.02:
        return "333_OR_333_33"
    if abs(x-400.0) < 1e-6:
        return "400"
    raise ValueError(f"FAIL_CLOSED_CIRCUMFERENCE_{x}")


def row_key(reg: str, row: dict) -> tuple:
    missing = sorted(REQ_ROW - set(row))
    if missing:
        raise ValueError("FAIL_CLOSED_MISSING_ROW_FIELDS_" + ",".join(missing))
    if row.get("valid_pre_row_for_support") is not True:
        raise ValueError("FAIL_CLOSED_INVALID_PRE_ROW")
    if reg6(row.get("registration_number")) != reg:
        raise ValueError("FAIL_CLOSED_ROW_REG_BINDING")
    h = str(row.get("source_file_sha256") or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", h):
        raise ValueError("FAIL_CLOSED_SOURCE_SHA256")
    if row.get("day") != "Day1":
        raise ValueError("FAIL_CLOSED_NOT_DAY1")
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", str(row.get("race_date"))):
        raise ValueError("FAIL_CLOSED_RACE_DATE")
    if not str(row.get("venue") or "").strip():
        raise ValueError("FAIL_CLOSED_VENUE")
    rn, cn = int(row.get("race_no")), int(row.get("car_no"))
    if not 1 <= rn <= 12 or not 1 <= cn <= 9:
        raise ValueError("FAIL_CLOSED_RACE_OR_CAR_NO")
    return (reg, bucket(row["circumference_m"]), row["race_date"], row["venue"], rn, cn, h)


def extract_rows(receipt: dict) -> list[dict]:
    sr = receipt.get("supported_rows")
    if isinstance(sr, dict):
        rows = [v for v in sr.values() if isinstance(v, dict)]
    elif isinstance(sr, list):
        rows = sr
    else:
        raise ValueError("FAIL_CLOSED_SUPPORTED_ROWS")
    if not rows:
        raise ValueError("FAIL_CLOSED_EMPTY_SUPPORTED_ROWS")
    return rows


def validate_receipt(receipt: dict) -> dict:
    load_prespec()
    rider = receipt.get("rider") or {}
    if not str(rider.get("name") or "").strip():
        raise ValueError("FAIL_CLOSED_RIDER_NAME")
    reg = reg6(rider.get("official_registration_number"))
    for k in FORBIDDEN_TRUE:
        if receipt.get(k) is True:
            raise ValueError("FAIL_CLOSED_FORBIDDEN_SOURCE_" + k)
    if receipt.get("result_join_authorized") is not False or receipt.get("formula_fit_authorized") is not False:
        raise ValueError("FAIL_CLOSED_DOWNSTREAM_AUTHORITY")
    rows = extract_rows(receipt)
    keys = [row_key(reg, r) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("FAIL_CLOSED_DUPLICATE_ROW_WITHIN_RECEIPT")
    buckets = {k[1] for k in keys}
    cross = {"333_OR_333_33","400"}.issubset(buckets)
    decision = receipt.get("support_decision") or {}
    if decision.get("same_official_registration_number_across_333_and_400") is not True:
        raise ValueError("FAIL_CLOSED_IDENTITY_CROSS_BINDING")
    if decision.get("both_rows_valid_pre") is not True:
        raise ValueError("FAIL_CLOSED_BOTH_PRE")
    if decision.get("result_needed_for_support_decision") is not False:
        raise ValueError("FAIL_CLOSED_RESULT_NEEDED_FLAG")
    if cross and decision.get("cross_circumference_supported_rider") is not True:
        raise ValueError("FAIL_CLOSED_DECISION_CROSS_MISMATCH")
    return {"registration_number":reg,"rider_name":rider["name"],"canonical_row_keys":[list(k) for k in keys],"cross_circumference_qualified":cross}


def account(receipts: list[dict]) -> dict:
    validated = [validate_receipt(r) for r in receipts]
    seen_rows, qualified_regs = set(), set()
    new_rows = 0
    for v in validated:
        if v["cross_circumference_qualified"]:
            qualified_regs.add(v["registration_number"])
        for k in map(tuple, v["canonical_row_keys"]):
            if k not in seen_rows:
                seen_rows.add(k); new_rows += 1
    return {
        "record":"KEIRIN_SUPPORT_RECEIPT_GUARD_v1",
        "status":"PASS_DUPLICATE_SAFE_PROVENANCE_SHAPE_VALIDATED",
        "receipt_count":len(receipts),
        "qualified_unique_registration_numbers":len(qualified_regs),
        "unique_canonical_row_keys":len(seen_rows),
        "duplicate_rows_removed":sum(len(v["canonical_row_keys"]) for v in validated)-len(seen_rows),
        "support_increment_authorized_now":0,
        "result_accessed":False,
        "result_join_authorized":False,
        "formula_fit_authorized":False,
        "main_or_runtime_mutation":False,
    }


def selftest() -> dict:
    row333={"race_date":"2099-01-01","venue":"防府","circumference_m":333,"day":"Day1","race_no":1,"car_no":1,"pre_artifact":"x","source_file_sha256":"a"*64,"registration_number":"012345","valid_pre_row_for_support":True}
    row400={"race_date":"2099-01-02","venue":"川崎","circumference_m":400,"day":"Day1","race_no":2,"car_no":2,"pre_artifact":"y","source_file_sha256":"b"*64,"registration_number":"012345","valid_pre_row_for_support":True}
    r={"rider":{"name":"テスト","official_registration_number":"012345"},"supported_rows":{"333m":row333,"400m":row400},"support_decision":{"same_official_registration_number_across_333_and_400":True,"both_rows_valid_pre":True,"cross_circumference_supported_rider":True,"result_needed_for_support_decision":False},"result_accessed":False,"target_result_accessed":False,"payout_accessed":False,"odds_accessed":False,"human_forecast_accessed":False,"result_join_authorized":False,"formula_fit_authorized":False}
    tests={}
    a=account([r,r]); tests["duplicate_receipt_dedup"] = a["qualified_unique_registration_numbers"]==1 and a["unique_canonical_row_keys"]==2 and a["duplicate_rows_removed"]==2
    bad=json.loads(json.dumps(r)); bad["supported_rows"]["333m"].pop("source_file_sha256")
    try: validate_receipt(bad); tests["missing_hash_fail_closed"]=False
    except ValueError: tests["missing_hash_fail_closed"]=True
    bad2=json.loads(json.dumps(r)); bad2["result_accessed"]=True
    try: validate_receipt(bad2); tests["result_flag_fail_closed"]=False
    except ValueError: tests["result_flag_fail_closed"]=True
    return {"record":"KEIRIN_SUPPORT_RECEIPT_GUARD_SELFTEST_v1","status":"PASS" if all(tests.values()) else "FAIL","tests":tests,"network_access":False,"support_increment_authorized_now":0,"result_accessed":False}


def main() -> int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True); sub.add_parser("selftest")
    p=sub.add_parser("validate"); p.add_argument("receipts",nargs="+")
    a=ap.parse_args()
    if a.cmd=="selftest":
        x=selftest(); print(json.dumps(x,ensure_ascii=False,sort_keys=True)); return 0 if x["status"]=="PASS" else 2
    try:
        xs=[json.loads(pathlib.Path(p).read_text(encoding="utf-8")) for p in a.receipts]
        print(json.dumps(account(xs),ensure_ascii=False,sort_keys=True)); return 0
    except Exception as e:
        print(json.dumps({"record":"KEIRIN_SUPPORT_RECEIPT_GUARD_v1","status":"FAIL_CLOSED_RECEIPT_GUARD","fatal_error":f"{type(e).__name__}: {str(e)[:400]}","support_increment_authorized_now":0,"result_accessed":False},ensure_ascii=False,sort_keys=True)); return 3

if __name__=="__main__": raise SystemExit(main())
