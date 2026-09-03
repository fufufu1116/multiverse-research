#!/usr/bin/env python3
import copy
import json
import pathlib
import tempfile
import threading
import unittest

from orchestrator_mvp_v2 import OrchestratorError
from orchestrator_role_relay_policy_v4 import CandidateBindingPolicy, PolicyRelayStore
from orchestrator_role_relay_policy_source_v5 import ReviewedPolicySource, SourceBoundPolicyRelayStore
from orchestrator_policy_change_control_v6 import (
    BASE_V5_AUDITOR_COMMENT_ID,
    BASE_V5_CLOSURE_COMMENT_ID,
    BASE_V5_LAB_COMMENT_ID,
    CANDIDATE_REVIEW_REQUIRED,
    CHANGE_CONTROL_BASELINE_SHA256,
    NO_CHANGE,
    OWNER_GATE_REQUIRED,
    ChangeControlBaseline,
    PolicyChangeControlStore,
    PolicyChangeControlWorker,
    classify_policy_change,
)

HERE = pathlib.Path(__file__).resolve().parent
BASELINE = HERE / "MULTIVERSE_AUTOMATION_POLICY_CHANGE_CONTROL_V6_BASELINE.json"
BASE_POLICY = HERE / "MULTIVERSE_AUTOMATION_REVIEWED_POLICY_SOURCE_V5.json"


def base_doc():
    return json.loads(BASE_POLICY.read_text(encoding="utf-8"))


