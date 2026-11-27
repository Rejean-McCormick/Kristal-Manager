import json,sqlite3,tempfile,unittest,copy
from pathlib import Path
from jsonschema import Draft202012Validator
from kristal_manager import lexical_compatibility_v52161 as m
ROOT=Path(__file__).resolve().parents[2];FW=ROOT/'Kristal-Framework'
r=m.op.load(FW/'tools/v11/lexical_compatibility_v52161.py','v52161_reader_test');LEX=Draft202012Validator(m.read(FW/'schemas/v11/kristal-wikidata-lexical-record.schema.json'))
class CompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.db.execute('CREATE TABLE v520_verified_record(namespace_id,semantic_id,language_tag,external_id,source_snapshot,source_revision,record_json,status)');self.rec={'namespace_id':'ns','semantic_id':'KQ1','external_id':'Q1','language':'fr','preferred_term':'mot','source_snapshot':m.LEGACY}
    def tearDown(self):self.db.close()
    def fixture(self,root,record=None):
        row=self.rec if record is None else record;raw=m.bytes_json(row).replace(b'\n',b' ')+b'\n';(root/'lex.jsonl').write_bytes(raw);h=m.sha(raw);m.write(root/'catalog.json',{'namespace_id':'ns','catalog_id':'c','languages':[{'tag':'fr','layers':[{'kind':'wikidata','path':'lex.jsonl','sha256':h,'source_snapshot':row['source_snapshot']}]}]});return {'catalog':'catalog.json'}, {'s':{h:{'source_path':'historical.jsonl','missing':int('aliases' not in row),'language':'fr','source_snapshot':m.LEGACY}}}
    def test_pinned_placeholder_not_evidence(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);cfg,pins=self.fixture(p);inv=m.inventory(p);patch,rows,unknown=m.repair_catalog(self.db,p,cfg,'s','ns',pins,LEX);self.assertEqual(unknown,0);self.assertEqual(rows[0]['status'],'LEGACY_ALIASES_NOT_RECORDED_PRIVATE_PLACEHOLDER');self.assertEqual(m.strict_json(patch['lex.jsonl']),dict(self.rec,aliases=[]));self.assertFalse(rows[0]['canonical_repair_authorized']);self.assertEqual(inv,m.inventory(p))
    def test_unknown_layer_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);cfg,_=self.fixture(p);patch,rows,unknown=m.repair_catalog(self.db,p,cfg,'s','ns',{},LEX);self.assertEqual(unknown,1);self.assertFalse(patch);self.assertIsNone(rows[0]['private_replacement'])
    def test_exact_revision_required(self):
        record=dict(self.rec,source_snapshot='wbgetentities-sha256-'+'a'*64,source_revision=42);full=dict(record,aliases=['syn']);self.db.execute('INSERT INTO v520_verified_record VALUES(?,?,?,?,?,?,?,?)',('ns','KQ1','fr','Q1',record['source_snapshot'],42,json.dumps(full),'ACTIVE_CANONICAL_SOURCE_LABEL'));self.assertEqual(m.verified_alias(self.db,record)[0],['syn']);self.assertIsNone(m.verified_alias(self.db,self.rec));self.assertIsNone(m.verified_alias(self.db,dict(record,source_revision=41)));self.assertIsNone(m.verified_alias(self.db,dict(record,preferred_term='autre')))
    def test_existing_alias_unchanged(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);cfg,pins=self.fixture(p,dict(self.rec,aliases=['syn']));self.assertEqual(m.repair_catalog(self.db,p,cfg,'s','ns',pins,LEX),({},[],0))
    def test_layer_hash_drift(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);cfg,pins=self.fixture(p);(p/'lex.jsonl').write_bytes(b'{}\n');self.assertRaises(ValueError,m.repair_catalog,self.db,p,cfg,'s','ns',pins,LEX)
    def test_duplicate_json_refused(self):
        self.assertRaises(ValueError,m.strict_json,b'{"a":1,"a":2}');self.assertRaises(ValueError,m.strict_json,b'{"a":NaN}')
    def test_external_missing_editorial_fields_not_repaired(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);rec={'namespace_id':'ns','semantic_id':'KP1','language':'fr','preferred_term':'x','source_system':'s','source_snapshot':'x','source_record_id':'y','license':'CC0','alignment':{'evidence_refs':['KS1']}};raw=json.dumps(rec).encode()+b'\n';(p/'e.jsonl').write_bytes(raw);m.write(p/'catalog.json',{'namespace_id':'ns','catalog_id':'c','languages':[{'tag':'fr','layers':[{'kind':'external','path':'e.jsonl','sha256':m.sha(raw)}]}]});v=Draft202012Validator(m.read(FW/'schemas/v11/kristal-external-lexical-record.schema.json'));issues=m.lexical_schema_issues(p,{'catalog':'catalog.json'},'s',{'external':v});self.assertEqual(len(issues),2);self.assertTrue(all(x['json_path']=='$.alignment' for x in issues));self.assertEqual((p/'e.jsonl').read_bytes(),raw)
    def test_history_never_restored(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);doc={'namespace_id':'ns','assertions':[{'id':'KA1','subject':'KQ1'}]};m.write(p/'g.json',doc);state={'canonical_artifacts':[{'path':'g.json','logical_contract':{'id':'kristal.v11.semantic-graph'}}]};rows,pins,errs=m.history_audit(p,state,'selected.json','ns',{'KA1','KA2'},Draft202012Validator({}));self.assertEqual(len(rows),2);self.assertEqual(rows[0]['status'],'HISTORICAL_RECORD_FOUND_NOT_SELECTED');self.assertFalse(rows[0]['restoration_authorized']);self.assertEqual(rows[1]['status'],'HISTORICAL_NOT_FOUND_IN_REGISTERED_GRAPHS');self.assertFalse(errs)
    def test_history_conflict(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);state={'canonical_artifacts':[]}
            for i in range(2):
                path=f'g{i}.json';m.write(p/path,{'namespace_id':'ns','assertions':[{'id':'KA1','subject':str(i)}]});state['canonical_artifacts'].append({'path':path,'logical_contract':{'id':'kristal.v11.semantic-graph'}})
            rr,_,_=m.history_audit(p,state,'selected.json','ns',{'KA1'},Draft202012Validator({}));self.assertEqual(rr[0]['status'],'HISTORICAL_RECORDS_CONFLICT')
    def test_reader_private_gate(self):
        for s in r.PRIVATE:
            self.assertRaises(ValueError,r.graph_access,s,'active-only');self.assertFalse(r.graph_access(s,'private-review')['original_canonical_lexical_qualified']);self.assertFalse(r.graph_access(s,'private-review')['lexical_content_served'])
        self.assertTrue(r.graph_access(r.STRICT,'active-only')['original_canonical_lexical_qualified']);self.assertRaises(ValueError,r.graph_access,'BLOCKED_ACTIVE_GRAPH','private-review')
if __name__=='__main__':unittest.main()
