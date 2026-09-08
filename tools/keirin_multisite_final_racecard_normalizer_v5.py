#!/usr/bin/env python3
"""Trusted source-family ↔ hostname binding for final Day1 normalizer v5.

v5 builds on v4 and binds each of the existing six trusted source families to
the provider hostnames already evidenced in repository watch/audit artifacts.

This closes source-family spoofing such as source_family="CTC" paired with an
unrelated hostname. Path/namespace RESULT/PAYOUT/ODDS/PREDICTION/comment
blocking remains owned by v2/v4 and is preserved.

No new provider family is admitted and no RESULT surface is opened.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

import keirin_multisite_final_racecard_normalizer_v2 as v2
import keirin_multisite_final_racecard_normalizer_v4 as v4

RacecardNormalizerError=v2.RacecardNormalizerError

# Existing repository evidence:
# - KEIRIN_FINAL_DAY1_MULTISITE_WATCH_SET_20260908_v1.json
#   CTC, KDREAMS, WINTICKET, KEIRIN.JP, CHARILOTO target URLs.
# - KEIRIN_MULTISITE_FINAL_RACECARD_NORMALIZER_IMPLEMENTATION_RECEIPT_20260908_v2.json
#   explicitly documents safe oddspark.com hostname handling.
SOURCE_HOST_ROOTS={
    "CTC":"ctc.gr.jp",
    "KDREAMS":"keirin.kdreams.jp",
    "WINTICKET":"winticket.jp",
    "KEIRIN.JP":"keirin.jp",
    "CHARILOTO":"chariloto.com",
    "ODDSPARK":"oddspark.com",
}


def _hostname(value:Any)->str:
    text=v2._nfkc(value)
    if not text:
        return ""
    try:
        parsed=urlsplit(text)
    except ValueError:
        return ""
    return (parsed.hostname or "").lower().rstrip(".")


def _host_is_bound(family:str,host:str)->bool:
    root=SOURCE_HOST_ROOTS.get(family)
    if root is None:
        return False
    return host==root or host.endswith("."+root)


def _filter_host_bound_observations(
    observations:Iterable[Mapping[str,Any]],
)->tuple[list[Mapping[str,Any]],list[dict]]:
    accepted=[]
    rejected=[]
    for raw in observations:
        if not isinstance(raw,Mapping):
            # Preserve v4's existing fail-closed type handling.
            accepted.append(raw)
            continue

        family=v2._source_family(raw)
        if family not in v2.TRUSTED_SOURCE_FAMILIES:
            # Preserve v4/v2's existing untrusted-family rejection semantics.
            accepted.append(raw)
            continue

        host=_hostname(raw.get("source_url"))
        if not _host_is_bound(family,host):
            rejected.append({
                "key":v2._candidate_key_from_raw(raw),
                "source_family":family,
                "observed_hostname":host,
                "expected_host_root":SOURCE_HOST_ROOTS[family],
                "status":"REJECTED",
                "reason":"source_family_hostname_binding_mismatch",
            })
            continue
        accepted.append(raw)
    return accepted,rejected


def normalize(
    locked_order:Mapping[str,Any],
    observations:Iterable[Mapping[str,Any]],
)->dict:
    selected,host_rejects=_filter_host_bound_observations(observations)
    out=v4.normalize(locked_order,selected)
    out["rejected_observations"].extend(host_rejects)
    out["record"]="KEIRIN_MULTISITE_FINAL_RACECARD_NORMALIZATION_OUTPUT_v5"
    out["source_family_hostname_binding"]={
        "status":"ENFORCED",
        "roots":dict(SOURCE_HOST_ROOTS),
        "subdomains_of_bound_root_allowed":True,
        "unrelated_hostname_rejected":True,
        "url_path_namespace_filter_preserved":True,
        "new_source_family_admitted":False,
    }
    return out


def build_finalizer_manifest(
    shell:Mapping[str,Any],
    locked_order:Mapping[str,Any],
    observations:Iterable[Mapping[str,Any]],
)->dict:
    result=normalize(locked_order,observations)
    out=deepcopy(dict(shell))
    by_reg={r["official_registration_number"]:r for r in result["normalized_rows"]}
    rows=[]
    for row in out.get("rows") or []:
        reg=v2._nfkc(row.get("official_registration_number"))
        rows.append(deepcopy(by_reg.get(reg,row)))
    out["rows"]=rows
    out["record"]="KEIRIN_35_FINAL_DAY1_PRE_INPUT_MANIFEST_MULTISITE_NORMALIZED_v5"
    out["multisite_normalizer"]="tools/keirin_multisite_final_racecard_normalizer_v5.py"
    out["multisite_normalization"]=result
    out["support_increment_authorized_now"]=0
    out["result_access_authorized"]=False
    out["runtime"]=False
    return out
