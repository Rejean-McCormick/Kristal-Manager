import unittest,sys,tempfile,sqlite3,json,os
from pathlib import Path
from kristal_manager import maintenance_scan as m
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0,os.environ['KRISTALIZER_ROOT'])
        from kristalizer import maintenance_evidence
        cls.e=maintenance_evidence
    def test_exact_namespace(self):
        with self.assertRaises(ValueError):self.e.anchors({'namespace_id':'other','format':'dik.bulk-secondpass/2'},'ns',{})
    def test_kind_and_ambiguity(self):
        d={'namespace_id':'ns','format':'dik.bulk-secondpass/2','by_kind':{'Q':{'a':'KQ1','b':'KQ2','c':'KP3'},'P':{'a':'KP1','d':'KP2'}}}
        self.assertEqual(self.e.anchors(d,'ns',{'KQ1':'entity','KQ2':'entity','KP1':'property','KP2':'property','KP3':'property'}),{'b':'KQ2','d':'KP2'})
    def test_no_language_guess(self):
        d={'referents':[{'ref':'a','label':'not attested','label_fr':'exact','labels':[{'lang':'en','text':'exact EN'}]}]}
        self.assertEqual([(n,l,t) for n,l,t,p,k in self.e.observations(d)],[('a','fr','exact'),('a','en','exact EN')])
    def test_ambiguous_native_id(self):
        self.assertEqual(list(self.e.observations({'referents':[{'ref':'a','id':'b','label_fr':'X'}]})),[])
    def test_v8_space_required(self):
        d={'artifact_type':'kristall_lexicon','language':'fr','entries':[{'semantic_ref':{'identity_space':'other','id':'a'},'preferred_term':'A'}]}
        self.assertEqual(list(self.e.observations(d)),[])
    def test_duplicate_json(self):
        with self.assertRaises(ValueError):m.parse(b'{"x":1,"x":2}')
    def test_nonfinite(self):
        with self.assertRaises(ValueError):m.parse(b'{"x":NaN}')
    def test_unsafe_path(self):
        for x in ('../x','/x','C:x','a\\b'):
            with self.assertRaises(ValueError):m.safe(x)
    def test_local_compact_exact_observation(self):
        from kristalizer.core import EncyIndex
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'test.sqlite'
            with sqlite3.connect(p) as db:
                db.execute('CREATE TABLE entity(id INTEGER,wid TEXT,kind TEXT,label_fr TEXT,label_en TEXT,description_fr TEXT,description_en TEXT)')
                db.execute("INSERT INTO entity VALUES (42,'Q42','item','un','one','','')")
            db.close()
            before=m.digest(p)
            with EncyIndex(p) as idx:
                self.assertEqual(idx.details('Q42')['label'],'un');self.assertEqual(idx.details('Q43'),{'missing':True})
            self.assertEqual(before,m.digest(p))
    def test_private_reader_gate(self):
        import importlib.util
        p=Path(os.environ['DIK_MAINTENANCE_READER']);s=importlib.util.spec_from_file_location('maint_read',p);mod=importlib.util.module_from_spec(s);s.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);base=p/'base';scan=p/'scan';base.mkdir();scan.mkdir()
            c=sqlite3.connect(base/'active.sqlite');c.executescript("CREATE TABLE identity(namespace_id,semantic_id,kind);INSERT INTO identity VALUES('ns','KQ1','entity');CREATE TABLE lexical(namespace_id,semantic_id,language_tag,preferred_term);");c.close()
            c=sqlite3.connect(scan/'maintenance.sqlite');c.executescript("CREATE TABLE resolution(ns,sid,lang,status,term,variants_json);INSERT INTO resolution VALUES('ns','KQ1','fr','PRIVATE_EXACT_ANCHOR_CONSENSUS','terme','[\"terme\"]');CREATE TABLE observation(ns,sid,lang,native_id,path,sha256,pointer,method);");c.close()
            h=m.digest(scan/'maintenance.sqlite');(scan/'report.json').write_text(json.dumps({'base_database_sha256':m.digest(base/'active.sqlite'),'maintenance_database_sha256':h}));(scan/'diagnostic.json').write_text(json.dumps({'status':'PASS_PRIVATE_RECEIPT_SCOPE','source_bytes_and_pointers_checked':True,'database_sha256':h}));(scan/'COMPLETE').touch()
            self.assertEqual(mod.lookup(base,scan,'ns','KQ1','fr')['status'],'MISSING_ACTIVE_LABEL');self.assertEqual(mod.lookup(base,scan,'ns','KQ1','fr',True)['term'],'terme')
            with (scan/'maintenance.sqlite').open('ab') as f:f.write(b'drift')
            with self.assertRaises(ValueError):mod.lookup(base,scan,'ns','KQ1','fr',True)
