#!/usr/bin/env python3
import json
import multiprocessing as mp
import pathlib
import tempfile
import time
import unittest

from orchestrator_mvp_v2 import OrchestratorError, demo_spec, operation_key
from orchestrator_provider_adapter_v7 import (
    PROVIDER_ADAPTER_CANONICAL_MAIN,
    PROVIDER_ADAPTER_ID,
    PROVIDER_ADAPTER_MANIFEST_SHA256,
    DeterministicLocalAdapter,
    ProviderAdapterManifest,
    ProviderAdapterReceiptStore,
    provider_adapter_process_one,
    provider_request_from_job,
)
from orchestrator_role_relay_policy_source_v5 import ReviewedPolicySource, SourceBoundPolicyRelayStore

HERE = pathlib.Path(__file__).resolve().parent
POLICY_MANIFEST = HERE / "MULTIVERSE_AUTOMATION_REVIEWED_POLICY_SOURCE_V5.json"
ADAPTER_MANIFEST = HERE / "MULTIVERSE_AUTOMATION_PROVIDER_ADAPTER_CONTRACT_V7.json"
V5_BRANCH = "agent/automation-orchestrator-policy-source-v5-20260903-v1"
V7_BRANCH = "agent/automation-orchestrator-provider-adapter-contract-v7-20260903-v1"
TASK_HEAD = "e803723309a045086287e613f924a90a880b5a3b"


def _receipt_once(path, manifest_path, request, result, q):
    manifest = ProviderAdapterManifest.load(manifest_path)
    store = ProviderAdapterReceiptStore(path, manifest)
    try:
        out = store.execute_local_once(request["operation_key"], request,
                                       DeterministicLocalAdapter({"IMPLEMENT": {"1": result}}))
        q.put(out)
    finally:
        store.close()


