#!/usr/bin/env python3
"""Strict, read-only alignment of a UNESCO Workbench v11 *candidate* registry.

KQ/KP/KS here are *preexisting provisional identifiers*, never approved IDs.
An accepted Wikidata exactMatch requires separate authority and evidence.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re

BRANCH='unesco-mt1-10'
KQ=re.compile(r'KQ[1-9][0-9]*\Z')
KP=re.compile(r'KP[1-9][0-9]*\Z')
KS=re.compile(r'KS[1-9][0-9]*\Z')
CID=re.compile(r'concept[1-9][0-9]*\Z')
QID=re.compile(r'Q[1-9][0-9]*\Z')
class AlignmentError(ValueError):pass

def read_json(path:Path, limit=8_000_000):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>limit:
        raise AlignmentError('Fichier absent, symbolique ou trop gros: '+str(path))
    return json.loads(path.read_text('utf-8-sig'))

def digest(path:Path):return hashlib.sha256(path.read_bytes()).hexdigest()

def align(workspace:Path, editorial:dict):
    ws=Path(workspace)
    if ws.is_symlink() or not ws.is_dir():raise AlignmentError('Workbench indisponible')
    meta=read_json(ws/'kristal.workspace.json')
    if meta.get('slug')!=BRANCH:raise AlignmentError('Branche differente dans Workbench')
    auth=read_json(ws/'.kristal/v11/authoring.json')
    if auth.get('semantic_profile')!='kristal.semantic-identity/11.0':raise AlignmentError('Profil v11 absent')
    known={'registry':'canon/domain/v11/registry.json', 'graph':'canon/domain/v11/graph.json',
           'crosswalk':'canon/domain/v11/crosswalk.json'}
    for k,v in known.items():
        if auth.get(k)!=v:raise AlignmentError('Chemin v11 inattendu: '+k)
    reg=read_json(ws/known['registry']);g=read_json(ws/known['graph']);cw=read_json(ws/known['crosswalk'])
    mp=read_json(ws/'.kristal/v11/identity-migration-map.json')
    if (reg.get('schema_version')!='11.0' or reg.get('artifact_type')!='kristal_identity_registry'
        or g.get('artifact_type')!='kristal_semantic_graph' or cw.get('artifact_type')!='kristal_external_crosswalk'):
        raise AlignmentError('Artifacts v11 non conformes')
    identities=reg.get('identities',[])
    if not isinstance(identities,list) or len(identities)!=45:raise AlignmentError('45 identites provisoires attendues')
    id_by={}
    for item in identities:
        i=item.get('id');kind=item.get('kind');status=item.get('status')
        typ='entity' if isinstance(i,str) and KQ.fullmatch(i) else 'property' if isinstance(i,str) and KP.fullmatch(i) else 'source' if isinstance(i,str) and KS.fullmatch(i) else None
        if i in id_by or not typ or typ!=kind or status!='provisional':
            raise AlignmentError('Identite non provisoire, dupliquee ou de mauvais type: '+str(i))
        id_by[i]=item
    q={k.split(':',1)[1]:v for k,v in mp.get('by_kind',{}).get('Q',{}).items() if k.startswith('unesco-skos:')}
    if len(q)!=41 or len(set(q.values()))!=41 or any(not CID.fullmatch(k) or v not in id_by for k,v in q.items()):
        raise AlignmentError('Carte UNESCO-KQ incomplete ou ambigue')
    p=mp.get('by_kind',{}).get('P',{})
    if len(p)!=3 or any(v not in id_by for v in p.values()):raise AlignmentError('Carte des 3 KP incomplete')
    if (set(g.get('entities',[]))!=set(q.values()) or set(g.get('properties',[]))!=set(p.values())
        or len(g.get('assertions',[]))!=0):raise AlignmentError('Le graphe Workbench ne doit pas inclure de KA')
    namespace=reg.get('namespace_id')
    if not namespace or namespace!=g.get('namespace_id'):raise AlignmentError('Namespace v11 incompatible')
    if editorial.get('branch')!=BRANCH or editorial.get('canonical_graph_built') is not False:raise AlignmentError('Graphe v14 non candidat')
    nodes=editorial.get('nodes',[])
    if len(nodes)!=41 or len(editorial.get('candidate_statements',[]))!=85 or len(editorial.get('skos_internal_observations',[]))!=61:
        raise AlignmentError('Cardinalite editorial incoherente')
    seen=set();rows=[]
    by_cw={}
    for item in cw.get('mappings',[]):
        kq=(item.get('local_ref') or {}).get('id'); external=(item.get('external_ref') or {}).get('id')
        if item.get('status')=='accepted':raise AlignmentError('Crosswalk accepte inattendu dans candidat initial')
        if item.get('status')!='candidate' or kq not in id_by or not QID.fullmatch(external or ''):raise AlignmentError('Candidat crosswalk inattendu')
        if kq in by_cw:raise AlignmentError('QID multiples pour une identite non examinee')
        by_cw[kq]=external
    if len(by_cw)!=36:raise AlignmentError('36 QID candidats attendus')
    for n in nodes:
        u=n.get('unesco_id'); qid=n.get('qid_candidate_unapproved') or ''
        if not isinstance(u,str) or not CID.fullmatch(u) or u in seen or u not in q:raise AlignmentError('Concept UNESCO invalide')
        seen.add(u);assigned=q[u]
        if qid!=(by_cw.get(assigned) or ''):raise AlignmentError('Divergence Wikidata/Workbench pour '+u)
        rows.append({'unesco_id':u,'provisional_KQ':assigned,'qid_candidate_unapproved':qid,
                     'label_en':n['label_en'],'identity_status':'PROVISIONAL_NOT_ADMITTED',
                     'can_use_as_canonical_KQ':False})
    for claim in editorial['candidate_statements']:
        if claim.get('unesco_id') not in seen or claim.get('evidence_status')!='NOT_ATTESTED':
            raise AlignmentError('Proposition sans ancrage ou preuve non attestee incorrecte')
    return {'format':'kristal-manager.unesco-workbench-alignment/1.0','branch':BRANCH,
      'provisional_registry_namespace':namespace,'source_registry_sha256':digest(ws/known['registry']),
      'source_crosswalk_sha256':digest(ws/known['crosswalk']),
      'concepts':rows,'concept_count':41,'provisional_KQ_count':41,'provisional_KP_count':3,
      'provisional_KS_count':1,'wikidata_candidates':36,
      'provisional_properties':p,'all_identifiers_status':'PROVISIONAL',
      'canonical_KA_approved':0,'accepted_exact_matches':0,'minted_ids':0,'publication_authorized':False}
