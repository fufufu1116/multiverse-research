import os, tempfile, unittest
import config, db
from integration_bridge import IntegrationBinding
from exact_v7_shared_engine import ExactV7SharedEngine
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD

HEAD='5'*40; BRANCH='agent/automation-shared-engine-integration-v8-test'

class V8DomainCreationBypassSupportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); config.DB_PATH=os.path.join(self.tmp.name,'task.db'); db.init_schema()
        self.binding=IntegrationBinding(CANONICAL_MAIN,BRANCH,HEAD,V7_HEAD)
        self.engine=ExactV7SharedEngine(self.binding,os.path.join(self.tmp.name,'bridge.db'),os.path.join(self.tmp.name,'provider.db'))
    def tearDown(self): self.engine.close(); self.tmp.cleanup()

    def test_direct_db_task_with_keirin_denied_task_type_can_enter_engine(self):
        # Adversarial reproduction only: submit() correctly rejects this task type,
        # but direct task-store creation bypasses the domain registry and the execution
        # path currently does not revalidate persisted domain/task_type before starting.
        tid=db.create_task('keirin','should never execute',task_type='real_money_wagering')
        gen=self.engine.claim_and_start(tid,'worker-1')
        self.assertEqual(gen,1)
        self.assertEqual(db.get_task(tid)['state'],'IN_IMPLEMENT')

if __name__=='__main__': unittest.main()
