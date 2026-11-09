#!/usr/bin/env python3
"""Read-only reconciliation of UNESCO Q candidates against a Kit-verified registry.

Never manufacture KQ/KP/KS, exactMatch, evidence or human decisions. An accepted
crosswalk in an explicitly selected UNESCO-bound workspace may provide a vetted
identity hint, but is not authority to mint assertions or publish.
"""
from __future__ import annotations
import json
from pathlib import Path
import re

class ReconcileError(ValueError):pass
QID=re.compile(r'^Q[1-9][0-9]*$')
KQ=re.compile(r'^KQ[1-9][0-9]*$')


def reconcile(graph:dict,kit_report:dict):
    if (graph.get('branch')!='unesco-mt1-10' or len(graph.get('nodes',[]))!=41
       or graph.get('canonical_graph_built') is not False):
        raise ReconcileError('Graphe v14 non admissible')
    registry=kit_report.get('registry',{})
    permitted=kit_report.get('workspace_v11_status')=='EXISTING_WORKSPACE_KIT_CHECK_V11_PASSED' and kit_report.get('workspace_branch_binding')=='EXPLICIT_SLUG_MATCH'
    ids=registry.get('identities',{}) if permitted else {}
    pairs={}
    for ref in kit_report.get('accepted_exact_matches_in_existing_workspace',[]) if permitted else []:
        kq=ref.get('KQ_or_KP');qid=ref.get('external_id')
        if not (isinstance(qid,str) and QID.fullmatch(qid) and isinstance(kq,str) and KQ.fullmatch(kq)):
            continue
        identity=ids.get(kq,{})
        if (identity.get('kind')=='entity' and identity.get('status')=='stable'
            and isinstance(ref.get('decision_id'),str) and ref['decision_id'].strip()
            and isinstance(ref.get('evidence_refs'),list) and ref['evidence_refs']):
            pairs.setdefault(qid,set()).add(kq)
    rows=[];verified=0;ambiguous=0;missing=0
    seen_unesco=set()
    for n in graph['nodes']:
        uid=n['unesco_id']; qid=n.get('qid_candidate_unapproved') or ''
        if not re.fullmatch(r'concept[1-9][0-9]*',uid) or uid in seen_unesco:raise ReconcileError('ID UNESCO non conforme ou double')
        seen_unesco.add(uid)
        if qid and not QID.fullmatch(qid):raise ReconcileError('QID candidat invalide: '+uid)
        found=sorted(pairs.get(qid,set())) if qid else []
        status=('MISSING_QID_CANDIDATE' if not qid else
                'NO_APPROVED_EXACTMATCH_IN_EXPLICIT_REGISTRY' if not found else
                'AMBIGUOUS_ACCEPTED_EXACTMATCH' if len(found)>1 else
                'EXISTING_REGISTRY_CROSSWALK_VERIFIED_REVIEW_STILL_REQUIRED')
        verified+=status=='EXISTING_REGISTRY_CROSSWALK_VERIFIED_REVIEW_STILL_REQUIRED'
        ambiguous+=status=='AMBIGUOUS_ACCEPTED_EXACTMATCH'
        missing+=status=='MISSING_QID_CANDIDATE'
        rows.append({'unesco_id':uid,'label_en':n['label_en'],
          'qid_candidate':qid,'existing_KQ_candidates':found,'status':status,
          'approved_for_this_pipeline':False})
    property_ids=sorted(k for k,v in ids.items() if k.startswith('KP') and v.get('kind')=='property' and v.get('status')=='stable')
    source_ids=sorted(k for k,v in ids.items() if k.startswith('KS') and v.get('kind')=='source' and v.get('status')=='stable')
    return {'format':'kristal-manager.unesco-mt1-10-registry-reconciliation/1.0','branch':'unesco-mt1-10',
     'workspace_registry_verified_for_branch':permitted,'registry_sha256':registry.get('sha256') if permitted else None,
     'concepts':rows,'count':len(rows),'qid_candidates':len(rows)-missing,
     'qid_missing':missing,'exactmatch_existing_candidates':verified,'ambiguous_existing_matches':ambiguous,
     'existing_stable_KP_available_for_manual_property_review':property_ids,
     'existing_stable_KS_available_for_manual_evidence_review':source_ids,
     'KS_attestations_performed_by_this_tool':0,'canonical_IDs_minted':0,
     'publication_authorized':False}
