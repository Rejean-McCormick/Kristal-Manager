import tempfile,unittest
from pathlib import Path
from kristal_manager import native_extension_v5212 as n

class AdapterTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name);self.w=self.root/'workspace';self.w.mkdir();self.out=self.root/'candidate'
        self.reg={'referents':[{'ref':'a','kind':'concept','labels':[{'lang':'fr','text':'A'}]},{'ref':'b','kind':'concept','label_fr':'B'}]}
        self.state={'schema_version':'6.0','artifact_type':'kristal_state','source_refs':['s'],'assertions':[{'assertion_id':'a1','statement':{'subject':{'kind':'item','id':'a'},'predicate':'p','object':{'kind':'item','id':'b'}},'assertion_status':'sourced','record_role':'reference_knowledge','evidence_refs':['ev:s'],'notes':['keep']}]}
        self.ev={'artifact_type':'evidence_registry','evidence':[{'evidence_id':'ev:s','source_id':'s'}]};self.catalog={'sources':[{'source_id':'s'}]}
    def fixture(self):
        paths={'registry':'knowledge-base/corpus/referents.json','state':'knowledge-base/corpus/state.json','index':'knowledge-base/corpus/index.json','workspace':'kristal.workspace.json','state_index':'canon/state.index.json','evidence_registry':'knowledge-base/sources/evidence-registry.json','source_catalog':'knowledge-base/sources/source-catalog.json'}
        values={'registry':self.reg,'state':self.state,'index':{},'workspace':{'slug':'fixture'},'state_index':{'canonical_artifacts':[]},'evidence_registry':self.ev,'source_catalog':self.catalog}
        for k,p in paths.items():n.write(self.w/p,values[k])
        return {'paths':paths,'sha256':{k:n.digest(self.w/p) for k,p in paths.items()}}
    def build(self):return n.build_candidate(self.w,'fixture',self.out,self.fixture())
    def test_explicit_evidence_mapping(self):
        r=self.build();self.assertTrue(n.verify_bridge(self.out));self.assertEqual(r['sources'],1);self.assertEqual(r['labels'],2);self.assertEqual(r['implicit_predicates'],1)
    def test_unresolved_evidence(self):
        self.ev['evidence'][0]['source_id']='missing'
        with self.assertRaisesRegex(ValueError,'unresolved evidence'):self.build()
    def test_duplicate_evidence(self):
        self.ev['evidence']*=2
        with self.assertRaisesRegex(ValueError,'Ambiguous'):self.build()
    def test_missing_evidence_structural_only(self):
        a=self.state['assertions'][0];a.update(assertion_status='reviewed',record_role='structural_record');del a['evidence_refs'];r=self.build();self.assertEqual(r['structural_without_evidence'],1);self.assertEqual(n.read(self.out/'canon/domain/v11/graph.json')['assertions'][0]['sources'],[])
    def test_missing_evidence_sourced_rejected(self):
        del self.state['assertions'][0]['evidence_refs']
        with self.assertRaisesRegex(ValueError,'Missing evidence'):self.build()
    def test_catalog_only_source(self):
        self.assertEqual(n.source_records({'state':{},'source_catalog':{'items':[{'id':'s'}]}}),('source_catalog','items',[{'id':'s'}]))
    def test_catalog_mismatch(self):
        self.catalog['sources']=[]
        with self.assertRaisesRegex(ValueError,'Source catalog mismatch'):self.build()
    def test_aging_list_still_refused(self):
        self.state['assertions'][0]['statement']['object']={'kind':'string','value':['a','b'],'language':'fr'}
        with self.assertRaisesRegex(ValueError,'Unsupported literal type'):self.build()
    def test_plan_and_approval(self):
        r=self.build();packet=n.review_packet(self.out,r);plan=n.registration_plan(self.out,self.w,r,packet);self.assertEqual(len(plan['artifacts']),4);self.assertFalse(plan['activation_authorized']);self.assertFalse((self.w/'.kristal/v11/authoring.json').exists());a=n.approval_template(packet)
        with self.assertRaises(ValueError):n.check_bound_approval(packet,plan,a)
        a.update(reviewer='Test fixture',decision_id='test',decision='approve',independence_declared=True,attestations={k:True for k in packet['required_attestations']},registration_plan_sha256=n.sha(n.bytes_json(plan)),epistemic_reader_contract_verified=True)
        self.assertEqual(n.check_bound_approval(packet,plan,a),'DECLARATION_COMPLETE_NO_PRODUCTION_ACTIVATION')
        with self.assertRaisesRegex(ValueError,'registration plan'):n.check_bound_approval(packet,{**plan,'state_index_sha256':'bad'},a)
    def test_plan_source_drift(self):
        r=self.build();packet=n.review_packet(self.out,r);(self.w/'canon/state.index.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'Original source drift'):n.registration_plan(self.out,self.w,r,packet)
    def test_predicate_explicit_observation_only(self):
        r=self.build();packet=n.review_packet(self.out,r);n.write(self.w/'knowledge-base/sources/predicates.json',{'predicates':[{'id':'p','label_fr':'Relation'},{'id':'other','label_fr':'Other'}]});items=n.exact_predicate_observations(self.out,self.w,packet);self.assertEqual(len(items),1);self.assertEqual(items[0]['observations'][0]['term'],'Relation');self.assertEqual(items[0]['occurrences'],1)
    def test_bridge_rejects_tampered_evidence(self):
        self.build();(self.out/'native-originals/evidence_registry.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'Original source hash mismatch'):n.verify_bridge(self.out)
if __name__=='__main__':unittest.main()
