import os
import tempfile
import unittest

import config
import db
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD
from exact_v7_shared_engine import ExactV7SharedEngine
from integration_bridge import BridgeError, IntegrationBinding
from orchestrator_provider_adapter_v7 import ProviderAdapterReceiptStore

HEAD='5'*40
BRANCH='agent/automation-shared-engine-integration-v8-test'


class V8RolePreexecutionSupportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        config.DB_PATH=os.path.join(self.tmp.name,'task.db')
        db.init_schema()
        self.binding=IntegrationBinding(CANONICAL_MAIN,BRANCH,HEAD,V7_HEAD)
        self.provider_db=os.path.join(self.tmp.name,'provider.db')
        self.engine=ExactV7SharedEngine(self.binding,os.path.join(self.tmp.name,'bridge.db'),self.provider_db)

    def tearDown(self):
        self.engine.close()
        self.tmp.cleanup()

    def test_wrong_state_lab_executes_provider_before_role_state_rejection(self):
        task_id=self.engine.submit('core','implement','wrong-state probe')
        generation=self.engine.claim_and_start(task_id,'worker-1')
        self.assertEqual(db.get_task(task_id)['state'],'IN_IMPLEMENT')

        with self.assertRaisesRegex(BridgeError,'ROLE_STATE_MISMATCH:LAB:IN_IMPLEMENT'):
            self.engine.execute_role(
                task_id,'LAB',0,'wrong-state-lab','worker-1',generation,
                {'verdict':'PASS','reviewed_head':HEAD,'evidence_ref':'wrong-state-lab-evidence'},
            )

        store=ProviderAdapterReceiptStore(self.provider_db,self.engine.manifest)
        try:
            self.assertEqual(store.execution_count('wrong-state-lab'),1)
        finally:
            store.close()
        self.assertEqual(db.get_task(task_id)['state'],'IN_IMPLEMENT')


if __name__=='__main__':
    unittest.main()
