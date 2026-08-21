#!/usr/bin/env python3
"""Noncanonical R1 source vertical-slice prototype v1.

Purpose:
- exercise one no-contact Source-candidate flow with fake records only;
- demonstrate idempotent convergence, finite retry, fencing-token/CAS safety,
  and concise Owner exception reporting;
- reuse an already-issued authorization decision rather than inventing a
  second permission authority.

This prototype performs no network access, no source admission, no real/live
PRE collection, no external contact, no RESULT/PAYOUT or holdout access, and
no model/economic work. It does NOT claim exactly-once execution.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, Optional


class R1Error(RuntimeError):
    pass


class StaleState(R1Error):
    pass


class AuthorizationDenied(R1Error):
    pass


class FencingConflict(R1Error):
    pass


class ReceiptConflict(R1Error):
    pass


class DeadLettered(R1Error):
    pass


@dataclass
class CacheRecord:
    candidate_id: str
    docs_hash: str
    state: str
    version: int = 0
    verdict_reason: str = ""


@dataclass
class Task:
    task_id: str
    idempotency_key: str
    candidate_id: str
    input_hash: str
    expected_cache_version: int
    retry_budget: int = 2
    attempt_count: int = 0
    fencing_token: int = 0
    lease_owner: Optional[str] = None
    checkpoint_ref: Optional[str] = None
    durable_receipt_ref: Optional[str] = None
    dead_letter_reason: Optional[str] = None


@dataclass(frozen=True)
class Receipt:
    receipt_id: str
    idempotency_key: str
    payload_hash: str
    candidate_id: str
    committed_state: str
    cache_version_after: int


@dataclass
class R1Engine:
    pinned_main: str
    cache: Dict[str, CacheRecord] = field(default_factory=dict)
    tasks: Dict[str, Task] = field(default_factory=dict)
    task_by_idempotency: Dict[str, str] = field(default_factory=dict)
    receipts_by_idempotency: Dict[str, Receipt] = field(default_factory=dict)

    @staticmethod
    def _digest(value: object) -> str:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _require_current_main(self, current_main: str) -> None:
        if current_main != self.pinned_main:
            raise StaleState(f"STALE_CANONICAL_MAIN:{current_main}")

    def preflight(
        self,
        *,
        current_main: str,
        authorization_decision: str,
        protected_data_requested: bool = False,
    ) -> None:
        self._require_current_main(current_main)
        if protected_data_requested:
            raise AuthorizationDenied("R1_SCOPE_PROHIBITS_PROTECTED_DATA")
        if authorization_decision != "ALLOW":
            raise AuthorizationDenied("EXISTING_AUTHORIZATION_DECISION_NOT_ALLOW")

    def seed_reviewed_no_admission(self, candidate_id: str, docs_hash: str) -> None:
        self.cache[candidate_id] = CacheRecord(
            candidate_id=candidate_id,
            docs_hash=docs_hash,
            state="REVIEWED_NO_ADMISSION",
            version=1,
            verdict_reason="FAKE_SEED_FOR_SELFTEST",
        )

    def inspect_candidate(
        self,
        *,
        current_main: str,
        candidate_id: str,
        docs_hash: str,
        authorization_decision: str = "ALLOW",
    ) -> Optional[Task]:
        self.preflight(
            current_main=current_main,
            authorization_decision=authorization_decision,
        )
        existing = self.cache.get(candidate_id)
        if existing and existing.docs_hash == docs_hash:
            if existing.state in {
                "REVIEWED_NO_ADMISSION",
                "EXPLICIT_INELIGIBLE_WHEN_EVIDENCE_SUPPORTS_IT",
            }:
                return None
            if existing.state in {"REVIEW_REQUIRED", "CHANGED_REVIEW_REQUIRED"}:
                idem = f"source-review:{candidate_id}:{docs_hash}"
                old_task_id = self.task_by_idempotency.get(idem)
                if old_task_id:
                    return self.tasks[old_task_id]

        if existing is None:
            record = CacheRecord(
                candidate_id=candidate_id,
                docs_hash=docs_hash,
                state="REVIEW_REQUIRED",
                version=0,
            )
            self.cache[candidate_id] = record
        else:
            existing.docs_hash = docs_hash
            existing.state = "CHANGED_REVIEW_REQUIRED"
            existing.version += 1
            existing.verdict_reason = ""
            record = existing

        idem = f"source-review:{candidate_id}:{docs_hash}"
        old_task_id = self.task_by_idempotency.get(idem)
        if old_task_id:
            return self.tasks[old_task_id]

        task_id = f"task-{self._digest(idem)[:16]}"
        task = Task(
            task_id=task_id,
            idempotency_key=idem,
            candidate_id=candidate_id,
            input_hash=docs_hash,
            expected_cache_version=record.version,
        )
        self.tasks[task_id] = task
        self.task_by_idempotency[idem] = task_id
        return task

    def checkpoint(self, task_id: str, checkpoint_ref: str) -> None:
        self.tasks[task_id].checkpoint_ref = checkpoint_ref

    def acquire_lease(self, task_id: str, worker_id: str) -> int:
        task = self.tasks[task_id]
        if task.dead_letter_reason:
            raise DeadLettered(task.dead_letter_reason)
        task.fencing_token += 1
        task.lease_owner = worker_id
        return task.fencing_token

    def record_failure(self, task_id: str, reason: str) -> None:
        task = self.tasks[task_id]
        task.attempt_count += 1
        if task.attempt_count > task.retry_budget:
            task.dead_letter_reason = reason

    def commit_review(
        self,
        *,
        current_main: str,
        task_id: str,
        fencing_token: int,
        authorization_decision: str,
        committed_state: str,
        verdict_reason: str,
    ) -> Receipt:
        self.preflight(
            current_main=current_main,
            authorization_decision=authorization_decision,
        )
        task = self.tasks[task_id]
        if task.dead_letter_reason:
            raise DeadLettered(task.dead_letter_reason)

        payload = {
            "task_id": task.task_id,
            "candidate_id": task.candidate_id,
            "input_hash": task.input_hash,
            "committed_state": committed_state,
            "verdict_reason": verdict_reason,
        }
        payload_hash = self._digest(payload)

        # A retry after "state committed but transport ACK lost" returns the
        # same durable receipt if and only if the requested payload is equal.
        old_receipt = self.receipts_by_idempotency.get(task.idempotency_key)
        if old_receipt:
            if old_receipt.payload_hash != payload_hash:
                raise ReceiptConflict("IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD")
            return old_receipt

        if fencing_token != task.fencing_token:
            raise FencingConflict(
                f"STALE_FENCING_TOKEN:{fencing_token}:CURRENT:{task.fencing_token}"
            )

        record = self.cache[task.candidate_id]
        if record.version != task.expected_cache_version:
            raise StaleState(
                f"STALE_CACHE_VERSION:{task.expected_cache_version}:CURRENT:{record.version}"
            )

        if committed_state not in {
            "REVIEWED_NO_ADMISSION",
            "EXPLICIT_INELIGIBLE_WHEN_EVIDENCE_SUPPORTS_IT",
        }:
            raise R1Error(f"R1_CANNOT_COMMIT_STATE:{committed_state}")

        record.state = committed_state
        record.verdict_reason = verdict_reason
        record.version += 1

        receipt = Receipt(
            receipt_id=f"receipt-{payload_hash[:16]}",
            idempotency_key=task.idempotency_key,
            payload_hash=payload_hash,
            candidate_id=task.candidate_id,
            committed_state=committed_state,
            cache_version_after=record.version,
        )
        self.receipts_by_idempotency[task.idempotency_key] = receipt
        task.durable_receipt_ref = receipt.receipt_id
        return receipt

    @staticmethod
    def owner_view(*, changed: str, blocked: Optional[str] = None) -> dict:
        if blocked:
            return {
                "what_changed": changed,
                "what_ran_automatically": "SAFE_INTERNAL_STEPS_ONLY",
                "what_did_not_run": "BLOCKED_STEP_NOT_EXECUTED",
                "what_is_blocked": blocked,
                "owner_action_required": True,
                "next_safe_action": "OWNER_DECISION_OR_REQUIRED_REVIEW",
            }
        return {
            "what_changed": changed,
            "what_ran_automatically": "SOURCE_CANDIDATE_INTERNAL_AUDIT_FLOW",
            "what_did_not_run": "NO_EXTERNAL_OR_PROTECTED_ACTIONS",
            "what_is_blocked": "NONE",
            "owner_action_required": False,
            "next_safe_action": "NONE",
        }


def run_selftest() -> int:
    MAIN = "40a1522ad74f6ef7c82c5c2b948ee775d2133f56"

    e = R1Engine(MAIN)
    e.seed_reviewed_no_admission("s1", "h1")
    assert e.inspect_candidate(current_main=MAIN, candidate_id="s1", docs_hash="h1") is None

    t1 = e.inspect_candidate(current_main=MAIN, candidate_id="s1", docs_hash="h2")
    t2 = e.inspect_candidate(current_main=MAIN, candidate_id="s1", docs_hash="h2")
    assert t1 is not None and t2 is not None and t1.task_id == t2.task_id

    tok_a = e.acquire_lease(t1.task_id, "worker-a")
    e.checkpoint(t1.task_id, "checkpoint://fake/1")
    tok_b = e.acquire_lease(t1.task_id, "worker-b")
    assert tok_b > tok_a
    assert e.tasks[t1.task_id].checkpoint_ref == "checkpoint://fake/1"
    try:
        e.commit_review(
            current_main=MAIN,
            task_id=t1.task_id,
            fencing_token=tok_a,
            authorization_decision="ALLOW",
            committed_state="REVIEWED_NO_ADMISSION",
            verdict_reason="FAKE_TEST",
        )
        raise AssertionError("old worker commit should fail")
    except FencingConflict:
        pass

    r1 = e.commit_review(
        current_main=MAIN,
        task_id=t1.task_id,
        fencing_token=tok_b,
        authorization_decision="ALLOW",
        committed_state="REVIEWED_NO_ADMISSION",
        verdict_reason="FAKE_TEST",
    )
    r2 = e.commit_review(
        current_main=MAIN,
        task_id=t1.task_id,
        fencing_token=tok_b,
        authorization_decision="ALLOW",
        committed_state="REVIEWED_NO_ADMISSION",
        verdict_reason="FAKE_TEST",
    )
    assert r1 == r2

    try:
        e.commit_review(
            current_main=MAIN,
            task_id=t1.task_id,
            fencing_token=tok_b,
            authorization_decision="ALLOW",
            committed_state="REVIEWED_NO_ADMISSION",
            verdict_reason="DIFFERENT",
        )
        raise AssertionError("different payload should conflict")
    except ReceiptConflict:
        pass

    try:
        e.inspect_candidate(current_main="stale", candidate_id="s2", docs_hash="h")
        raise AssertionError("stale main should fail")
    except StaleState:
        pass

    try:
        e.inspect_candidate(
            current_main=MAIN,
            candidate_id="s2",
            docs_hash="h",
            authorization_decision="DENY",
        )
        raise AssertionError("DENY should fail")
    except AuthorizationDenied:
        pass

    try:
        e.preflight(
            current_main=MAIN,
            authorization_decision="ALLOW",
            protected_data_requested=True,
        )
        raise AssertionError("protected data request should fail")
    except AuthorizationDenied:
        pass

    e2 = R1Engine(MAIN)
    t = e2.inspect_candidate(current_main=MAIN, candidate_id="s3", docs_hash="h3")
    assert t is not None
    e2.record_failure(t.task_id, "timeout")
    e2.record_failure(t.task_id, "timeout")
    assert e2.tasks[t.task_id].dead_letter_reason is None
    e2.record_failure(t.task_id, "timeout")
    assert e2.tasks[t.task_id].dead_letter_reason == "timeout"
    try:
        e2.acquire_lease(t.task_id, "worker")
        raise AssertionError("dead-lettered task should not reacquire")
    except DeadLettered:
        pass

    ok = e.owner_view(changed="SOURCE_AUDIT_CACHE_UPDATED")
    assert ok["owner_action_required"] is False
    blocked = e.owner_view(changed="NO_CANONICAL_CHANGE", blocked="OWNER_GATE_REQUIRED")
    assert blocked["owner_action_required"] is True

    print("MULTIVERSE_R1_SOURCE_VERTICAL_SLICE_PROTOTYPE_SELFTEST_PASS")
    print("NETWORK_ACCESS_PERFORMED=false")
    print("SOURCE_ADMISSION_PERFORMED=false")
    print("REAL_LIVE_PRE_ACCESSED=false")
    print("EXTERNAL_PROVIDER_CONTACT_PERFORMED=false")
    print("RESULT_PAYOUT_ACCESSED=false")
    print("HOLDOUT_ACCESSED=false")
    print("MODEL_PROMOTION_PERFORMED=false")
    print("EXACTLY_ONCE_CLAIM=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_selftest())
