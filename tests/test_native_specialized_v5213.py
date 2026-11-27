import tempfile,unittest
from pathlib import Path
from kristal_manager import native_specialized_v5213 as n

class SpecializedTests(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);self.w=Path(td.name)/'w';self.w.mkdir();self.out=Path(td.name)/'candidate';self.slug='pouvoirs-japon';self.path='knowledge-base/corpus/state.json'
        self.state={'schema_version':'6.0','artifact_type':'kristal_state','source_refs':[{'source_id':'s','title':'Source'}],'assertions':[{'assertion_id':'A1','statement':{'subject':{'kind':'actor_or_norm','id':'a'},'predicate':'p','object':{'kind':'proposition','value':'Texte de référence','language':'fr'}},'assertion_status':'sourced','record_role':'authoritative_constraint','evidence_refs':['s'],'notes':'keep'}]}
    def fixture(self):
        n.write(self.w/self.path,self.state);n.write(self.w/'kristal.workspace.json',{'slug':self.slug});n.write(self.w/'canon/state.index.json',{'canonical_artifacts':[]});return {'files':[{'artifact_type':self.state['artifact_type'],'path':self.path,'sha256':n.digest(self.w/self.path)}]}
    def build(self):return n.build(self.w,self.slug,self.out,self.fixture())
    def graph(self):return n.read(self.out/'canon/domain/v11/graph.json')
    def test_proposition_preserved(self):
        r=self.build();self.assertEqual(r['proposition_projections'],1);self.assertEqual(self.graph()['assertions'][0]['object'],{'kind':'literal','datatype':'string','value':'Texte de référence','language':'fr'});self.assertEqual(n.read(self.out/'native-originals/state.json'),self.state);self.assertEqual(r['labels'],0)
    def test_array_refused(self):
        self.state['assertions'][0]['statement']['object']['value']=['a','b']
        with self.assertRaisesRegex(ValueError,'Unsupported structured'):self.build()
    def test_boolean_not_integer(self):
        self.assertEqual(n.scalar({'kind':'value','value':True},{'value'})['datatype'],'boolean')
    def test_unknown_source_refused(self):
        self.state['assertions'][0]['evidence_refs']=['missing']
        with self.assertRaisesRegex(ValueError,'Unresolved'):self.build()
    def test_missing_source_refused(self):
        self.state['assertions'][0]['evidence_refs']=[]
        with self.assertRaisesRegex(ValueError,'Missing native evidence'):self.build()
    def test_japan_reviewed_rule(self):
        self.state['assertions'][0].update(evidence_refs=[],assertion_status='reviewed',record_role='organizational_rule');r=self.build();self.assertEqual(r['without_evidence'],1);self.assertEqual(self.graph()['assertions'][0]['sources'],[])
    def test_embedded_qualifier(self):
        self.slug='catho';s=self.state['source_refs'][0];self.state.update(schema_version='1.0',artifact_type='semantic_corpus');a=self.state['assertions'][0];a['statement']={'subject':{'external_id':'a','label':'A'},'predicate':{'external_id':'p','label':'P'},'object':{'kind':'item','value':{'external_id':'b','label':'B'}},'qualifiers':[{'predicate':{'external_id':'q','label':'Q'},'object':{'kind':'string','value':'Texte'}}]};a['evidence_refs']=[{'evidence_status':'provided','source_ref':s}];r=self.build();self.assertEqual(r['qualifiers'],1);self.assertEqual(r['labels'],0);self.assertEqual(len(self.graph()['assertions'][0]['qualifiers']),1);self.assertEqual(r['unqualified_label_observations'],4)
    def test_source_hash_drift(self):
        pin=self.fixture();(self.w/self.path).write_text('{}')
        with self.assertRaisesRegex(ValueError,'State drift'):n.build(self.w,self.slug,self.out,pin)
    def test_approval_pending(self):
        r=self.build();packet=n.packet_for(self.out,r);plan=n.n.registration_plan(self.out,self.w,r,packet);approval=n.e.approval_template(packet);self.assertFalse(plan['activation_authorized'])
        with self.assertRaises(ValueError):n.n.check_bound_approval(packet,plan,approval)
    def test_explicit_label_only(self):
        self.slug='time';a=self.state['assertions'][0];a['statement']={'subject':{'kind':'item','id':'a'},'predicate':'time.label_fr','object':{'kind':'value','value':'Temps'}};r=self.build();self.assertEqual(r['labels'],1);self.assertEqual(n.read(self.out/'canon/domain/v11/dictionaries/native-fr.json')['entries'][0]['preferred_term'],'Temps')
if __name__=='__main__':unittest.main()
