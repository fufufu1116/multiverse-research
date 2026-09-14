#!/usr/bin/env python3
"""Governed PRE-only provenance-value audit v2.5.

Reads one exact hash-pinned PRE_PROVENANCE.jsonl.gz and persists only the
preregistered provenance summary. It never opens raw payloads and never uses
outcome, price, economics, labels, training or model-selection information.
"""
from __future__ import annotations
import argparse, collections, gzip, hashlib, json, urllib.parse

EXPECTED_SHA256 = "86627fe4151074f2d20db637a7f5468e24ae3c6e878a82a33fde7b3218261b27"
ALLOWED = ("race_id", "payload_sha256", "retrieved_at_utc", "source_url", "availability_proof")
FORBIDDEN_KEY_TOKENS = (
    "result", "payout", "finish", "winner", "settlement", "odds", "price",
    "profit", "roi", "bankroll", "return_amount", "着順", "払戻", "オッズ"
)

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def url_template(value):
    if not isinstance(value, str) or not value:
        return None
    p = urllib.parse.urlsplit(value)
    return f"{p.scheme}://{p.netloc}{p.path}" if p.scheme and p.netloc else value.split("?",1)[0].split("#",1)[0]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("output")
    args = ap.parse_args()
    actual = sha256_file(args.source)
    if actual != EXPECTED_SHA256:
        raise SystemExit(f"STOP_SOURCE_HASH_DRIFT actual={actual}")

    rows = 0
    seen_keys = set()
    race_ids = set()
    payloads = set()
    missing = collections.Counter()
    url_counts = collections.Counter()
    availability_counts = collections.Counter()
    retrieval_min = None
    retrieval_max = None

    with gzip.open(args.source, "rt", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            keys = set(obj.keys())
            seen_keys |= keys
            forbidden = sorted(k for k in keys if any(t in k.lower() for t in FORBIDDEN_KEY_TOKENS))
            if forbidden:
                raise SystemExit("STOP_UNEXPECTED_FORBIDDEN_SCHEMA_KEY=" + ",".join(forbidden))
            rows += 1
            vals = {k: obj.get(k) for k in ALLOWED}
            for k, v in vals.items():
                if v is None or v == "":
                    missing[k] += 1
            rid = vals["race_id"]
            if rid not in (None, ""):
                race_ids.add(str(rid))
            ph = vals["payload_sha256"]
            if ph not in (None, ""):
                payloads.add(str(ph))
            tmpl = url_template(vals["source_url"])
            if tmpl:
                url_counts[tmpl] += 1
            rt = vals["retrieved_at_utc"]
            if isinstance(rt, str) and rt:
                retrieval_min = rt if retrieval_min is None or rt < retrieval_min else retrieval_min
                retrieval_max = rt if retrieval_max is None or rt > retrieval_max else retrieval_max
            av = vals["availability_proof"]
            availability_counts[json.dumps(av, ensure_ascii=False, sort_keys=True, separators=(",", ":"))] += 1

    out = {
        "record": "KEIRIN_REAL_PRE_ONLY_ENRICHMENT_AUDIT_V2_5_PROVENANCE_VALUE_RESULT",
        "status": "COMPLETE_PROVENANCE_VALUE_AUDIT_STOP_BEFORE_RAW_PAYLOAD_BYTES",
        "evidence_class": "REAL_PRE_ONLY_ENRICHMENT_SUITABILITY_COMPATIBILITY_EVIDENCE_NOT_PREDICTIVE_PERFORMANCE",
        "source_sha256_expected": EXPECTED_SHA256,
        "source_sha256_actual": actual,
        "row_count": rows,
        "unique_race_id_count": len(race_ids),
        "unique_payload_sha256_count": len(payloads),
        "missingness": {k: int(missing[k]) for k in ALLOWED},
        "payload_sha256_deterministic_first5": sorted(payloads)[:5],
        "source_url_templates": dict(sorted(url_counts.items())),
        "retrieved_at_utc_min": retrieval_min,
        "retrieved_at_utc_max": retrieval_max,
        "availability_proof_counts": dict(sorted(availability_counts.items())),
        "schema_recheck_keys": sorted(seen_keys),
        "raw_payload_bytes_accessed": False,
        "RESULT_PAYOUT": "NOT_ACCESSED",
        "outcome_or_settlement_labels": "NOT_ACCESSED",
        "odds_price": "NOT_ACCESSED",
        "economics": "NOT_COMPUTED",
        "training_or_fit": False,
        "model_selection": False,
        "model_promotion": False,
        "ECON_HOLDOUT1000": "SEALED_NOT_ACCESSED",
        "runtime": "OFF",
        "automatic_betting": False
    }
    with open(args.output, "w", encoding="utf-8") as g:
        json.dump(out, g, ensure_ascii=False, indent=2, sort_keys=True)
        g.write("\n")

if __name__ == "__main__":
    main()
