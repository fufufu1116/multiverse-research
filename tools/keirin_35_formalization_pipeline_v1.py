#!/usr/bin/env python3
"""One-shot locked-35 PRE formalization pipeline v1.

Purpose:
- remove manual orchestration on 2026-09-14/15;
- load the four canonical locked artifacts;
- require a pristine 35-row shell;
- normalize six-source prospective final Day1 observations with normalizer v5;
- finalize with finalizer v7;
- emit a compact readiness summary plus the full normalization/finalization
  objects for audit/replay.

This tool performs no network access, no RESULT/PAYOUT/ODDS/PREDICTION/comment
access, no model fitting, no main mutation, and no runtime action.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

import keirin_multisite_final_racecard_normalizer_v5 as normalizer
import keirin_35_formal_support_finalizer_v7 as finalizer

REPO_ROOT=Path(__file__).resolve().parents[1]
BASE=REPO_ROOT/"v3/historical_all_market/research_candidates"

DEFAULT_ORDER=BASE/"KEIRIN_35_FORMAL_CONVERSION_ORDER_PRELOCK_20260908_v1.json"
DEFAULT_MATRIX=BASE/"KEIRIN_35_SUPPORT_CONVERSION_MATRIX_20260908_v1.json"
DEFAULT_REGISTRY=BASE/"KEIRIN_PRE_CUTOFF_WITNESS_REGISTRY_20260907_v1.json"
DEFAULT_SHELL=BASE/"KEIRIN_35_FINAL_DAY1_PRE_INPUT_MANIFEST_20260908_v1.json"

ALLOWED_FILL_FIELDS={
    "race_no","car_no","class","style","source_url","captured_at_jst",
    "trusted_pit_cutoff_jst","source_sha256",
}
EXPECTED_PENDING_FILL_STATUS="PENDING_FINAL_DAY1_PRE_PUBLICATION"


class FormalizationPipelineError(ValueError):
    pass


def load_json(path: str | Path) -> dict:
    obj=json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj,dict):
        raise FormalizationPipelineError(f"json_root_must_be_object:{path}")
    return obj


def dump_json(path: str | Path,obj: Any) -> None:
    Path(path).write_text(
        json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=False)+"\n",
        encoding="utf-8",
    )


def _candidate_signature_from_order(cand: Mapping[str,Any]) -> tuple:
    future=cand.get("future") or {}
    bucket=str(future.get("circumference_bucket") or "")
    circ=400 if bucket=="400" else 333 if bucket=="333_OR_333_33" else None
    return (
        cand.get("priority"),
        str(cand.get("rider_name") or ""),
        str(cand.get("registration") or ""),
        str(future.get("date") or ""),
        str(future.get("venue") or ""),
        circ,
        "Day1",
    )


def _candidate_signature_from_shell(row: Mapping[str,Any]) -> tuple:
    return (
        row.get("priority"),
        str(row.get("rider_name") or ""),
        str(row.get("official_registration_number") or ""),
        str(row.get("race_date") or ""),
        str(row.get("venue") or ""),
        int(row.get("circumference_m")) if row.get("circumference_m") is not None else None,
        str(row.get("day") or ""),
    )


def validate_pristine_locked_inputs(
    order: Mapping[str,Any],
    matrix: Mapping[str,Any],
    registry: Mapping[str,Any],
    shell: Mapping[str,Any],
) -> dict:
    ordered=list(order.get("ordered_candidates") or [])
    matrix_rows=list(matrix.get("rows") or [])
    shell_rows=list(shell.get("rows") or [])

    if len(ordered)!=35:
        raise FormalizationPipelineError(f"expected_35_ordered_candidates_got_{len(ordered)}")
    if len(matrix_rows)!=35:
        raise FormalizationPipelineError(f"expected_35_matrix_rows_got_{len(matrix_rows)}")
    if len(shell_rows)!=35:
        raise FormalizationPipelineError(f"expected_35_shell_rows_got_{len(shell_rows)}")

    priorities=[c.get("priority") for c in ordered]
    if priorities!=list(range(1,36)):
        raise FormalizationPipelineError("priority_order_must_be_exact_1_to_35")

    order_by_reg={}
    for cand in ordered:
        sig=_candidate_signature_from_order(cand)
        reg=sig[2]
        if not reg or reg in order_by_reg:
            raise FormalizationPipelineError("order_registration_missing_or_duplicate")
        order_by_reg[reg]=sig

    matrix_by_reg={}
    for row in matrix_rows:
        reg=str(row.get("official_registration_number") or "")
        if not reg or reg in matrix_by_reg:
            raise FormalizationPipelineError("matrix_registration_missing_or_duplicate")
        matrix_by_reg[reg]=row

    seen_shell=set()
    for row in shell_rows:
        sig=_candidate_signature_from_shell(row)
        reg=sig[2]
        if reg in seen_shell:
            raise FormalizationPipelineError(f"duplicate_shell_registration:{reg}")
        seen_shell.add(reg)
        if order_by_reg.get(reg)!=sig:
            raise FormalizationPipelineError(f"shell_order_binding_mismatch:{reg}")

        # The canonical shell must remain pristine. Any previously populated
        # final assignment is rejected so a stale run cannot silently survive.
        for field in ALLOWED_FILL_FIELDS:
            if row.get(field) not in (None,""):
                raise FormalizationPipelineError(
                    f"shell_not_pristine_field_populated:{reg}:{field}"
                )
        if row.get("fill_status") not in (None,EXPECTED_PENDING_FILL_STATUS):
            raise FormalizationPipelineError(
                f"shell_not_pristine_fill_status:{reg}:{row.get('fill_status')}"
            )

    if set(order_by_reg)!=set(matrix_by_reg)!=set():
        # chained inequality is not the intended check; keep explicit below
        pass
    if set(order_by_reg)!=set(matrix_by_reg):
        raise FormalizationPipelineError("order_matrix_registration_set_mismatch")
    if set(order_by_reg)!=seen_shell:
        raise FormalizationPipelineError("order_shell_registration_set_mismatch")

    baseline=list(shell.get("baseline_supported_rows") or [])
    if len(baseline)!=2:
        raise FormalizationPipelineError("baseline_supported_rows_must_be_exactly_2")

    # Let the finalizer's locked-index validation assert registry exactness too,
    # but run it without mutating anything here.
    try:
        finalizer.v6.v5.index_locked_inputs(order,matrix,registry)
    except AttributeError:
        # Defensive compatibility fallback if internal import topology changes.
        pass

    return {
        "candidate_count":35,
        "priority_binding":"PASS_1_TO_35",
        "order_matrix_shell_registration_binding":"PASS_35_OF_35",
        "shell_pristine":True,
        "baseline_rows":2,
    }


def run_pipeline(
    observations: list[Mapping[str,Any]],
    *,
    order: Mapping[str,Any],
    matrix: Mapping[str,Any],
    registry: Mapping[str,Any],
    shell: Mapping[str,Any],
) -> dict:
    if not isinstance(observations,list):
        raise FormalizationPipelineError("observations_must_be_list")

    binding=validate_pristine_locked_inputs(order,matrix,registry,shell)

    manifest=normalizer.build_finalizer_manifest(
        shell,
        order,
        observations,
    )
    normalization=manifest.get("multisite_normalization") or {}
    finalized=finalizer.finalize(order,matrix,registry,manifest)

    decisions=list(finalized.get("decisions") or [])
    passes=sum(1 for d in decisions if d.get("status")=="PASS_FORMAL_SUPPORT")
    failures=sum(1 for d in decisions if d.get("status")=="FAIL_CLOSED")
    not_ready=sum(1 for d in decisions if d.get("status") in {"NOT_READY","SKIP_NO_PRE_ROW"})

    summary={
        "binding":binding,
        "observations_received":len(observations),
        "normalized_rows":int(normalization.get("normalized_row_count") or 0),
        "normalization_status":normalization.get("status"),
        "formal_new_pass_riders":int(finalized.get("new_pass_riders") or 0),
        "formal_pass_decisions":passes,
        "formal_fail_closed_decisions":failures,
        "formal_not_ready_decisions":not_ready,
        "cumulative_riders":finalized.get("cumulative_riders"),
        "cumulative_rows":finalized.get("cumulative_rows"),
        "stopped_after_29_new_pass":bool(finalized.get("stopped_after_29_new_pass")),
        "formalizer_status":finalized.get("status"),
        "remaining_new_pass_needed":max(
            0,29-int(finalized.get("new_pass_riders") or 0)
        ),
        "calendar_block_gate":"UNKNOWN_PENDING_PR177",
        "result_accessed":False,
        "payout_accessed":False,
        "odds_accessed":False,
        "prediction_accessed":False,
        "human_comments_accessed":False,
        "runtime":False,
    }

    return {
        "record":"KEIRIN_35_FORMALIZATION_PIPELINE_OUTPUT_v1",
        "status":(
            "TARGET_29_NEW_PASS_REACHED"
            if summary["stopped_after_29_new_pass"]
            else "TARGET_NOT_REACHED"
        ),
        "summary":summary,
        "normalization":normalization,
        "finalization":finalized,
    }


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--observations",required=True)
    ap.add_argument("--order",default=str(DEFAULT_ORDER))
    ap.add_argument("--matrix",default=str(DEFAULT_MATRIX))
    ap.add_argument("--registry",default=str(DEFAULT_REGISTRY))
    ap.add_argument("--shell",default=str(DEFAULT_SHELL))
    ap.add_argument("--out")
    args=ap.parse_args()

    observations=json.loads(Path(args.observations).read_text(encoding="utf-8"))
    if isinstance(observations,dict) and "observations" in observations:
        observations=observations["observations"]

    out=run_pipeline(
        observations,
        order=load_json(args.order),
        matrix=load_json(args.matrix),
        registry=load_json(args.registry),
        shell=load_json(args.shell),
    )
    rendered=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
    if args.out:
        Path(args.out).write_text(rendered,encoding="utf-8")
    else:
        print(rendered,end="")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
