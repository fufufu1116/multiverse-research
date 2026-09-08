# MULTIVERSE Publisher Resilience Integration v1

Status: Research Lane B repository-only Candidate for Issue #245 / parent #201.

RUNTIME: OFF.

## Goal

Compose three already-frozen hardening ideas into one publisher path without changing the fixed shared Lab/Auditor Steps:

1. publish-time canonical request freshness from PR #227;
2. deterministic trusted-result canonicalization from PR #232;
3. existing canonical result receipt recovery from PR #234.

## Integrated flow

For the exact current job:

1. Run the existing Fresh publisher verification and additionally require that the job request is still the canonical latest exact request.
2. Compute the exact result marker.
3. If a trusted result already exists for that marker, select the smallest trusted GitHub comment ID and recover the publish receipt only if the embedded artifact and exact request/head/tree/main binding match.
4. Otherwise call the preserved legacy publisher.
5. If the legacy pre-publication duplicate check loses a race and reports that a current result already exists, Fresh verify again and recover only from the deterministic canonical trusted result.
6. After a new result is posted, Fresh verify the request again and refetch comments. Return a successful receipt only if the newly posted result is the deterministic canonical smallest trusted result.

## Failure properties

- A superseding request appearing before or after result publication prevents a successful stale receipt.
- A concurrent later duplicate result cannot emit the successful receipt used by downstream stages.
- A process crash after durable result publication but before local receipt persistence is recoverable without a second result publication.
- Wrong producer, wrong marker, wrong artifact, or wrong exact binding fails closed.
- Durable noncanonical duplicates may remain visible on GitHub but are non-consumable.

## Compatibility

The adopted publisher implementation is preserved byte-for-byte as `publisher_legacy_v1.py`. `publisher.py` is a thin orchestration wrapper. The canonical validator implementation is similarly preserved as `validator_legacy_v1.py`, while the Candidate validator checks legacy publisher invariants against the preserved file and integration invariants against the wrapper/helpers.

No fixed Independent Lab/Auditor Steps are edited.

## Proof ceiling

`PUBLISHER_FRESHNESS_CANONICAL_RESULT_RECEIPT_RECOVERY_INTEGRATION_REPOSITORY_PREPARATION_ONLY`

No machine-readable review request, Owner Gate, T1, Auditor request, T2, Build/Retry, merge/main/ruleset mutation, Runtime/provider/production/protected-data/live-effect/spend authority.

RUNTIME: OFF.
