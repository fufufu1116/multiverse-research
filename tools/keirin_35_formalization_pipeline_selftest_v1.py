#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import hashlib
import importlib
import pathlib
import sys

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(HERE))

pipe=importlib.import_module("keirin_35_formalization_pipeline_v1")


def load_inputs():
    return (
        pipe.load_json(pipe.DEFAULT_ORDER),
        pipe.load_json(pipe.DEFAULT_MATRIX),
        pipe.load_json(pipe.DEFAULT_REGISTRY),
        pipe.load_json(pipe.DEFAULT_SHELL),
    )


def observation_from_shell(row, *, family="CTC", suffix="", race_no=None, car_no=None, captured=None):
    race_date=date.fromisoformat(row["race_date"])
    if captured is None:
        captured=(race_date-timedelta(days=1)).isoformat()+"T12:00:00+09:00"
    race_no = race_no if race_no is not None else 1 + ((int(row["priority"])-1) % 10)
    car_no = car_no if car_no is not None else 1 + ((int(row["priority"])-1) % 7)

    host={
        "CTC":"ctc.gr.jp",
        "KDREAMS":"keirin.kdreams.jp",
        "WINTICKET":"www.winticket.jp",
        "KEIRIN.JP":"www.keirin.jp",
        "CHARILOTO":"www.chariloto.com",
        "ODDSPARK":"www.oddspark.com",
    }[family]
    payload=f'{family}|{row["official_registration_number"]}|{row["race_date"]}|{race_no}|{car_no}|{suffix}'
    return {
        "source_family":family,
        "source_role":"FINAL_DAY1_RACECARD",
        "source_namespace":"schedule/racecard",
        "source_title":"初日出走表",
        "page_kind":"final_day1_racecard",
        "source_url":f"https://{host}/keirin/racecard/{row['official_registration_number']}{suffix}",
        "source_sha256":hashlib.sha256(payload.encode()).hexdigest(),
        "captured_at_jst":captured,
        "official_registration_number":row["official_registration_number"],
        "rider_name":row["rider_name"],
        "race_date":row["race_date"],
        "venue":row["venue"],
        "day":"Day1",
        "circumference_m":row["circumference_m"],
        "race_no":race_no,
        "car_no":car_no,
        "class":"S1",
        "style":"追",
        "status":"ACTIVE",
    }


def build_observations(shell, start_priority=1):
    return [
        observation_from_shell(row)
        for row in shell["rows"]
        if int(row["priority"])>=start_priority
    ]


def must_fail(fn, contains=None):
    try:
        fn()
    except Exception as exc:
        if contains is not None:
            assert contains in str(exc),(contains,str(exc))
        return str(exc)
    raise AssertionError("expected fail-closed error")


