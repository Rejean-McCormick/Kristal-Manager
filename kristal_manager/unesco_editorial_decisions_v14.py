#!/usr/bin/env python3
"""Decisions editoriales IA UNESCO, jamais autorisation de canonisation.

Entrées contrôlées en amont : tables stage11 et revue ChatGPT stage12.
Les 191 choix ici sont substantiels pour la COMPOSITION PRIVEE. Ils ne remplacent
ni signature humaine, ni KS, ni KQ/KP, ni autorite de publication.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256

FORMAT='kristal-manager.unesco-mt1-10-editorial-dispositions/1.0'
EDITOR='ChatGPT - decision editoriale non signee, commande par utilisateur dans conversation'
class EditorialError(ValueError): pass

def _check(ref,condition,why):
    if not condition: raise EditorialError(ref+': '+why)

def decide(tables:dict, reviews:dict):
    identities, proposals, relations, sources=(tables[n] for n in ('identities','proposals','relations','sources'))
    rids,rprops,rrels,rsources=(reviews[n] for n in ('identities','proposals','relations','sources'))
    for src, rev, count in ((identities,rids,41),(proposals,rprops,85),(relations,rrels,61),(sources,rsources,81)):
        _check('all',set(src)==set(rev) and len(src)==count,'inventaire/revue non concordants')
    out=[]
    for ref,src in sorted(identities.items()):
        row=rids[ref];qid=src['qid_candidat']
        _check(ref,(row['unesco_uri'],row['qid_candidat'])==(src['unesco_uri'],qid),'identite modifiee')
        _check(ref,row['exactMatch_approuve']=='NON' and row['approval_humaine']=='PENDING','approbation imprevue')
        out.append({'type':'IDENTITE','ref':ref,'unesco_id':ref,'decision_editoriale':'ANCRER_UNESCO_SANS_CROSSWALK_CANONIQUE',
            'source_uri':src['unesco_uri'],'label_en':src['label_en'],'label_fr':src['label_fr'],
            'qid_candidate':qid or None,'crosswalk_status':'CANDIDATE_UNVERIFIED' if qid else 'MISSING',
            'motif_fr':('Conserver la notice UNESCO en brouillon; ne pas assimiler QID a KQ ni approuver exactMatch.'
                        if qid else 'Ancrage UNESCO conserve, QID non trouve; ne rien inventer.' )})
    for ref,src in sorted(proposals.items()):
        row=rprops[ref]
        original=src['statement_en']; suggested=row['texte_propose_en']
        _check(ref,row['texte_original_en']==original and row['unesco_id']==src['unesco_id'],'texte ou concept divergent')
        cat=row['avis_chatgpt_non_signe']
        if cat=='REFORMULATION_SUGGEREE_A_REVOIR':
            decision='UTILISER_REFORMULATION_DANS_APERCU_PRIVE'
            _check(ref,suggested.strip() and suggested != original,'reformulation absente')
        elif cat=='PASSAGE_PRIMAIRE_A_CAPTURER_ET_ATTESTER':
            decision='RETENIR_SOUS_RESERVE_PREUVE_PRIMAIRE'
        elif cat=='AVIS_DE_RECHERCHE_A_ETAYER':
            decision='RETENIR_COMME_HYPOTHESE_DANS_APERCU_PRIVE'
        else: raise EditorialError('Categorie inconnue: '+cat)
        _check(ref,src['review_preavis'] in ('PLAUSIBLE_A_DOCUMENTER','REFORMULATION_REQUISE','REFERENCE_PRIMAIRE_REPEREE'),'statut source inconnu')
        out.append({'type':'PROPOSITION','ref':ref,'unesco_id':src['unesco_id'],'decision_editoriale':decision,
            'original_en':original,'chosen_text_en':suggested,'original_sha256':sha256(original.encode('utf8')).hexdigest(),
            'changed_from_original':suggested!=original,'risk_fr':row['precision_et_risque_fr'],
            'evidence_to_seek_fr':row['preuve_a_chercher_fr'],'source_lead':src['source_lead'],
            'evidence_status':'NOT_ATTESTED','motif_fr':'Admis pour la composition privee seulement, pas pour KA.'})
    for ref,src in sorted(relations.items()):
        row=rrels[ref]
        _check(ref,(row['source_id'],row['target_id'],row['relation_skos'])==(src['source_ou_membre_a'],src['cible_ou_membre_b'],src['relation_normalisee']),'triplet SKOS divergent')
        _check(ref,row['observations_reciproques']==src['observations_reciproques'],'réciprocité divergente')
        value='MAINTENIR_LIEN_SKOS_PRIVE'
        if row['avis_chatgpt_non_signe']=='VERIFIER_HIERARCHIE_THEMATIQUE':value='MAINTENIR_ET_SIGNALER_HIERARCHIE'
        elif row['avis_chatgpt_non_signe']!='CONSERVER_OBSERVATION_SKOS_SANS_KA':raise EditorialError('Avis relation inconnu')
        out.append({'type':'SKOS_INTERNE','ref':ref,'decision_editoriale':value,
            'source_unesco_id':row['source_id'],'target_unesco_id':row['target_id'],
            'relation_skos':row['relation_skos'],'observations_reciproques':row['observations_reciproques'],
            'motif_fr':row['note_fr']})
    targeted=[ref for ref,src in sorted(sources.items()) if src['portee']=='CIBLE_CONCEPT10']
    _check('source',len(targeted)==4,'quatre references concept10 attendues')
    for ref in targeted:
        row=rsources[ref];src=sources[ref]
        _check(ref,row['url']==src['url'] and row['KS_approvee']=='NON','source incompatible ou fausse approbation')
        out.append({'type':'SOURCE_CONCEPT10','ref':ref,'decision_editoriale':'PRIORISER_CAPTURE_ET_ATTESTATION',
                    'url':src['url'],'passage_attendu':src['passage_attendu'],
                    'motif_fr':row['commentaire_non_signe'],'KS_approved':False})
    counts=Counter(e['type'] for e in out)
    _check('all',counts==Counter({'IDENTITE':41,'PROPOSITION':85,'SKOS_INTERNE':61,'SOURCE_CONCEPT10':4}),'191 decisions incorrectes')
    split=Counter(x['decision_editoriale'] for x in out if x['type']=='PROPOSITION')
    _check('all',split==Counter({'RETENIR_COMME_HYPOTHESE_DANS_APERCU_PRIVE':72,
         'UTILISER_REFORMULATION_DANS_APERCU_PRIVE':10,'RETENIR_SOUS_RESERVE_PREUVE_PRIMAIRE':3}), 'triage IA imprevu')
    return {'format':FORMAT,'branch':'unesco-mt1-10','editorial_actor':EDITOR,
        'editorial_decisions_count':len(out),'all_editorial_positions_set':True,
        'user_requested_editorial_decision_workflow':True,'mandate_is_not_signature_verification':True,
        'editorial_counts':dict(sorted(Counter(x['decision_editoriale'] for x in out).items())),
        'human_authorization_verified':False,'human_signed_approvals':0,'canonical_KQ_KP_KA_KS_created':0,
        'actual_KS_qualified':0,'admission_to_canon_authorized':False,'publication_authorized':False,
        'decisions':out}
