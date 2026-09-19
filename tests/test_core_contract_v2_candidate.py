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
        self.assertTrue(self.core.verify_task(task_id,"independent evidence placeholder"))
        self.assertTrue(self.core.realize_revenue_and_close(task_id,100))
        state=self.core.get_state_snapshot()
        self.assertEqual(state["realized_revenue"],100)
        self.assertEqual(state["tasks"][0]["status"],"CLOSED")

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
            self.assertTrue({"claimed_revenue","result","result_provider","verification_note"}.issubset(cols))
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
        ).validate()

if __name__=="__main__":
    unittest.main()
