#!/usr/bin/env python3
"""Order-independent same-source integrity hardening for final Day1 normalizer v4.

Builds on v3 exact-integer policy and v2 six-source semantics.

Key changes:
- duplicate observations from one source family never inflate corroboration;
- multiple valid observations from the same source family with different
  assignment signatures fail the whole locked candidate closed;
- identical same-family observations are deterministically deduplicated;
- an invalid observation from a family does not make a later valid observation
  from that same family disappear merely because of input order;
- cross-family agreement/conflict behavior remains v2-compatible.

No new URL-domain allowlist is invented here because the current six-source
watch-set does not freeze a hostname-to-family mapping as a formal blocker.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any, Iterable, Mapping

import keirin_multisite_final_racecard_normalizer_v2 as v2
import keirin_multisite_final_racecard_normalizer_v3 as v3

RacecardNormalizerError=v2.RacecardNormalizerError


def _assignment_signature(row: Mapping[str, Any]) -> tuple:
    return (
        row["race_no"],
        row["car_no"],
        row["class"],
        row["style"],
        row["circumference_m"],
    )


def _candidate_key_from_normalized(row: Mapping[str, Any]) -> tuple[str,str,str]:
    return (
        v2._nfkc(row.get("official_registration_number")),
        v2._nfkc(row.get("race_date")),
        v2._venue(row.get("venue")),
    )


def _deterministic_raw_key(raw: Mapping[str, Any]) -> tuple:
    return (
        v2._nfkc(raw.get("source_url")),
        v2._nfkc(raw.get("source_sha256")).lower(),
        v2._nfkc(raw.get("captured_at_jst")),
        v2._nfkc(raw.get("source_namespace")),
        v2._nfkc(raw.get("source_role")),
    )


def _pre_resolve_same_family(
    locked_order: Mapping[str, Any],
    hardened_observations: list[Mapping[str, Any]],
) -> tuple[list[Mapping[str, Any]], dict, list[dict]]:
    """Select at most one valid row per candidate/source family before v2.

    Returns:
      selected observations passed to v3/v2,
      same-family hard conflicts keyed by candidate key,
      extra rejected-observation audit rows.
    """
    candidates=v2._candidate_index(locked_order)
    grouped=defaultdict(list)
    passthrough=[]
    extra_rejects=[]

    for raw in hardened_observations:
        key=v2._candidate_key_from_raw(raw)
        candidate=candidates.get(key)
        if candidate is None:
            passthrough.append(raw)
            continue

        # Any explicit withdrawal/substitution remains visible to v2, which
        # already hard-blocks the candidate independently of source ordering.
        status=v2._nfkc(raw.get("status")).upper()
        if status in v2.WITHDRAWAL_STATUSES:
            passthrough.append(raw)
            continue

        family=v2._source_family(raw)
        grouped[(key,family)].append(raw)

    conflicts=defaultdict(list)

    for (key,family), raws in grouped.items():
        candidate=candidates[key]
        valid=[]
        invalid=[]

        for raw in raws:
            try:
                normalized=v2._validate_complete_observation(raw,candidate)
                valid.append((raw,normalized))
            except v2.RacecardNormalizerError as exc:
                invalid.append((raw,str(exc)))

        if valid:
            by_signature=defaultdict(list)
            for raw,normalized in valid:
                by_signature[_assignment_signature(normalized)].append((raw,normalized))

            if len(by_signature)>1:
                conflicts[key].append({
                    "source_family":family,
                    "assignments":[
                        {
                            "race_no":sig[0],
                            "car_no":sig[1],
                            "class":sig[2],
                            "style":sig[3],
                            "circumference_m":sig[4],
                        }
                        for sig in sorted(by_signature,key=lambda x:tuple(str(v) for v in x))
                    ],
                })
                # Do not pass any valid row for this family. The candidate will
                # be converted to hard FAIL_CLOSED after base normalization.
            else:
                # Same assignment, same family: one deterministic representative.
                representatives=next(iter(by_signature.values()))
                chosen_raw,_=min(representatives,key=lambda pair:_deterministic_raw_key(pair[0]))
                passthrough.append(chosen_raw)

                for raw,_normalized in valid:
                    if raw is chosen_raw:
                        continue
                    extra_rejects.append({
                        "key":key,
                        "source_family":family,
                        "status":"DEDUPED",
                        "reason":"duplicate_source_family_same_assignment_deduped",
                    })

            # Invalid siblings are still audited but cannot erase a valid
            # same-family racecard solely because they appeared first.
            for _raw,reason in invalid:
                extra_rejects.append({
                    "key":key,
                    "source_family":family,
                    "status":"REJECTED",
                    "reason":reason,
                })
        else:
            # No valid observation from this family. Pass one deterministic raw
            # to retain v2's normal rejection semantics and audit the rest.
            if raws:
                chosen=min(raws,key=_deterministic_raw_key)
                passthrough.append(chosen)
                chosen_marked=False
                for raw,reason in invalid:
                    if raw is chosen and not chosen_marked:
                        chosen_marked=True
                        continue
                    extra_rejects.append({
                        "key":key,
                        "source_family":family,
                        "status":"REJECTED",
                        "reason":reason,
                    })

    return passthrough,dict(conflicts),extra_rejects


def normalize(
    locked_order: Mapping[str, Any],
    observations: Iterable[Mapping[str, Any]],
) -> dict:
    hardened=v3._harden_observations(observations)
    selected,conflicts,extra_rejects=_pre_resolve_same_family(
        locked_order,hardened
    )

    # v3 preserves exact-integer input policy while v2 owns the existing
    # cross-family consensus/conflict contract.
    out=v3.normalize(locked_order,selected)

    # Apply same-family conflicts as candidate-level hard blocks. This is the
    # behavior promised by the existing FAIL_CLOSED_NO_SOURCE_PREFERENCE rule.
    if conflicts:
        conflict_keys=set(conflicts)

        out["normalized_rows"]=[
            row for row in out["normalized_rows"]
            if _candidate_key_from_normalized(row) not in conflict_keys
        ]
        out["normalized_row_count"]=len(out["normalized_rows"])

        decisions=[]
        seen=set()
        for d in out["decisions"]:
            key=tuple(d.get("key") or ())
            if key in conflict_keys:
                if key in seen:
                    continue
                seen.add(key)
                decisions.append({
                    "key":key,
                    "priority":d.get("priority"),
                    "status":"CONFLICT_FAIL_CLOSED",
                    "reason":"same_source_assignment_conflict",
                    "same_source_conflicts":conflicts[key],
                })
            else:
                decisions.append(d)

        # Defensive fallback if base output omitted a locked key unexpectedly.
        candidate_index=v2._candidate_index(locked_order)
        for key in sorted(conflict_keys):
            if key not in seen:
                decisions.append({
                    "key":key,
                    "priority":candidate_index[key].get("priority"),
                    "status":"CONFLICT_FAIL_CLOSED",
                    "reason":"same_source_assignment_conflict",
                    "same_source_conflicts":conflicts[key],
                })

        out["decisions"]=sorted(
            decisions,key=lambda d:(d.get("priority",999),str(d.get("key")))
        )
        out["status"]="FAIL_CLOSED"

        for key,details in conflicts.items():
            out["rejected_observations"].append({
                "key":key,
                "status":"REJECTED_HARD_CONFLICT",
                "reason":"same_source_assignment_conflict",
                "same_source_conflicts":details,
            })

    out["rejected_observations"].extend(extra_rejects)
    out["record"]="KEIRIN_MULTISITE_FINAL_RACECARD_NORMALIZATION_OUTPUT_v4"
    out["integer_input_policy"]="RACE_NO_CAR_NO_INTEGER_OR_DIGIT_STRING_ONLY_BOOL_FLOAT_REJECTED"
    out["same_source_policy"]="DEDUP_IDENTICAL_ASSIGNMENT; CONFLICTING_VALID_ASSIGNMENT_FAILS_CANDIDATE_CLOSED"
    out["corroboration_unit"]="DISTINCT_TRUSTED_SOURCE_FAMILY"
    out["input_order_independent_same_family_resolution"]=True
    out["url_domain_family_mapping_added"]=False
    return out


def build_finalizer_manifest(
    shell: Mapping[str, Any],
    locked_order: Mapping[str, Any],
    observations: Iterable[Mapping[str, Any]],
) -> dict:
    result=normalize(locked_order,observations)
    out=deepcopy(dict(shell))
    by_reg={r["official_registration_number"]:r for r in result["normalized_rows"]}
    rows=[]
    for row in out.get("rows") or []:
        reg=v2._nfkc(row.get("official_registration_number"))
        rows.append(deepcopy(by_reg.get(reg,row)))
    out["rows"]=rows
    out["record"]="KEIRIN_35_FINAL_DAY1_PRE_INPUT_MANIFEST_MULTISITE_NORMALIZED_v4"
    out["multisite_normalizer"]="tools/keirin_multisite_final_racecard_normalizer_v4.py"
    out["multisite_normalization"]=result
    out["support_increment_authorized_now"]=0
    out["result_access_authorized"]=False
    out["runtime"]=False
    return out
