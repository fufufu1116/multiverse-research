from __future__ import annotations

from automation.review_dispatcher_v1 import publisher_legacy_v1 as _legacy
from automation.review_dispatcher_v1.publisher_freshness_v1 import (
    assert_job_request_still_canonical,
)

_original_fresh_verify = _legacy._fresh_verify


def _fresh_verify(job):
    comments = _original_fresh_verify(job)
    assert_job_request_still_canonical(job, comments)
    return comments


_legacy._fresh_verify = _fresh_verify

for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)


def main() -> int:
    return _legacy.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (_legacy.ReviewContractError, _legacy.GitHubAppError) as exc:
        print(f"PUBLISH_FIX_REQUIRED:{exc}")
        raise SystemExit(1)
