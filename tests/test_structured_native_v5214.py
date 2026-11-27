import unittest,tempfile,json,importlib.util
from pathlib import Path
from decimal import Decimal
from kristal_manager import structured_native_v5214 as n

ROOT=Path(__file__).resolve().parents[2]
K=ROOT/'Kristal-Authoring-Kit';F=ROOT/'Kristal-Framework'
class StructuredTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.builder=n.load_kit(K);cls.f=cls.builder.load_framework(F)
    def test_nested_json(self):
        f=self.f;v=f.decode(b'{"kind":"json","value":{"a":[true,null,123,0.12345678901234567890123456789]}}');self.assertEqual(f.describe(v,'/x')['form'],'json_object');self.assertEqual(f.decode(f.encode(v)),v);self.assertEqual(v['value']['a'][3],Decimal('0.12345678901234567890123456789'))
    def test_array_set_distinction(self):
        f=self.f;self.assertEqual(f.describe({'kind':'json','value':['x','x']},'/x')['form'],'json_array');self.assertEqual(f.describe({'kind':'set','value':['x','x']},'/x')['form'],'native_set_sequence')
    def test_unapproved_string_array(self):
        with self.assertRaises(ValueError):self.f.describe({'kind':'string','value':['x']},'/x')
    def test_monolingual_text(self):
        f=self.f;self.assertEqual(f.describe({'kind':'monolingual_text','value':{'text':'Bonjour','lang':'fr'}},'/x')['form'],'monolingual_text');
        with self.assertRaises(ValueError):f.describe({'kind':'monolingual_text','value':{'text':'Bonjour'}},'/x')
    def test_enriched_reference(self):self.assertEqual(self.f.describe({'kind':'referent','id':'x','value':'question'},'/x')['form'],'enriched_reference')
    def test_duplicate_keys(self):
        with self.assertRaises(ValueError):self.f.decode(b'{"a":1,"a":2}')
    def test_nonfinite(self):
        with self.assertRaises(ValueError):self.f.decode(b'{"a":NaN}')
    def test_boolean_distinct(self):
        with self.assertRaises(ValueError):self.f.describe({'kind':'boolean','value':1},'/x')
    def test_unknown_kind(self):
        with self.assertRaises(ValueError):self.f.describe({'kind':'made-up','value':'x'},'/x')
    def test_path_traversal(self):
        with self.assertRaises(ValueError):self.f.safe(Path('.'),'../x')
    def fixture(self,root,discovery=False):
        a={'assertion_id':'a','assertion_status':'claimed','statement':{'subject':{'kind':'item','id':'s'},'predicate':'p','object':{'kind':'json','value':{'a':[1,False,None]}},'qualifiers':[{'predicate':'q','object':{'kind':'string','value':'first'}},{'predicate':'q','object':{'kind':'boolean','value':True}}]},'evidence_refs':[],'uncertainty':{'notes':'not verified'}}
        files={'kristal.workspace.json':{'slug':'demo'},'canon/state.index.json':{'canonical_artifacts':[{'path':'native.json','artifact_id':'urn:a','logical_contract':{'id':'native','version':'1'}}]},'native.json':{'schema_version':'6.0','artifact_type':'kristal_state','assertions':[a,a]}}
        pin={'state':None if discovery else 'native.json','assertions':0 if discovery else 2,'files':{}}
        for p,x in files.items():q=root/p;q.parent.mkdir(parents=True,exist_ok=True);b=json.dumps(x).encode();q.write_bytes(b);pin['files'][p]=self.f.sha(b)
        return pin,a
    def test_roundtrip_duplicate_occurrences_and_qualifiers(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);pin,a=self.fixture(p/'in');packet=self.builder.build(p/'in','demo',pin,p/'out',self.f);rr=packet['records'];self.assertNotEqual(rr[0]['occurrence_id'],rr[1]['occurrence_id']);x=self.f.read_occurrence(p/'out',packet,rr[1]['occurrence_id']);self.assertEqual(x['native_assertion'],a);self.assertEqual(x['status'],self.f.STATUS);self.assertEqual(x['record']['qualifiers'][1]['object']['form'],'scalar_boolean')
    def test_tampered_packet(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);pin,_=self.fixture(p/'in');packet=self.builder.build(p/'in','demo',pin,p/'out',self.f);packet['records'][0]['native_status']='validated'
            with self.assertRaises(ValueError):self.f.validate_packet(p/'out',packet)
    def test_source_tamper(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);pin,_=self.fixture(p/'in');packet=self.builder.build(p/'in','demo',pin,p/'out',self.f);(p/'out/originals/native.json').write_text('{}')
            with self.assertRaises(ValueError):self.f.validate_packet(p/'out',packet)
    def test_discovery_no_occurrences(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);pin,_=self.fixture(p/'in',True);packet=self.builder.build(p/'in','demo',pin,p/'out',self.f);self.assertEqual(len(packet['registered_artifacts']),1);self.assertEqual(packet['records'],[])
            with self.assertRaises(ValueError):self.f.read_occurrence(p/'out',packet,'unknown')
    def test_pin_drift(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);pin,_=self.fixture(p/'in');(p/'in/native.json').write_text('{}')
            with self.assertRaises(ValueError):self.builder.build(p/'in','demo',pin,p/'out',self.f)
if __name__=='__main__':unittest.main()
