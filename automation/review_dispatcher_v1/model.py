from __future__ import annotations

from automation.review_dispatcher_v1 import model_legacy_v1 as _legacy

for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)

from automation.review_dispatcher_v1.request_arbitration_v6 import (
    exact_current_owner_requests_v6,
    latest_exact_current_owner_request_v6,
)


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