def main():
    order,matrix,registry,shell=load_inputs()

    binding=pipe.validate_pristine_locked_inputs(order,matrix,registry,shell)
    assert binding["candidate_count"]==35
    assert binding["order_matrix_shell_registration_binding"]=="PASS_35_OF_35"
    assert binding["shell_pristine"] is True

    # Empty current state: no fabricated support.
    empty=pipe.run_pipeline(
        [],order=order,matrix=matrix,registry=registry,shell=shell
    )
    assert empty["summary"]["formal_new_pass_riders"]==0
    assert empty["summary"]["remaining_new_pass_needed"]==29
    assert empty["status"]=="TARGET_NOT_REACHED"

    # All 35 prospectively available => deterministic stop at 29.
    all_obs=build_observations(shell,1)
    all_out=pipe.run_pipeline(
        all_obs,order=order,matrix=matrix,registry=registry,shell=shell
    )
    assert all_out["summary"]["observations_received"]==35
    assert all_out["summary"]["normalized_rows"]==35
    assert all_out["summary"]["formal_new_pass_riders"]==29
    assert all_out["summary"]["stopped_after_29_new_pass"] is True
    assert all_out["summary"]["remaining_new_pass_needed"]==0
    assert all_out["status"]=="TARGET_29_NEW_PASS_REACHED"

    # First six unavailable => remaining 29 still reaches target.
    six_out=pipe.run_pipeline(
        build_observations(shell,7),
        order=order,matrix=matrix,registry=registry,shell=shell
    )
    assert six_out["summary"]["observations_received"]==29
    assert six_out["summary"]["formal_new_pass_riders"]==29
    assert six_out["status"]=="TARGET_29_NEW_PASS_REACHED"

    # First seven unavailable => only 28 new PASS, never relax.
    seven_out=pipe.run_pipeline(
        build_observations(shell,8),
        order=order,matrix=matrix,registry=registry,shell=shell
    )
    assert seven_out["summary"]["observations_received"]==28
    assert seven_out["summary"]["formal_new_pass_riders"]==28
    assert seven_out["summary"]["remaining_new_pass_needed"]==1
    assert seven_out["status"]=="TARGET_NOT_REACHED"

    # A stale/prefilled shell cannot be reused.
    stale=deepcopy(shell)
    stale["rows"][0]["race_no"]=1
    must_fail(
        lambda:pipe.run_pipeline(
            [],order=order,matrix=matrix,registry=registry,shell=stale
        ),
        "shell_not_pristine_field_populated",
    )

    # A trusted-family label on an unrelated host is rejected. Other 34 can
    # still satisfy the target, so check the normalization audit explicitly.
    bad_host=build_observations(shell,1)
    bad_host[0]["source_url"]="https://evil.example/racecard"
    bad_host_out=pipe.run_pipeline(
        bad_host,order=order,matrix=matrix,registry=registry,shell=shell
    )
    assert any(
        x.get("reason")=="source_family_hostname_binding_mismatch"
        for x in bad_host_out["normalization"]["rejected_observations"]
    )
    assert bad_host_out["summary"]["formal_new_pass_riders"]==29

    # Same-family conflicting valid assignments fail that candidate closed.
    conflict=build_observations(shell,1)
    conflict.append(
        observation_from_shell(
            shell["rows"][0],suffix="-conflict",race_no=9
        )
    )
    conflict_out=pipe.run_pipeline(
        conflict,order=order,matrix=matrix,registry=registry,shell=shell
    )
    assert conflict_out["normalization"]["status"]=="FAIL_CLOSED"
    assert any(
        d.get("reason")=="same_source_assignment_conflict"
        for d in conflict_out["normalization"]["decisions"]
    )
    assert conflict_out["summary"]["formal_new_pass_riders"]==29

    # Unambiguously next-day capture fails only that candidate; no reconstruction.
    late=build_observations(shell,1)
    d=date.fromisoformat(shell["rows"][0]["race_date"])+timedelta(days=1)
    late[0]["captured_at_jst"]=d.isoformat()+"T00:00:00+09:00"
    late_out=pipe.run_pipeline(
        late,order=order,matrix=matrix,registry=registry,shell=shell
    )
    guard=late_out["finalization"]["post_event_reconstruction_guard"]
    assert guard["blocked_row_count"]==1
    assert guard["blocked_rows"][0]["priority"]==1
    assert late_out["summary"]["formal_new_pass_riders"]==29

    # Six trusted source families agreeing for one candidate count as six
    # distinct corroborations but still only one rider support increment.
    multi=[]
    for family in ("CTC","KDREAMS","WINTICKET","KEIRIN.JP","CHARILOTO","ODDSPARK"):
        multi.append(
            observation_from_shell(
                shell["rows"][0],
                family=family,
                suffix="-"+family.replace(".","_"),
            )
        )
    multi_out=pipe.run_pipeline(
        multi,order=order,matrix=matrix,registry=registry,shell=shell
    )
    row=multi_out["normalization"]["normalized_rows"][0]
    assert row["corroboration_count"]==6
    assert row["fill_status"]=="CONSENSUS_PASS"
    assert multi_out["summary"]["formal_new_pass_riders"]==1

    print("PASS 18/18")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
