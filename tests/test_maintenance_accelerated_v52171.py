import json,sqlite3,tempfile,unittest,os,sys
from pathlib import Path
from contextlib import closing
sys.path.insert(0,os.environ['KRISTALIZER_ROOT'])
sys.path.insert(0,os.environ['KRISTALDIAG_ROOT'])
from kristalizer.maintenance_fast_v52171 import query,inspect,discover,recover_partial,fingerprint
from kristal_manager import maintenance_accelerated_v52171 as manager
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.r=Path(self.tmp.name);self.idx=self.r/'fast.db';self.dump=self.r/'dump.bz2';self.dump.write_bytes(b'NOT A COMPRESSED STREAM')
        with closing(sqlite3.connect(self.idx)) as c, c:
            c.executescript('CREATE TABLE entity(id INTEGER PRIMARY KEY,wid TEXT,kind TEXT,label_fr TEXT,label_en TEXT,description_fr TEXT,description_en TEXT);CREATE TABLE name(entity_id INTEGER,lang TEXT,name_kind INTEGER,value TEXT);CREATE INDEX nm ON name(entity_id);');c.execute("INSERT INTO entity VALUES(1,'Q1','item','un','one',NULL,NULL)");c.execute("INSERT INTO name VALUES(1,'fr',17,'raw')")
        self.part=self.r/'partial.sqlite';self.rec={'external_id':'Q1','source_revision':12,'labels':{'fr':{'language':'fr','value':'un'}},'aliases':{'fr':[{'language':'fr','value':'uno'}]},'line_sha256':'a'*64,'uncompressed_offset':1,'source_authenticated':False,'historical_equivalence_claimed':False}
        with closing(sqlite3.connect(self.part)) as c, c:
            c.executescript('CREATE TABLE dump_checkpoint(k TEXT PRIMARY KEY,v TEXT);CREATE TABLE dump_record(wid TEXT PRIMARY KEY,record_json TEXT);');c.executemany('INSERT INTO dump_checkpoint VALUES (?,?)',[('binding',json.dumps([fingerprint(self.dump),['Q1','Q2']])),('offset','10')]);c.execute('INSERT INTO dump_record VALUES (?,?)',('Q1',json.dumps(self.rec)))
    def test_indexed_lookup(self):
        d,_,s=query(self.idx,['Q1','Q2']);self.assertEqual(set(d),{'Q1'});self.assertEqual(d['Q1']['label_fr'],'un');self.assertEqual(d['Q1']['name_observations'],[['fr',17,'raw']]);self.assertTrue(s['names_indexed'])
    def test_wrong_kind(self):
        with closing(sqlite3.connect(self.idx)) as c, c:c.execute("UPDATE entity SET kind='property'")
        self.assertEqual(query(self.idx,['Q1'])[0],{})
    def test_unindexed_refused(self):
        with closing(sqlite3.connect(self.idx)) as c, c:c.executescript('ALTER TABLE entity RENAME TO old;CREATE TABLE entity AS SELECT * FROM old;')
        self.assertIsNone(inspect(self.idx))
    def test_names_unindexed(self):
        with closing(sqlite3.connect(self.idx)) as c, c:c.execute('DROP INDEX nm')
        self.assertEqual(query(self.idx,['Q1'])[0]['Q1']['name_observations'],[])
    def test_partial_without_decompression(self):
        data,meta=recover_partial(self.part,self.dump,['Q1','Q2']);self.assertEqual(data['Q1'],self.rec);self.assertFalse(meta['source_lines_rechecked'])
    def test_wrong_targets(self):
        with self.assertRaises(ValueError):recover_partial(self.part,self.dump,['Q1'])
    def test_outside_checkpoint(self):
        with closing(sqlite3.connect(self.part)) as c, c:c.execute("UPDATE dump_checkpoint SET v='1' WHERE k='offset'")
        data,meta=recover_partial(self.part,self.dump,['Q1','Q2']);self.assertFalse(data);self.assertEqual(len(meta['invalid_records']),1)
    def test_discovery(self):
        d,_=discover(self.r);self.assertEqual([p for p,s in d],[self.idx])
    def test_end_to_end(self):
        base=self.r/'base';scan=self.r/'scan';compact=self.r/'compact';partial=self.r/'partial';out=self.r/'out';fast=self.r/'fast';fast.mkdir()
        for p in (base,scan,compact,partial):p.mkdir()
        (base/'active.sqlite').write_bytes(b'fixture');(compact/'repair.sqlite').write_bytes(b'fixture2');(partial/'repair.sqlite').write_bytes(self.part.read_bytes())
        with closing(sqlite3.connect(scan/'maintenance.sqlite')) as c, c:c.executescript("CREATE TABLE alias_target(wid TEXT,lang TEXT,occurrences INTEGER);INSERT INTO alias_target VALUES('Q1','fr',1),('Q1','und',1);CREATE TABLE ambiguous(external_id TEXT);INSERT INTO ambiguous VALUES('Q2');")
        from unittest.mock import patch
        b,m,k=[manager.sha(p) for p in (base/'active.sqlite',scan/'maintenance.sqlite',compact/'repair.sqlite')]
        (compact/'report.json').write_text(json.dumps({'database_sha256':k,'baseline_sha256':b,'maintenance_sha256':m}));(compact/'diagnostic.json').write_text(json.dumps({'database_sha256':k,'status':'PASS_PRIVATE_OPERATIONAL_SCOPE'}));(compact/'COMPLETE').write_text(k)
        with patch.multiple(manager,BASE_SHA=b,SCAN_SHA=m,COMPACT_SHA=k):
            r=manager.run(base,scan,compact,partial,self.idx,fast,self.dump,out,Path(os.environ['KRISTALIZER_ROOT']),Path(os.environ['KRISTALDIAG_ROOT']))
        self.assertEqual(r['counts']['partial_dump_ids'],1);self.assertEqual(r['counts']['pairs_with_dump_alias_observation'],1);self.assertEqual(r['counts']['unobserved_ids'],1);self.assertTrue((out/'COMPLETE').is_file())
        with closing(sqlite3.connect(out/'accelerated.sqlite')) as c, c:self.assertEqual(c.execute("SELECT aliases_json FROM alias_observation WHERE lang='und'").fetchone(),(None,))
