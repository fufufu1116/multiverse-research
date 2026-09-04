import os, tempfile, unittest
import config, db
from domain_registry import DomainPolicyError
from integration_bridge import IntegrationBinding
from exact_v7_shared_engine import ExactV7SharedEngine
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD

HEAD='5'*40; BRANCH='agent/automation-shared-engine-integration-v8-test'

class V8PersistedDomainRevalidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); config.DB_PATH=os.path.join(self.tmp.name,'task.db'); db.init_schema()
        self.binding=IntegrationBinding(CANONICAL_MAIN,BRANCH,HEAD,V7_HEAD)
        self.engine=ExactV7SharedEngine(self.binding,os.path.join(self.tmp.name,'bridge.db'),os.path.join(self.tmp.name,'provider.db'))
    def tearDown(self): self.engine.close(); self.tmp.cleanup()

    def test_direct_db_denied_keirin_task_type_cannot_start(self):
        tid=db.create_task('keirin','must remain inert',task_type='real_money_wagering')
        before=db.get_task(tid)
        with self.assertRaisesRegex(DomainPolicyError,'TASK_TYPE_DENIED:keirin:real_money_wagering'):
            self.engine.claim_and_start(tid,'worker-1')
        after=db.get_task(tid)
        self.assertEqual(after['state'],before['state'])
        self.assertEqual(after['claimed_by'],before['claimed_by'])
        self.assertEqual(after['claim_generation'],before['claim_generation'])
        self.assertEqual(after['lease_until'],before['lease_until'])

    def test_unknown_direct_db_domain_cannot_start(self):
        tid=db.create_task('shadow-domain','must remain inert',task_type='research')
        with self.assertRaisesRegex(DomainPolicyError,'UNKNOWN_DOMAIN:shadow-domain'):
            self.engine.claim_and_start(tid,'worker-1')
        self.assertEqual(db.get_task(tid)['state'],'PENDING')
        self.assertIsNone(db.get_task(tid)['claimed_by'])

    def test_execution_job_revalidates_persisted_task_after_start(self):
        tid=self.engine.submit('core','implement','valid start')
        gen=self.engine.claim_and_start(tid,'worker-1')
        con=db._conn(); con.execute('BEGIN IMMEDIATE')
        try:
            con.execute("UPDATE tasks SET domain='shadow-domain' WHERE id=?",(tid,)); con.commit()
        finally: con.close()
        with self.assertRaisesRegex(DomainPolicyError,'UNKNOWN_DOMAIN:shadow-domain'):
            self.engine.execute_role(tid,'IMPLEMENT',0,'op','worker-1',gen,{'status':'READY','candidate_head':HEAD,'diff_lines':0,'cost_microusd':0,'evidence_ref':'e'})
        self.assertEqual(db.get_task(tid)['state'],'IN_IMPLEMENT')

if __name__=='__main__': unittest.main()
