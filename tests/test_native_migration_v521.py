from contextlib import closing
from pathlib import Path
import json, sqlite3, tempfile, unittest
from kristal_manager import native_migration_v521 as m
from kristal_manager.active_semantic_federation_v518 import _schema, _ingest_active
from collections import Counter

class MigrationTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name);self.w=self.root/'workspace';self.w.mkdir()
        self.registry={'referents':[{'ref':'urn:fixture:one','kind':'concept','labels':[{'lang':'fr','text':'Un'}]},{'ref':'urn:fixture:two','kind':'concept','labels':[{'lang':'en','text':'Two'}]}]}
        self.state={'schema_version':'6.0','artifact_type':'kristal_state','source_refs':[{'source_id':'urn:source'}],'assertions':[{'assertion_id':'a','statement':{'subject':{'kind':'item','id':'urn:fixture:one'},'predicate':'fixture:predicate','object':{'kind':'item','id':'urn:fixture:two'}},'assertion_status':'reviewed','record_role':'reference_knowledge','evidence_refs':['urn:source'],'notes':['kept']}]}
        self.write_fixture()
    def write_fixture(self):
        for rel,data in [('kristal.workspace.json',{'slug':'fixture'}),('canon/state.index.json',{'canonical_artifacts':[]}),('knowledge-base/corpus/index.json',{'state':'state.json','registry':'registry.json'}),('knowledge-base/corpus/state.json',self.state),('knowledge-base/corpus/registry.json',self.registry)]:
            p=self.w/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(m.bytes_json(data))
    def build(self,name='out',expected=None):return m.build_candidate(self.w,'fixture',self.root/name,expected)
    def test_exact_bridge_and_determinism(self):
        r=self.build();other=self.build('out2');self.assertEqual(r,other);self.assertTrue(m.verify_bridge(self.root/'out'));self.assertEqual(r['implicit_predicates'],1);self.assertEqual(r['labels'],2);self.assertFalse((self.w/'.kristal/v11/authoring.json').exists())
    def test_duplicate_occurrences_preserved(self):
        a=json.loads(json.dumps(self.state['assertions'][0]));a['notes']=['different metadata'];self.state['assertions'].append(a);self.write_fixture();r=self.build();self.assertEqual(r['assertion_occurrences'],2);self.assertEqual(r['duplicate_assertion_ids'],1)
    def test_conflicting_duplicate_rejected(self):
        a=json.loads(json.dumps(self.state['assertions'][0]));a['statement']['object']={'kind':'literal','value':'different'};self.state['assertions'].append(a);self.write_fixture();self.assertRaisesRegex(ValueError,'different statement',self.build)
    def test_unknown_subject_or_evidence_rejected(self):
        self.state['assertions'][0]['evidence_refs']=['unknown'];self.write_fixture();self.assertRaisesRegex(ValueError,'Missing evidence',self.build)
    def test_native_drift_rejected(self):
        self.assertRaisesRegex(ValueError,'source changed',lambda:self.build(expected={}))
    def test_already_active_rejected(self):
        p=self.w/'.kristal/v11/authoring.json';p.parent.mkdir(parents=True);p.write_text('{}');self.assertRaisesRegex(ValueError,'Already active',self.build)
    def test_tampered_original_rejected(self):
        self.build();(self.root/'out/native-originals/state.json').write_text('{}');self.assertRaisesRegex(ValueError,'hash mismatch',lambda:m.verify_bridge(self.root/'out'))
    def test_typed_literal(self):
        self.assertEqual(m.literal({'kind':'literal','value':False}),{'kind':'literal','datatype':'boolean','value':False});self.assertRaises(ValueError,m.literal,{'kind':'literal','value':{'x':1}})
    def test_future_queue_and_existing_queue(self):
        with closing(sqlite3.connect(':memory:')) as db:
            _schema(db);db.execute("INSERT INTO workspace VALUES ('fixture','fixture','ns',1,NULL,'hash',NULL,1)")
            p={'identities':[{'id':sid,'kind':kind,'status':'stable','wikidata':{'accepted_exact':None,'candidate_exact':[]},'labels':{}} for sid,kind in [('KQ1','entity'),('KP1','property'),('KA1','assertion'),('KS1','source')]]};_ingest_active(db,'ns','fixture',p,Counter());self.assertEqual(db.execute('SELECT count(*) FROM review_queue').fetchone()[0],2)
            db.execute("INSERT INTO review_queue VALUES ('ns','KS1','MISSING_ACTIVE_LABEL','{}')");db.execute("INSERT INTO review_queue VALUES ('ns','KA1','OTHER','{}')");r=m.correct_queue(db);self.assertEqual(r,{'before':3,'after':2,'removed':1});self.assertEqual(db.execute('SELECT count(*) FROM identity').fetchone()[0],4);self.assertEqual(db.execute("SELECT count(*) FROM review_queue WHERE issue='OTHER'").fetchone()[0],1)

if __name__=='__main__':unittest.main()
