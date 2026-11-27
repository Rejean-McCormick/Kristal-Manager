import copy,sqlite3,unittest,tempfile,json,os
from pathlib import Path
from kristal_manager import operational_native_v5216 as m
ROOT=Path(__file__).resolve().parents[2]
KIT=Path(os.environ.get('KRISTAL_V5216_TEST_KIT',ROOT/'Kristal-Authoring-Kit'))
FW=Path(os.environ.get('KRISTAL_V5216_TEST_FRAMEWORK',ROOT/'Kristal-Framework'))
a=m.load(KIT/'tools/operational_native_v5216.py','preflight_test');r=m.load(FW/'tools/v11/operational_native_v5216.py','reader_test')
class OperationalTests(unittest.TestCase):
    def fixture(self,root):
        idx=root/'canon/state.index.json';idx.parent.mkdir();idx.write_text('{"canonical_artifacts": []}');native=root/'native.json';native.write_text('{}');roles=['registry','graph','crosswalk','catalog'];arts=[{'role':k,'source':k+'.json','target':'canon/domain/v11/updates/test/'+k+'.json','sha256':'a'*64,'artifact_id':'urn:'+k} for k in roles];inv={x['source']:x['sha256'] for x in arts};plan={'format':'koa.kristal-native-registration-plan/1.0','status':'PRIVATE_REHEARSAL_ONLY','activation_authorized':False,'requires_independent_editorial_approval':True,'requires_epistemic_reader_contract':True,'slug':'test','candidate_inventory':inv,'source_paths':{'state':'native.json'},'source_sha256':{'state':m.digest(native)},'state_index_sha256':m.digest(idx),'artifacts':arts,'layers':[],'profile':{x['role']:x['target'] for x in arts}};return plan,{'slug':'test'},inv
    def check(self,root,plan,pkt,inv):return a.preflight(root,plan,pkt,inv,safe=m.member,digest=m.digest)
    def test_preflight_no_approval(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p,pkt,i=self.fixture(root);before=m.inventory(root);res=self.check(root,p,pkt,i);self.assertFalse(res['production_activation']);self.assertFalse(res['transaction_executor_implemented']);self.assertEqual(before,m.inventory(root))
    def test_source_drift(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p,pkt,i=self.fixture(root);(root/'native.json').write_text('{"changed":true}')
            with self.assertRaises(ValueError):self.check(root,p,pkt,i)
    def test_target_collision(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p,pkt,i=self.fixture(root);target=root/p['artifacts'][0]['target'];target.parent.mkdir(parents=True);target.write_text('{}')
            with self.assertRaises(ValueError):self.check(root,p,pkt,i)
    def test_approval_cannot_be_inferred(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p,pkt,i=self.fixture(root);p['activation_authorized']=True
            with self.assertRaises(ValueError):self.check(root,p,pkt,i)
    def test_profile_exists(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p,pkt,i=self.fixture(root);f=root/'.kristal/v11/authoring.json';f.parent.mkdir(parents=True);f.write_text('{}')
            with self.assertRaises(ValueError):self.check(root,p,pkt,i)
    def test_active_only_refuses_nonactive(self):
        reader=object.__new__(r.Reader);reader.purpose='active-only'
        for layer in ('candidate','structured','native-record','native-artifact'):
            with self.assertRaises(ValueError):reader.read(layer,'x')
        self.assertFalse(hasattr(reader,'candidate'))
    def test_envelope_authority(self):
        out=r.envelope('active',{}, {},'active-only');self.assertFalse(out['activation_authorized']);self.assertFalse(out['publication_authorized']);self.assertFalse(out['production_integrated']);self.assertEqual(out['authority'],'EXISTING_ACTIVE_RECORD_NOT_NEW_TRUTH')
        with self.assertRaises(ValueError):r.envelope('candidate',{}, {},'active-only')
        self.assertEqual(r.envelope('candidate',{}, {},'private-review')['authority'],'NO_NEW_AUTHORITY_GRANTED')
    def test_scope_and_index_drift(self):
        db=sqlite3.connect(':memory:');db.executescript('CREATE TABLE identity(namespace_id,semantic_id,owner_slug,kind,lifecycle_status,accepted_wikidata,candidate_wikidata_json); CREATE TABLE lexical(namespace_id,semantic_id,language_tag,preferred_term,priority); INSERT INTO identity VALUES ("ns","KQ1","test","entity","stable",NULL,"[]");');reg={'namespace_id':'ns','identities':[{'id':'KQ1','kind':'entity','status':'stable'}]};projection={'namespace_id':'ns','identities':[{'id':'KQ1','kind':'entity','status':'stable','wikidata':{'accepted_exact':None,'candidate_exact':[]},'labels':{}}]};self.assertEqual(len(m.compare_projection(db,'ns','test',projection,reg)),1)
        with self.assertRaises(ValueError):m.compare_projection(db,'other','test',projection,reg)
        projection['identities'][0]['wikidata']['accepted_exact']='Q1'
        with self.assertRaises(ValueError):m.compare_projection(db,'ns','test',projection,reg)
        db.close()
    def test_unsafe_target(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p,pkt,i=self.fixture(root);p['artifacts'][0]['target']='canon/domain/v11/updates/../../../../escape.json';p['profile']['registry']=p['artifacts'][0]['target']
            with self.assertRaises(ValueError):self.check(root,p,pkt,i)
    def test_pending_journal_blocks(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p,pkt,i=self.fixture(root);f=root/'.kristal/v11/transactions/test.json';f.parent.mkdir(parents=True);f.write_text('{"profile":"kristal.v11-recoverable-registration/1.0","status":"pending"}')
            with self.assertRaises(ValueError):self.check(root,p,pkt,i)
    def test_plan_wrong_scope(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p,pkt,i=self.fixture(root);pkt['slug']='other'
            with self.assertRaises(ValueError):self.check(root,p,pkt,i)
if __name__=='__main__':unittest.main()
