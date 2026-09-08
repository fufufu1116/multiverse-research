#!/usr/bin/env python3
from copy import deepcopy
import importlib
import pathlib
import sys

HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))

v5=importlib.import_module("keirin_multisite_final_racecard_normalizer_v5")
v2test=importlib.import_module("keirin_multisite_final_racecard_normalizer_selftest_v2")

URLS={
    "CTC":"https://ctc.gr.jp/schedule/detail.php?id=3720260914",
    "KDREAMS":"https://keirin.kdreams.jp/ito/racecard/37202609140100/",
    "WINTICKET":"https://www.winticket.jp/keirin/ito/racecard/2026091437/1",
    "KEIRIN.JP":"https://www.keirin.jp/pc/racecard/example",
    "KEIRIN_JP":"https://www.keirin.jp/pc/racecard/example2",
    "CHARILOTO":"https://www.chariloto.com/keirin/racecard/example",
    "ODDSPARK":"https://www.oddspark.com/keirin/racecard/example",
}


def obs(family="CTC",**kw):
    x=v2test.obs(family,**kw)
    x["source_url"]=URLS.get(family,"https://unknown.example/racecard")
    return x


def normalize(rows):
    return v5.normalize(v2test.order(),rows)


def main():
    # All six existing source families accept only their bound host roots.
    families=["CTC","KDREAMS","WINTICKET","KEIRIN.JP","CHARILOTO","ODDSPARK"]
    out=normalize([obs(f) for f in families])
    assert out["normalized_row_count"]==1
    assert out["normalized_rows"][0]["corroboration_count"]==6
    assert out["normalized_rows"][0]["fill_status"]=="CONSENSUS_PASS"
    assert out["source_family_hostname_binding"]["status"]=="ENFORCED"

    # Subdomains of an established provider root are allowed.
    sub=obs("CTC")
    sub["source_url"]="https://race.ctc.gr.jp/racecard/example"
    sub_out=normalize([sub])
    assert sub_out["normalized_row_count"]==1

    # Unrelated and suffix-spoof hosts cannot impersonate a trusted family.
    for family,bad_url in [
        ("CTC","https://evil.example/racecard"),
        ("CTC","https://ctc.gr.jp.evil.example/racecard"),
        ("KDREAMS","https://kdreams.example/racecard"),
        ("WINTICKET","https://winticket.jp.evil.example/keirin/racecard"),
        ("KEIRIN.JP","https://keirin.jp.evil.example/pc/racecard"),
        ("CHARILOTO","https://chariloto.com.evil.example/keirin/racecard"),
        ("ODDSPARK","https://oddspark.com.evil.example/keirin/racecard"),
    ]:
        bad=obs(family)
        bad["source_url"]=bad_url
        x=normalize([bad])
        assert x["normalized_row_count"]==0,(family,bad_url,x)
        assert any(
            r.get("reason")=="source_family_hostname_binding_mismatch"
            for r in x["rejected_observations"]
        )

    # KEIRIN_JP alias canonicalizes to KEIRIN.JP and remains one family.
    alias=normalize([obs("KEIRIN.JP"),obs("KEIRIN_JP")])
    assert alias["normalized_row_count"]==1
    assert alias["normalized_rows"][0]["corroboration_count"]==1
    assert alias["normalized_rows"][0]["corroborating_source_families"]==["KEIRIN.JP"]

    # A bad-host snapshot cannot suppress a later valid same-family snapshot.
    bad=obs("CTC")
    bad["source_url"]="https://evil.example/racecard"
    survived=normalize([bad,obs("CTC")])
    assert survived["normalized_row_count"]==1
    assert survived["normalized_rows"][0]["corroboration_count"]==1
    assert any(
        r.get("reason")=="source_family_hostname_binding_mismatch"
        for r in survived["rejected_observations"]
    )

    # Same-family valid assignment conflicts from the correct provider still
    # fail closed under v4 semantics.
    conflict=normalize([obs("CTC",race_no=7),obs("CTC",race_no=8)])
    assert conflict["status"]=="FAIL_CLOSED"
    assert conflict["normalized_row_count"]==0

    # Cross-family conflict remains fail closed.
    cross=normalize([obs("CTC",race_no=7),obs("KDREAMS",race_no=8)])
    assert cross["status"]=="FAIL_CLOSED"
    assert cross["normalized_row_count"]==0

    # Provider host alone is not enough: forbidden result-like paths remain
    # rejected by the inherited namespace/path firewall.
    result_path=obs("CHARILOTO")
    result_path["source_url"]="https://www.chariloto.com/keirin/results/37?year=2026"
    result_out=normalize([result_path])
    assert result_out["normalized_row_count"]==0
    assert any(
        "forbidden_source_namespace" in r.get("reason","")
        for r in result_out["rejected_observations"]
    )

    # v3 exact integer rule is still inherited.
    float_row=obs("KDREAMS")
    float_row["race_no"]=7.9
    float_out=normalize([float_row])
    assert float_out["normalized_row_count"]==0

    print("PASS 16/16")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
