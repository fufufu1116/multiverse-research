#!/usr/bin/env python3
"""Deterministic fake-worker rehearsal for bounded R1 canary preparation.

This is not runtime activation. It uses temporary local storage and synthetic metadata only.
"""
import argparse
import json
import tempfile
from pathlib import Path

from multiverse_r1_auth_v1 import AuthorizationDenied
from multiverse_r1_engine_v1 import CANONICAL_DESIGN_MERGE, DeadLettered, FencingConflict, R1Engine
from multiverse_r1_source_vertical_slice_v2 import auth, runtime
from multiverse_r1_state_v1 import PersistentStore, StaleState


def expect(exc, fn):
    try:
        fn()
    except exc:
        return True
    raise AssertionError(f"expected {exc.__name__}")


def takeover_and_restart_rehearsal():
    m = CANONICAL_DESIGN_MERGE
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        store = PersistentStore(root)
        engine = R1Engine(store, m)
        router = "router"
        candidate = "canary-source-a"
        docs_hash = "fake-docs-a-v1"
        inspect_auth = auth(
            "R1_SOURCE_CACHE_INSPECT_OR_STAGE",
            f"source-candidate:{candidate}",
            "P1_REVERSIBLE_INTERNAL_WRITE",
            "PUBLIC_TERMS_METADATA_ONLY",
            router,
        )
        task = engine.inspect_candidate(
            current_main=m,
            candidate_id=candidate,
            docs_hash=docs_hash,
            authorization=inspect_auth,
            auth_runtime=runtime(router),
        )
        assert task == engine.inspect_candidate(
            current_main=m,
            candidate_id=candidate,
            docs_hash=docs_hash,
            authorization=inspect_auth,
            auth_runtime=runtime(router),
        )

        worker_a = "worker-a"
        lease_a_auth = auth(
            "R1_TASK_ACQUIRE_LEASE", f"task:{task}", "P1_REVERSIBLE_INTERNAL_WRITE", "INTERNAL_R1_STATE_ONLY", worker_a
        )
        epoch_a = engine.acquire_lease(
            current_main=m,
            task_id=task,
            worker_id=worker_a,
            now_tick=1,
            lease_ticks=5,
            authorization=lease_a_auth,
            auth_runtime=runtime(worker_a),
        )
        checkpoint_a_auth = auth(
            "R1_TASK_CHECKPOINT", f"task:{task}", "P1_REVERSIBLE_INTERNAL_WRITE", "INTERNAL_R1_STATE_ONLY", worker_a
        )
        engine.checkpoint(
            current_main=m,
            task_id=task,
            worker_id=worker_a,
            lease_epoch=epoch_a,
            now_tick=2,
            checkpoint_ref="phase-a-complete",
            authorization=checkpoint_a_auth,
            auth_runtime=runtime(worker_a),
        )

        worker_b = "worker-b"
        lease_b_auth = auth(
            "R1_TASK_ACQUIRE_LEASE", f"task:{task}", "P1_REVERSIBLE_INTERNAL_WRITE", "INTERNAL_R1_STATE_ONLY", worker_b
        )
        epoch_b = engine.acquire_lease(
            current_main=m,
            task_id=task,
            worker_id=worker_b,
            now_tick=7,
            lease_ticks=10,
            authorization=lease_b_auth,
            auth_runtime=runtime(worker_b),
        )
        assert epoch_b > epoch_a
        before = store.read()["tasks"][task]
        assert before["checkpoint_ref"] == "phase-a-complete"
        attempts_before = before["attempt_count"]

        expect(
            FencingConflict,
            lambda: engine.checkpoint(
                current_main=m,
                task_id=task,
                worker_id=worker_a,
                lease_epoch=epoch_a,
                now_tick=8,
                checkpoint_ref="stale-overwrite",
                authorization=checkpoint_a_auth,
                auth_runtime=runtime(worker_a),
            ),
        )
        failure_a_auth = auth(
            "R1_TASK_RECORD_FAILURE", f"task:{task}", "P1_REVERSIBLE_INTERNAL_WRITE", "INTERNAL_R1_STATE_ONLY", worker_a
        )
        expect(
            FencingConflict,
            lambda: engine.record_failure(
                current_main=m,
                task_id=task,
                worker_id=worker_a,
                lease_epoch=epoch_a,
                now_tick=8,
                reason="stale-worker-must-not-poison",
                authorization=failure_a_auth,
                auth_runtime=runtime(worker_a),
            ),
        )
        after_stale = store.read()["tasks"][task]
        assert after_stale["checkpoint_ref"] == "phase-a-complete"
        assert after_stale["attempt_count"] == attempts_before
        assert after_stale["dead_letter_reason"] is None

        commit_a_auth = auth(
            "R1_SOURCE_REVIEW_COMMIT", f"task:{task}", "P1_REVERSIBLE_INTERNAL_WRITE", "PUBLIC_TERMS_METADATA_ONLY", worker_a
        )
        expect(
            FencingConflict,
            lambda: engine.commit_review(
                current_main=m,
                task_id=task,
                worker_id=worker_a,
                lease_epoch=epoch_a,
                now_tick=8,
                committed_state="REVIEWED_NO_ADMISSION",
                verdict_reason="stale worker",
                evidence_refs=["fake-evidence"],
                authorization=commit_a_auth,
                auth_runtime=runtime(worker_a),
            ),
        )

        checkpoint_b_auth = auth(
            "R1_TASK_CHECKPOINT", f"task:{task}", "P1_REVERSIBLE_INTERNAL_WRITE", "INTERNAL_R1_STATE_ONLY", worker_b
        )
        engine.checkpoint(
            current_main=m,
            task_id=task,
            worker_id=worker_b,
            lease_epoch=epoch_b,
            now_tick=8,
            checkpoint_ref="phase-b-complete",
            authorization=checkpoint_b_auth,
            auth_runtime=runtime(worker_b),
        )
        commit_b_auth = auth(
            "R1_SOURCE_REVIEW_COMMIT", f"task:{task}", "P1_REVERSIBLE_INTERNAL_WRITE", "PUBLIC_TERMS_METADATA_ONLY", worker_b
        )
        receipt = engine.commit_review(
            current_main=m,
            task_id=task,
            worker_id=worker_b,
            lease_epoch=epoch_b,
            now_tick=9,
            committed_state="REVIEWED_NO_ADMISSION",
            verdict_reason="fake public terms review completed",
            evidence_refs=["fake-evidence"],
            authorization=commit_b_auth,
            auth_runtime=runtime(worker_b),
        )

        idem = engine.idem(candidate, docs_hash)
        del engine
        del store
        restarted_store = PersistentStore(root)
        restarted_engine = R1Engine(restarted_store, m)
        replay = restarted_engine.commit_review(
            current_main=m,
            task_id=task,
            worker_id=worker_b,
            lease_epoch=epoch_b,
            now_tick=10,
            committed_state="REVIEWED_NO_ADMISSION",
            verdict_reason="fake public terms review completed",
            evidence_refs=["fake-evidence"],
            authorization=commit_b_auth,
            auth_runtime=runtime(worker_b),
        )
        assert replay == receipt
        read_auth = auth(
            "R1_RECEIPT_READ",
            f"receipt-idempotency:{idem}",
            "P0_READ_PUBLIC_OR_CANONICAL",
            "INTERNAL_R1_RECEIPT_ONLY",
            "reader",
        )
        assert restarted_engine.read_receipt(
            idempotency_key=idem, authorization=read_auth, auth_runtime=runtime("reader")
        ) == receipt
        assert receipt["worker_id"] == worker_b
        assert receipt["canonical_main"] == m
        return {
            "duplicate_delivery_converged": True,
            "takeover_preserved_checkpoint": True,
            "stale_worker_checkpoint_denied": True,
            "stale_worker_failure_poisoning_denied": True,
            "stale_worker_commit_denied": True,
            "lost_ack_process_restart_converged": True,
        }


