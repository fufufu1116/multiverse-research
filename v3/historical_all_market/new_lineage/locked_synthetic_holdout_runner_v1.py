from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping

from balanced_synthetic_fit_cal_v1 import evaluate_holdout

HERE = Path(__file__).resolve().parent
GOVERNANCE = HERE.parent / "governance"
PREREG = GOVERNANCE / "KEIRIN_PREREG_BALANCED_SYNTHETIC_ABLATION_v1.json"
FROZEN_RECEIPT = GOVERNANCE / "KEIRIN_FROZEN_PRE_HOLDOUT_COEFFICIENT_RECEIPT_v1.json"

EXPECTED_RECEIPT_RECORD = "KEIRIN_FROZEN_PRE_HOLDOUT_COEFFICIENT_RECEIPT_v1"
EXPECTED_RECEIPT_STATUS = "FROZEN_PRE_HOLDOUT_INPUT_NOT_EXECUTED"
EXPECTED_RECEIPT_GIT_BLOB = "f531d72929c846da1c932451873c94bb9b526ae7"
EXPECTED_RECEIPT_SHA256 = "4d68c9d7a87b38b8e18e5eb983f9b87865dc7345f6c248656222bdc4c9c6e597"
EXPECTED_PREREG_GIT_BLOB = "e4131621bf770068ec9d0c44da16356f64027e80"
EXPECTED_PREREG_SHA256 = "ff565fcbcb524c0d290b22046c2006648f58bed8e20c913704ae6b9ed4634889"

EXPECTED_C1 = {
    "train_params": {"line_mean_coef": 0.0, "position_scale": 0.5, "size_coef": 0.0},
    "cal_shrinkage": 0.75,
}
EXPECTED_N1 = {
    "c1_base_train_params": {"line_mean_coef": 0.0, "position_scale": 0.5, "size_coef": 0.0},
    "conditional_train_params": {"same_line_coef": 0.1, "follower_coef": 0.1, "chain_coef": 0.2},
    "cal_shrinkage": 0.75,
}


def _git_blob_sha(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("utf-8")
    return hashlib.sha1(header + raw).hexdigest()


def _load_and_verify_binding() -> tuple[dict, dict]:
    receipt_raw = FROZEN_RECEIPT.read_bytes()
    receipt_sha256 = hashlib.sha256(receipt_raw).hexdigest()
    receipt_git_blob = _git_blob_sha(receipt_raw)
    if receipt_sha256 != EXPECTED_RECEIPT_SHA256:
        raise ValueError("frozen_receipt_sha256_mismatch")
    if receipt_git_blob != EXPECTED_RECEIPT_GIT_BLOB:
        raise ValueError("frozen_receipt_git_blob_mismatch")

    receipt = json.loads(receipt_raw.decode("utf-8"))
    if receipt.get("record") != EXPECTED_RECEIPT_RECORD:
        raise ValueError("frozen_receipt_record_mismatch")
    if receipt.get("status") != EXPECTED_RECEIPT_STATUS:
        raise ValueError("frozen_receipt_status_mismatch")
    if receipt.get("holdout_execution") != "NOT_EXECUTED":
        raise ValueError("frozen_receipt_not_pre_holdout")
    if receipt.get("post_holdout_retuning") != "PROHIBITED":
        raise ValueError("post_holdout_retuning_rule_drift")

    prereg_raw = PREREG.read_bytes()
    prereg_sha256 = hashlib.sha256(prereg_raw).hexdigest()
    prereg_git_blob = _git_blob_sha(prereg_raw)
    if prereg_sha256 != EXPECTED_PREREG_SHA256:
        raise ValueError("prereg_sha256_mismatch")
    if prereg_git_blob != EXPECTED_PREREG_GIT_BLOB:
        raise ValueError("prereg_git_blob_mismatch")
    prereg_ref = receipt.get("prereg", {})
    if prereg_ref.get("sha256") != EXPECTED_PREREG_SHA256:
        raise ValueError("receipt_prereg_sha256_mismatch")
    if prereg_ref.get("git_blob_sha") != EXPECTED_PREREG_GIT_BLOB:
        raise ValueError("receipt_prereg_git_blob_mismatch")

    frozen = receipt.get("frozen_after_cal", {})
    if frozen.get("C0") != {"architecture": "score_only_PL", "fitted": False}:
        raise ValueError("frozen_c0_identity_mismatch")
    if frozen.get("C1") != EXPECTED_C1:
        raise ValueError("frozen_c1_coefficients_mismatch")
    if frozen.get("N1") != EXPECTED_N1:
        raise ValueError("frozen_n1_coefficients_mismatch")

    executable = {
        "prereg_sha256": EXPECTED_PREREG_SHA256,
        "holdout_execution": "NOT_EXECUTED",
        "frozen_after_cal": frozen,
    }
    assurance = {
        "frozen_receipt_path": str(FROZEN_RECEIPT),
        "frozen_receipt_sha256": receipt_sha256,
        "frozen_receipt_git_blob_sha": receipt_git_blob,
        "prereg_sha256": prereg_sha256,
        "prereg_git_blob_sha": prereg_git_blob,
        "arbitrary_json_input_accepted": False,
        "binding": "PASS",
    }
    return executable, assurance


def verify_only() -> dict:
    _, assurance = _load_and_verify_binding()
    return {
        "record": "KEIRIN_FROZEN_HOLDOUT_BINDING_CHECK_v1",
        "status": "BINDING_VERIFIED_HOLDOUT_NOT_EXECUTED",
        "assurance": assurance,
        "fresh_synthetic_holdout_executed": False,
        "untouched_real_validation_opened": False,
    }


def execute_holdout_after_lab_authorization() -> dict:
    frozen, assurance = _load_and_verify_binding()
    result = evaluate_holdout(frozen)
    result["frozen_receipt_binding"] = assurance
    result["execution_entrypoint"] = "locked_synthetic_holdout_runner_v1"
    result["arbitrary_json_input_accepted"] = False
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=("verify-binding", "execute-after-lab-authorization"),
        default="verify-binding",
    )
    args = parser.parse_args()
    if args.stage == "verify-binding":
        result = verify_only()
    else:
        result = execute_holdout_after_lab_authorization()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
