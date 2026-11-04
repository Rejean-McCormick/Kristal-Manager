"""Read-only, non-approving Kristal-Manager intake of a private Spek handoff.

Verifies supplied graph/migration octets and explicit assertion membership. This
intake never sets C1/C2/C3 or copies a source into a public checkout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

FORMAT='spek.private-editorial-handoff/1.0'
DIGEST=re.compile(r'^sha256:[0-9a-f]{64}$')

class PrivateIntakeError(ValueError):
    pass


def _read(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size>20_000_000:
        raise PrivateIntakeError('Fichier privé absent ou non sûr')
    try:
        obj=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:
        raise PrivateIntakeError('Données JSON privées illisibles') from exc
    if not isinstance(obj,dict):
        raise PrivateIntakeError('Objet JSON attendu')
    return obj


def _hash(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size>20_000_000:
        raise PrivateIntakeError('Source de provenance absente ou non sûre')
    return 'sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(lock: dict, *, graph_path: Path, identity_map: Path | None = None) -> dict:
    if not isinstance(lock,dict) or lock.get('format')!=FORMAT or lock.get('status')!='PRIVATE_UNQUALIFIED_NOT_PUBLISHABLE':
        raise PrivateIntakeError('Paquet Spek privé invalide ou statut interdit')
    qualification=lock.get('qualification')
    if not isinstance(qualification,dict) or any(value is not False for value in qualification.values()) or set(qualification)!={
        'semantic_entailment_checked','semantik_result_pairs_verified','rhetorical_relations_approved','c1_c2_c3_approved','publication_authorized'}:
        raise PrivateIntakeError('Le paquet ne peut jamais s’auto-attribuer une qualification')
    source=lock.get('source')
    if not isinstance(source,dict) or source.get('kind')!='kristal_v11_semantic_graph' or source.get('sha256')!=_hash(Path(graph_path)):
        raise PrivateIntakeError('Empreinte du graphe canonique non conforme')
    graph=_read(Path(graph_path))
    if graph.get('schema_version')!='11.0' or graph.get('artifact_type')!='kristal_semantic_graph':
        raise PrivateIntakeError('Graphe sémantique v11 requis')
    entries=graph.get('assertions')
    if not isinstance(entries,list) or not all(isinstance(a,dict) and isinstance(a.get('id'),str) for a in entries):
        raise PrivateIntakeError('Assertions de source invalides')
    active={a['id'] for a in entries}
    if len(active)!=len(entries):
        raise PrivateIntakeError('Assertions dupliquées')
    mapping={}
    if identity_map is not None:
        if source.get('identity_migration_sha256')!=_hash(Path(identity_map)):
            raise PrivateIntakeError('Empreinte de migration d’identité non conforme')
        metadata=_read(Path(identity_map));bykind=metadata.get('by_kind')
        mapping=bykind.get('A') if isinstance(bykind,dict) else None
        if not isinstance(mapping,dict):
            raise PrivateIntakeError('Table de migration A invalide')
    elif source.get('identity_migration_sha256') is not None:
        raise PrivateIntakeError('Table de migration requise, mais absente')
    fields=lock.get('fields')
    templates=lock.get('template_locks')
    if not isinstance(fields,list) or not fields or not isinstance(templates,list) or not templates:
        raise PrivateIntakeError('Champs ou templates manquants')
    template_refs=set()
    for t in templates:
        if not isinstance(t,dict) or not isinstance(t.get('template_ref'),str) or not DIGEST.fullmatch(t.get('sha256','')) or t['template_ref'] in template_refs:
            raise PrivateIntakeError('Verrou de template invalide ou dupliqué')
        template_refs.add(t['template_ref'])
    refs=set(); keys=set()
    for field in fields:
        if not isinstance(field,dict) or not isinstance(field.get('realization_key'),str) or field['realization_key'] in keys or not DIGEST.fullmatch(field.get('request_sha256','')):
            raise PrivateIntakeError('Champ de réalisation invalide ou dupliqué')
        keys.add(field['realization_key'])
        anchors=field.get('source_assertion_refs')
        if not isinstance(anchors,list) or not anchors or len(set(anchors))!=len(anchors) or not all(isinstance(r,str) for r in anchors):
            raise PrivateIntakeError('Références source absentes ou dupliquées')
        refs.update(anchors)
    if lock.get('selected_assertion_count')!=len(refs):
        raise PrivateIntakeError('Compte d’assertions incohérent')
    translated=[mapping.get(r,r) for r in refs]
    if len(set(translated))!=len(refs) or not set(translated).issubset(active):
        raise PrivateIntakeError('Identités source absentes ou ambiguës dans le graphe canonique')
    relations=lock.get('relations_declared_unverified')
    if not isinstance(relations,list):
        raise PrivateIntakeError('Déclarations de relations manquantes')
    for relation in relations:
        anchors = relation.get('source_assertion_refs') if isinstance(relation,dict) else None
        if (not isinstance(anchors,list) or not anchors or not all(isinstance(r,str) and r for r in anchors)
            or len(anchors)!=len(set(anchors))):
            raise PrivateIntakeError('Relation sans ancrages uniques explicites')
        if (not isinstance(relation,dict) or relation.get('status')!='declared_unverified'
            or relation.get('template_ref') not in template_refs or
            not isinstance(relation.get('source_assertion_refs'),list) or
            not set(relation['source_assertion_refs']).issubset(refs)):
            raise PrivateIntakeError('Relation rhétorique non supportée par les références du plan')
    return {'format':'kristal-manager.spek-private-intake/1.0',
            'status':'PASS_IDENTITY_ONLY_NOT_QUALIFIED',
            'field_count':len(fields),'source_assertion_count':len(refs),
            'identity_mapped_count':sum(1 for r in refs if mapping.get(r,r)!=r),
            'rhetorical_relation_count':len(relations),
            'semantic_entailment_approved':False,'c1_c2_c3_approved':False,
            'publication_authorized':False}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Verifier un handoff privé Spek (sans autorisation)')
    parser.add_argument('--lock',required=True,type=Path)
    parser.add_argument('--graph',required=True,type=Path)
    parser.add_argument('--identity-map',type=Path)
    args=parser.parse_args(argv)
    try:
        result=inspect(_read(args.lock),graph_path=args.graph,identity_map=args.identity_map)
    except PrivateIntakeError as exc:
        parser.exit(2,'REFUS PRIVÉ : '+str(exc)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
