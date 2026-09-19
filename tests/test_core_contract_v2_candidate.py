import os
import tempfile
import unittest

from core_state import CoreStateEngine
from config.queue import DeterministicTaskQueue
from config.fail_closed import FailClosedEnforcer
from config.executor import TaskExecutor

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

    def test_failed_transition_requires_running(self):
        task_id=self.core.add_task("queued task","システム改善",0)
        queue=DeterministicTaskQueue(self.core)
        self.assertFalse(queue.mark_task_failed(task_id,"not running"))

if __name__=="__main__":
    unittest.main()
