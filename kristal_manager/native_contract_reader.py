"""Observe registered native canonical contracts without asserting a KQ/KP graph.

All observed material comes exclusively from canon/state.index.json selections.
Reference manifests are not automatically dereferenced to historical or derived
objects. No semantic identity, exactMatch, or Framework qualification is inferred.
"""
from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import PurePosixPath

VERSION='kristal.manager-native-contract-observation/0.2'
MAX_FIELDS=110
MAX_BRANCHES=60


def _str(v):
    return v if isinstance(v,str) and bool(v.strip()) else None


def _walk(value, key_counts, paths, *, depth=0, prefix='$'):
    """Bounded structural inspection; never uses arbitrary text values as facts."""
    if depth>12 or len(paths)>=MAX_FIELDS:return
    if isinstance(value,dict):
        for key,child in value.items():
            k=str(key)
            key_counts[k]+=1
            if len(paths)<MAX_FIELDS:paths.append(prefix+'.'+k)
            _walk(child,key_counts,paths,depth=depth+1,prefix=prefix+'.'+k)
    elif isinstance(value,list):
        for child in value[:3]:
            if len(paths)>=MAX_FIELDS:break
            _walk(child,key_counts,paths,depth=depth+1,prefix=prefix+'[]')


def _contract_observation(rel, entry, data):
    """Only explicit recognized structures qualify, with non-authoritative summaries."""
    contract=(entry.get('logical_contract') or {})
    cid=contract.get('id') if isinstance(contract,dict) else None
    common={'path':rel,'contract_id':cid,'contract_version':contract.get('version') if isinstance(contract,dict) else None}
    # A reference component contains no domain assertions: digest != source content.
    if data.get('model')=='native_json_component' and isinstance(data.get('component'),dict):
        c=data['component']; digest=(c.get('logical_content') or {}) if isinstance(c.get('logical_content'),dict) else {}
        if _str(c.get('role')) in ('canonical_state','identity_registry') and _str(digest.get('digest')) and _str(digest.get('profile')):
            return {**common,'kind':'component_reference','role':c['role'],
                 'reference_profile':digest['profile'],'reference_digest':digest['digest'],
                 'source_contract':c.get('source_contract'),'content_coverage':'reference_only'}
    if data.get('portable_contract')=='kristal_state/6.0' and _str(data.get('state_id')):
        ch=data.get('content_hash')
        if isinstance(ch,dict) and _str(ch.get('value')) and isinstance(data.get('assertion_count'),int) and data['assertion_count']>=0:
            return {**common,'kind':'portable_v6_state_reference', 'role':'state',
                  'reported_assertion_count':data['assertion_count'],
                  'legacy_state_id':data['state_id'], 'content_coverage':'reference_only'}
    if data.get('resource_model')=='canonical-json-resource-set' and isinstance(data.get('resources'),list):
        resources=data['resources']
        if all(isinstance(x,dict) and _str(x.get('resource_id')) and _str(x.get('role')) for x in resources):
            return {**common,'kind':'resource_reference_set','role':'resource_basis',
                    'domain':_str(data.get('domain')),'resource_count':len(resources),
                    'resource_roles':[x['role'] for x in resources[:80]],
                    'semantic_boundaries_count':len(data.get('semantic_boundaries',[])) if isinstance(data.get('semantic_boundaries'),list) else None,
                    'content_coverage':'reference_only'}
    if (_str(data.get('native_shape')) and isinstance(data.get('canonical_roles'),list)
          and isinstance(data.get('basis'),dict) and _str(data['basis'].get('artifact_id'))):
        return {**common,'kind':'domain_state_description','role':'domain_state',
                'domain':_str(data.get('domain')),'native_shape':data['native_shape'],
                'canonical_roles':[x for x in data['canonical_roles'] if isinstance(x,str)][:80],
                'semantic_boundaries_count':len(data.get('semantic_boundaries',[])) if isinstance(data.get('semantic_boundaries'),list) else None,
                'content_coverage':'structural_description'}
    if (data.get('canonical_model')=='domain_native_payload' and isinstance(data.get('files'),list)
          and data.get('profile')=='kristal-domain-native-canonical-payload/1.0'):
        items=data['files']
        # Inlined source objects are canonical *within the registered payload*;
        # do not read their corresponding historic filesystem paths or write to them.
        if all(isinstance(item,dict) and _str(item.get('path')) and isinstance(item.get('content'),(dict,list)) for item in items):
            count=0
            embedded=[]
            for item in items:
                content=item['content']; a=content.get('assertions') if isinstance(content,dict) else None
                assertions=len(a) if isinstance(a,list) else None
                if assertions is not None:count+=assertions
                embedded.append({'embedded_path':item['path'],'top_level_keys':list(content)[:40] if isinstance(content,dict) else [],
                                 'embedded_assertion_rows':assertions})
            return {**common,'kind':'embedded_domain_native_payload','role':'domain_state',
                    'embedded_files':embedded[:50],
                    'embedded_file_count':len(items),'embedded_assertion_rows':count,
                    'content_coverage':'embedded_canonical_content'}
    # Distinct selected native models; recognize only manifest-bound contract families
    # and concrete format evidence. Not equivalent to a KQ/KP semantic graph.
    if (cid and cid.startswith('k.monetary.') and _str(data.get('id'))
            and _str(data.get('format')) and data['format'].startswith('k.monetary.')
            and entry.get('artifact_id')):
        return {**common,'kind':'monetary_design_contract','role':'native_domain_model',
                'native_format':data['format'],'content_coverage':'structured_native'}
    if (cid and cid.startswith('urn:kristal:contract:pitheory-prime-bridge:')
            and _str(data.get('format')) and data['format'].startswith('pitheory-prime-bridge.')
            and (_str(data.get('id')) or (cid.endswith(':epistemic:claim-ledger') and isinstance(data.get('claims'),list)))):
        return {**common,'kind':'research_model_contract','role':'native_domain_model',
                'native_format':data['format'],'content_coverage':'structured_native'}
    if (data.get('artifact_type')=='kristal_logical_artifact' and _str(data.get('artifact_id'))
            and isinstance(data.get('payload'),(dict,list))
            and isinstance(data.get('logical_contract'),dict)
            and data['logical_contract'].get('id')==cid
            and isinstance(data.get('logical_commitment'),dict)
            and _str(data['logical_commitment'].get('digest'))
            and cid and (cid.startswith('king-klown.') or cid.startswith('education-quebec.')
                         or cid in ('kristal.repository-resource-set','pi-theory.semantic-state'))):
        return {**common,'kind':'native_logical_artifact','role':'native_domain_model',
                'artifact_id':data['artifact_id'],
                'embedded_payload_fields':list(data['payload'])[:40] if isinstance(data['payload'],dict) else None,
                'embedded_payload_items':len(data['payload']) if isinstance(data['payload'],list) else None,
                'content_coverage':'structural_logical_payload'}
    if (cid and cid.startswith('kristal.catho.') and _str(data.get('schema_version'))):
        if data.get('artifact_type')=='semantic_corpus' and isinstance(data.get('assertions'),list):
            return {**common,'kind':'documentary_semantic_corpus','role':'native_domain_model',
                    'reported_assertion_rows':len(data['assertions']),
                    'content_coverage':'structured_native'}
        if (cid=='kristal.catho.personnes-reconnaissances' and isinstance(data.get('personnes'),list)) or (cid=='kristal.catho.wikidata-import' and isinstance(data.get('records'),list)) or (cid=='kristal.catho.wikidata-alignments' and isinstance(data.get('person_alignments'),(list,dict))) or (cid=='kristal.catho.semantic-links' and isinstance(data.get('counts'),dict)) or (cid=='kristal.catho.topics' and isinstance(data.get('counts'),dict)):
            return {**common,'kind':'documentary_research_register','role':'native_domain_model',
                    'content_coverage':'structured_native'}
    if (data.get('artifact_type')=='structured_epistemic_state'
            and cid in ('policeops.structured-epistemic-state','structured_epistemic_state')
            and _str(data.get('state_id')) and isinstance(data.get('assertions'),list)
            and _str(data.get('schema_version'))):
        return {**common,'kind':'structured_epistemic_state','role':'native_domain_model',
                'historical_state_id':data['state_id'],
                'reported_assertion_rows':len(data['assertions']),
                'content_coverage':'structured_native'}
    if (cid=='prime-numbers.kristall-v7-semantic-bundle' and
            isinstance(data.get('formal_core'),dict) and isinstance(data.get('subjects'),list)
            and isinstance(data.get('policies'),dict) and isinstance(data.get('registries'),dict)):
        return {**common,'kind':'formal_mathematical_bundle','role':'native_domain_model',
                'content_coverage':'structured_native'}
    return None


