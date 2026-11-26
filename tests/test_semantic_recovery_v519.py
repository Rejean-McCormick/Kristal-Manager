import hashlib,json,sqlite3,tempfile,unittest
from pathlib import Path
from kristal_manager.local_first_audit import ReadOnlyTree,LocalFirstAuditError
from kristal_manager.active_semantic_federation_v518 import _schema
from kristal_manager.semantic_recovery_v519 import schema,scan_owner,resolve,guard,source_class
from collections import Counter

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); self.root=Path(t.name)
        self.db=sqlite3.connect(':memory:'); self.addCleanup(self.db.close); _schema(self.db); schema(self.db)
        self.db.execute("INSERT INTO workspace VALUES ('test','Kristal-Test','ns',1,NULL,'state',NULL,1)")
        self.ids={'KQ1':('entity','Q1'),'KQ2':('entity',None),'KS1':('source',None)}
        for sid,(kind,qid) in self.ids.items(): self.db.execute('INSERT INTO identity VALUES (?,?,?,?,?,?,?)',('ns',sid,'test',kind,'stable',qid,'[]'))
        self.counts=Counter()
    def write(self,path,obj):
        p=self.root/'Kristal-Test'/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj),encoding='utf8'); return p
    def dictionary(self,name,entries,ns='ns'):
        return self.write('canon/domain/v11/old/dictionaries/'+name+'.json',{'namespace_id':ns,'language':'fr','entries':entries})
    def row(self,sid,term,**kw): return {'semantic_id':sid,'preferred_term':term,**kw}
    def scan(self):
        tree=ReadOnlyTree(self.root)
        try: scan_owner(self.db,tree,'test','Kristal-Test','ns',self.ids,self.counts); resolve(self.db)
        finally: tree.close()
    def test_scope_and_kind(self):
        self.dictionary('a',[self.row('KQ1','alpha'),self.row('KS1','source'),self.row('KQ2','wrong',namespace_id='other')]); self.dictionary('b',[self.row('KQ1','foreign')],ns='other'); self.scan()
        self.assertEqual(self.db.execute('SELECT suggested_term FROM recovery_resolution').fetchall(),[('alpha',)])
        self.assertEqual(self.db.execute('SELECT count(*) FROM lexical').fetchone()[0],0)
    def test_active_precedence_and_conflict(self):
        self.db.execute("INSERT INTO lexical VALUES ('ns','KQ1','fr','canon','canon',1,'{}')")
        self.dictionary('a',[self.row('KQ1','wrong'),self.row('KQ2','a')]); self.dictionary('b',[self.row('KQ2','b')]); self.scan()
        self.assertEqual(self.db.execute('SELECT status,suggested_term FROM recovery_resolution ORDER BY semantic_id').fetchall(),[('ACTIVE_PRECEDENCE_CONFLICT',None),('UNREVIEWED_CONFLICT',None)])
        self.assertEqual(self.db.execute('SELECT term,status FROM recovery_lookup').fetchall(),[('canon','ACTIVE_CANONICAL')])
    def test_accepted_cache_only(self):
        for q in ('Q1','Q2'):
            self.write('external-source-library/wikidata/snap/entities/'+q+'.json',{'id':q,'labels':{'en':{'language':'en','value':q}},'descriptions':{'en':{'language':'en','value':'description'}},'aliases':{'en':[{'language':'en','value':'alias'}]}})
        self.scan(); self.assertEqual(self.db.execute('SELECT semantic_id,description,aliases_json FROM recovery_evidence').fetchall(),[('KQ1','description','["alias"]')]); self.assertEqual(self.counts['cache_without_active_accepted_anchor'],1)
    def test_mismatched_external_id(self):
        self.dictionary('a',[self.row('KQ1','bad',external_id='Q2'),self.row('KQ2','bad',external_id='Q2')]); self.scan(); self.assertEqual(self.db.execute('SELECT count(*) FROM recovery_evidence').fetchone()[0],0)
    def test_legacy_is_not_joined(self):
        self.write('.kristal/v8/lexicon-fr.json',{'artifact_type':'kristall_lexicon','language':'fr','entries':[{'semantic_ref':{'id':'KQ1','identity_space':'legacy'},'preferred_term':'legacy'}]}); self.scan()
        self.assertEqual(self.db.execute('SELECT count(*) FROM recovery_legacy').fetchone()[0],1); self.assertEqual(self.db.execute('SELECT count(*) FROM recovery_evidence').fetchone()[0],0)
    def test_malformed_file_is_atomic(self):
        p=self.root/'Kristal-Test/canon/domain/v11/old/dictionaries/a.jsonl';p.parent.mkdir(parents=True);p.write_text(json.dumps({'semantic_id':'KQ1','namespace_id':'ns','language':'fr','preferred_term':'alpha'})+'\n{bad\n',encoding='utf8'); self.scan()
        self.assertEqual(self.db.execute('SELECT count(*) FROM recovery_evidence').fetchone()[0],0); self.assertEqual(self.db.execute('SELECT status FROM recovery_source').fetchone()[0],'REJECTED_MALFORMED')
    def test_source_hash_and_locator(self):
        p=self.dictionary('a',[self.row('KQ1','alpha')]);self.scan();self.assertEqual(self.db.execute('SELECT sha256 FROM recovery_source').fetchone()[0],hashlib.sha256(p.read_bytes()).hexdigest());self.assertEqual(self.db.execute('SELECT locator FROM recovery_evidence').fetchone()[0],'/entries/0')
    def test_link_refused(self):
        p=self.root/'link'
        try: p.symlink_to(self.root,target_is_directory=True)
        except OSError: self.skipTest('symlink creation unavailable')
        with self.assertRaises(LocalFirstAuditError): guard(p)

if __name__=='__main__': unittest.main()
