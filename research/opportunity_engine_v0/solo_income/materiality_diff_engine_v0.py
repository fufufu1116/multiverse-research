#!/usr/bin/env python3
"""Deterministic materiality classifier for normalized vendor facts.

Research-only utility. It does not fetch vendor pages or publish anything.
Input snapshots are normalized evidence rows produced by a separate extractor/reviewer.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from typing import Any, Dict, List

MATERIAL_FIELDS = {
    "price": "PRICE",
    "billing_basis": "BILLING_BASIS",
    "minimum_or_bucket_rule": "MINIMUM_SEATS_OR_BUCKET",
    "billable_actor_rule": "BILLABLE_ACTOR",
    "currency_tax_basis": "CURRENCY_OR_TAX",
    "eligibility_region": "ELIGIBILITY_OR_REGION",
    "feature_state": "FEATURE_INCLUDED_OR_REMOVED",
    "ai_packaging_credit_model": "AI_PACKAGING_OR_CREDIT_MODEL",
    "plan_generation_or_migration_state": "PLAN_GENERATION_OR_MIGRATION",
    "effective_date": "DEPRECATION_OR_EFFECTIVE_DATE",
    "term_commitment_renewal_refund": "TERM_COMMITMENT_RENEWAL_REFUND",
}

HUMAN_REVIEW_STATES = {"CONFLICTING", "NOT_FOUND", "REQUIRES_VENDOR_CONFIRMATION"}


@dataclass
class Change:
    field: str
    category: str
    before: Any
    after: Any
    human_review: bool
    reason: str


def classify(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    changes: List[Change] = []

    # Evidence-state degradation is independently material even if normalized value is unchanged.
    b_state = before.get("evidence_state", "NOT_FOUND")
    a_state = after.get("evidence_state", "NOT_FOUND")
    if b_state != a_state:
        review = a_state in HUMAN_REVIEW_STATES
        changes.append(Change(
            field="evidence_state",
            category="UNKNOWN_OR_CONFLICTING" if review else "EVIDENCE_STATE",
            before=b_state,
            after=a_state,
            human_review=review,
            reason="Evidence confidence/state changed; preserve uncertainty rather than auto-resolving it.",
        ))

    for field, category in MATERIAL_FIELDS.items():
        if before.get(field) == after.get(field):
            continue
        force_review = category == "PLAN_GENERATION_OR_MIGRATION"
        if after.get("evidence_state") in HUMAN_REVIEW_STATES:
            force_review = True
        changes.append(Change(
            field=field,
            category=category,
            before=before.get(field),
            after=after.get(field),
            human_review=force_review,
            reason=(
                "Plan-generation/migration drift can invalidate the prior decision boundary."
                if category == "PLAN_GENERATION_OR_MIGRATION"
                else "Decision-material normalized fact changed."
            ),
        ))

    if not changes:
        status = "NO_MATERIAL_NORMALIZED_CHANGE"
        human_review = False
    else:
        human_review = any(c.human_review for c in changes)
        status = "HUMAN_REVIEW_REQUIRED" if human_review else "RECOMPUTE_DECISION_ROWS"

    return {
        "status": status,
        "human_review_required": human_review,
        "changes": [asdict(c) for c in changes],
    }


def _self_test() -> None:
    base = {
        "price": "$9/user/month",
        "billing_basis": "per user per month",
        "minimum_or_bucket_rule": None,
        "billable_actor_rule": "Workspace member",
        "currency_tax_basis": "USD / tax not normalized",
        "eligibility_region": "public global page",
        "feature_state": "Brain AI add-on",
        "ai_packaging_credit_model": "1,500 Super Credits/user/month",
        "plan_generation_or_migration_state": "CLASSIC_ADDON_PUBLIC_MODEL",
        "effective_date": None,
        "term_commitment_renewal_refund": "auto-renewing add-on",
        "evidence_state": "CONFIRMED",
    }

    same = dict(base)
    assert classify(base, same)["status"] == "NO_MATERIAL_NORMALIZED_CHANGE"

    price_change = dict(base, price="$10/user/month")
    r = classify(base, price_change)
    assert r["status"] == "RECOMPUTE_DECISION_ROWS"
    assert r["changes"][0]["category"] == "PRICE"

    migration = dict(base, plan_generation_or_migration_state="NEW_INCLUDED_AI_PLAN")
    r = classify(base, migration)
    assert r["status"] == "HUMAN_REVIEW_REQUIRED"
    assert r["human_review_required"] is True

    conflict = dict(base, evidence_state="CONFLICTING")
    r = classify(base, conflict)
    assert r["status"] == "HUMAN_REVIEW_REQUIRED"

    print("SELF_TEST_PASS")


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        _self_test()
        return
    if len(sys.argv) != 3:
        print("usage: materiality_diff_engine_v0.py BEFORE.json AFTER.json", file=sys.stderr)
        raise SystemExit(2)
    with open(sys.argv[1], encoding="utf-8") as f:
        before = json.load(f)
    with open(sys.argv[2], encoding="utf-8") as f:
        after = json.load(f)
    print(json.dumps(classify(before, after), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