def _observed_canonical_script(rel, entry, reader):
    """Register a selected Pi-Bridge verification script without executing it.

    We require the canonical manifest's explicit sha256 commitment to match
    the exact bytes read. Mismatch is an issue, not a recognized artifact.
    """
    contract=entry.get('logical_contract') or {}
    cid=contract.get('id') if isinstance(contract,dict) else None
    digest=(entry.get('commitment') or {}).get('digest')
    if not (rel.startswith('canon/operations/') and rel.endswith('.py')
            and _str(cid) and cid.startswith('urn:kristal:contract:pitheory-prime-bridge:operation:')
            and isinstance(digest,str) and digest.startswith('sha256:')):
        return None
    blob=reader.blob(rel,True)
    if blob is None:return None
    if hashlib.sha256(blob).hexdigest()!=digest[7:]:
        reader.issues.append('Selected canonical script digest mismatch: '+rel)
        return None
    return {'path':rel,'contract_id':cid,'contract_version':contract.get('version'),
            'kind':'verified_research_script','role':'native_verification_source',
            'sha256':digest,'content_coverage':'code_reference_not_executed'}


def observe(registered, reader):
    """Return None if there is no recognized native content in selected artifacts.

    If unknown selected artifacts exist, coverage is explicitly *partial*, not
    an implicit successful validation. Every selected source remains bound by
    its canonical inventory path and Reader dependency digest.
    """
    if not registered:return None
    pieces=[];unknown=[];keys=Counter();branches=[];failed=[]
    for rel,entry in sorted(registered.items()):
        if not rel.endswith('.json'):
            script=_observed_canonical_script(rel,entry,reader)
            if script is not None:
                pieces.append(script)
            else:
                unknown.append(rel)
            continue
        obj=reader.obj(rel,True)
        if not obj:
            failed.append(rel);continue
        val=_contract_observation(rel,entry,obj)
        if val is None:
            unknown.append(rel)
            continue
        pieces.append(val)
        paths=[]
        _walk(obj,keys,paths)
        branches.append({'path':rel,'fields':paths[:MAX_FIELDS], 'top_level_keys':list(obj)[:40]})
    if not pieces:return None
    modes={p['kind'] for p in pieces}
    declared_only=all(p['content_coverage']!='embedded_canonical_content' for p in pieces)
    structured=any(p['content_coverage'] in ('structured_native','structural_logical_payload') for p in pieces)
    return {'format':VERSION,'mode':'native_embedded' if 'embedded_domain_native_payload' in modes else 'native_structured' if structured else 'native_reference',
            'coverage':'partial' if unknown or failed else ('embedded' if not declared_only else 'structured_native' if structured else 'references_and_descriptions'),
            'all_registered_artifacts_recognized':not (unknown or failed),
            'selected_artifacts':pieces,'unknown_registered_artifacts':unknown,
            'unreadable_registered_artifacts':failed,
            'registered_selected_count':len(registered),
            'observed_selected_count':len(pieces),
            'keys_observed':len(keys),
            'top_level_branches':branches[:MAX_BRANCHES],
            'embedded_assertion_rows':sum(p.get('embedded_assertion_rows',0) for p in pieces),
            'reported_legacy_assertion_count':sum(p.get('reported_assertion_count',0) for p in pieces),
            'reported_native_assertion_rows':sum(p.get('reported_assertion_rows',0) for p in pieces),
            'limits':['Reference digests do not expose source assertions or identities.',
                'An embedded or historical assertion row count does not establish a normalized graph, validated truth or distinct semantic assertions.',
                'Registered scripts are hashed and never executed; design simulations are not run.',
                'No diK/UNESCO/Arketype/Framework qualification, release, publication, activation or source rewrite.']}
