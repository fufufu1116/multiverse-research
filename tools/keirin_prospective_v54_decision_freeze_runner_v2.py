#!/usr/bin/env python3
"""Hardened prospective v54 decision freeze runner v2.

v2 closes the v1 competition-score injection gap.  It never accepts a caller-
supplied race-gate score.  Instead it requires the exact PRE payload already
bound by the PRE-freeze receipt, verifies the canonical SHA256, recomputes the
frozen S0/challenger strict-0.40 gate score with the pinned producer, and only
then delegates the remaining frozen v54 decision logic to v1.

No network, result, payout, fitting, retuning, overwrite, or live execution.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

V1_REL = "tools/keirin_prospective_v54_decision_freeze_runner_v1.py"
V1_GIT_BLOB = "417fa8947ab9b15dde305adc15085d558659d134"
SCORE_PRODUCER_REL = "tools/keirin_prospective_competition_gate_score_v1.py"
SCORE_PRODUCER_GIT_BLOB = "e975bb3704863dbc7ebdb88d1d7f9a7ac82d5700"


class FailClosed(RuntimeError):
    pass


def git_blob_sha1_bytes(b: bytes) -> str:
    return hashlib.sha1(f"blob {len(b)}\0".encode("ascii") + b).hexdigest()


def _load_pinned(repo_root: Path, rel: str, expected_blob: str, module_name: str):
    p = repo_root / rel
    if not p.is_file():
        raise FailClosed(f"missing_pinned_module:{rel}")
    observed = git_blob_sha1_bytes(p.read_bytes())
    if observed != expected_blob:
        raise FailClosed(f"pinned_module_blob_mismatch:{rel}:{observed}")
    spec = importlib.util.spec_from_file_location(module_name, p)
    if spec is None or spec.loader is None:
        raise FailClosed(f"cannot_import_pinned_module:{rel}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_v2(envelope: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    if not isinstance(envelope, dict):
        raise FailClosed("input_envelope_not_object")
    if "competition_score" in envelope:
        raise FailClosed("caller_supplied_competition_score_forbidden_in_v2")

    v1 = _load_pinned(repo_root, V1_REL, V1_GIT_BLOB, "keirin_v54_decision_v1_pinned")
    score_mod = _load_pinned(
        repo_root,
        SCORE_PRODUCER_REL,
        SCORE_PRODUCER_GIT_BLOB,
        "keirin_strict40_score_v1_pinned",
    )

    pre_receipt = envelope.get("pre_freeze_receipt")
    if not isinstance(pre_receipt, dict):
        raise FailClosed("pre_freeze_receipt_missing")
    pre_payload = envelope.get("pre_payload_for_gate_score")
    if not isinstance(pre_payload, dict):
        raise FailClosed("pre_payload_for_gate_score_missing")

    expected_pre_sha = str(pre_receipt.get("pre_payload_sha256", "")).strip().lower()
    if len(expected_pre_sha) != 64:
        raise FailClosed("pre_freeze_receipt_pre_payload_sha256_missing")
    observed_pre_sha = v1.sha256_bytes(v1.canonical_bytes(pre_payload))
    if observed_pre_sha != expected_pre_sha:
        raise FailClosed("pre_payload_for_gate_score_sha256_mismatch")

    model = score_mod.load_frozen_model(repo_root)
    generated = score_mod.produce_gate_score(pre_payload, model)

    target_identity = pre_receipt.get("target_identity")
    if not isinstance(target_identity, dict):
        raise FailClosed("pre_freeze_receipt_target_identity_missing")
    # The score producer is bound to the exact PRE bytes; additionally require
    # the PRE identity itself to agree with the frozen receipt identity.
    if v1.identity_tuple(pre_payload) != v1.identity_tuple(target_identity):
        raise FailClosed("pre_payload_for_gate_score_target_identity_mismatch")

    capture_time = pre_receipt.get("capture_time")
    if capture_time is None:
        raise FailClosed("pre_freeze_receipt_capture_time_missing")

    delegated = copy.deepcopy(envelope)
    delegated.pop("pre_payload_for_gate_score", None)
    delegated["competition_score"] = {
        "value": generated["value"],
        "captured_at": capture_time,
        "frozen_before_target_cutoff": True,
        "provenance": {
            "target_identity": dict(target_identity),
            "pre_payload_sha256": observed_pre_sha,
            "semantic_name": generated["semantic_name"],
            "top1_agreement": generated["top1_agreement"],
            "s0_top1_car_no": generated["s0_top1_car_no"],
            "challenger_top1_car_no": generated["challenger_top1_car_no"],
            "s0_top1_probability": generated["s0_top1_probability"],
            "challenger_top1_probability": generated["challenger_top1_probability"],
            "frozen_model_git_blob": generated["frozen_model_git_blob"],
            "score_producer_git_blob": SCORE_PRODUCER_GIT_BLOB,
        },
        "method_binding": f"git_blob:{SCORE_PRODUCER_GIT_BLOB}",
    }

    base = v1.run(delegated, repo_root)
    # Do not mutate the v1 receipt because its own receipt hash binds its body.
    wrapper = {
        "record": "KEIRIN_PROSPECTIVE_V54_DECISION_FREEZE_RECEIPT_v2",
        "status": "PASS_HARDENED_SCORE_PRODUCER_BOUND",
        "v1_runner_git_blob": V1_GIT_BLOB,
        "score_producer_git_blob": SCORE_PRODUCER_GIT_BLOB,
        "pre_payload_sha256": observed_pre_sha,
        "generated_competition_gate_score": generated,
        "v1_decision_receipt": base,
        "caller_supplied_competition_score_accepted": False,
        "retune": False,
        "result_accessed": False,
        "payout_accessed": False,
        "network_access": False,
        "runtime": "OFF",
        "automatic_betting": False,
    }
    wrapper["decision_freeze_receipt_v2_sha256"] = v1.sha256_bytes(v1.canonical_bytes(wrapper))
    return wrapper


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    inp = Path(a.input)
    out = Path(a.output)
    if out.exists():
        raise FailClosed("output_already_exists")
    envelope = json.loads(inp.read_text(encoding="utf-8"))
    rec = run_v2(envelope, Path(a.repo_root).resolve())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
