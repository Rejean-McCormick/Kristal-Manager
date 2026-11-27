import bz2,importlib.util,json,os,sqlite3,sys,tempfile,unittest
from pathlib import Path
from contextlib import closing
sys.path.insert(0,os.environ['KRISTALIZER_ROOT']);sys.path.insert(0,os.environ['KRISTALDIAG_ROOT'])
from kristal_manager.maintenance_repair_v5217 import scan_doc,run,digest,j
from kristalizer.maintenance_external_v5217 import lookup
from kristalizer.maintenance_dump_v5217 import extract
from kristaldiag.maintenance_repair_check_v5217 import verify
spec=importlib.util.spec_from_file_location('reader',os.environ['DIK_REPAIR_READER']);reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
class Tests(unittest.TestCase):
    def test_scoped_dictionary(self):
        d={'artifact_type':'kristal_curated_dictionary','namespace_id':'n','language':'fr','entries':[{'semantic_id':'KQ1','preferred_term':'a'}]};o=[];scan_doc(j(d).encode(),'x/dictionaries/a.json','n',{'KQ1'},{},o);self.assertEqual(o[0][1:4],('KQ1','fr','a'));o=[];scan_doc(j(d).encode(),'x/dictionaries/a.json','wrong',{'KQ1'},{},o);self.assertEqual(o,[])
    def test_no_invented_language(self):
        o=[];scan_doc(j({'artifact_type':'kristal_curated_dictionary','namespace_id':'n','entries':[{'semantic_id':'KQ1','preferred_term':'a'}]}).encode(),'x/dictionaries/a.json','n',{'KQ1'},{},o);self.assertEqual(o,[])
    def test_no_unaccepted_jsonl(self):
        o=[];scan_doc(b'{"semantic_id":"KQ1","preferred_term":"a"}','x/dictionaries/a.jsonl','n',{'KQ1'},{},o);self.assertEqual(o,[])
    def test_compact_exact_lang(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'idx.db'
            with closing(sqlite3.connect(p)) as c:
                c.executescript('create table entity(id integer primary key,wid text,kind text,label_fr text,label_en text,description_fr text,description_en text);create table name(entity_id int,lang text,name_kind int,value text);create index ix on name(entity_id);insert into entity values(1,\'Q1\',\'item\',NULL,\'English\',NULL,NULL);insert into name values(1,\'en\',1,\'Other\');');c.commit()
            r,fp=lookup(p,['Q1','Q2']);self.assertIsNone(r['Q1']['label_fr']);self.assertEqual(r['Q1']['label_en'],'English');self.assertEqual(r['Q1']['name_observations'],[['en',1,'Other']]);self.assertNotIn('Q2',r);self.assertFalse(fp['source_authenticated'])
    def test_dump_alias_exact(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.bz2';p.write_bytes(bz2.compress(b'[\n{"id":"Q1","type":"item","lastrevid":3,"labels":{"en":{"language":"en","value":"a"}},"aliases":{"en":[{"language":"en","value":"b"}]}},\n{"id":"Q2","type":"item","lastrevid":5}\n]\n'))
            with closing(sqlite3.connect(':memory:')) as c:
                extract(p,c,['Q1']);r=json.loads(c.execute('select record_json from dump_record').fetchone()[0]);self.assertEqual(r['aliases']['en'][0]['value'],'b');self.assertEqual(r['source_revision'],3);self.assertFalse(r['source_authenticated']);extract(p,c,['Q1']);self.assertEqual(c.execute('select count(*) from dump_record').fetchone()[0],1)
    def test_dump_rejects_wrong_type(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.bz2';p.write_bytes(bz2.compress(b'{"id":"Q1","type":"property","lastrevid":3}\n'))
            with closing(sqlite3.connect(':memory:')) as c:
                with self.assertRaises(ValueError):extract(p,c,['Q1'])
    def test_dump_rejects_changed_targets(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.bz2';p.write_bytes(bz2.compress(b'{"id":"Q1","type":"item","lastrevid":3}\n'))
            with closing(sqlite3.connect(':memory:')) as c:
                extract(p,c,['Q1'])
                with self.assertRaises(ValueError):extract(p,c,['Q2'])
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);root=td/'locals';base=td/'base';scan=td/'scan';out=td/'out';base.mkdir();scan.mkdir();owner='Kristal-Test';ns='n';folder=root/owner;folder.mkdir(parents=True)
            def write(rel,d):p=folder/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(j(d),encoding='utf8');return digest(p)
            mp='.kristal/v11/identity-migration-map.json';mh=write(mp,{'format':'dik.bulk-secondpass/2','namespace_id':ns,'by_kind':{'Q':{'native-one':'KQ1'},'P':{'predicate':'KP1'}}});path='knowledge-base/corpus/registry.json';sh=write(path,{'artifact_type':'test_referent_registry','referents':[{'id':'native-one','label_fr':'Un'}]});graph='canon/domain/graph.json';gh=write(graph,{'assertions':[{'id':'KA1'}]});gp=base/'active-graphs'/ 'test'/graph;gp.parent.mkdir(parents=True);gp.write_bytes((folder/graph).read_bytes())
            # Historical catalog contributes a genuinely new, exact KP label.
            write('canon/domain/dictionaries/historical.json',{'artifact_type':'kristal_curated_dictionary','namespace_id':ns,'language':'en','entries':[{'semantic_id':'KP1','preferred_term':'predicate label'}]})
            with closing(sqlite3.connect(base/'active.sqlite')) as c:
                c.executescript('''create table workspace(slug,local_directory,namespace_id,active);create table identity(namespace_id,semantic_id,kind,owner_slug);create table lexical(namespace_id,semantic_id,language_tag,preferred_term);create table v52161_active_graph(slug,namespace_id,status,report_json);create table v52161_alias_review(slug,path,line,status,record_json);create table v52161_active_assertion(namespace_id,semantic_id,slug,json_pointer);''');c.execute('insert into workspace values (?,?,?,1)',('test',owner,ns));c.executemany('insert into identity values (?,?,?,?)',[(ns,'KQ1','entity','test'),(ns,'KP1','property','test'),(ns,'KQ2','entity','test'),(ns,'KA1','assertion','test')]);c.execute('insert into lexical values (?,?,?,?)',(ns,'KQ2','fr','Deux'));r={'core_graph_registry_crosswalk_qualified':True,'source_pins':{graph:gh},'assertions':1,'graph_path':'active-graphs/test/'+graph,'graph_sha256':gh};c.execute('insert into v52161_active_graph values (?,?,?,?)',('test',ns,'PRIVATE_GRAPH_ONLY_LEXICAL_BLOCKED',j(r)));c.execute('insert into v52161_active_assertion values (?,?,?,?)',(ns,'KA1','test','/assertions/0'));c.commit()
            bh=digest(base/'active.sqlite');(base/'report.json').write_text(j({'database_sha256':bh}))
            with closing(sqlite3.connect(scan/'maintenance.sqlite')) as c:
                c.executescript('''create table target(ns,sid,slug,kind);create table anchor(ns,native_id,sid,path,sha256);create table observation(ns,sid,lang,term,native_id,path,sha256,pointer,method);create table resolution(ns,sid,lang,status,term,variants_json);create table source(path,sha256,status);create table alias_target(wid,lang,occurrences);create table ambiguous(ns,sid,external_id,source_status);''');c.executemany('insert into target values (?,?,?,?)',[(ns,'KQ1','test','entity'),(ns,'KP1','test','property')]);c.execute('insert into anchor values (?,?,?,?,?)',(ns,'native-one','KQ1',owner+'/'+mp,mh));c.executemany('insert into source values (?,?,?)',[(owner+'/'+mp,mh,'MAP'),(owner+'/'+path,sh,'OBS')]);c.execute('insert into observation values (?,?,?,?,?,?,?,?,?)',(ns,'KQ1','fr','Un','native-one',owner+'/'+path,sh,'/referents/0/label_fr','NATIVE_REGISTRY'));c.execute('insert into resolution values (?,?,?,?,?,?)',(ns,'KQ1','fr','PRIVATE_EXACT_ANCHOR_CONSENSUS','Un','["Un"]'));c.commit()
            sm=digest(scan/'maintenance.sqlite');(scan/'report.json').write_text(j({'maintenance_database_sha256':sm,'base_database_sha256':bh,'counts':{'targets':2,'observations':1},'policy':{k:False for k in ('canonical_modified','public_modified','external_links_accepted','labels_promoted','network_used','historical_aliases_invented')}}))
            from unittest.mock import patch
            with patch('kristaldiag.maintenance_repair_check_v5217.verify',side_effect=ValueError('simulated interruption')):
                with self.assertRaises(ValueError):run(root,base,scan,out,Path(os.environ['KRISTALIZER_ROOT']),Path(os.environ['KRISTALDIAG_ROOT']))
            self.assertFalse((out/'COMPLETE').exists())
            report=run(root,base,scan,out,Path(os.environ['KRISTALIZER_ROOT']),Path(os.environ['KRISTALDIAG_ROOT']));self.assertEqual(report['counts']['recovered_cells'],2);self.assertEqual(report['counts']['displayable_identities'],3)
            r=reader.Reader(out,base)
            try:
                self.assertEqual(r.label(ns,'KQ1','fr')['text'],'Un');self.assertEqual(r.label(ns,'KP1','en')['text'],'predicate label');self.assertFalse(r.label(ns,'KP1','fr')['is_label']);self.assertEqual(r.label(ns,'KQ1','fr',True)['status'],'MISSING_CANONICAL_LABEL');self.assertEqual(r.assertion(ns,'KA1')['assertion']['id'],'KA1');self.assertEqual(r.assertion(ns,'KA1',True)['status'],'LEXICALLY_BLOCKED')
            finally:r.close()
            self.assertEqual(digest(base/'active.sqlite'),bh);self.assertEqual(digest(scan/'maintenance.sqlite'),sm)
            with self.assertRaises(ValueError):run(root,base,scan,out,Path(os.environ['KRISTALIZER_ROOT']),Path(os.environ['KRISTALDIAG_ROOT']))
            (folder/graph).write_text('{}');self.assertRaises(ValueError,verify,out,base,scan,root)
if __name__=='__main__':unittest.main()