class ProviderAdapterV7Tests(unittest.TestCase):
    def _job(self):
        return {
            "schema_version": "MULTIVERSE_ORCHESTRATOR_ROLE_RELAY_v3",
            "task_id": "provider-v7-task",
            "role": "IMPLEMENT",
            "operation_key": operation_key("provider-v7-task", "IMPLEMENT", 0),
            "semantic_generation": 0,
            "candidate_head": TASK_HEAD,
            "candidate_branch": V5_BRANCH,
            "canonical_main": PROVIDER_ADAPTER_CANONICAL_MAIN,
            "objective": "deterministic provider-neutral contract",
            "authority": {
                "candidate_only": True,
                "live_provider": False,
                "production": False,
                "runtime": False,
                "spend": False,
            },
        }

    def test_exact_manifest_identity_and_all_false_authority(self):
        manifest = ProviderAdapterManifest.load(ADAPTER_MANIFEST)
        self.assertEqual(manifest.raw_sha256, PROVIDER_ADAPTER_MANIFEST_SHA256)
        self.assertEqual(manifest.adapter_id, PROVIDER_ADAPTER_ID)
        self.assertEqual(manifest.canonical_main, PROVIDER_ADAPTER_CANONICAL_MAIN)

    def test_manifest_tamper_and_runtime_adapter_injection_fail_closed(self):
        manifest = ProviderAdapterManifest.load(ADAPTER_MANIFEST)
        with tempfile.TemporaryDirectory() as td:
            bad = pathlib.Path(td) / ADAPTER_MANIFEST.name
            doc = json.loads(ADAPTER_MANIFEST.read_text())
            doc["authority"]["network"] = True
            bad.write_text(json.dumps(doc, separators=(",", ":"), sort_keys=True))
            with self.assertRaisesRegex(OrchestratorError, "PROVIDER_ADAPTER_MANIFEST_SHA256"):
                ProviderAdapterManifest.load(bad)

            store = ProviderAdapterReceiptStore(pathlib.Path(td) / "r.sqlite", manifest)
            request = provider_request_from_job(self._job(), manifest)
            class SneakyAdapter(DeterministicLocalAdapter):
                pass
            try:
                with self.assertRaisesRegex(OrchestratorError, "PROVIDER_ADAPTER_RUNTIME_INJECTION_DENIED"):
                    store.execute_local_once(request["operation_key"], request,
                                             SneakyAdapter({"IMPLEMENT": {"1": {"x": 1}}}))
            finally:
                store.close()

    def test_receipt_idempotency_conflicting_replay_and_manifest_pinning(self):
        manifest = ProviderAdapterManifest.load(ADAPTER_MANIFEST)
        result = {"status": "READY", "candidate_head": TASK_HEAD, "diff_lines": 1,
                  "cost_microusd": 0, "evidence_ref": "provider-v7-unit"}
        with tempfile.TemporaryDirectory() as td:
            db = pathlib.Path(td) / "receipt.sqlite"
            request = provider_request_from_job(self._job(), manifest)
            store = ProviderAdapterReceiptStore(db, manifest)
            try:
                first = store.execute_local_once(request["operation_key"], request,
                                                 DeterministicLocalAdapter({"IMPLEMENT": {"1": result}}))
                second = store.execute_local_once(request["operation_key"], request,
                                                  DeterministicLocalAdapter({"IMPLEMENT": {"1": {"bad": True}}}))
                self.assertEqual(first, result)
                self.assertEqual(second, result)
                self.assertEqual(store.execution_count(request["operation_key"]), 1)
                conflicting = dict(request)
                conflicting["objective"] = "different"
                with self.assertRaisesRegex(OrchestratorError, "PROVIDER_ADAPTER_CONFLICTING_REPLAY"):
                    store.execute_local_once(request["operation_key"], conflicting,
                                             DeterministicLocalAdapter({"IMPLEMENT": {"1": result}}))
            finally:
                store.close()
            altered = ProviderAdapterManifest(
                manifest.raw_sha256, manifest.canonical_json_text + " ", manifest.adapter_id,
                manifest.adapter_kind, manifest.source_branch, manifest.predecessor_head,
                manifest.canonical_main,
            )
            with self.assertRaisesRegex(OrchestratorError, "PROVIDER_ADAPTER_META_MISMATCH:manifest_json"):
                ProviderAdapterReceiptStore(db, altered)

    def test_concurrent_identical_receipt_execution_serializes_to_one(self):
        manifest = ProviderAdapterManifest.load(ADAPTER_MANIFEST)
        request = provider_request_from_job(self._job(), manifest)
        result = {"status": "READY", "candidate_head": TASK_HEAD, "diff_lines": 2,
                  "cost_microusd": 0, "evidence_ref": "provider-v7-concurrent"}
        with tempfile.TemporaryDirectory() as td:
            db = str(pathlib.Path(td) / "receipt.sqlite")
            ctx = mp.get_context("fork")
            q = ctx.Queue()
            ps = [ctx.Process(target=_receipt_once, args=(db, str(ADAPTER_MANIFEST), request, result, q))
                  for _ in range(2)]
            for p in ps:
                p.start()
            for p in ps:
                p.join(10)
                self.assertEqual(p.exitcode, 0)
            self.assertEqual(q.get(timeout=2), result)
            self.assertEqual(q.get(timeout=2), result)
            store = ProviderAdapterReceiptStore(db, manifest)
            try:
                self.assertEqual(store.execution_count(request["operation_key"]), 1)
            finally:
                store.close()

    def test_job_authority_and_existing_policy_prevent_widening(self):
        manifest = ProviderAdapterManifest.load(ADAPTER_MANIFEST)
        request = provider_request_from_job(self._job(), manifest)
        self.assertFalse(request["authority"]["network"])
        bad_job = self._job()
        bad_job["authority"] = dict(bad_job["authority"])
        bad_job["authority"]["live_provider"] = True
        with self.assertRaisesRegex(OrchestratorError, "PROVIDER_JOB_AUTHORITY"):
            provider_request_from_job(bad_job, manifest)

        with tempfile.TemporaryDirectory() as td:
            source = ReviewedPolicySource.load(POLICY_MANIFEST)
            relay = SourceBoundPolicyRelayStore(pathlib.Path(td) / "relay.sqlite", source)
            spec = demo_spec("provider-v7-widen", canonical_main=PROVIDER_ADAPTER_CANONICAL_MAIN,
                             candidate_head=TASK_HEAD)
            spec["domain"] = "automation-v7"
            spec["candidate_branch"] = V7_BRANCH
            task = {"task_id": spec["task_id"], "spec": spec}
            try:
                with self.assertRaisesRegex(OrchestratorError, "RELAY_BINDING_POLICY_DENIED"):
                    relay.enqueue(role="IMPLEMENT", task=task,
                                  operation_key_value=operation_key(spec["task_id"], "IMPLEMENT", 0),
                                  semantic_attempt=1, transient_attempt=0)
            finally:
                relay.close()

    def test_crash_after_durable_adapter_receipt_replays_without_second_execution(self):
        manifest = ProviderAdapterManifest.load(ADAPTER_MANIFEST)
        result = {"status": "READY", "candidate_head": TASK_HEAD, "diff_lines": 3,
                  "cost_microusd": 0, "evidence_ref": "provider-v7-crash"}
        script = {"IMPLEMENT": {"1": result}}
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            relay_db = root / "relay.sqlite"
            receipt_db = root / "receipt.sqlite"
            source = ReviewedPolicySource.load(POLICY_MANIFEST)
            relay = SourceBoundPolicyRelayStore(relay_db, source)
            spec = demo_spec("provider-v7-crash", canonical_main=PROVIDER_ADAPTER_CANONICAL_MAIN,
                             candidate_head=TASK_HEAD)
            spec["domain"] = "automation-v5"
            spec["candidate_branch"] = V5_BRANCH
            task = {"task_id": spec["task_id"], "spec": spec}
            op = operation_key(spec["task_id"], "IMPLEMENT", 0)
            relay.enqueue(role="IMPLEMENT", task=task, operation_key_value=op,
                          semantic_attempt=1, transient_attempt=0)
            relay.close()
            self.assertEqual(
                provider_adapter_process_one(str(relay_db), str(receipt_db), str(POLICY_MANIFEST),
                                             str(ADAPTER_MANIFEST), "provider-one", script,
                                             lease_seconds=1, crash_after_receipt=True),
                "CRASH_AFTER_RECEIPT",
            )
            time.sleep(1.1)
            self.assertEqual(
                provider_adapter_process_one(str(relay_db), str(receipt_db), str(POLICY_MANIFEST),
                                             str(ADAPTER_MANIFEST), "provider-two", script,
                                             lease_seconds=1),
                "COMPLETE",
            )
            receipts = ProviderAdapterReceiptStore(receipt_db, manifest)
            try:
                self.assertEqual(receipts.execution_count(op), 1)
            finally:
                receipts.close()
            relay = SourceBoundPolicyRelayStore(relay_db, source)
            try:
                self.assertEqual(relay.result(op), result)
            finally:
                relay.close()

    def test_invalid_result_is_rejected_before_durable_receipt(self):
        bad = {"status": "READY", "candidate_head": "0" * 40, "diff_lines": 1,
               "cost_microusd": 0, "evidence_ref": "bad-head"}
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            relay_db = root / "relay.sqlite"
            receipt_db = root / "receipt.sqlite"
            source = ReviewedPolicySource.load(POLICY_MANIFEST)
            relay = SourceBoundPolicyRelayStore(relay_db, source)
            spec = demo_spec("provider-v7-bad-head", canonical_main=PROVIDER_ADAPTER_CANONICAL_MAIN,
                             candidate_head=TASK_HEAD)
            spec["domain"] = "automation-v5"
            spec["candidate_branch"] = V5_BRANCH
            task = {"task_id": spec["task_id"], "spec": spec}
            op = operation_key(spec["task_id"], "IMPLEMENT", 0)
            relay.enqueue(role="IMPLEMENT", task=task, operation_key_value=op,
                          semantic_attempt=1, transient_attempt=0)
            relay.close()
            with self.assertRaisesRegex(OrchestratorError, "PROVIDER_ADAPTER_IMPLEMENT_HEAD_MISMATCH"):
                provider_adapter_process_one(str(relay_db), str(receipt_db), str(POLICY_MANIFEST),
                                             str(ADAPTER_MANIFEST), "provider", {"IMPLEMENT": {"1": bad}},
                                             lease_seconds=1)
            receipts = ProviderAdapterReceiptStore(receipt_db, ProviderAdapterManifest.load(ADAPTER_MANIFEST))
            try:
                self.assertEqual(receipts.execution_count(op), 0)
            finally:
                receipts.close()
            relay = SourceBoundPolicyRelayStore(relay_db, source)
            try:
                self.assertIsNone(relay.result(op))
            finally:
                relay.close()


if __name__ == "__main__":
    unittest.main()
