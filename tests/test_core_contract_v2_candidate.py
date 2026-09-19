import os
import tempfile
import unittest
import base64
import hashlib

from core_state import CoreStateEngine
from config.queue import DeterministicTaskQueue
from config.fail_closed import FailClosedEnforcer
from config.executor import TaskExecutor
from config.mission_packet import MissionPacket

class CoreCandidateTests(unittest.TestCase):
    def setUp(self):
        fd,self.path=tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(self.path)
        self.core=CoreStateEngine(self.path)
        self.verifier_id="auditor_external"
        self._auditor_private_exponent=int(
            "7579634e3e5c8076100601690f8d86f8a283ebfd881e14e7d27f83f7324e21ce"
            "4fd414d913431ec42c4052410e68534cdc5ce0227c33e3ca14e60791ab84f03f3"
            "a69ab7c4c3c1acfde480db2aacd40cc462604d58159afbbf3b9707224b4a8d5e"
            "12ec60b1d9fb9fc16711161d61028be3ec1d80df9df19619afad89e73ccdc71",16)

    def _sign_as_independent_auditor(self,task_id,receipt_id,evidence_ref,evidence_sha256,verdict="ACCEPT"):
        payload=self.core._verification_payload(task_id,receipt_id,self.verifier_id,evidence_ref,evidence_sha256,verdict)
        trust=__import__("core_state").CANONICAL_TRUSTED_VERIFIERS[self.verifier_id]
        n=trust["modulus"]; k=(n.bit_length()+7)//8
        digest_info=bytes.fromhex("3031300d060960864801650304020105000420")+hashlib.sha256(payload).digest()
        encoded=b"\x00\x01"+b"\xff"*(k-len(digest_info)-3)+b"\x00"+digest_info
        signature=pow(int.from_bytes(encoded,"big"),self._auditor_private_exponent,n).to_bytes(k,"big")
        return base64.b64encode(signature).decode()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_claim_does_not_realize_revenue(self):
        task_id=self.core.add_task("simulation task","AI研究",5000)
        queue=DeterministicTaskQueue(self.core)
        executor=TaskExecutor(self.core,queue,FailClosedEnforcer(self.core))
        self.assertTrue(executor.run_next_task())
        state=self.core.get_state_snapshot()
        self.assertEqual(state["realized_revenue"],0)
        self.assertEqual(state["tasks"][0]["status"],"SUCCESS_CLAIMED")

    def test_revenue_requires_verified_task_and_explicit_amount(self):
        task_id=self.core.add_task("simulation task","AI研究",999999)
        queue=DeterministicTaskQueue(self.core)
        executor=TaskExecutor(self.core,queue,FailClosedEnforcer(self.core))
        executor.run_next_task()
        self.assertFalse(self.core.realize_revenue_and_close(task_id,100))
        digest="a"*64
        bad="not-a-valid-external-signature"
        self.assertFalse(self.core.apply_verification_receipt(
            task_id,"r0","mock_gemini","evidence://x",digest,"ACCEPT",bad))
        integrity=self._sign_as_independent_auditor(task_id,"r1","evidence://verified",digest)
        self.assertTrue(self.core.apply_verification_receipt(
            task_id,"r1",self.verifier_id,"evidence://verified",digest,"ACCEPT",integrity))
        self.assertTrue(self.core.realize_revenue_and_close(task_id,100))
        state=self.core.get_state_snapshot()
        self.assertEqual(state["realized_revenue"],100)
        self.assertEqual(state["tasks"][0]["status"],"CLOSED")

    def test_verification_requires_receipt_and_audit_chain_is_valid(self):
        task_id=self.core.add_task("evidence task","AI研究",0)
        q=DeterministicTaskQueue(self.core)
        TaskExecutor(self.core,q,FailClosedEnforcer(self.core)).run_next_task()
        digest="b"*64
        self.assertFalse(self.core.apply_verification_receipt(task_id,"","","",digest,"ACCEPT",""))
        self.assertFalse(self.core.apply_verification_receipt(
            task_id,"r-self","mock_gemini","evidence://x",digest,"ACCEPT","0"*64))
        integrity=self._sign_as_independent_auditor(task_id,"r-ok","evidence://ok",digest)
        self.assertTrue(self.core.apply_verification_receipt(
            task_id,"r-ok",self.verifier_id,"evidence://ok",digest,"ACCEPT",integrity))
        self.assertTrue(self.core.verify_audit_chain())

    def test_provider_disable_is_persistent_and_enforced(self):
        fc=FailClosedEnforcer(self.core)
        fc.disable_provider("mock_gemini","test")
        self.assertFalse(self.core.is_provider_enabled("mock_gemini"))
        task_id=self.core.add_task("blocked","AI研究",0)
        q=DeterministicTaskQueue(self.core)
        self.assertFalse(TaskExecutor(self.core,q,fc).run_next_task())

    def test_duplicate_idempotency_key_returns_same_task(self):
        first=self.core.add_task("same","司令塔",0,"request-1")
        second=self.core.add_task("same","司令塔",0,"request-1")
        self.assertEqual(first,second)
        self.assertEqual(len(self.core.get_state_snapshot()["tasks"]),1)

    def test_idempotency_key_reuse_with_different_content_fails_closed(self):
        first=self.core.add_task("same","司令塔",0,"request-bound")
        self.assertIsNotNone(first)
        self.assertIsNone(self.core.add_task("different","司令塔",0,"request-bound"))
        self.assertIsNone(self.core.add_task("same","司令塔",1,"request-bound"))
        self.assertEqual(len(self.core.get_state_snapshot()["tasks"]),1)

    def test_implementation_cannot_mint_independent_auditor_receipt_from_source_trust_material(self):
        task_id=self.core.add_task("implementation forgery","AI研究",0)
        q=DeterministicTaskQueue(self.core)
        TaskExecutor(self.core,q,FailClosedEnforcer(self.core)).run_next_task()
        digest="8"*64
        from core_state import CANONICAL_TRUSTED_VERIFIERS
        trust=CANONICAL_TRUSTED_VERIFIERS[self.verifier_id]
        self.assertNotIn("private_key",trust)
        self.assertNotIn("secret",trust)
        forged=base64.b64encode(hashlib.sha256((str(trust)+task_id+"r-impl").encode()).digest()).decode()
        self.assertFalse(self.core.apply_verification_receipt(
            task_id,"r-impl",self.verifier_id,"evidence://impl",digest,"ACCEPT",forged))
        self.assertEqual(self.core.get_state_snapshot()["tasks"][0]["status"],"SUCCESS_CLAIMED")

    def test_plain_checksum_is_not_authentication(self):
        task_id=self.core.add_task("evidence boundary","AI研究",0)
        q=DeterministicTaskQueue(self.core)
        TaskExecutor(self.core,q,FailClosedEnforcer(self.core)).run_next_task()
        digest="c"*64
        self.assertFalse(self.core.apply_verification_receipt(
            task_id,"r-plain",self.verifier_id,"evidence://plain",digest,"ACCEPT",digest))
        self.assertEqual(self.core.get_state_snapshot()["tasks"][0]["status"],"SUCCESS_CLAIMED")

    def test_verification_receipt_binds_verifier_and_evidence_identity(self):
        task_id=self.core.add_task("bound receipt","AI研究",0)
        q=DeterministicTaskQueue(self.core)
        TaskExecutor(self.core,q,FailClosedEnforcer(self.core)).run_next_task()
        digest="d"*64
        integrity=self._sign_as_independent_auditor(task_id,"r-bound","evidence://one",digest)
        self.assertFalse(self.core.apply_verification_receipt(
            task_id,"r-bound",self.verifier_id,"evidence://two",digest,"ACCEPT",integrity))
        self.assertFalse(self.core.apply_verification_receipt(
            task_id,"r-bound",self.verifier_id,"evidence://one","e"*64,"ACCEPT",integrity))
        self.assertFalse(self.core.apply_verification_receipt(
            task_id,"r-bound","other_auditor","evidence://one",digest,"ACCEPT",integrity))
        self.assertTrue(self.core.apply_verification_receipt(
            task_id,"r-bound",self.verifier_id,"evidence://one",digest,"ACCEPT",integrity))

    def test_arbitrary_verifier_self_enrollment_and_self_signature_fail_closed(self):
        self.assertFalse(hasattr(self.core,"register_trusted_verifier"))
        task_id=self.core.add_task("self enrollment attack","AI研究",0)
        q=DeterministicTaskQueue(self.core)
        TaskExecutor(self.core,q,FailClosedEnforcer(self.core)).run_next_task()
        attacker_id="attacker_chosen_verifier"
        attacker_key="attacker-chosen-key"
        digest="9"*64
        forged=base64.b64encode(hashlib.sha256((attacker_key+attacker_id).encode()).digest()).decode()
        self.assertFalse(self.core.apply_verification_receipt(
            task_id,"r-forged",attacker_id,"evidence://forged",digest,"ACCEPT",forged))
        self.assertEqual(self.core.get_state_snapshot()["tasks"][0]["status"],"SUCCESS_CLAIMED")

    def test_untrusted_verifier_is_rejected(self):
        task_id=self.core.add_task("untrusted","AI研究",0)
        q=DeterministicTaskQueue(self.core)
        TaskExecutor(self.core,q,FailClosedEnforcer(self.core)).run_next_task()
        digest="f"*64
        integrity="attacker-self-signature"
        self.assertFalse(self.core.apply_verification_receipt(
            task_id,"r-x","unknown","evidence://x",digest,"ACCEPT",integrity))

    def test_old_database_is_migrated(self):
        import sqlite3
        old_path=self.path + ".old"
        with sqlite3.connect(old_path) as conn:
            conn.execute("""CREATE TABLE tasks (
                id TEXT PRIMARY KEY,title TEXT NOT NULL,troop TEXT,revenue INTEGER DEFAULT 0,
                status TEXT DEFAULT 'QUEUED',created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""")
            conn.execute("""CREATE TABLE revenues (id TEXT PRIMARY KEY,amount INTEGER NOT NULL,source_task TEXT,timestamp TEXT NOT NULL)""")
            conn.execute("""CREATE TABLE audit_logs (id TEXT PRIMARY KEY,event_type TEXT NOT NULL,payload JSON,timestamp TEXT NOT NULL)""")
        migrated=CoreStateEngine(old_path)
        with sqlite3.connect(old_path) as conn:
            cols={r[1] for r in conn.execute("PRAGMA table_info(tasks)")}
            self.assertTrue({"claimed_revenue","result","result_provider","verification_note","idempotency_key","request_fingerprint"}.issubset(cols))
            indexes=list(conn.execute("PRAGMA index_list(tasks)"))
            self.assertTrue(any(r[2] for r in indexes))
            rcols={r[1] for r in conn.execute("PRAGMA table_info(revenues)")}
            self.assertIn("source_task_id",rcols)
            legacy=conn.execute("SELECT source_task_id FROM revenues").fetchall()
            self.assertEqual(legacy,[])
        os.remove(old_path)

    def test_failed_transition_requires_running(self):
        task_id=self.core.add_task("queued task","システム改善",0)
        queue=DeterministicTaskQueue(self.core)
        self.assertFalse(queue.mark_task_failed(task_id,"not running"))

    def test_mission_packet_requires_evidence_and_stop_conditions(self):
        with self.assertRaises(ValueError):
            MissionPacket(mission_id="m1", objective="x", completion_condition="done").validate()
        MissionPacket(
            mission_id="m2",
            objective="continue without progress-only stops",
            required_evidence=["test result"],
            completion_condition="all checks pass or genuine gate reached",
            stop_conditions=["Owner Gate"],
            prohibited_actions=["production","spend","credentials"],
            canonical_refs=["github://canonical"],
            output_schema="evidence-backed result",
        ).validate()

    def test_provider_disable_survives_engine_reopen(self):
        FailClosedEnforcer(self.core).disable_provider("mock_gemini","persistent")
        reopened=CoreStateEngine(self.path)
        self.assertFalse(reopened.is_provider_enabled("mock_gemini"))

    def test_provider_capability_routing_stays_simulation_only(self):
        from config.provider import ProviderRegistry
        registry=ProviderRegistry()
        eligible=registry.eligible_providers("text_generation",allow_external=False)
        self.assertEqual([p.provider_id for p in eligible],["mock_gemini"])
        self.assertFalse(eligible[0].capabilities.external_calls)

if __name__=="__main__":
    unittest.main()
