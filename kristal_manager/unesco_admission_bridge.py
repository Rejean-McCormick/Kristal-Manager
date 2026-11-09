#!/usr/bin/env python3
"""Non-canonical UNESCO decision triage, read-only for the current 41-concept branch."""
from __future__ import annotations
import argparse
import csv
from io import StringIO
import json
from pathlib import Path
import re
import sys

FORMAT='kristal-manager.unesco-mt1-10-decision-triage/1.0'
CANON=re.compile(r'^K(Q|P|A|S)[1-9][0-9]*$')
SHA=re.compile(r'^[0-9a-f]{64}$')
SPECS=(
 ('DECISIONS_41_IDENTITES_EDITABLE.csv','unesco_id',41,'TABLEAU_41_IDENTITES.csv','unesco_id'),
 ('DECISIONS_85_PROPOSITIONS_EDITABLE.csv','proposal_ref',85,'TABLEAU_85_PROPOSITIONS.csv','proposal_ref'),
 ('DECISIONS_61_RELATIONS_EDITABLE.csv','group_ref',61,'GROUPES_61_RELATIONS_INTERNES.csv','group_ref'),
 ('DECISIONS_4_SOURCES_CONCEPT10_EDITABLE.csv','reference_id',4,'FILE_81_SOURCES_A_ATTESTER.csv','reference_id'),
)
FIELDS={
 'DECISIONS_41_IDENTITES_EDITABLE.csv':{'KQ_existant':'entity','KS_identite_existante':'source'},
 'DECISIONS_85_PROPOSITIONS_EDITABLE.csv':{'KQ_existant':'entity','KP_existant':'property','KS_existante':'source'},
 'DECISIONS_61_RELATIONS_EDITABLE.csv':{'KQ_source_existant':'entity','KP_existant':'property','KQ_cible_existant':'entity','KS_existante':'source'},
 'DECISIONS_4_SOURCES_CONCEPT10_EDITABLE.csv':{'KS_existante':'source'},
}
class TriageError(ValueError):pass