class PolicyChangeControlV6Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.db = self.root / "change-control-v6.sqlite"
        self.baseline = ChangeControlBaseline.load(BASELINE)
        self.source = ReviewedPolicySource.load(BASE_POLICY)

    def tearDown(self):
        self.tmp.cleanup()

    def test_exact_baseline_and_v5_review_chain_are_pinned(self):
        self.assertEqual(self.baseline.raw_sha256, CHANGE_CONTROL_BASELINE_SHA256)
        self.assertEqual(self.baseline.lab_comment_id, BASE_V5_LAB_COMMENT_ID)
        self.assertEqual(self.baseline.auditor_comment_id, BASE_V5_AUDITOR_COMMENT_ID)
        self.assertEqual(self.baseline.closure_comment_id, BASE_V5_CLOSURE_COMMENT_ID)
        self.baseline.verify_base_source(self.source)

    def test_exact_unchanged_policy_is_no_change_and_never_apply(self):
        d = classify_policy_change(self.baseline, self.source, base_doc())
        self.assertEqual(d.classification, NO_CHANGE)
        self.assertFalse(d.may_apply)
        self.assertFalse(d.owner_gate_required)
        self.assertFalse(d.may_route_independent_review)

    def test_binding_removal_is_nonwidening_candidate_review(self):
        proposed = base_doc()
        proposed["allowed_bindings"] = proposed["allowed_bindings"][:1]
        proposed["policy_id"] = "automation-candidate-policy-source-v6-narrow"
        proposed["source_branch"] = "agent/automation-policy-v6-narrow"
        d = classify_policy_change(self.baseline, self.source, proposed)
        self.assertEqual(d.classification, CANDIDATE_REVIEW_REQUIRED)
        self.assertTrue(d.may_route_independent_review)
        self.assertFalse(d.may_apply)
        self.assertFalse(d.owner_gate_required)

    def test_identity_rotation_without_widening_requires_candidate_review(self):
        proposed = base_doc()
        proposed["policy_id"] = "automation-candidate-policy-source-v6-identity"
        proposed["source_branch"] = "agent/automation-policy-v6-identity"
        d = classify_policy_change(self.baseline, self.source, proposed)
        self.assertEqual(d.classification, CANDIDATE_REVIEW_REQUIRED)
        self.assertIn("POLICY_IDENTITY_ROTATED", d.reasons)
        self.assertFalse(d.may_apply)

    def test_invalid_source_branch_identity_is_owner_gate(self):
        invalid = ["agent/", "agent/a..b", "agent/a//b", "agent/a.lock", "not-agent/x"]
        for branch in invalid:
            with self.subTest(branch=branch):
                proposed = base_doc()
                proposed["source_branch"] = branch
                proposed["policy_id"] = "automation-candidate-policy-source-v6-invalid-branch"
                d = classify_policy_change(self.baseline, self.source, proposed)
                self.assertEqual(d.classification, OWNER_GATE_REQUIRED)
                self.assertTrue(d.owner_gate_required)
                self.assertFalse(d.may_route_independent_review)
                self.assertFalse(d.may_apply)
                self.assertIn("SOURCE_BRANCH_INVALID", d.reasons)

    def test_added_or_substituted_binding_is_owner_gate(self):
        added = base_doc()
        added["allowed_bindings"].append({
            "domain": "automation-v6",
            "candidate_branch": "agent/automation-policy-v6",
        })
        d1 = classify_policy_change(self.baseline, self.source, added)
        self.assertEqual(d1.classification, OWNER_GATE_REQUIRED)
        self.assertTrue(d1.owner_gate_required)
        self.assertFalse(d1.may_apply)

        swapped = base_doc()
        swapped["allowed_bindings"][0] = {
            "domain": "automation-v4",
            "candidate_branch": "agent/automation-v4-different",
        }
        d2 = classify_policy_change(self.baseline, self.source, swapped)
        self.assertEqual(d2.classification, OWNER_GATE_REQUIRED)
        self.assertTrue(d2.owner_gate_required)

    def test_protected_boundary_changes_are_owner_gate(self):
        mutations = []
        p = base_doc(); p["canonical_main"] = "b" * 40; mutations.append(p)
        p = base_doc(); p["canonical_repo"] = "other/repo"; mutations.append(p)
        p = base_doc(); p["candidate_only"] = False; mutations.append(p)
        p = base_doc(); p["authority"]["runtime"] = True; mutations.append(p)
        p = base_doc(); p["authority"]["new_authority"] = False; mutations.append(p)
        p = base_doc(); p["unexpected"] = "field"; mutations.append(p)
        p = base_doc(); p["allowed_bindings"] = []; mutations.append(p)
        p = base_doc(); p["allowed_bindings"].append(copy.deepcopy(p["allowed_bindings"][0])); mutations.append(p)
        for proposed in mutations:
            with self.subTest(proposed=proposed):
                d = classify_policy_change(self.baseline, self.source, proposed)
                self.assertEqual(d.classification, OWNER_GATE_REQUIRED)
                self.assertTrue(d.owner_gate_required)
                self.assertFalse(d.may_apply)

    def test_durable_replay_same_request_is_idempotent_conflict_denied(self):
        store = PolicyChangeControlStore(self.db, self.baseline, self.source)
        try:
            proposed = base_doc()
            first = store.decide("req-1", proposed)
            second = store.decide("req-1", proposed)
            self.assertEqual(first, second)
            changed = base_doc()
            changed["policy_id"] = "different"
            with self.assertRaisesRegex(OrchestratorError, "CHANGE_REQUEST_REPLAY_CONFLICT"):
                store.decide("req-1", changed)
        finally:
            store.close()

    def test_concurrent_first_open_identical_decision_converges(self):
        barrier = threading.Barrier(2)
        out = []
        errors = []

        def run_one():
            try:
                local_baseline = ChangeControlBaseline.load(BASELINE)
                local_source = ReviewedPolicySource.load(BASE_POLICY)
                barrier.wait(timeout=2)
                store = PolicyChangeControlStore(self.db, local_baseline, local_source)
                try:
                    out.append(store.decide("req-first-open", base_doc()))
                finally:
                    store.close()
            except Exception as exc:
                errors.append(exc)

        a = threading.Thread(target=run_one)
        b = threading.Thread(target=run_one)
        a.start(); b.start(); a.join(5); b.join(5)
        self.assertFalse(a.is_alive() or b.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0], out[1])
        self.assertEqual(out[0]["classification"], NO_CHANGE)

    def test_inherited_v4_v5_empty_db_first_open_is_lock_safe(self):
        v4_policy = CandidateBindingPolicy.exact(
            "fufufu1116/multiverse-research",
            ("automation-v5", "agent/automation-orchestrator-policy-source-v5-20260903-v1"),
        )

        def race(label, factory):
            for round_no in range(12):
                db = self.root / f"{label}-{round_no}.sqlite"
                barrier = threading.Barrier(2)
                errors = []

                def run_one():
                    store = None
                    try:
                        barrier.wait(timeout=2)
                        store = factory(db)
                    except Exception as exc:
                        errors.append(exc)
                    finally:
                        if store is not None:
                            store.close()

                a = threading.Thread(target=run_one)
                b = threading.Thread(target=run_one)
                a.start(); b.start(); a.join(5); b.join(5)
                self.assertFalse(a.is_alive() or b.is_alive(), f"{label}:{round_no}:thread_stuck")
                self.assertEqual(errors, [], f"{label}:{round_no}:{errors!r}")

        race("v4", lambda db: PolicyRelayStore(db, v4_policy))
        race("v5", lambda db: SourceBoundPolicyRelayStore(db, self.source))

    def test_concurrent_identical_decision_converges_across_connections(self):
        seed = PolicyChangeControlStore(self.db, self.baseline, self.source)
        seed.close()
        barrier = threading.Barrier(2)
        out = []
        errors = []

        def run_one():
            try:
                local_baseline = ChangeControlBaseline.load(BASELINE)
                local_source = ReviewedPolicySource.load(BASE_POLICY)
                store = PolicyChangeControlStore(self.db, local_baseline, local_source)
                try:
                    barrier.wait(timeout=2)
                    out.append(store.decide("req-concurrent", base_doc()))
                finally:
                    store.close()
            except Exception as exc:
                errors.append(exc)

        a = threading.Thread(target=run_one)
        b = threading.Thread(target=run_one)
        a.start(); b.start(); a.join(5); b.join(5)
        self.assertFalse(a.is_alive() or b.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0], out[1])
        self.assertEqual(out[0]["classification"], NO_CHANGE)

    def test_partial_meta_and_v5_adapter_bypass_fail_closed(self):
        store = PolicyChangeControlStore(self.db, self.baseline, self.source)
        store.conn.execute("DELETE FROM meta WHERE k='base_policy_source_sha256'")
        store.conn.commit()
        store.close()
        with self.assertRaisesRegex(OrchestratorError, "CHANGE_CONTROL_META_PARTIAL"):
            PolicyChangeControlStore(self.db, self.baseline, self.source)

        clean = self.root / "schema4.sqlite"
        store2 = PolicyChangeControlStore(clean, self.baseline, self.source)
        store2.close()
        with self.assertRaisesRegex(OrchestratorError, "POLICY_SOURCE_DB_SCHEMA_VERSION_MISMATCH"):
            SourceBoundPolicyRelayStore(clean, self.source)

    def test_worker_has_no_apply_surface(self):
        worker = PolicyChangeControlWorker(self.db, BASELINE, BASE_POLICY)
        out = worker.run("worker-1", base_doc())
        self.assertEqual(out["classification"], NO_CHANGE)
        self.assertFalse(out["may_apply"])
        self.assertTrue(worker.replay_safe)
        self.assertFalse(hasattr(worker, "apply"))
        self.assertFalse(hasattr(worker, "merge"))
        self.assertFalse(hasattr(worker, "dispatch"))


if __name__ == "__main__":
    unittest.main()
