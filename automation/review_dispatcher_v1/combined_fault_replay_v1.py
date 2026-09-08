from __future__ import annotations

from dataclasses import dataclass


class ReplayError(RuntimeError):
    pass


@dataclass(frozen=True)
class Request:
    comment_id: int
    request_id: str
    sha256: str
    predecessor: str | None


@dataclass(frozen=True)
class Result:
    comment_id: int
    request_sha256: str
    trusted: bool = True


@dataclass(frozen=True)
class T2:
    comment_id: int
    request_sha256: str
    auditor_result_comment_id: int
    trusted: bool = True


def canonical_request_chain(requests: list[Request]) -> list[Request]:
    ids = [r.request_id for r in requests]
    if len(ids) != len(set(ids)):
        raise ReplayError("DUPLICATE_REQUEST_ID")
    by_predecessor: dict[str | None, list[Request]] = {}
    for request in requests:
        by_predecessor.setdefault(request.predecessor, []).append(request)
    chain: list[Request] = []
    predecessor: str | None = None
    seen_sha: set[str] = set()
    while predecessor in by_predecessor:
        generation = sorted(by_predecessor[predecessor], key=lambda r: r.comment_id)
        winner = generation[0]
        if winner.sha256 in seen_sha:
            raise ReplayError("REQUEST_CHAIN_CYCLE")
        chain.append(winner)
        seen_sha.add(winner.sha256)
        predecessor = winner.sha256
    known = {r.sha256 for r in chain}
    for request in requests:
        if request in chain:
            continue
        if request.predecessor is not None and request.predecessor not in known:
            # Same-generation losers are allowed only when they point to a canonical predecessor.
            generation = by_predecessor.get(request.predecessor, [])
            if not generation or min(g.comment_id for g in generation) == request.comment_id:
                raise ReplayError("UNKNOWN_OR_LOSER_PREDECESSOR")
    return chain


def assert_job_still_current(job_request_sha256: str, chain: list[Request]) -> None:
    if not chain or chain[-1].sha256 != job_request_sha256:
        raise ReplayError("STALE_JOB_REQUEST")


def canonical_result(results: list[Result], request_sha256: str) -> Result:
    trusted = [r for r in results if r.trusted and r.request_sha256 == request_sha256]
    if not trusted:
        raise ReplayError("NO_TRUSTED_RESULT")
    return min(trusted, key=lambda r: r.comment_id)


def recover_result_receipt(results: list[Result], request_sha256: str, comment_id: int) -> dict:
    winner = canonical_result(results, request_sha256)
    if winner.comment_id != comment_id:
        raise ReplayError("NONCANONICAL_RESULT_RECEIPT")
    return {
        "request_sha256": request_sha256,
        "published_comment_id": winner.comment_id,
        "verdict": "PASS",
        "recovered": True,
    }


def canonical_t2(items: list[T2], request_sha256: str, auditor_result_comment_id: int) -> T2:
    trusted = [
        item for item in items
        if item.trusted
        and item.request_sha256 == request_sha256
        and item.auditor_result_comment_id == auditor_result_comment_id
    ]
    if not trusted:
        raise ReplayError("NO_TRUSTED_T2")
    return min(trusted, key=lambda item: item.comment_id)


def recover_t2_receipt(items: list[T2], request_sha256: str, auditor_result_comment_id: int, comment_id: int) -> dict:
    winner = canonical_t2(items, request_sha256, auditor_result_comment_id)
    if winner.comment_id != comment_id:
        raise ReplayError("NONCANONICAL_T2_RECEIPT")
    return {
        "request_sha256": request_sha256,
        "auditor_comment_id": auditor_result_comment_id,
        "t2_comment_id": winner.comment_id,
        "verdict": "PASS",
        "recovered": True,
    }


def replay_happy_fault_sequence() -> dict:
    # Generation 0 collision: comment 10 wins, comment 11 is a harmless loser.
    first = Request(10, "request-a", "a" * 64, None)
    sibling = Request(11, "request-b", "b" * 64, None)
    # Legitimate supersession advances from the canonical winner only.
    second = Request(20, "request-c", "c" * 64, first.sha256)
    chain = canonical_request_chain([sibling, second, first])
    if [r.comment_id for r in chain] != [10, 20]:
        raise ReplayError("REQUEST_CONVERGENCE_FAILED")

    # A build for the old winner becomes stale after supersession.
    stale_rejected = False
    try:
        assert_job_still_current(first.sha256, chain)
    except ReplayError as exc:
        stale_rejected = str(exc) == "STALE_JOB_REQUEST"
    if not stale_rejected:
        raise ReplayError("STALE_JOB_NOT_REJECTED")
    assert_job_still_current(second.sha256, chain)

    # Concurrent result publication converges to the earliest trusted result.
    results = [
        Result(101, second.sha256),
        Result(100, second.sha256),
        Result(1, second.sha256, trusted=False),
    ]
    result = canonical_result(results, second.sha256)
    if result.comment_id != 100:
        raise ReplayError("RESULT_CONVERGENCE_FAILED")
    result_receipt = recover_result_receipt(results, second.sha256, 100)

    # Concurrent T2 publication converges the same way and is recoverable.
    t2s = [
        T2(201, second.sha256, result.comment_id),
        T2(200, second.sha256, result.comment_id),
        T2(2, second.sha256, result.comment_id, trusted=False),
    ]
    t2 = canonical_t2(t2s, second.sha256, result.comment_id)
    if t2.comment_id != 200:
        raise ReplayError("T2_CONVERGENCE_FAILED")
    t2_receipt = recover_t2_receipt(t2s, second.sha256, result.comment_id, 200)

    return {
        "canonical_request_comments": [r.comment_id for r in chain],
        "canonical_result_comment": result.comment_id,
        "canonical_t2_comment": t2.comment_id,
        "result_receipt_recovered": result_receipt["recovered"],
        "t2_receipt_recovered": t2_receipt["recovered"],
        "verdict": "PASS",
    }