def read_csv(path:Path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 3_000_000:
        raise TriageError('CSV de revue absent/non fiable : '+path.name)
    rdr=csv.DictReader(StringIO(path.read_text('utf-8-sig'),newline=''))
    if not rdr.fieldnames or None in rdr.fieldnames:
        raise TriageError('En-tete CSV invalide : '+path.name)
    rows=list(rdr)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise TriageError('CSV malforme : '+path.name)
    return rows

def triage(stage11:Path, kit:dict|None=None):
    if stage11.is_symlink() or not stage11.is_dir():
        raise TriageError('Dossier source absent ou symbolique')
    registry=(kit or {}).get('registry',{}).get('identities',{})
    exact_matches={(m.get('KQ_or_KP'),m.get('external_id')) for m in (kit or {}).get('accepted_exact_matches_in_existing_workspace',[])}
    registry_verified=((kit or {}).get('workspace_v11_status')=='EXISTING_WORKSPACE_KIT_CHECK_V11_PASSED'
                       and (kit or {}).get('workspace_branch_binding')=='EXPLICIT_SLUG_MATCH')
    counts={}; blockers=[]; refs_checked=[]
    for decision_name,key,size,anchor_name,anchor_key in SPECS:
        rows=read_csv(stage11/decision_name)
        anchor=read_csv(stage11/anchor_name)
        if len(rows)!=size:
            raise TriageError(f'{decision_name}: {len(rows)} lignes au lieu de {size}')
        ids=[r.get(key,'') for r in rows]
        if not all(ids) or len(set(ids))!=size:
            raise TriageError('References doubles ou absentes : '+decision_name)
        if not set(ids).issubset({a.get(anchor_key) for a in anchor}):
            raise TriageError('Decision sans ancrage : '+decision_name)
        anchor_by_id={a[anchor_key]:a for a in anchor}
        readonly_columns={
            'DECISIONS_41_IDENTITES_EDITABLE.csv':('qid_candidat',),
            'DECISIONS_85_PROPOSITIONS_EDITABLE.csv':('unesco_id',),
            'DECISIONS_61_RELATIONS_EDITABLE.csv':('source_ou_membre_a','cible_ou_membre_b', 'relation_normalisee','observations_reciproques'),
            'DECISIONS_4_SOURCES_CONCEPT10_EDITABLE.csv':(),
        }[decision_name]
        statuses={}
        for row in rows:
            ref=row[key]; status=row.get('decision','')
            if any(row.get(col)!=anchor_by_id[ref].get(col) for col in readonly_columns):
                raise TriageError('Colonne d ancrage modifiee : '+ref)
            allowed={'PENDING','CAPTURE_A_VERIFIER','REJETER'} if 'SOURCES_' in decision_name else {'PENDING','SOUMETTRE_A_LA_REVUE','REFORMULER','REJETER'}
            if status not in allowed:
                raise TriageError('Decision interdite : '+ref+' / '+status)
            statuses[status]=statuses.get(status,0)+1
            if status!='PENDING' and any(not row.get(f,'').strip() for f in ('responsable','decision_id','justification')):
                raise TriageError('Decision non justifiee : '+ref)
            # Even a justified decision is not a cryptographically verified human signature.
            if status=='SOUMETTRE_A_LA_REVUE':
                blockers.append({'ref':ref,'reason':'REQUIRES_INDEPENDENT_AUTHORITY_APPROVAL'})
            if status=='CAPTURE_A_VERIFIER':
                capture=row.get('capture_relative_path','')
                if ('..' in Path(capture).parts or Path(capture).is_absolute()
                        or ':' in capture or '\\' in capture):
                    raise TriageError('Chemin de capture non sur : '+ref)
                if not SHA.fullmatch(row.get('capture_sha256','')) or not capture or not row.get('passage_exact'):
                    blockers.append({'ref':ref,'reason':'CAPTURE_INCOMPLETE_OR_UNVERIFIED'})
                else:
                    blockers.append({'ref':ref,'reason':'SOURCE_BYTES_NOT_ATTESTED_AS_KS'})
            for field,kind in FIELDS[decision_name].items():
                value=row.get(field,'').strip()
                if not value: continue
                if not CANON.fullmatch(value) or {'entity':'KQ','property':'KP','source':'KS'}[kind]!=value[:2]:
                    raise TriageError(f'Identifiant canonique non conforme : {ref}/{field}')
                index=registry.get(value)
                match=bool(registry_verified and index and index.get('kind')==kind and index.get('status')=='stable')
                refs_checked.append({'decision_ref':ref,'field':field,'id':value,'registered_stable':match})
                if not match:
                    blockers.append({'ref':ref,'reason':'CANON_ID_NOT_VERIFIED_IN_EXISTING_KIT_REGISTRY','id':value})
                if (decision_name=='DECISIONS_41_IDENTITES_EDITABLE.csv' and field=='KQ_existant'
                        and row.get('qid_candidat') and registry_verified
                        and (value,row['qid_candidat']) not in exact_matches):
                    blockers.append({'ref':ref,'reason':'NO_ACCEPTED_EXACTMATCH_FOR_QID',
                                     'id':value,'candidate_qid':row['qid_candidat']})
        counts[decision_name]=statuses
    pending=sum(x.get('PENDING',0) for x in counts.values())
    return {'format':FORMAT,'branch':'unesco-mt1-10', 'one_branch_kristal':True,
            'rows_total':191,'decisions_by_file':counts,'pending':pending,
            'submitted_for_review':sum(c.get('SOUMETTRE_A_LA_REVUE',0) for c in counts.values()),
            'registry_available':registry_verified,'explicit_canonical_refs_checked':refs_checked,
            'blocking_checks':blockers,
            'human_decision_signatures_verified':0,'canon_write_authorized':False,
            'canonical_created':0,'publication_authorized':False}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage11',required=True,type=Path)
    p.add_argument('--kit-report',type=Path)
    args=p.parse_args(argv)
    kit=None
    if args.kit_report:
        if args.kit_report.is_symlink() or not args.kit_report.is_file():
            raise TriageError('Rapport Kit absent')
        kit=json.loads(args.kit_report.read_text('utf-8-sig'))
    print(json.dumps(triage(args.stage11,kit),ensure_ascii=False,sort_keys=True,indent=2))
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (TriageError,ValueError,OSError,KeyError,UnicodeError,json.JSONDecodeError) as e:
        print('MANAGER TRIAGE BLOQUE: '+str(e),file=sys.stderr);sys.exit(2)
