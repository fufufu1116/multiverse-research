import os
import sqlite3
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


class V8RolePreexecutionGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        config.DB_PATH=os.path.join(self.tmp.name,'task.db')
        db.init_schema()
        self.binding=IntegrationBinding(CANONICAL_MAIN,BRANCH,HEAD,V7_HEAD)
        self.bridge_db=os.path.join(self.tmp.name,'bridge.db')
        self.provider_db=os.path.join(self.tmp.name,'provider.db')
        self.engine=ExactV7SharedEngine(self.binding,self.bridge_db,self.provider_db)

    def tearDown(self):
        self.engine.close()
        self.tmp.cleanup()

    def test_wrong_state_lab_is_rejected_before_provider_and_bridge_receipts(self):
        task_id=self.engine.submit('core','implement','wrong-state probe')
        generation=self.engine.claim_and_start(task_id,'worker-1')
        before=db.get_task(task_id)

        with self.assertRaisesRegex(BridgeError,'ROLE_STATE_MISMATCH:LAB:IN_IMPLEMENT'):
            self.engine.execute_role(
                task_id,'LAB',0,'wrong-state-lab','worker-1',generation,
                {'verdict':'PASS','reviewed_head':HEAD,'evidence_ref':'wrong-state-lab-evidence'},
            )

        store=ProviderAdapterReceiptStore(self.provider_db,self.engine.manifest)
        try:
            self.assertEqual(store.execution_count('wrong-state-lab'),0)
        finally:
            store.close()
        conn=sqlite3.connect(self.bridge_db)
        try:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM receipts').fetchone()[0],0)
        finally:
            conn.close()
        after=db.get_task(task_id)
        for key in ('state','claimed_by','claim_generation','lease_until','result'):
            self.assertEqual(after[key],before[key])

    def test_wrong_state_audit_is_rejected_before_provider_execution(self):
        task_id=self.engine.submit('core','implement','wrong-audit probe')
        generation=self.engine.claim_and_start(task_id,'worker-2')
        self.engine.execute_role(
            task_id,'IMPLEMENT',0,'implement-ok','worker-2',generation,
            {'status':'READY','candidate_head':HEAD,'diff_lines':0,'cost_microusd':0,'evidence_ref':'implement-ok'},
        )
        self.assertEqual(db.get_task(task_id)['state'],'IN_LAB')
        with self.assertRaisesRegex(BridgeError,'ROLE_STATE_MISMATCH:AUDIT:IN_LAB'):
            self.engine.execute_role(
                task_id,'AUDIT',0,'wrong-state-audit','worker-2',generation,
                {'verdict':'PASS','reviewed_head':HEAD,'evidence_ref':'wrong-state-audit-evidence'},
            )
        store=ProviderAdapterReceiptStore(self.provider_db,self.engine.manifest)
        try:
            self.assertEqual(store.execution_count('wrong-state-audit'),0)
        finally:
            store.close()
        self.assertEqual(db.get_task(task_id)['state'],'IN_LAB')


if __name__=='__main__':
    unittest.main()
