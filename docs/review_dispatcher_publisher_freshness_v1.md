# MULTIVERSE Publish-Time Canonical Request Freshness v1

Status: repository-only Research Lane B Candidate for Issue #226 / parent #201.

RUNTIME: OFF.

## Problem

The fixed publisher revalidates PR/head/tree/main, the exact original request comment, its canonical SHA256, and owner authorship before publishing a PASS result. It then fetches all PR comments for duplicate-result protection. However, it does not prove that the job request is still the canonical latest exact request at publish time.

A legitimate same-envelope superseding request can therefore appear after dispatcher discovery but before result publication. Without an additional freshness check, the old build may still publish a PASS bound to a request that is no longer current.

## Design

After the existing publisher `_fresh_verify(job)` has fetched the complete current comment set, re-run the canonical request selector using the job's exact repo/PR/lane/head/tree/base/main envelope.

Require all three to match the job:

- canonical request comment ID == `job.request_comment`;
- canonical request SHA256 == `job.request_sha256`;
- canonical request JSON == `job.request`.

If any mismatch exists, publication fails closed before GitHub App result publication.

## Compatibility

This hardening deliberately calls the existing public `latest_exact_current_owner_request` function. Therefore it works with today's strict predecessor-chain model and automatically follows any separately adopted successor request-selection policy, including deterministic collision arbitration, without coupling this Candidate to that successor.

The current publisher implementation is preserved byte-for-byte as `publisher_legacy_v1.py`. A thin `publisher.py` compatibility wrapper patches only `_fresh_verify` to add the canonical-current assertion, then re-exports the legacy publisher surface.

## Safety properties

- request comment mutation remains rejected by the existing legacy verification;
- main/head/tree/base drift remains rejected by the existing legacy verification;
- a newer legitimate superseding request prevents stale PASS publication;
- current request publication remains unchanged;
- duplicate result protection remains unchanged;
- no shared Independent Lab/Auditor Steps change is required.

## Proof ceiling

`PUBLISH_TIME_CANONICAL_REQUEST_FRESHNESS_REPOSITORY_PREPARATION_ONLY`

No machine-readable review request, Owner Gate, T1, Auditor request, Build/Retry, shared-Step mutation, merge/main/ruleset mutation, Runtime/provider/production/protected-data/live-effect/spend authority.

RUNTIME: OFF.
