import hashlib,json,sqlite3,tempfile,unittest,os,shutil,datetime
from unittest.mock import patch
from urllib.error import HTTPError
from email.message import Message
from kristal_manager import semantic_qualification_v520 as qualification
from pathlib import Path
from contextlib import closing
from kristal_manager.active_semantic_federation_v518 import _schema
from kristal_manager.semantic_recovery_v519 import schema
from kristal_manager.local_first_audit import ReadOnlyTree
from kristal_manager.semantic_qualification_v520 import parse_batch,lexical_record,targets,native_review,refresh,run
class QualificationTests(unittest.TestCase):
    def entity(self):return {'id':'Q42','type':'item','lastrevid':123,'labels':{'en':{'language':'en','value':'Douglas Adams'},'fr':{'language':'en','value':'fallback'}},'aliases':{'en':[{'language':'en','value':'D. Adams'},{'language':'en','value':'D. Adams'}]},'descriptions':{'en':{'language':'en','value':'writer'}}}
    def response(self,e):return json.dumps({'success':1,'entities':{'Q42':e}}).encode()
    def test_exact_language_and_revision(self):
        e=self.entity();found,missing=parse_batch(self.response(e),['Q42']);self.assertFalse(missing);self.assertEqual(found['Q42'],e)
        row=lexical_record(e,'ns','KQ1','Q42','en','snapshot');self.assertEqual((row['preferred_term'],row['source_revision'],row['aliases'],row['description']),('Douglas Adams',123,['D. Adams'],'writer'))
        self.assertIsNone(lexical_record(e,'ns','KQ1','Q42','fr','snapshot'))
    def test_mismatched_or_deleted_qid(self):
        for e in [dict(self.entity(),id='Q43'),dict(self.entity(),missing=''),dict(self.entity(),lastrevid=0),dict(self.entity(),type='property')]:self.assertEqual(parse_batch(self.response(e),['Q42']),({},['Q42']))
    def test_api_error(self):
        with self.assertRaises(ValueError):parse_batch(b'{"error":{"code":"maxlag"}}',['Q42'])
    def test_redirect_refused(self):
        with self.assertRaises(ValueError):parse_batch(b'{"success":1,"entities":{},"redirects":{"Q42":"Q43"}}',['Q42'])
    def test_non_nfc_label_is_not_changed(self):
        e=self.entity();e['labels']['en']['value']='e\u0301';self.assertIsNone(lexical_record(e,'ns','KQ1','Q42','en','snapshot'))
    def test_scope_targets_and_review_queue(self):
        db=sqlite3.connect(':memory:');self.addCleanup(db.close);_schema(db);schema(db)
        for owner,ns in [('a','ns'),('b','ns2')]:db.execute('INSERT INTO workspace VALUES (?,?,?,?,?,?,?,?)',(owner,'Kristal-'+owner,ns,1,None,'x',None,0))
        for ns,sid,owner,kind,q in [('ns','KQ1','a','entity','Q42'),('ns','KQ2','a','entity',None),('ns','KS1','a','source',None),('ns2','KQ1','b','entity','Q42')]:
            db.execute('INSERT INTO identity VALUES (?,?,?,?,?,?,?)',(ns,sid,owner,kind,'stable',q,'[]'));db.execute('INSERT INTO review_queue VALUES (?,?,?,?)',(ns,sid,'MISSING_ACTIVE_LABEL','{}'))
        self.assertEqual(len(targets(db)),2)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=root/'Kristal-a/knowledge-base/corpus/a.referent-registry.json';p.parent.mkdir(parents=True);p.write_text(json.dumps({'referents':[{'ref':'urn:test:a'}]}),encoding='utf8');
            for owner in ('a','b'):db.execute('INSERT INTO recovery_legacy VALUES (?,?,?,?,?,?,?,?)',(owner,'kristal_v6','urn:test:a','en','term',owner+'/lex.json','/entries/0','{}'))
            tree=ReadOnlyTree(root);native_review(tree,db,list(db.execute('SELECT * FROM workspace')));tree.close()
            self.assertEqual(db.execute('SELECT owner_slug,status FROM v520_legacy_review ORDER BY owner_slug').fetchall(),[('a','EXACT_NATIVE_V6_REF_ONLY'),('b','NO_EXPLICIT_NATIVE_REF_OR_V11_BRIDGE')]);self.assertEqual(db.execute('SELECT count(*) FROM v520_review_queue').fetchone()[0],3)
            self.assertEqual(db.execute('SELECT source_sha256 FROM v520_native_ref').fetchone()[0],hashlib.sha256(p.read_bytes()).hexdigest())
    def test_rate_limit_retry_after(self):
        headers=Message();headers['Retry-After']='95'
        exc=HTTPError(qualification.ENDPOINT,429,'Too Many Requests',headers,None)
        raw=self.response(self.entity())
        with patch.object(qualification,'_fetch_once',side_effect=[exc,raw]) as fetch,patch.object(qualification.time,'sleep') as sleep:
            self.assertEqual(qualification.fresh_fetch(['Q42']),raw)
            self.assertEqual(fetch.call_count,2);sleep.assert_called_once_with(95)
    def test_maxlag_and_retry_budget(self):
        with patch.object(qualification,'_fetch_once',return_value=b'{"error":{"code":"maxlag"}}') as fetch,patch.object(qualification.time,'sleep') as sleep:
            with self.assertRaisesRegex(OSError,'retry budget exhausted'):qualification.fresh_fetch(['Q42'])
            self.assertEqual(fetch.call_count,3);self.assertEqual([c.args[0] for c in sleep.call_args_list],[60,120])
    def test_long_retry_after_stops_without_retry(self):
        headers=Message();headers['Retry-After']='3600'
        exc=HTTPError(qualification.ENDPOINT,429,'Too Many Requests',headers,None)
        with patch.object(qualification,'_fetch_once',side_effect=exc) as fetch,patch.object(qualification.time,'sleep') as sleep:
            with self.assertRaisesRegex(OSError,'exceeds wait budget'):qualification.fresh_fetch(['Q42'])
            self.assertEqual(fetch.call_count,1);sleep.assert_not_called()
    def test_resume_batches_validate_hash_scope_and_age(self):
        with tempfile.TemporaryDirectory() as td:
            private=Path(td);rp=private/'SEMANTIC_V520_012345abcdef.json';ev=rp.with_suffix('.evidence');ev.mkdir();db=rp.with_suffix('.sqlite');db.write_bytes(b'database')
            ids=sorted('Q'+str(i) for i in range(1,52));batch=ids[:50];raw=json.dumps({'success':1,'entities':{q:dict(self.entity(),id=q) for q in batch}}).encode();sha=hashlib.sha256(raw).hexdigest();f=ev/(sha+'.json');f.write_bytes(raw)
            meta={'source_snapshot':'wbgetentities-sha256-'+sha,'sha256':sha,'file':f.name,'requested_ids':batch,'endpoint':qualification.ENDPOINT,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
            d={'format':qualification.FORMAT,'status':'COMPLETE_WITH_NETWORK_BLOCKER','network_completed':False,'network_requested':True,'canonical_modified':False,'canonical_changes':[],'target_distinct_external_ids':51,'evidence_directory':str(ev),'database':str(db),'database_sha256':hashlib.sha256(db.read_bytes()).hexdigest(),'source_batches':[meta]}
            rp.write_text(json.dumps(d),encoding='utf-8');self.assertEqual(qualification.latest_resume_report(private),rp)
            self.assertEqual(qualification.resume_batches(private,rp,ids),{tuple(batch):(raw,meta)})
            self.assertEqual(qualification.resume_batches(private,rp,ids[:-1]),{})
            f.write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'evidence hash mismatch'):qualification.resume_batches(private,rp,ids)
            f.write_bytes(raw);meta['retrieved_utc']=(datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(hours=25)).isoformat();rp.write_text(json.dumps(d),encoding='utf-8')
            self.assertEqual(qualification.resume_batches(private,rp,ids),{})
    def test_complete_pipeline_simulated_source(self):
        base_repo=Path(__file__).resolve().parents[2]
        kit=Path(os.environ.get('KRISTAL_KIT_ROOT',str(base_repo/'Kristal-Authoring-Kit')))
        framework=Path(os.environ.get('KRISTAL_FRAMEWORK_ROOT',str(base_repo/'Kristal-Framework')))
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);local=base/'locals';pub=base/'public';private=base/'private';local.mkdir();private.mkdir();(pub/'kristals').mkdir(parents=True);(pub/'kristals/index.json').write_text('{"kristals":[]}',encoding='utf8')
            root=local/'Kristal-Test';shutil.copytree(kit/'examples/demo-semantic-v11',root)
            p=root/'canon/domain/v11/dictionaries/catalog.json';d=json.loads(p.read_text());d['languages'][0]['layers']=[];p.write_text(json.dumps(d),encoding='utf8')
            public_before=(pub/'kristals/index.json').read_bytes();source=refresh(local,pub,private)
            crosswalk=(root/'canon/domain/v11/crosswalk.json').read_bytes()
            def fake(ids):return json.dumps({'success':1,'entities':{q:{'id':q,'type':'item','lastrevid':1,'labels':{'en':{'language':'en','value':'Augustine'}}} for q in ids}}).encode()
            prior=run(local,private,Path(source['database']),public=pub,kit=kit,framework=framework,online=True,fetch=fake)
            # Simulate the persisted state of a previous interrupted acquisition.
            prior['status']='COMPLETE_WITH_NETWORK_BLOCKER';prior['network_completed']=False
            rp=Path(prior['report']);rp.write_text(json.dumps(prior),encoding='utf-8')
            def no_network(ids):raise AssertionError('cached batch must not be downloaded again')
            result=run(local,private,Path(source['database']),public=pub,kit=kit,framework=framework,online=True,apply_catalogs=True,fetch=no_network,resume_report=rp)
            self.assertEqual(result['reused_source_batches'],1);self.assertEqual(result['fresh_source_batches'],0)
            self.assertEqual(prior['source_batches'],result['source_batches'])
            self.assertEqual(result['status'],'COMPLETE');self.assertEqual(result['new_active_cells'],1);self.assertEqual(result['after']['KQ_KP_with_active_label'],1)
            self.assertEqual(public_before,(pub/'kristals/index.json').read_bytes());self.assertEqual(crosswalk,(root/'canon/domain/v11/crosswalk.json').read_bytes())
            with closing(sqlite3.connect(result['database'])) as db:
                self.assertEqual(db.execute('SELECT status FROM v520_verified_record').fetchone()[0],'ACTIVE_CANONICAL_SOURCE_LABEL')
            # Explicitly exercise the Windows-sensitive file removal while the
            # connection object is still in scope. No GC or cleanup suppression.
            Path(result['database']).unlink()
            self.assertFalse(Path(result['database']).exists())
    def test_network_failure_keeps_canon(self):
        base_repo=Path(__file__).resolve().parents[2];kit=Path(os.environ.get('KRISTAL_KIT_ROOT',str(base_repo/'Kristal-Authoring-Kit')));framework=Path(os.environ.get('KRISTAL_FRAMEWORK_ROOT',str(base_repo/'Kristal-Framework')))
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);local=base/'locals';pub=base/'public';private=base/'private';local.mkdir();private.mkdir();(pub/'kristals').mkdir(parents=True);(pub/'kristals/index.json').write_text('{"kristals":[]}',encoding='utf8')
            root=local/'Kristal-Test';shutil.copytree(kit/'examples/demo-semantic-v11',root);p=root/'canon/domain/v11/dictionaries/catalog.json';d=json.loads(p.read_text());d['languages'][0]['layers']=[];p.write_text(json.dumps(d),encoding='utf8')
            source=refresh(local,pub,private);state=(root/'canon/state.index.json').read_bytes();profile=(root/'.kristal/v11/authoring.json').read_bytes()
            def fake(ids):raise OSError('simulated network failure')
            result=run(local,private,Path(source['database']),public=pub,kit=kit,framework=framework,online=True,apply_catalogs=True,fetch=fake)
            self.assertEqual(result['status'],'COMPLETE_WITH_NETWORK_BLOCKER');self.assertFalse(result['canonical_modified']);self.assertEqual(state,(root/'canon/state.index.json').read_bytes());self.assertEqual(profile,(root/'.kristal/v11/authoring.json').read_bytes())
if __name__=='__main__':unittest.main()
