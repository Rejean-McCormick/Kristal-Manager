import tempfile, unittest, json
from pathlib import Path
from kristal_manager import native_extension_v5211 as m

class ExtensionTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name);self.w=self.root/'workspace';self.w.mkdir()
        self.reg={'referents':[{'referent_id':'a','kind':'domain','label_fr':'Un'},{'referent_id':'b','kind':'concept','label_fr':'Deux'}]}
        self.state={'schema_version':'6.0','artifact_type':'kristal_state','source_refs':['s'],'assertions':[{'assertion_id':'a1','statement':{'subject':{'kind':'referent','id':'a'},'predicate':'p','object':{'kind':'referent','id':'b'}},'assertion_status':'validated','record_role':'reference_knowledge','evidence_refs':['s'],'notes':['kept']}]}
    def fixture(self):
        paths={'registry':'knowledge-base/corpus/referents.json','state':'knowledge-base/corpus/state.json','index':'knowledge-base/corpus/index.json','workspace':'kristal.workspace.json','state_index':'canon/state.index.json'}
        for k,d in [('registry',self.reg),('state',self.state),('index',{}),('workspace',{'slug':'fixture'}),('state_index',{})]:
            p=self.w/paths[k];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(m.bytes_json(d))
        return {'paths':paths,'sha256':{k:m.digest(self.w/p) for k,p in paths.items()}}
    def build(self):return m.build_candidate(self.w,'fixture',self.root/'out',self.fixture())
    def test_direct_original_refs_and_labels(self):
        r=self.build();self.assertEqual(r['labels'],2);self.assertEqual(r['implicit_predicates'],1);self.assertTrue(m.verify_bridge(self.root/'out'));self.assertFalse((self.w/'.kristal/v11/authoring.json').exists())
    def test_label_variants(self):
        self.assertEqual(m.ref_labels({'label':'A','label_en':'B'}),[('fr','A'),('en','B')]);self.assertEqual(dict(m.ref_labels({'labels':{'fr':'A','en':'B'}})),{'fr':'A','en':'B'})
    def test_ambiguous_ref_rejected(self):
        with self.assertRaises(ValueError):m.ref_id({'id':'a','ref':'b'})
    def test_list_literal_rejected(self):
        self.state['assertions'][0]['statement']['object']={'kind':'string','value':['a','b'],'language':'fr'}
        with self.assertRaisesRegex(ValueError,'Unsupported literal type'):self.build()
    def test_unknown_evidence_rejected(self):
        self.state['assertions'][0]['evidence_refs']=['unknown']
        with self.assertRaisesRegex(ValueError,'Missing evidence'):self.build()
    def test_epistemic_status_not_recast(self):
        self.state['assertions'][0]['record_role']='structural_record';self.state['assertions'][0]['assertion_status']='reviewed';r=self.build();p=m.review_packet(self.root/'out',r);self.assertEqual(p['assertion_review'][0]['role'],'structural_record');self.assertIn('notes',p['native_assertion_fields'])
    def test_source_pin_refuses_drift(self):
        pin=self.fixture();(self.w/pin['paths']['registry']).write_text('{}')
        with self.assertRaisesRegex(ValueError,'Native source changed'):m.build_candidate(self.w,'fixture',self.root/'out',pin)
    def test_approval_default_blocked_and_hash_bound(self):
        p=m.review_packet(self.root/'out',self.build());a=m.approval_template(p)
        with self.assertRaises(ValueError):m.approval_gate(p,a)
        a.update(reviewer='External reviewer',decision_id='test-1',decision='approve',independence_declared=True,attestations={k:True for k in p['required_attestations']})
        self.assertEqual(m.approval_gate(p,a),'DECLARATION_COMPLETE_INDEPENDENCE_NOT_VERIFIED_ACTIVATION_PENDING')
        with self.assertRaises(ValueError):m.approval_gate({**p,'slug':'other'},a)
    def test_original_drift_rejected(self):
        self.build();(self.root/'out/native-originals/state.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'Original source hash mismatch'):m.verify_bridge(self.root/'out')
    def test_audit_has_exact_hash_and_no_authority(self):
        self.fixture();a=m.corpus_audit(self.w,{'slug':'fixture','local_directory':'workspace'});self.assertEqual(len(a['files']),3);self.assertEqual(a['status'],'NEEDS_NATIVE_ADAPTER_REVIEW');self.assertTrue(all(len(x['sha256'])==64 for x in a['files']))

if __name__=='__main__':unittest.main()
