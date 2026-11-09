import json
from pathlib import Path
import sys
import unittest

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO.parents[1]
sys.path.insert(0,str(REPO/'kristal_manager'))
from unesco_workbench_alignment_v17 import align, AlignmentError

WB=ROOT/'EncyKlopedia/UNESCO_Workbench/candidates/educational-policy-en-v11/unesco-mt1-10'

def sample():
    data=json.loads((WB/'derived/v11/identity-review.en.json').read_text(encoding='utf8'))['concepts']
    nodes=[{'unesco_id':x['unesco_id'],'label_en':x['english_label'],
      'qid_candidate_unapproved':x.get('wikidata_qid_candidate') or ''} for x in data]
    return {'branch':'unesco-mt1-10','canonical_graph_built':False,'nodes':nodes,
      'candidate_statements':[{'unesco_id':nodes[i%41]['unesco_id'],'evidence_status':'NOT_ATTESTED'} for i in range(85)],
      'skos_internal_observations':[{} for _ in range(61)]}

@unittest.skipUnless(WB.is_dir(),'Workbench non fourni dans cette copie du code')
class TestWorkBench(unittest.TestCase):
    def test_41_preexisting_not_approved(self):
        r=align(WB,sample())
        self.assertEqual((r['concept_count'],r['provisional_KP_count'],r['wikidata_candidates']),(41,3,36))
        self.assertEqual(r['accepted_exact_matches'],0)
        self.assertTrue(all(not x['can_use_as_canonical_KQ'] for x in r['concepts']))
    def test_changed_qid_refused(self):
        g=sample();g['nodes'][0]['qid_candidate_unapproved']='Q1234567'
        with self.assertRaises(AlignmentError):align(WB,g)
    def test_fake_approval_refused(self):
        g=sample();g['candidate_statements'][0]['evidence_status']='QUALIFIED_KS'
        with self.assertRaises(AlignmentError):align(WB,g)
    def test_duplicate_refused(self):
        g=sample();g['nodes'][1]['unesco_id']=g['nodes'][0]['unesco_id']
        with self.assertRaises(AlignmentError):align(WB,g)
if __name__=='__main__':unittest.main()
