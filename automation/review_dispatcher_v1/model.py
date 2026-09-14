from __future__ import annotations

from automation.review_dispatcher_v1 import model_legacy_v1 as _legacy

for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)

from automation.review_dispatcher_v1.auditor_upstream_compat_v1 import (
    normalize_auditor_upstream_v1,
)
from automation.review_dispatcher_v1.request_arbitration_v6 import (
    exact_current_owner_requests_v6,
    latest_exact_current_owner_request_v6,
)


def validate_request(request):
    try:
        return _legacy.validate_request(request)
    except _legacy.ReviewContractError as exc:
        if str(exc) != "AUDITOR_UPSTREAM_SCHEMA" or request.get("lane") != "AUDITOR":
            raise
        normalized = dict(request)
        normalize_auditor_upstream_v1(request.get("upstream"))
        # Validate every non-upstream field with the legacy canonical validator.
        # A synthetic legacy-shaped upstream is used only for schema validation;
        # downstream review still verifies durable LAB/T1 evidence independently.
        normalized["upstream"] = {
            "lab_pass_comment": request["upstream"]["lab_result_comment"],
            "lab_request_sha256": "0" * 64,
            "t1_comment": request["upstream"]["lab_result_comment"],
        }
        _legacy.validate_request(normalized)
        return request


def exact_current_owner_requests(
    comments,
    *,
    repo,
    pr,
    lane,
    head,
    tree,
    base,
    main,
):
    return exact_current_owner_requests_v6(
        comments,
        repo=repo,
        pr=pr,
        lane=lane,
        head=head,
        tree=tree,
        base=base,
        main=main,
    )


def latest_exact_current_owner_request(
    comments,
    *,
    repo,
    pr,
    lane,
    head,
    tree,
    base,
    main,
):
    return latest_exact_current_owner_request_v6(
        comments,
        repo=repo,
        pr=pr,
        lane=lane,
        head=head,
        tree=tree,
        base=base,
        main=main,
    )
