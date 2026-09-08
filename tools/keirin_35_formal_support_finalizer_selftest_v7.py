#!/usr/bin/env python3
from copy import deepcopy
import importlib
import pathlib
import sys

HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))

v7=importlib.import_module("keirin_35_formal_support_finalizer_v7")
v5test=importlib.import_module("keirin_35_formal_support_finalizer_selftest_v5")


def decision(out,priority):
    return next(x for x in out["decisions"] if x.get("priority")==priority)


def main():
    order,matrix,registry,manifest=v5test.fixture()

    # Existing prospective fixture still reaches the 29-new-rider stop.
    out=v7.finalize(order,matrix,registry,manifest)
    assert out["record"]=="KEIRIN_35_FORMAL_SUPPORT_FINALIZATION_OUTPUT_v7"
    assert out["new_pass_riders"]==29
    assert out["stopped_after_29_new_pass"] is True
    assert out["post_event_reconstruction_guard"]["blocked_row_count"]==0
    assert out["post_event_reconstruction_guard"]["same_day_capture_allowed"] is True
    assert out["post_event_reconstruction_guard"]["exact_pit_cutoff_timestamp_required"] is False

    # Previous-day capture remains eligible.
    prior=deepcopy(manifest)
    prior["rows"][0]["captured_at_jst"]="2026-09-13T23:59:00+09:00"
    prior_out=v7.finalize(order,matrix,registry,prior)
    assert decision(prior_out,1)["status"]=="PASS_FORMAL_SUPPORT"

    # Same-day capture remains eligible under the owner policy.
    same=deepcopy(manifest)
    same["rows"][0]["captured_at_jst"]="2026-09-14T23:59:00+09:00"
    same_out=v7.finalize(order,matrix,registry,same)
    assert decision(same_out,1)["status"]=="PASS_FORMAL_SUPPORT"
    assert same_out["post_event_reconstruction_guard"]["blocked_row_count"]==0

    # UTC input is compared by its actual JST calendar date.
    utc_same=deepcopy(manifest)
    utc_same["rows"][0]["captured_at_jst"]="2026-09-14T14:59:00+00:00"  # 23:59 JST
    utc_same_out=v7.finalize(order,matrix,registry,utc_same)
    assert decision(utc_same_out,1)["status"]=="PASS_FORMAL_SUPPORT"

    utc_next=deepcopy(manifest)
    utc_next["rows"][0]["captured_at_jst"]="2026-09-14T15:00:00+00:00"  # 00:00 JST next day
    utc_next_out=v7.finalize(order,matrix,registry,utc_next)
    assert decision(utc_next_out,1)["status"]=="FAIL_CLOSED"
    assert utc_next_out["post_event_reconstruction_guard"]["blocked_row_count"]==1

    # Explicit next-day/later captures fail only that candidate row; fixed-order
    # processing continues for the remaining candidates.
    late=deepcopy(manifest)
    late["rows"][0]["captured_at_jst"]="2026-09-15T00:00:00+09:00"
    late_out=v7.finalize(order,matrix,registry,late)
    assert decision(late_out,1)["status"]=="FAIL_CLOSED"
    assert late_out["post_event_reconstruction_guard"]["blocked_row_count"]==1
    assert late_out["post_event_reconstruction_guard"]["blocked_rows"][0]["priority"]==1

    much_later=deepcopy(manifest)
    much_later["rows"][0]["captured_at_jst"]="2026-10-01T12:00:00+09:00"
    later_out=v7.finalize(order,matrix,registry,much_later)
    assert decision(later_out,1)["status"]=="FAIL_CLOSED"
    assert later_out["post_event_reconstruction_guard"]["blocked_row_count"]==1

    # Malformed/naive timestamps are not reinterpreted here; v6/v5's existing
    # timestamp validation remains responsible and must fail the candidate.
    naive=deepcopy(manifest)
    naive["rows"][0]["captured_at_jst"]="2026-09-13T20:00:00"
    naive_out=v7.finalize(order,matrix,registry,naive)
    assert decision(naive_out,1)["status"]=="FAIL_CLOSED"

    malformed=deepcopy(manifest)
    malformed["rows"][0]["captured_at_jst"]="not-a-time"
    malformed_out=v7.finalize(order,matrix,registry,malformed)
    assert decision(malformed_out,1)["status"]=="FAIL_CLOSED"

    print("PASS 10/10")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
