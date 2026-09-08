#!/usr/bin/env python3
from copy import deepcopy
import importlib
import pathlib
import sys

HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))

v3=importlib.import_module("keirin_multisite_final_racecard_normalizer_v3")
v2test=importlib.import_module("keirin_multisite_final_racecard_normalizer_selftest_v2")


def main():
    locked=v2test.order()

    good=v2test.obs("CTC")
    out=v3.normalize(locked,[good])
    assert out["normalized_row_count"]==1
    assert out["normalized_rows"][0]["race_no"]==7
    assert out["normalized_rows"][0]["car_no"]==3
    assert out["record"]=="KEIRIN_MULTISITE_FINAL_RACECARD_NORMALIZATION_OUTPUT_v3"

    digit=deepcopy(good)
    digit["race_no"]="7"
    digit["car_no"]="3"
    digit_out=v3.normalize(locked,[digit])
    assert digit_out["normalized_row_count"]==1
    assert digit_out["normalized_rows"][0]["race_no"]==7
    assert digit_out["normalized_rows"][0]["car_no"]==3

    for field,value in [
        ("race_no",7.9),
        ("car_no",3.2),
        ("race_no",True),
        ("car_no",False),
        ("race_no","7.0"),
        ("car_no","3.0"),
    ]:
        bad=deepcopy(good)
        bad[field]=value
        badout=v3.normalize(locked,[bad])
        assert badout["normalized_row_count"]==0,(field,value,badout)
        assert any(
            r.get("reason")=="invalid_race_or_car_number"
            for r in badout["rejected_observations"]
        ),(field,value,badout)

    # Cross-source consensus remains unchanged.
    consensus=v3.normalize(
        locked,
        [v2test.obs("CTC"),v2test.obs("KEIRIN.JP")],
    )
    assert consensus["normalized_row_count"]==1
    assert consensus["normalized_rows"][0]["fill_status"]=="CONSENSUS_PASS"
    assert consensus["normalized_rows"][0]["corroboration_count"]==2

    # Genuine assignment conflict remains fail-closed.
    conflict=v3.normalize(
        locked,
        [v2test.obs("CTC"),v2test.obs("KDREAMS",race_no=8)],
    )
    assert conflict["status"]=="FAIL_CLOSED"
    assert conflict["normalized_row_count"]==0

    print("PASS 11/11")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
