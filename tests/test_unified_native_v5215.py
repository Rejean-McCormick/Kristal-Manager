import hashlib, json, sqlite3, tempfile, unittest
from pathlib import Path
from contextlib import closing
from kristal_manager import unified_native_v5215 as n
ROOT=Path(__file__).resolve().parents[2];KIT=ROOT/'Kristal-Authoring-Kit';FRAMEWORK=ROOT/'Kristal-Framework'
# Isolated development may supply explicit repo roots, production uses siblings.
import os
KIT=Path(os.environ.get('KRISTAL_V5215_TEST_KIT',str(KIT)));FRAMEWORK=Path(os.environ.get('KRISTAL_V5215_TEST_FRAMEWORK',str(FRAMEWORK)))
class UnifiedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.k=n.load_kit(KIT);cls.r=cls.k.framework_reader(FRAMEWORK);cls.f=cls.r.f
    def test_pointer_exact(self):self.assertEqual(self.r.pointer({'a/b':{'~': [3]}},'/a~1b/~0/0'),3)
    def test_invalid_pointer(self):
        for p in ('/a/01','/a/-','/a/9','/a/~2','a'):
            with self.assertRaises(ValueError):self.r.pointer({'a':[1]},p)
    def test_bad_report_hash(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'report.json').write_text('{}')
            with self.assertRaises(ValueError):self.r.Reader(d,'0'*64)
    def test_verified_source_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,'x.json');p.write_bytes(b'{}');h=self.f.sha(p.read_bytes());self.assertEqual(self.r.verified(d,'x.json',h),b'{}');p.write_bytes(b'[]')
            with self.assertRaises(ValueError):self.r.verified(d,'x.json',h)
    def test_unsafe_path(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):self.r.verified(d,'../x','0'*64)
    def test_layer_active_metadata_only(self):
        e=self.r.envelope('active',{'namespace_id':'n','semantic_id':'KQ1'},{'identity':{},'labels':[],'content_availability':'INDEX_METADATA_ONLY','source_database_sha256':'a'*64});self.assertEqual(e['status'],'ACTIVE_INDEX_METADATA_ONLY');self.assertFalse(e['activation_authorized'])
    def test_layer_distinct(self):
        p={k:None for k in ('identity','labels','bridge_entry','native_record','projection','source_path','source_sha256','original_pointer','epistemic_status')};e=self.r.envelope('candidate',{'namespace_id':'n','semantic_id':'KA1'},p);self.assertEqual(e['status'],'PRIVATE_V11_CANDIDATE_NOT_ACTIVE');self.assertFalse(e['production_integrated'])
    def test_wrong_scope_rejected(self):
        from jsonschema import ValidationError
        with self.assertRaises(ValidationError):self.r.envelope('active',{'slug':'s'},{})
    def test_native_exact_collection(self):
        p='canon/epistemic/hypotheses.json';doc={'format':'k.monetary.epistemic/hypotheses/0.1.0','items':[{'id':'H1','status':'proposed'}]};self.assertEqual(self.k.native_rows(self.r,'k-monetary-system',p,doc),[('k-monetary-system',p,'/items','H1','id','/items/0')]);self.assertEqual(self.k.native_rows(self.r,'other',p,doc),[])
    def test_native_duplicate_id(self):
        with self.assertRaises(ValueError):self.k.native_rows(self.r,'k-monetary-system','canon/epistemic/hypotheses.json',{'format':'k.monetary.epistemic/hypotheses/0.1.0','items':[{'id':'H1'},{'id':'H1'}]})
    def test_native_wrong_contract(self):
        with self.assertRaises(ValueError):self.k.native_rows(self.r,'pitheory-prime-bridge','canon/epistemic/claim-ledger.json',{'format':'wrong','claims':[]})
    def test_prime_registry_namespace(self):
        doc={'registries':{}}
        for k in ('entities','properties','assertions','sources'):doc['registries'][k]={'schema_version':'7.0','namespace_id':'wrong',k:[]}
        with self.assertRaises(ValueError):self.k.native_rows(self.r,'prime-numbers','canon/domain/v9-logical-payload.json',doc)
    def test_active_scope_and_immutable_db(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=root/'active.sqlite'
            with closing(sqlite3.connect(path)) as c:
                c.executescript("CREATE TABLE workspace(slug,namespace_id,active);CREATE TABLE identity(namespace_id,semantic_id,owner_slug);CREATE TABLE lexical(namespace_id,semantic_id,language_tag,preferred_term);INSERT INTO workspace VALUES('s','n',1),('t','m',0);INSERT INTO identity VALUES('n','KQ1','s'),('m','KQ1','t');INSERT INTO lexical VALUES('n','KQ1','fr','test');");c.commit()
            raw=json.dumps({'status':self.r.STATUS,'database_sha256':n.digest(path)}).encode();(root/'report.json').write_bytes(raw);r=self.r.Reader(root,self.f.sha(raw));self.assertEqual(r.active('n','KQ1')['payload']['labels'][0]['preferred_term'],'test')
            with self.assertRaises(ValueError):r.active('m','KQ1')
            with closing(r.db()) as c:
                with self.assertRaises(sqlite3.OperationalError):c.execute('DELETE FROM identity')
if __name__=='__main__':unittest.main()
