import os,sys,tempfile,unittest,json,gzip,sqlite3,hashlib,importlib.util
from pathlib import Path
from contextlib import closing
from unittest.mock import patch
sys.path[:0]=[os.environ['KRISTALIZER_ROOT'],os.environ['KRISTALDIAG_ROOT']]
from kristalizer import encyk_indexed_v5218 as e
from kristal_manager import maintenance_indexed_v5218 as m
from kristaldiag.encyk_indexed_check_v5218 import verify

def entity(w='Q1'):
    return {'id':w,'type':'item','lastrevid':42,'labels':{'fr':{'language':'fr','value':'Un'}},'aliases':{'fr':[{'language':'fr','value':'Premier'}]},'descriptions':{}}
def emit(folder,ids,b,rows=None,missing=None):
    rows=[entity(w) for w in ids] if rows is None else rows;missing=[] if missing is None else missing
    p=folder/'entities.jsonl.gz'
    with gzip.open(p,'wt',encoding='utf8') as f:
        for obj in rows:f.write(json.dumps(obj)+'\n')
    meta={'format':'kristal.wikidata-indexed-reader/1.0','source_dump':b['dump'],'index_locator':b['locator'],'compression_index':b['compression'],'backend':{'backend':'indexed_bzip2','random_access':True},'requested':len(ids),'located':len(rows),'found':len(rows),'unlocated_qids':missing,'rejected':[],'sha256':e.sha(p),'source_modified':False,'scan_entire_dump':False}
    (folder/'entities.jsonl.gz.reader.json').write_text(json.dumps(meta),encoding='utf8');return meta
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.b={'dump':str(self.root/'dump'),'locator':str(self.root/'locator'),'compression':str(self.root/'compression')}
    def test_exact_language(self):
        d=e.lexical(entity(),'Q1');self.assertEqual(d['aliases'],{'fr':['Premier']});self.assertEqual(d['revision'],42);self.assertNotIn('und',d['labels'])
    def test_missing_not_empty(self):
        d=entity();del d['aliases'];self.assertIsNone(e.lexical(d,'Q1')['aliases'])
    def test_wrong_id_type_revision(self):
        for k,v in [('id','Q2'),('type','property'),('lastrevid',True)]:
            d=entity();d[k]=v
            with self.assertRaises(ValueError):e.lexical(d,'Q1')
    def test_wrong_language(self):
        d=entity();d['labels']['fr']['language']='en'
        with self.assertRaises(ValueError):e.lexical(d,'Q1')
    def test_json_strict(self):
        for s in ['{"a":1,"a":2}','{"a":NaN}']:
            with self.assertRaises(ValueError):e.load(s)
    def test_batch_accounting(self):
        emit(self.root,['Q1','Q2'],self.b,[entity()],['Q2']);d,r=e.validate_batch(self.root,['Q1','Q2'],self.b);self.assertEqual(set(d),{'Q1'});self.assertEqual(r['unlocated'],['Q2'])
    def test_wrong_scope(self):
        emit(self.root,['Q1'],self.b,[entity('Q2')]);
        with self.assertRaises(ValueError):e.validate_batch(self.root,['Q1'],self.b)
    def test_no_full_scan(self):
        meta=emit(self.root,['Q1'],self.b);meta['scan_entire_dump']=True;(self.root/'entities.jsonl.gz.reader.json').write_text(json.dumps(meta),encoding='utf8')
        with self.assertRaises(ValueError):e.validate_batch(self.root,['Q1'],self.b)
    def test_tamper(self):
        emit(self.root,['Q1'],self.b);(self.root/'entities.jsonl.gz').write_bytes(b'bad')
        with self.assertRaises(ValueError):e.validate_batch(self.root,['Q1'],self.b)
    def test_end_to_end_resume(self):
        root=self.root/'source';root.mkdir();private=self.root/'private';private.mkdir();factory=self.root/'factory';factory.mkdir();scan=private/'maintenance.sqlite';base=private/'base.sqlite';base.write_bytes(b'base')
        with closing(sqlite3.connect(scan)) as c, c:
            c.executescript("CREATE TABLE alias_target(wid TEXT,lang TEXT,occurrences INTEGER);CREATE TABLE ambiguous(external_id TEXT);INSERT INTO alias_target VALUES('Q1','fr',1),('Q1','und',2),('P1','en',1),('Q2','fr',1);")
        # Fix the simulated source binding to the paths the orchestrator supplies.
        index=root/'30_working/wikidata/wikidata.compact.sqlite';dump=root/'10_sources/wikidata/dumps/current/wikidata-20260922-all.json.bz2';b={**self.b,'dump':str(dump),'compact':str(index),'files':{str(index):{}}}
        calls=[]
        def worker(factory,root,dump,index,folder,ids,b,timeout):
            calls.append(ids);emit(folder,ids,b);return e.validate_batch(folder,ids,b)
        def query(index,remaining,progress):
            self.assertEqual(remaining,{'P1'});return {'P1':{'wid':'P1','kind':'property','label_en':'property'}},{},{}
        args=(scan,base,root,factory,private,Path(os.environ['KRISTALIZER_ROOT']),Path(os.environ['KRISTALDIAG_ROOT']))
        with patch.object(m,'SCAN_SHA',e.sha(scan)),patch.object(m,'BASE_SHA',e.sha(base)),patch.object(e,'binding',return_value=b),patch.object(e,'worker',side_effect=worker),patch('kristalizer.maintenance_fast_v52171.query',side_effect=query):
            a=m.run(*args,batch_size=1);z=m.run(*args,batch_size=1)
        self.assertEqual(len(calls),2);r=json.loads((z/'report.json').read_bytes());self.assertEqual(r['counts']['reused_batches'],2);self.assertEqual(r['counts']['observed_ids'],3);self.assertEqual(r['counts']['und_pairs'],1);self.assertEqual(verify(z,scan,base)['cached_entity_records_checked'],2)
        spec=importlib.util.spec_from_file_location('dikread',os.environ['DIK_ENCYK_READER']);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);self.assertEqual(mod.read(z,'Q1','fr')['aliases'],['Premier']);self.assertIsNone(mod.read(z,'Q1','und')['label']);self.assertIsNone(mod.read(z,'P1','en')['revision'])
if __name__=='__main__':unittest.main()