def drift_and_fail_closed_rehearsal():
    m = CANONICAL_DESIGN_MERGE
    with tempfile.TemporaryDirectory() as td:
        store = PersistentStore(Path(td))
        engine = R1Engine(store, m)
        router = "router-drift"
        candidate = "canary-source-b"
        inspect_v1 = auth(
            "R1_SOURCE_CACHE_INSPECT_OR_STAGE",
            f"source-candidate:{candidate}",
            "P1_REVERSIBLE_INTERNAL_WRITE",
            "PUBLIC_TERMS_METADATA_ONLY",
            router,
        )
        old_task = engine.inspect_candidate(
            current_main=m,
            candidate_id=candidate,
            docs_hash="fake-docs-b-v1",
            authorization=inspect_v1,
            auth_runtime=runtime(router),
        )
        old_worker = "worker-old-docs"
        old_lease_auth = auth(
            "R1_TASK_ACQUIRE_LEASE", f"task:{old_task}", "P1_REVERSIBLE_INTERNAL_WRITE", "INTERNAL_R1_STATE_ONLY", old_worker
        )
        old_epoch = engine.acquire_lease(
            current_main=m,
            task_id=old_task,
            worker_id=old_worker,
            now_tick=1,
            lease_ticks=20,
            authorization=old_lease_auth,
            auth_runtime=runtime(old_worker),
        )
        new_task = engine.inspect_candidate(
            current_main=m,
            candidate_id=candidate,
            docs_hash="fake-docs-b-v2",
            authorization=inspect_v1,
            auth_runtime=runtime(router),
        )
        assert new_task != old_task
        old_commit_auth = auth(
            "R1_SOURCE_REVIEW_COMMIT", f"task:{old_task}", "P1_REVERSIBLE_INTERNAL_WRITE", "PUBLIC_TERMS_METADATA_ONLY", old_worker
        )
        expect(
            StaleState,
            lambda: engine.commit_review(
                current_main=m,
                task_id=old_task,
                worker_id=old_worker,
                lease_epoch=old_epoch,
                now_tick=2,
                committed_state="REVIEWED_NO_ADMISSION",
                verdict_reason="must be stale after docs drift",
                evidence_refs=["fake-evidence-old"],
                authorization=old_commit_auth,
                auth_runtime=runtime(old_worker),
            ),
        )
        new_worker = "worker-new-docs"
        new_lease_auth = auth(
            "R1_TASK_ACQUIRE_LEASE", f"task:{new_task}", "P1_REVERSIBLE_INTERNAL_WRITE", "INTERNAL_R1_STATE_ONLY", new_worker
        )
        expect(
            StaleState,
            lambda: engine.acquire_lease(
                current_main="0" * 40,
                task_id=new_task,
                worker_id=new_worker,
                now_tick=2,
                lease_ticks=5,
                authorization=new_lease_auth,
                auth_runtime=runtime(new_worker),
            ),
        )
        safe_candidate = "canary-source-safe-mode"
        safe_auth = auth(
            "R1_SOURCE_CACHE_INSPECT_OR_STAGE",
            f"source-candidate:{safe_candidate}",
            "P1_REVERSIBLE_INTERNAL_WRITE",
            "PUBLIC_TERMS_METADATA_ONLY",
            "safe-router",
        )
        expect(
            AuthorizationDenied,
            lambda: engine.inspect_candidate(
                current_main=m,
                candidate_id=safe_candidate,
                docs_hash="fake-safe-docs",
                authorization=safe_auth,
                auth_runtime=runtime("safe-router", safe=True),
            ),
        )
        assert safe_candidate not in store.read()["cache"]
        return {
            "old_task_denied_after_docs_drift": True,
            "stale_canonical_identity_denied": True,
            "safe_mode_write_denied_without_mutation": True,
        }


