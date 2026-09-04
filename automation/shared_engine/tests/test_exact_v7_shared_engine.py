import os, tempfile, unittest
import config, db
from domain_registry import DomainPolicyError
from integration_bridge import IntegrationBinding, apply_receipt
from exact_v7_shared_engine import ExactV7SharedEngine, V7_MANIFEST
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD, v7_result_to_bridge_receipt
from current_state import shared_current
from orchestrator_provider_adapter_v7 import ProviderAdapterManifest, ProviderAdapterReceiptStore, DeterministicLocalAdapter, provider_request_from_job, OrchestratorError

HEAD='5'*40; BRANCH='agent/automation-shared-engine-integration-v8-test'

class ExactV7SharedEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); config.DB_PATH=os.path.join(self.tmp.name,'task.db'); db.init_schema()
        self.binding=IntegrationBinding(CANONICAL_MAIN,BRANCH,HEAD,V7_HEAD)
        self.engine=ExactV7SharedEngine(self.binding,os.path.join(self.tmp.name,'bridge.db'),os.path.join(self.tmp.name,'provider.db'))
    def tearDown(self): self.engine.close(); self.tmp.cleanup()
    def test_actual_v7_manifest_is_loaded(self):
        m=ProviderAdapterManifest.load(V7_MANIFEST); self.assertEqual(m.canonical_main,CANONICAL_MAIN)
    def test_same_exact_v7_path_runs_core_and_keirin_to_done(self):
        c=self.engine.submit('core','implement','core candidate',priority=2); self.assertEqual(self.engine.run_happy_path(c,'wc'),'DONE')
        k=self.engine.submit('keirin','research','PIT-safe research',priority=2); self.assertEqual(self.engine.run_happy_path(k,'wk'),'DONE')
        self.assertEqual(db.get_task(c)['state'],'DONE'); self.assertEqual(db.get_task(k)['state'],'DONE')
        snap=shared_current({'canonical_main':CANONICAL_MAIN,'automation_candidate':HEAD,'keirin_research':'d76a76b0ebd520626cee010fded9fa7a19f65c50'})
        self.assertEqual(snap['domains']['core']['done_count'],1); self.assertEqual(snap['domains']['keirin']['done_count'],1); self.assertFalse(snap['authority']['chat'])
    def test_keirin_firewall_blocks_before_task_creation(self):
        before=len(db.list_tasks())
        with self.assertRaisesRegex(DomainPolicyError,'result_feature_access'): self.engine.submit('keirin','research','unsafe',requested_capabilities={'result_feature_access':True})
        with self.assertRaisesRegex(DomainPolicyError,'PROTECTED_RESOURCE_DENIED'): self.engine.submit('keirin','analysis','unsafe',resources={'ECON_HOLDOUT1000'})
        self.assertEqual(len(db.list_tasks()),before)
    def test_core_runtime_activation_blocks_before_task_creation(self):
        with self.assertRaisesRegex(DomainPolicyError,'runtime_activation'): self.engine.submit('core','implement','unsafe',requested_capabilities={'runtime_activation':True})
    def test_malformed_v7_implement_never_advances_task(self):
        t=self.engine.submit('core','implement','x'); gen=self.engine.claim_and_start(t,'w')
        with self.assertRaises(OrchestratorError):
            self.engine.execute_role(t,'IMPLEMENT',0,'bad','w',gen,{'status':'READY','candidate_head':HEAD,'diff_lines':True,'cost_microusd':0,'evidence_ref':'e'})
        self.assertEqual(db.get_task(t)['state'],'IN_IMPLEMENT')
    def test_stale_fence_rejects_even_valid_v7_result(self):
        t=self.engine.submit('core','implement','x'); gen=self.engine.claim_and_start(t,'w')
        with self.assertRaises(db.LostLeaseError):
            self.engine.execute_role(t,'IMPLEMENT',0,'stale','w',gen+1,{'status':'READY','candidate_head':HEAD,'diff_lines':0,'cost_microusd':0,'evidence_ref':'e'})
        self.assertEqual(db.get_task(t)['state'],'IN_IMPLEMENT')
    def test_actual_v7_provider_receipt_is_idempotent_once(self):
        m=ProviderAdapterManifest.load(V7_MANIFEST); path=os.path.join(self.tmp.name,'once.db'); store=ProviderAdapterReceiptStore(path,m)
        job={'operation_key':'op','task_id':'t','role':'IMPLEMENT','semantic_generation':0,'candidate_head':HEAD,'candidate_branch':BRANCH,'canonical_main':CANONICAL_MAIN,'objective':'x','authority':{'candidate_only':True,'live_provider':False,'production':False,'runtime':False,'spend':False}}
        req=provider_request_from_job(job,m); result={'status':'READY','candidate_head':HEAD,'diff_lines':0,'cost_microusd':0,'evidence_ref':'e'}
        try:
            self.assertEqual(store.execute_local_once('op',req,DeterministicLocalAdapter({'IMPLEMENT':{'1':result}})),result)
            self.assertEqual(store.execute_local_once('op',req,DeterministicLocalAdapter({'IMPLEMENT':{'1':result}})),result)
            self.assertEqual(store.execution_count('op'),1)
        finally: store.close()
    def test_crash_after_provider_receipt_before_task_transition_reuses_once(self):
        t=self.engine.submit('core','implement','crash-window'); gen=self.engine.claim_and_start(t,'w'); job=self.engine._job(t,'IMPLEMENT',0,'crash-op')
        req=provider_request_from_job(job,self.engine.manifest); result={'status':'READY','candidate_head':HEAD,'diff_lines':1,'cost_microusd':0,'evidence_ref':'crash-e'}
        store=ProviderAdapterReceiptStore(self.engine.provider_receipt_db,self.engine.manifest)
        try:
            durable=store.execute_local_once('crash-op',req,DeterministicLocalAdapter({'IMPLEMENT':{'1':result}}))
            self.assertEqual(store.execution_count('crash-op'),1)
        finally: store.close()
        self.assertEqual(db.get_task(t)['state'],'IN_IMPLEMENT')
        store=ProviderAdapterReceiptStore(self.engine.provider_receipt_db,self.engine.manifest)
        try:
            replay=store.execute_local_once('crash-op',req,DeterministicLocalAdapter({'IMPLEMENT':{'1':result}})); self.assertEqual(store.execution_count('crash-op'),1)
        finally: store.close()
        bridge=v7_result_to_bridge_receipt(job,replay,local_binding=self.binding); self.engine.bridge_receipts.record(bridge)
        self.assertEqual(apply_receipt(t,bridge,self.binding,'w',gen),'IN_LAB')
    def test_conflicting_same_operation_provider_replay_fails_closed(self):
        m=ProviderAdapterManifest.load(V7_MANIFEST); path=os.path.join(self.tmp.name,'conflict.db'); store=ProviderAdapterReceiptStore(path,m)
        base={'operation_key':'same','task_id':'t','role':'IMPLEMENT','semantic_generation':0,'candidate_head':HEAD,'candidate_branch':BRANCH,'canonical_main':CANONICAL_MAIN,'objective':'a','authority':{'candidate_only':True,'live_provider':False,'production':False,'runtime':False,'spend':False}}
        result={'status':'READY','candidate_head':HEAD,'diff_lines':0,'cost_microusd':0,'evidence_ref':'e'}
        try:
            store.execute_local_once('same',provider_request_from_job(base,m),DeterministicLocalAdapter({'IMPLEMENT':{'1':result}}))
            changed=dict(base); changed['objective']='b'
            with self.assertRaisesRegex(OrchestratorError,'CONFLICTING_REPLAY'):
                store.execute_local_once('same',provider_request_from_job(changed,m),DeterministicLocalAdapter({'IMPLEMENT':{'1':result}}))
        finally: store.close()
    def test_lab_fix_required_routes_without_owner_gate(self):
        t=self.engine.submit('core','implement','x'); gen=self.engine.claim_and_start(t,'w'); head=HEAD
        self.engine.execute_role(t,'IMPLEMENT',0,'i','w',gen,{'status':'READY','candidate_head':head,'diff_lines':0,'cost_microusd':0,'evidence_ref':'i'})
        state=self.engine.execute_role(t,'LAB',0,'l','w',gen,{'verdict':'FIX_REQUIRED','reviewed_head':head,'evidence_ref':'l','code':'EDGE','detail':'repair'})
        self.assertEqual(state,'LAB_FIX_REQUIRED'); self.assertNotEqual(db.get_task(t)['state'],'OWNER_GATE')
    def test_audit_fix_required_routes_without_owner_gate(self):
        t=self.engine.submit('core','implement','x'); gen=self.engine.claim_and_start(t,'w'); head=HEAD
        self.engine.execute_role(t,'IMPLEMENT',0,'i-audit','w',gen,{'status':'READY','candidate_head':head,'diff_lines':0,'cost_microusd':0,'evidence_ref':'i-audit'})
        self.engine.execute_role(t,'LAB',0,'l-pass','w',gen,{'verdict':'PASS','reviewed_head':head,'evidence_ref':'l-pass'})
        state=self.engine.execute_role(t,'AUDIT',0,'a-fix','w',gen,{'verdict':'FIX_REQUIRED','reviewed_head':head,'evidence_ref':'a-fix','code':'AUDIT_EDGE','detail':'bounded repair'})
        self.assertEqual(state,'AUDIT_FIX_REQUIRED'); self.assertNotEqual(db.get_task(t)['state'],'OWNER_GATE')

if __name__=='__main__': unittest.main()
