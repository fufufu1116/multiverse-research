import sqlite3
import tempfile
import unittest

from core_state import CoreStateEngine
from config.executor import TaskExecutor
from config.fail_closed import FailClosedEnforcer
from config.provider import CapabilityRecord, CapabilityRegistry
from config.queue import DeterministicTaskQueue
from config.router import RoutingRequest

class RouterExecutorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.NamedTemporaryFile(suffix=".db")
        self.core=CoreStateEngine(self.tmp.name)
        self.queue=DeterministicTaskQueue(self.core)
        self.fail=FailClosedEnforcer(self.core)

    def _status(self, task_id):
        with sqlite3.connect(self.core.db_path) as conn:
            return conn.execute("SELECT status,result_provider FROM tasks WHERE id=?",(task_id,)).fetchone()

    def test_evidence_backed_simulation_routes_and_claims(self):
        caps=CapabilityRegistry([CapabilityRecord("mock_gemini","simulation",.9,.9,1,0,1000,evidence_refs=("evidence://test",))])
        task=self.core.add_task("safe simulation","test")
        ex=TaskExecutor(self.core,self.queue,self.fail,capabilities=caps)
        self.assertTrue(ex.run_next_task(RoutingRequest("simulation",min_quality=.8)))
        self.assertEqual(self._status(task),("SUCCESS_CLAIMED","mock_gemini"))

    def test_no_matching_capability_evidence_fails_closed(self):
        task=self.core.add_task("no evidence route","test")
        ex=TaskExecutor(self.core,self.queue,self.fail,capabilities=CapabilityRegistry())
        self.assertFalse(ex.run_next_task(RoutingRequest("research")))
        self.assertEqual(self._status(task)[0],"FAILED")

    def test_explicit_empty_capability_registry_fails_closed(self):
        task=self.core.add_task("explicit empty registry","test")
        ex=TaskExecutor(self.core,self.queue,self.fail,capabilities=CapabilityRegistry())
        self.assertFalse(ex.run_next_task(RoutingRequest("simulation")))
        self.assertEqual(self._status(task)[0],"FAILED")

    def test_legacy_no_argument_call_stays_simulation_only(self):
        task=self.core.add_task("legacy safe simulation","test")
        ex=TaskExecutor(self.core,self.queue,self.fail)
        self.assertTrue(ex.run_next_task())
        self.assertEqual(self._status(task),("SUCCESS_CLAIMED","mock_gemini"))

    def test_request_cannot_bypass_external_boundary(self):
        self.assertNotIn("allow_external", RoutingRequest.__dataclass_fields__)

if __name__=="__main__":
    unittest.main()
