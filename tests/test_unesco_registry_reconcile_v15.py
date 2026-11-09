import importlib.util
from pathlib import Path
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'kristal_manager/unesco_registry_reconcile_v15.py'
spec=importlib.util.spec_from_file_location('unesco_registry_reconcile_v15',SCRIPT)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def graph():
    return {'branch':'unesco-mt1-10','canonical_graph_built':False,'nodes':[
        {'unesco_id':'concept'+str(i),'label_en':'Concept '+str(i),
         'qid_candidate_unapproved':('Q'+str(i) if i<37 else '')} for i in range(1,42)]}
def registry():
    return {'workspace_v11_status':'EXISTING_WORKSPACE_KIT_CHECK_V11_PASSED',
        'workspace_branch_binding':'EXPLICIT_SLUG_MATCH',
        'registry':{'identities':{'KQ10':{'kind':'entity','status':'stable'},
                                  'KQ11':{'kind':'entity','status':'stable'},
                                  'KP123':{'kind':'property','status':'stable'}}},
        'accepted_exact_matches_in_existing_workspace':[
            {'KQ_or_KP':'KQ10','external_id':'Q1','decision_id':'d1','evidence_refs':['KS1']}]}
class ReconciliationTests(unittest.TestCase):
    def test_no_explicit_registry_means_no_identity(self):
        r=mod.reconcile(graph(),{})
        self.assertEqual((r['count'],r['qid_candidates'],r['qid_missing']),(41,36,5))
        self.assertEqual(r['exactmatch_existing_candidates'],0)
    def test_accepted_stable_crosswalk_is_existing_hint_only(self):
        r=mod.reconcile(graph(),registry())
        self.assertEqual(r['exactmatch_existing_candidates'],1)
        self.assertFalse(r['concepts'][0]['approved_for_this_pipeline'])
    def test_no_evidence_no_identity_match(self):
        x=registry();x['accepted_exact_matches_in_existing_workspace'][0]['evidence_refs']=[]
        self.assertEqual(mod.reconcile(graph(),x)['exactmatch_existing_candidates'],0)
    def test_no_branch_binding_no_identity(self):
        x=registry();x['workspace_branch_binding']='NOT_ESTABLISHED'
        self.assertEqual(mod.reconcile(graph(),x)['exactmatch_existing_candidates'],0)
    def test_ambiguous_matches_are_blocked(self):
        x=registry();x['accepted_exact_matches_in_existing_workspace'].append(
           {'KQ_or_KP':'KQ11','external_id':'Q1','decision_id':'d2','evidence_refs':['KS2']})
        r=mod.reconcile(graph(),x)
        self.assertEqual(r['ambiguous_existing_matches'],1)
        self.assertEqual(r['exactmatch_existing_candidates'],0)
    def test_duplicate_unesco_ids_refused(self):
        g=graph();g['nodes'][0]['unesco_id']='concept2'
        with self.assertRaises(mod.ReconcileError):mod.reconcile(g,{})
    def test_noncanonical_fake_qid_rejected(self):
        g=graph();g['nodes'][0]['qid_candidate_unapproved']='KQ10'
        with self.assertRaises(mod.ReconcileError):mod.reconcile(g,{})

if __name__=='__main__':unittest.main()
