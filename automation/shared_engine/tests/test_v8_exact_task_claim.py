import os, tempfile, unittest
import config, db
from integration_bridge import IntegrationBinding
from exact_v7_shared_engine import ExactV7SharedEngine
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD

HEAD='6'*40
BRANCH='agent/automation-shared-engine-integration-v8-test'

class V8ExactTaskClaimTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old_db=config.DB_PATH
        config.DB_PATH=os.path.join(self.tmp.name,'task.db')
        db.init_schema()
        binding=IntegrationBinding(CANONICAL_MAIN,BRANCH,HEAD,V7_HEAD)
        self.engine=ExactV7SharedEngine(binding,os.path.join(self.tmp.name,'bridge.db'),os.path.join(self.tmp.name,'provider.db'))
    def tearDown(self):
        self.engine.close(); config.DB_PATH=self.old_db; self.tmp.cleanup()
    def test_targeted_start_does_not_claim_higher_priority_neighbor(self):
        target=self.engine.submit('core','implement','target',priority=0)
        other=self.engine.submit('core','implement','other',priority=100)
        gen=self.engine.claim_and_start(target,'worker-target')
        t=db.get_task(target); o=db.get_task(other)
        self.assertEqual(t['state'],'IN_IMPLEMENT')
        self.assertEqual(t['claimed_by'],'worker-target')
        self.assertEqual(t['claim_generation'],gen)
        self.assertEqual(o['state'],'PENDING')
        self.assertIsNone(o['claimed_by'])
        self.assertEqual(o['claim_generation'],0)
        self.assertIsNone(o['lease_until'])
    def test_claiming_already_claimed_target_fails_without_touching_neighbor(self):
        target=self.engine.submit('core','implement','target',priority=0)
        other=self.engine.submit('core','implement','other',priority=100)
        self.engine.claim_and_start(target,'worker-1')
        before=db.get_task(other)
        with self.assertRaises(db.InvalidTransitionError):
            self.engine.claim_and_start(target,'worker-2')
        after=db.get_task(other)
        for k in ('state','claimed_by','claim_generation','lease_until','result'):
            self.assertEqual(after[k],before[k])

if __name__=='__main__': unittest.main()
