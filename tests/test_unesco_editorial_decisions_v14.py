"""Offline synthetic tests of ChatGPT editorial dispositions (no canonical writes)."""
import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).resolve().parents[1]/'kristal_manager/unesco_editorial_decisions_v14.py'
s=importlib.util.spec_from_file_location('mgr_v14',P); m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def fixture():
    ident={}; props={}; rels={}; srcs={}; ri={};rp={};rr={};rs={}
    for i in range(41):
        c=f'concept{i+1}';q=f'Q{i+123}' if i<36 else ''
        ident[c]={'unesco_uri':f'https://unesco.example/thesaurus/{c}','qid_candidat':q,'label_en':f'Topic {i}', 'label_fr':f'Sujet {i}'}
        ri[c]={**ident[c],'approval_humaine':'PENDING','exactMatch_approuve':'NON'}
    for i in range(85):
        c=f'concept{1+i%41}'; ref=f'P-{i:03}'; t=f'Statement {i}';
        status='REFORMULATION_REQUISE' if i<10 else 'REFERENCE_PRIMAIRE_REPEREE' if i<13 else 'PLAUSIBLE_A_DOCUMENTER'
        cat={'REFORMULATION_REQUISE':'REFORMULATION_SUGGEREE_A_REVOIR','REFERENCE_PRIMAIRE_REPEREE':'PASSAGE_PRIMAIRE_A_CAPTURER_ET_ATTESTER',
            'PLAUSIBLE_A_DOCUMENTER':'AVIS_DE_RECHERCHE_A_ETAYER'}[status]
        props[ref]={'unesco_id':c,'statement_en':t,'review_preavis':status,'source_lead':''}
        rp[ref]={'unesco_id':c,'texte_original_en':t,'texte_propose_en':t+' (revised)' if i<10 else t,
                 'avis_chatgpt_non_signe':cat,'precision_et_risque_fr':'scope','preuve_a_chercher_fr':'source'}
    for i in range(61):
        ref=f'I-{i:03}';a=f'concept{1+i%41}';b=f'concept{1+(i+1)%41}';kind='broader' if i<38 else 'related'; obs=f'{i};{i+61}'
        rels[ref]={'source_ou_membre_a':a,'cible_ou_membre_b':b,'relation_normalisee':kind,'observations_reciproques':obs}
        rr[ref]={'source_id':a,'target_id':b,'relation_skos':kind,'observations_reciproques':obs,
                 'avis_chatgpt_non_signe':'VERIFIER_HIERARCHIE_THEMATIQUE' if i<13 else 'CONSERVER_OBSERVATION_SKOS_SANS_KA','note_fr':'observed'}
    for i in range(81):
        ref=f'REF-{i:03}'; scope='CIBLE_CONCEPT10' if i<4 else 'ANCRE_TERMINOLOGIQUE'
        srcs[ref]={'portee':scope,'url':f'https://source.example/{i}','passage_attendu':'verify'}
        rs[ref]={'url':f'https://source.example/{i}','KS_approvee':'NON','commentaire_non_signe':'verify'}
    return {'identities':ident,'proposals':props,'relations':rels,'sources':srcs}, {'identities':ri,'proposals':rp,'relations':rr,'sources':rs}

class Decisions(unittest.TestCase):
    def test_191_editorial_positions_with_zero_canonical(self):
        t,r=fixture();result=m.decide(t,r)
        self.assertEqual(result['editorial_decisions_count'],191)
        self.assertEqual(result['human_signed_approvals'],0)
        self.assertFalse(result['admission_to_canon_authorized'])
        self.assertEqual(sum(x['changed_from_original'] for x in result['decisions'] if x['type']=='PROPOSITION'),10)
    def test_missing_qid_kept_as_unesco_anchor(self):
        t,r=fixture();result=m.decide(t,r)
        self.assertEqual(sum(x['crosswalk_status']=='MISSING' for x in result['decisions'] if x['type']=='IDENTITE'),5)
    def test_text_substitution_is_rejected(self):
        t,r=fixture();r['proposals']['P-000']['texte_original_en']='CHANGED'
        with self.assertRaises(m.EditorialError):m.decide(t,r)
    def test_faux_canon_status_rejected(self):
        t,r=fixture();r['identities']['concept1']['exactMatch_approuve']='OUI'
        with self.assertRaises(m.EditorialError):m.decide(t,r)
    def test_missing_relation_fails(self):
        t,r=fixture();del t['relations']['I-000']
        with self.assertRaises(m.EditorialError):m.decide(t,r)
if __name__=='__main__':unittest.main()
