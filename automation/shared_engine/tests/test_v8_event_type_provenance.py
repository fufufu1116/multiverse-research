import json, os, sqlite3, tempfile, unittest
import config, db

class V8EventTypeProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        config.DB_PATH=os.path.join(self.tmp.name,'tasks.db')
        db.init_schema()

    def tearDown(self):
        self.tmp.cleanup()

    def test_caller_event_label_cannot_replace_authoritative_transition_type(self):
        tid=db.create_task('core','event type provenance')
        gen=db.claim_task(tid,'worker-1')
        db.transition(tid,'IN_IMPLEMENT',actor='Independent Auditor',event_type='AUDITOR_PASS',detail={'declared_event_type':'spoof'},fencing=('worker-1',gen))
        con=sqlite3.connect(config.DB_PATH); con.row_factory=sqlite3.Row
        row=con.execute("SELECT actor,event_type,before_state,after_state,detail_json FROM events WHERE task_id=? ORDER BY id DESC LIMIT 1",(tid,)).fetchone(); con.close()
        detail=json.loads(row['detail_json'])
        self.assertEqual(row['actor'],'worker-1')
        self.assertEqual(row['event_type'],'STATE_TRANSITION:PENDING->IN_IMPLEMENT')
        self.assertEqual(detail['declared_actor'],'Independent Auditor')
        self.assertEqual(detail['declared_event_type'],'AUDITOR_PASS')
        self.assertEqual(detail['fencing_worker'],'worker-1')

    def test_normal_engine_label_is_retained_only_as_declared_metadata(self):
        tid=db.create_task('core','normal event type')
        gen=db.claim_task(tid,'worker-1')
        db.transition(tid,'IN_IMPLEMENT',actor='exact_v7_shared_engine',event_type='START',fencing=('worker-1',gen))
        con=sqlite3.connect(config.DB_PATH); con.row_factory=sqlite3.Row
        row=con.execute("SELECT event_type,detail_json FROM events WHERE task_id=? ORDER BY id DESC LIMIT 1",(tid,)).fetchone(); con.close()
        detail=json.loads(row['detail_json'])
        self.assertEqual(row['event_type'],'STATE_TRANSITION:PENDING->IN_IMPLEMENT')
        self.assertEqual(detail['declared_event_type'],'START')
        self.assertEqual(detail['declared_actor'],'exact_v7_shared_engine')

if __name__=='__main__': unittest.main()
