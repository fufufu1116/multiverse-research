import os, sqlite3, tempfile, unittest
import config, db

class V8EventTypeSupportProbe(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        config.DB_PATH=os.path.join(self.tmp.name,'tasks.db')
        db.init_schema()

    def tearDown(self):
        self.tmp.cleanup()

    def test_fenced_worker_can_declare_misleading_durable_event_type(self):
        tid=db.create_task('core','probe event type provenance')
        gen=db.claim_task(tid,'worker-1')
        db.transition(tid,'IN_IMPLEMENT',actor='engine',event_type='AUDITOR_PASS',fencing=('worker-1',gen))
        con=sqlite3.connect(config.DB_PATH); con.row_factory=sqlite3.Row
        row=con.execute("SELECT actor,event_type,before_state,after_state,detail_json FROM events WHERE task_id=? ORDER BY id DESC LIMIT 1",(tid,)).fetchone(); con.close()
        self.assertEqual(row['actor'],'worker-1')
        self.assertEqual(row['before_state'],'PENDING')
        self.assertEqual(row['after_state'],'IN_IMPLEMENT')
        # Reproduction: state provenance is correct, but the durable semantic label is caller-controlled.
        self.assertEqual(row['event_type'],'AUDITOR_PASS')

if __name__=='__main__': unittest.main()
