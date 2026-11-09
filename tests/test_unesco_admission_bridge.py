"""No-network regression tests: UNESCO decisions cannot silently become canon."""
import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'kristal_manager'/'unesco_admission_bridge.py'
spec=importlib.util.spec_from_file_location('unesco_admission_bridge_v13',SCRIPT)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class TriageTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.items=[]
  for decision,key,n,source,sourcekey in mod.SPECS:
   fields={
     'DECISIONS_41_IDENTITES_EDITABLE.csv':['qid_candidat'],
     'DECISIONS_85_PROPOSITIONS_EDITABLE.csv':['unesco_id'],
     'DECISIONS_61_RELATIONS_EDITABLE.csv':['source_ou_membre_a','cible_ou_membre_b','relation_normalisee','observations_reciproques'],
     'DECISIONS_4_SOURCES_CONCEPT10_EDITABLE.csv':[],
   }[decision]
   originals=[];decisions=[]
   for i in range(n):
    ref=f'{key}-{i:03}'
    original={sourcekey:ref,**{f:f'anchor-{f}-{i}' for f in fields}}
    dec={key:ref,**{f:original[f] for f in fields},'decision':'PENDING','responsable':'', 'decision_id':'','justification':'',**{f:'' for f in mod.FIELDS[decision]}}
    originals.append(original);decisions.append(dec)
   for filename,rows in [(source,originals),(decision,decisions)]:
    with (self.root/filename).open('w',encoding='utf-8',newline='') as f:
     wr=csv.DictWriter(f,fieldnames=rows[0].keys());wr.writeheader();wr.writerows(rows)
   self.items.append((decision,key,decisions))
 def tearDown(self):self.tmp.cleanup()
 def save(self,filename,rows):
  with (self.root/filename).open('w',encoding='utf-8',newline='') as f:
   wr=csv.DictWriter(f,fieldnames=rows[0].keys());wr.writeheader();wr.writerows(rows)
 def test_191_pending_not_approved(self):
  result=mod.triage(self.root)
  self.assertEqual(result['pending'],191)
  self.assertEqual(result['rows_total'],191)
  self.assertFalse(result['canon_write_authorized'])
 def test_rogue_approved_status_rejected(self):
  filename,_,rows=self.items[0];rows[0]['decision']='APPROUVE';self.save(filename,rows)
  with self.assertRaises(mod.TriageError):mod.triage(self.root)
 def test_unauthenticated_submission_rejected(self):
  filename,_,rows=self.items[0];rows[0]['decision']='SOUMETTRE_A_LA_REVUE';self.save(filename,rows)
  with self.assertRaises(mod.TriageError):mod.triage(self.root)
 def test_justified_review_is_not_approval(self):
  filename,_,rows=self.items[0];rows[0].update(decision='SOUMETTRE_A_LA_REVUE',responsable='Editorial',decision_id='REV-10',justification='A examiner');self.save(filename,rows)
  r=mod.triage(self.root)
  self.assertEqual(r['submitted_for_review'],1)
  self.assertFalse(r['canon_write_authorized'])
 def test_wikidata_q_is_not_a_kq(self):
  filename,_,rows=self.items[0];rows[0]['KQ_existant']='Q69370';self.save(filename,rows)
  with self.assertRaises(mod.TriageError):mod.triage(self.root)
 def test_unverified_existing_kq_is_blocked(self):
  filename,_,rows=self.items[0];rows[0]['KQ_existant']='KQ123';self.save(filename,rows)
  r=mod.triage(self.root)
  self.assertEqual(r['explicit_canonical_refs_checked'][0]['registered_stable'],False)
  self.assertEqual(r['blocking_checks'][0]['reason'],'CANON_ID_NOT_VERIFIED_IN_EXISTING_KIT_REGISTRY')
 def test_unbound_demo_registry_is_not_proof(self):
  filename,_,rows=self.items[0];rows[0]['KQ_existant']='KQ123';self.save(filename,rows)
  kit={'workspace_v11_status':'EXISTING_WORKSPACE_KIT_CHECK_V11_PASSED',
    'workspace_branch_binding':'NOT_ESTABLISHED','registry':{'identities':{'KQ123':{'kind':'entity','status':'stable'}}}}
  self.assertFalse(mod.triage(self.root,kit)['explicit_canonical_refs_checked'][0]['registered_stable'])
 def test_tampered_immutable_column_is_blocked(self):
  filename,_,rows=self.items[1];rows[0]['unesco_id']='concept999';self.save(filename,rows)
  with self.assertRaises(mod.TriageError):mod.triage(self.root)
 def test_source_capture_missing_hash_is_not_attested(self):
  filename,_,rows=self.items[3];rows[0].update(decision='CAPTURE_A_VERIFIER',responsable='R',decision_id='S01',justification='Verifier');self.save(filename,rows)
  r=mod.triage(self.root)
  self.assertIn('CAPTURE_INCOMPLETE_OR_UNVERIFIED',{x['reason'] for x in r['blocking_checks']})

if __name__=='__main__':unittest.main()
