import os
import tempfile
import unittest

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
        self.assertFalse(self.core.apply_verification_receipt(task_id,"r0","mock_gemini","evidence://x","ACCEPT"))
        self.assertTrue(self.core.apply_verification_receipt(task_id,"r1","auditor_external","evidence://verified","ACCEPT"))
        self.assertTrue(self.core.realize_revenue_and_close(task_id,100))
        state=self.core.get_state_snapshot()
        self.assertEqual(state["realized_revenue"],100)
        self.assertEqual(state["tasks"][0]["status"],"CLOSED")

    def test_verification_requires_receipt_and_audit_chain_is_valid(self):
        task_id=self.core.add_task("evidence task","AI研究",0)
        q=DeterministicTaskQueue(self.core)
        TaskExecutor(self.core,q,FailClosedEnforcer(self.core)).run_next_task()
        self.assertFalse(self.core.apply_verification_receipt(task_id,"","","","ACCEPT"))
        self.assertFalse(self.core.apply_verification_receipt(task_id,"r-self","mock_gemini","evidence://x","ACCEPT"))
        self.assertTrue(self.core.apply_verification_receipt(task_id,"r-ok","auditor_external","evidence://ok","ACCEPT"))
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
            self.assertTrue({"claimed_revenue","result","result_provider","verification_note","idempotency_key"}.issubset(cols))
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