def finite_retry_rehearsal():
    m = CANONICAL_DESIGN_MERGE
    with tempfile.TemporaryDirectory() as td:
        store = PersistentStore(Path(td))
        engine = R1Engine(store, m)
        router = "retry-router"
        candidate = "canary-source-c"
        inspect_auth = auth(
            "R1_SOURCE_CACHE_INSPECT_OR_STAGE",
            f"source-candidate:{candidate}",
            "P1_REVERSIBLE_INTERNAL_WRITE",
            "PUBLIC_TERMS_METADATA_ONLY",
            router,
        )
        task = engine.inspect_candidate(
            current_main=m,
            candidate_id=candidate,
            docs_hash="fake-docs-c-v1",
            authorization=inspect_auth,
            auth_runtime=runtime(router),
        )
        worker = "retry-worker"
        lease_auth = auth(
            "R1_TASK_ACQUIRE_LEASE", f"task:{task}", "P1_REVERSIBLE_INTERNAL_WRITE", "INTERNAL_R1_STATE_ONLY", worker
        )
        epoch = engine.acquire_lease(
            current_main=m,
            task_id=task,
            worker_id=worker,
            now_tick=1,
            lease_ticks=20,
            authorization=lease_auth,
            auth_runtime=runtime(worker),
        )
        failure_auth = auth(
            "R1_TASK_RECORD_FAILURE", f"task:{task}", "P1_REVERSIBLE_INTERNAL_WRITE", "INTERNAL_R1_STATE_ONLY", worker
        )
        for tick in (2, 3, 4):
            engine.record_failure(
                current_main=m,
                task_id=task,
                worker_id=worker,
                lease_epoch=epoch,
                now_tick=tick,
                reason="synthetic-timeout",
                authorization=failure_auth,
                auth_runtime=runtime(worker),
            )
        assert store.read()["tasks"][task]["dead_letter_reason"] == "synthetic-timeout"
        later_worker = "later-worker"
        later_auth = auth(
            "R1_TASK_ACQUIRE_LEASE", f"task:{task}", "P1_REVERSIBLE_INTERNAL_WRITE", "INTERNAL_R1_STATE_ONLY", later_worker
        )
        expect(
            DeadLettered,
            lambda: engine.acquire_lease(
                current_main=m,
                task_id=task,
                worker_id=later_worker,
                now_tick=30,
                lease_ticks=5,
                authorization=later_auth,
                auth_runtime=runtime(later_worker),
            ),
        )
        return {"finite_retry_dead_letter_explicit": True}


def rehearse():
    report = {
        "mode": "BOUNDED_CANARY_PREPARATION_REHEARSAL_ONLY",
        "takeover_restart": takeover_and_restart_rehearsal(),
        "drift_fail_closed": drift_and_fail_closed_rehearsal(),
        "finite_retry": finite_retry_rehearsal(),
        "network_access_performed": False,
        "external_data_used": False,
        "source_admission_performed": False,
        "runtime_activation_performed": False,
    }
    print(json.dumps(report, sort_keys=True))
    print("MULTIVERSE_R1_BOUNDED_CANARY_PREPARATION_REHEARSAL_PASS")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rehearse", action="store_true")
    args = parser.parse_args()
    if args.rehearse:
        return rehearse()
    print("R1_BOUNDED_CANARY_PREPARATION_ONLY_NO_RUNTIME_ACTIVATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
