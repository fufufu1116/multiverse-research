#!/usr/bin/env python3
"""RESULT-firewalled Rider x Circumference development evaluator v2.

v2 preserves the frozen metric math from v1 but changes the execution order:
authorization is validated *before the race/outcome payload is touched at all*.
This prevents a blocked call from parsing winner targets before denial.

No network access. No payout/odds/prediction/human-comment payloads are accepted.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Mapping

import keirin_rider_circumference_development_evaluator_v1 as v1

S0_BETA=v1.S0_BETA
BOOTSTRAP_REPLICATES=v1.BOOTSTRAP_REPLICATES
BOOTSTRAP_SEED=v1.BOOTSTRAP_SEED
DevelopmentEvaluationError=v1.DevelopmentEvaluationError

_REQUIRED_TRUE=(
    "formal_support_gate_pass",
    "calendar_definition_adopted",
    "formula_frozen",
    "development_membership_frozen_preoutcome",
    "result_join_authorized",
    "source_gates_pass",
    "final_untouched_holdout_excluded",
)

_FORBIDDEN_TOKENS={
    "payout","payouts","odds","prediction","predictions",
    "forecast","forecasts","comment","comments",
    "finish","finishing","result","results","outcome","outcomes",
}
_FORBIDDEN_JP=("払戻","オッズ","予想","コメント","着順","結果")
_ALLOWED_TARGET_FIELDS={"winner_registration"}


def _finite(value,label):
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise DevelopmentEvaluationError(f"{label}_must_be_numeric")
    x=float(value)
    if not math.isfinite(x):
        raise DevelopmentEvaluationError(f"{label}_must_be_finite")
    return x


def authorization_preflight(auth):
    """Validate all static authority gates without touching any race payload."""
    if not isinstance(auth,Mapping):
        raise DevelopmentEvaluationError("authorization_must_be_mapping")

    for key in _REQUIRED_TRUE:
        if auth.get(key) is not True:
            raise DevelopmentEvaluationError(f"authorization_gate_not_true:{key}")

    beta=_finite(auth.get("s0_beta"),"authorization_s0_beta")
    if abs(beta-S0_BETA)>1e-15:
        raise DevelopmentEvaluationError("s0_beta_mutation_detected")

    calendar_id=auth.get("calendar_definition_id")
    if not isinstance(calendar_id,str) or not calendar_id.strip():
        raise DevelopmentEvaluationError("missing_calendar_definition_id")

    for key in ("formula_hash","membership_hash"):
        value=auth.get(key)
        if not isinstance(value,str) or not re.fullmatch(r"[0-9a-f]{64}",value):
            raise DevelopmentEvaluationError(f"invalid_{key}")

    frozen=auth.get("frozen_race_ids")
    if not isinstance(frozen,list) or any(not isinstance(x,str) or not x for x in frozen):
        raise DevelopmentEvaluationError("invalid_frozen_race_ids")
    if len(frozen)!=len(set(frozen)):
        raise DevelopmentEvaluationError("duplicate_frozen_race_id")

    return {
        "calendar_definition_id":calendar_id,
        "formula_hash":auth["formula_hash"],
        "membership_hash":auth["membership_hash"],
        "frozen_race_ids":tuple(frozen),
        "s0_beta":beta,
    }


def _field_tokens(key):
    raw=str(key)
    lowered=raw.lower()
    tokens={x for x in re.split(r"[^a-z0-9]+",lowered) if x}
    return raw,tokens


def _assert_evaluation_payload_clean(races):
    """After authority passes, reject non-target post-decision payload families."""
    if not isinstance(races,list):
        raise DevelopmentEvaluationError("races_must_be_nonempty_list")
    for ri,race in enumerate(races):
        if not isinstance(race,Mapping):
            raise DevelopmentEvaluationError(f"race_must_be_mapping:{ri}")
        for key in race:
            if key in _ALLOWED_TARGET_FIELDS:
                continue
            raw,tokens=_field_tokens(key)
            if tokens & _FORBIDDEN_TOKENS or any(x in raw for x in _FORBIDDEN_JP):
                raise DevelopmentEvaluationError(
                    f"forbidden_non_target_post_decision_field:race:{ri}:{raw}"
                )
        riders=race.get("riders")
        if isinstance(riders,list):
            for i,rider in enumerate(riders):
                if not isinstance(rider,Mapping):
                    continue
                for key in rider:
                    raw,tokens=_field_tokens(key)
                    if tokens & _FORBIDDEN_TOKENS or any(x in raw for x in _FORBIDDEN_JP):
                        raise DevelopmentEvaluationError(
                            f"forbidden_non_target_post_decision_field:rider:{ri}:{i}:{raw}"
                        )


def _membership_check(preflight, normalized):
    observed=[x["race_id"] for x in normalized]
    if set(preflight["frozen_race_ids"])!=set(observed):
        raise DevelopmentEvaluationError("input_race_membership_mismatch")
    if len(observed)!=len(preflight["frozen_race_ids"]):
        raise DevelopmentEvaluationError("input_race_membership_count_mismatch")


def evaluate(authorization,races,bootstrap_replicates=BOOTSTRAP_REPLICATES):
    # SECURITY ORDER IS INTENTIONAL:
    # 1) static authority only
    # 2) only after PASS, touch/scan outcome-bearing payload
    # 3) normalize and verify exact frozen membership
    # 4) apply unchanged v1 metric math
    preflight=authorization_preflight(authorization)
    _assert_evaluation_payload_clean(races)
    normalized=v1._normalize_races(races)
    _membership_check(preflight,normalized)

    out=v1._evaluate_metrics(
        normalized,
        bootstrap_replicates=bootstrap_replicates,
    )
    out.update({
        "record":"KEIRIN_RIDER_CIRCUMFERENCE_DEVELOPMENT_EVALUATION_v2",
        "window":"2026-09-16..2026-09-26 ALL DAY1 STARTS",
        "s0_beta":S0_BETA,
        "authorization_preflight_before_payload_access":True,
        "payload_firewall":"WINNER_REGISTRATION_TARGET_ONLY; PAYOUT_ODDS_PREDICTION_COMMENT_AND_EXTRA_RESULT_FIELDS_FAIL_CLOSED",
        "metric_math_source":"v1 FROZEN PREOUTCOME MATH UNCHANGED",
        "result_used_as_target_only":True,
        "result_used_as_feature":False,
        "payout_used":False,
        "odds_used":False,
        "human_forecast_used":False,
        "network_access":False,
        "runtime":False,
    })
    return out


def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--authorization",required=True)
    ap.add_argument("--races",required=True)
    ap.add_argument("--out")
    args=ap.parse_args()

    # The authorization file is parsed first. The race file is not opened until
    # authorization_preflight has passed.
    auth=json.loads(Path(args.authorization).read_text(encoding="utf-8"))
    authorization_preflight(auth)
    races=json.loads(Path(args.races).read_text(encoding="utf-8"))
    out=evaluate(auth,races)

    rendered=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
    if args.out:
        Path(args.out).write_text(rendered,encoding="utf-8")
    else:
        print(rendered,end="")


if __name__=="__main__":
    main()
