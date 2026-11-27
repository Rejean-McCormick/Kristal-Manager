"""V5.21.2 exact native adapters and approval-bound private registration rehearsal."""
from __future__ import annotations
import argparse, collections, json, os, sqlite3, tempfile, unicodedata, shutil, sys
from contextlib import closing
from pathlib import Path
from . import native_migration_v521 as v
from . import native_extension_v5211 as e
from .native_migration_v521 import must, guard, member, sha, digest, read, bytes_json, write, copy_bytes, uri, sid, literal, load_qualifier
from .native_extension_v5211 import ref_id, ref_labels, extended_literal, inventory, check_generation, review_packet, approval_template, approval_gate
BASE='SEMANTIC_V5211_66f477e821a9df6d'
EXPECTED_DB='c99f19d17c5dbad23cf55f0127559ccc67d691f5563401d441a0954d1c27c9fe'

def source_ref(row):
    if isinstance(row,str): return row
    must(isinstance(row,dict) and len(set(row)&{'id','source_id'})==1,'Ambiguous source ID')
    return row.get('source_id',row.get('id'))

def source_records(docs):
    rows=docs['state'].get('source_refs')
    if rows:
        must(isinstance(rows,list),'Invalid source refs')
        if 'source_catalog' in docs:
            cat=docs['source_catalog']['sources']
            ids=[source_ref(x) for x in cat]
            must(len(ids)==len(set(ids)) and set(map(source_ref,rows))<=set(ids),'Source catalog mismatch')
        return 'state','source_refs',rows
    must('source_catalog' in docs and isinstance(docs['source_catalog'].get('items'),list),'No explicit source catalog')
    return 'source_catalog','items',docs['source_catalog']['items']

def evidence_mapping(docs,sources):
    mapping={s:s for s in sources}
    if 'evidence_registry' in docs:
        reg=docs['evidence_registry'];must(reg['artifact_type']=='evidence_registry','Unexpected evidence registry')
        for row in reg['evidence']:
            key=row['evidence_id']; target=row['source_id']
            must(isinstance(key,str) and key and key not in mapping and target in sources,'Ambiguous or unresolved evidence ID')
            mapping[key]=target
    return mapping

def resolve_evidence(a,mapping):
    refs=a.get('evidence_refs',[])
    must(isinstance(refs,list) and all(isinstance(x,str) and x in mapping for x in refs),'Unknown evidence source')
    must(len(set(refs))==len(refs),'Duplicate evidence reference')
    if not refs:
        must(a['record_role']=='structural_record' and a['assertion_status']=='reviewed','Missing evidence outside reviewed structural record')
    return list(dict.fromkeys(mapping[x] for x in refs))

def build_candidate(w,slug,out,pin):
    w=guard(w); out=guard(out)
    must(not member(w,'.kristal/v11/authoring.json').exists(),'Already active')
    inputs=pin['paths']; raws={k:member(w,v).read_bytes() for k,v in inputs.items()}; hashes={k:sha(v) for k,v in raws.items()}
    must(hashes==pin['sha256'],'Native source changed since audited snapshot')
    reg,state,ws=[json.loads(raws[k]) for k in ('registry','state','workspace')]
    must(ws['slug']==slug and state['schema_version']=='6.0' and state['artifact_type']=='kristal_state','Native envelope mismatch')
    must(isinstance(reg.get('referents'),list) and reg['referents'],'Empty native registry')
    ns='kristal:native-v6:'+slug
    entries={}; refs={}; sources={}; bridge=[]; labels=collections.defaultdict(list); missing_preds=set(); assertions=[]; seen=collections.Counter(); previous_statements={}
    def alloc(kind,key,source,pointer,native_ref):
        ident=sid(ns,kind,key);must(ident not in entries,'Duplicate generated identity')
        entries[ident]={'id':ident,'kind':kind,'status':'provisional'}
        bridge.append({'semantic_id':ident,'kind':kind,'native_ref':native_ref,'source':source,'source_sha256':hashes[source],'json_pointer':pointer,'status':'CANDIDATE_EXACT_NATIVE_TRANSCRIPTION'})
        return ident
    for i,r in enumerate(reg['referents']):
        ref=ref_id(r);kind='property' if r.get('kind')=='predicate' else 'entity'
        must(kind and isinstance(ref,str) and ref and ref not in refs,'Invalid or duplicate native referent')
        ident=alloc(kind,ref,'registry',f'/referents/{i}',ref);refs[ref]=ident
        seen_lang=set()
        for j,(lang,term) in enumerate(ref_labels(r)):
            must(lang in ('fr','en') and lang not in seen_lang and isinstance(term,str) and term.strip() and unicodedata.is_normalized('NFC',term),'Unsupported or duplicate native label');seen_lang.add(lang)
            entry={'semantic_id':ident,'preferred_term':term,'review':{'decision_id':'v5212-transcription-'+sha(bytes_json([hashes['registry'],i,j]))[:24],'reviewer':'V5.21.2 deterministic transcription (candidate only)','reason':'Exact native label; not an editorial or publication approval.'}}
            if lang=='fr' and isinstance(r.get('definition_fr'),str):entry['definition']=r['definition_fr']
            labels[lang].append(entry)
    docs={k:json.loads(b) for k,b in raws.items()}
    extra_refs=docs.get('formal_schemata',{}).get('items',[])
    if extra_refs:
        must(slug=='logic' and docs['formal_schemata']['format']=='logic.formal-schemata.v1','Unexpected formal schema registry')
        for i,r in enumerate(extra_refs):
            ref=r['id'];must(isinstance(ref,str) and ref.startswith('logic:eq:') and ref not in refs,'Ambiguous formal schema ID')
            refs[ref]=alloc('entity',ref,'formal_schemata',f'/items/{i}',ref)
    source_key,source_field,source_rows=source_records(docs)
    for i,r in enumerate(source_rows):
        ref=source_ref(r);must(isinstance(ref,str) and ref and ref not in sources,'Invalid/duplicate source ID')
        sources[ref]=alloc('source',ref,source_key,f'/{source_field}/{i}',ref)
    evidence_map=evidence_mapping(docs,set(sources))
    for i,a in enumerate(state['assertions']):
        st=a['statement'];must(set(st)=={'subject','predicate','object'},'Unsupported statement/qualifier shape')
        must(a['assertion_status'] in ('reviewed','validated','sourced') and a['record_role'] in ('reference_knowledge','structural_record'),'Unsupported native epistemic status')
        sub=st['subject'];must(set(sub)=={'kind','id'},'Unsupported subject fields');must(sub['kind'] in ('item','referent') and refs.get(sub['id'],'').startswith('KQ'),'Unknown subject')
        pred=st['predicate'];must(isinstance(pred,str) and pred,'Invalid predicate')
        if pred not in refs:
            missing_preds.add(pred);refs[pred]=alloc('property',pred,'state',f'/assertions/{i}/statement/predicate',pred)
        must(refs[pred].startswith('KP'),'Predicate kind mismatch')
        o=st['object']
        if o['kind'] in ('item','referent'):
            must(set(o)=={'kind','id'},'Unsupported entity object fields');must(refs.get(o['id'],'').startswith('KQ'),'Unknown target');obj={'kind':'entity','id':refs[o['id']]}
        else:obj=extended_literal(o)
        ref=a['assertion_id'];must(isinstance(ref,str) and ref,'Empty native assertion id');seen[ref]+=1
        stmt_key=bytes_json(st)
        if ref in previous_statements:must(previous_statements[ref]==stmt_key,'Same native assertion id with different statement')
        previous_statements[ref]=stmt_key
        ident=alloc('assertion',[ref,seen[ref]],'state',f'/assertions/{i}',ref)
        evidence=resolve_evidence(a,evidence_map)
        assertions.append({'id':ident,'subject':refs[sub['id']],'predicate':refs[pred],'object':obj,'sources':[sources[x] for x in evidence]})
    must(len(assertions)==len(state['assertions']),'Assertion loss')
    envelope=lambda t: {'schema_version':'11.0','artifact_type':'kristal_'+t,'namespace_id':ns}
    registry={**envelope('identity_registry'),'registry_id':slug+'-native-v5212','identities':sorted(entries.values(),key=lambda x:x['id'])}
    graph={**envelope('semantic_graph'),'graph_id':slug+'-native-v5212','entities':sorted(x for x in entries if x.startswith('KQ')),'properties':sorted(x for x in entries if x.startswith('KP')),'sources':sorted(sources.values()),'assertions':assertions}
    cross={'schema_version':'11.0','artifact_type':'kristal_external_crosswalk','crosswalk_id':slug+'-native-v5212','mappings':[]}
    cat={**envelope('dictionary_catalog'),'catalog_id':slug+'-native-v5212','languages':[]}
    p=out/'canon/domain/v11'; p.mkdir(parents=True,exist_ok=False)
    for name,obj in [('registry',registry),('graph',graph),('crosswalk',cross)]:write(p/(name+'.json'),obj)
    for lang,rows in sorted(labels.items()):
        layer=p/'dictionaries'/f'native-{lang}.json';write(layer,{**envelope('curated_dictionary'),'language':lang,'entries':sorted(rows,key=lambda x:x['semantic_id'])})
        cat['languages'].append({'tag':lang,'fallbacks':[],'layers':[{'layer_id':'native-'+lang,'kind':'curated','priority':100,'path':layer.name,'sha256':digest(layer)}]})
    write(p/'dictionaries/catalog.json',cat)
    paths={'registry':'canon/domain/v11/registry.json','graph':'canon/domain/v11/graph.json','crosswalk':'canon/domain/v11/crosswalk.json','catalog':'canon/domain/v11/dictionaries/catalog.json'}
    # Synthetic staging registration, ONLY for running the Kit/Framework validators.
    # Not a real workspace, not a valid release, never copied back automatically.
    write(out/'canon/state.index.json',{'canonical_artifacts':[{'path':v} for v in paths.values()]})
    config={'format':'kristal.authoring-v11-profile/1.0','semantic_profile':'kristal.semantic-identity/11.0',**paths}
    write(out/'.kristal/v11/authoring.json',config)
    for key,b in raws.items():copy_bytes(out/'native-originals'/(key+'.json'),b)
    write(out/'bridge.json',{'format':'koa.kristal-native-bridge/1.0','slug':slug,'namespace_id':ns,'status':'UNAPPROVED_CANDIDATE','source_paths':inputs,'source_sha256':hashes,'entries':bridge,'duplicate_native_assertion_ids':{x:n for x,n in seen.items() if n>1},'implicit_predicates':sorted(missing_preds),'preservation':'Original bytes retained. Native status, applicability, provenance, notes and extensions are not represented by the V11 graph alone; consult originals using bridge pointers.'})
    verify_bridge(out)
    return {'slug':slug,'namespace_id':ns,'native_referents':len(reg['referents']),'implicit_predicates':len(missing_preds),'assertion_occurrences':len(assertions),'duplicate_assertion_ids':sum(n>1 for n in seen.values()),'sources':len(sources),'identities':len(entries),'labels':sum(map(len,labels.values())),'source_sha256':hashes,'candidate_files':{v:digest(out/v) for v in paths.values()},'status':'CANDIDATE_PENDING_EDITORIAL_QUALIFICATION','structural_without_evidence':sum(not a.get('evidence_refs') for a in state['assertions']),'formal_schema_entities':len(extra_refs)}

def verify_bridge(out):
    """Independently resolve every pointer to its preserved original; verify graph round-trip."""
    b=read(out/'bridge.json'); docs={}
    for key,expected in b['source_sha256'].items():
        p=out/'native-originals'/(key+'.json');must(digest(p)==expected,'Original source hash mismatch');docs[key]=read(p)
    v=out/'canon/domain/v11'; r=read(v/'registry.json'); g=read(v/'graph.json'); c=read(v/'crosswalk.json')
    must(not c['mappings'],'Unexpected external mappings')
    by_id={x['id']:x for x in r['identities']}; mapped={}; positions={}; lookup={}
    for row in b['entries']:
        id=row['semantic_id'];kind=row['kind'];must(id in by_id and by_id[id]['kind']==kind and by_id[id]['status']=='provisional' and id not in mapped,'Bridge identity mismatch')
        doc=docs[row['source']];ptr=row['json_pointer'];must(row['source_sha256']==b['source_sha256'][row['source']],'Bridge source hash mismatch')
        for part in ptr.split('/')[1:]:doc=doc[int(part)] if isinstance(doc,list) else doc[part]
        ref=source_ref(doc) if kind=='source' else doc['assertion_id'] if kind=='assertion' else doc if isinstance(doc,str) else ref_id(doc)
        must(ref==row['native_ref'],'Bridge native reference mismatch');mapped[id]=doc;positions[id]=ptr
        if kind!='assertion':must((kind,ref) not in lookup,'Duplicate native reference');lookup[kind,ref]=id
    must(set(mapped)==set(by_id),'Bridge identity coverage mismatch')
    must(all(('entity',r['id']) in lookup for r in docs.get('formal_schemata',{}).get('items',[])),'Formal schema coverage mismatch')
    source_key,source_field,source_rows=source_records(docs)
    must({source_ref(x) for x in source_rows}=={ref for kind,ref in lookup if kind=='source'},'Source coverage mismatch')
    evidence_map=evidence_mapping(docs,{ref for kind,ref in lookup if kind=='source'})
    native=docs['state']['assertions'];must(len(native)==len(g['assertions']),'Assertion count mismatch')
    seen=set()
    for a in g['assertions']:
        old=mapped[a['id']];ptr=positions[a['id']];must(ptr not in seen,'Duplicate assertion occurrence');seen.add(ptr)
        s=old['statement'];o=s['object'];expected={'kind':'entity','id':lookup['entity',o['id']]} if o['kind'] in ('item','referent') else extended_literal(o)
        must(a['subject']==lookup['entity',s['subject']['id']] and a['predicate']==lookup['property',s['predicate']] and a['object']==expected and a['sources']==[lookup['source',x] for x in resolve_evidence(old,evidence_map)],'Graph round-trip mismatch')
    must(seen=={f'/assertions/{i}' for i in range(len(native))},'Occurrence coverage mismatch')
    expected_labels={(lookup['property' if r.get('kind')=='predicate' else 'entity',ref_id(r)],lang):term for r in docs['registry']['referents'] for lang,term in ref_labels(r)}
    actual={}
    for loc in read(v/'dictionaries/catalog.json')['languages']:
        for layer in loc['layers']:
            p=member(v/'dictionaries',layer['path']);must(digest(p)==layer['sha256'],'Layer hash mismatch')
            for row in read(p)['entries']:
                key=(row['semantic_id'],loc['tag']);must(key not in actual,'Duplicate lexical cell');actual[key]=row['preferred_term']
    must(actual==expected_labels,'Native lexical round-trip mismatch')
    return True




ROLE_CONTRACTS={'registry':'kristal.v11.identity-registry','graph':'kristal.v11.semantic-graph','crosswalk':'kristal.v11.external-crosswalk','catalog':'kristal.v11.dictionary-catalog'}

def exact_predicate_observations(root,w,packet):
    """Owner-scoped explicit predicate records only, never infer labels from IDs."""
    bridge=read(root/'bridge.json'); state=read(root/'native-originals/state.json')
    wanted=set(bridge['implicit_predicates']); matches=collections.defaultdict(list)
    for folder in ('knowledge-base/corpus','knowledge-base/sources'):
        folder=member(w,folder)
        if not folder.is_dir():continue
        for f in sorted(folder.glob('*.json')):
            try: d=read(f)
            except (ValueError,UnicodeError):continue
            if not isinstance(d,dict):continue
            for field in ('referents','predicates','properties'):
                rows=d.get(field)
                if not isinstance(rows,list):continue
                for i,row in enumerate(rows):
                    if not isinstance(row,dict):continue
                    keys=set(row)&{'id','ref','referent_id'}
                    if len(keys)!=1:continue
                    ref=row[next(iter(keys))]
                    if not isinstance(ref,str) or ref not in wanted:continue
                    if row.get('kind') not in ('predicate','property') and field not in ('predicates','properties'):continue
                    if 'labels' not in row and 'label_fr' not in row:continue
                    if 'label' in row and 'labels' not in row:continue
                    try: labels=ref_labels(row)
                    except (ValueError,KeyError,TypeError):continue
                    for lang,term in labels:
                        if lang in ('fr','en') and isinstance(term,str) and term.strip() and unicodedata.is_normalized('NFC',term):
                            matches[ref].append({'language':lang,'term':term,'path':f.relative_to(w).as_posix(),'sha256':digest(f),'pointer':f'/{field}/{i}'})
    occurrences=collections.Counter(a['statement']['predicate'] for a in state['assertions'] if isinstance(a.get('statement',{}).get('predicate'),str))
    return [{'native_ref':b['native_ref'],'semantic_id':b['semantic_id'],'source_sha256':b['source_sha256'],'first_pointer':b['json_pointer'],'occurrences':occurrences[b['native_ref']],'observations':matches[b['native_ref']],'status':'EXPLICIT_LABEL_OBSERVATION_REVIEW_REQUIRED' if matches[b['native_ref']] else 'NO_EXPLICIT_LABEL_FOUND'} for b in bridge['entries'] if b['kind']=='property' and b['native_ref'] in wanted]

def registration_plan(root,w,result,packet):
    """Exact bytes, private plan only; no claim of editorial authority."""
    cfg=read(root/'.kristal/v11/authoring.json'); inv=inventory(root)
    must(inv==packet['candidate_inventory'],'Candidate inventory changed')
    must(not member(w,'.kristal/v11/authoring.json').exists(),'Existing authoring profile')
    original=read(root/'bridge.json');must(all(digest(member(w,p))==original['source_sha256'][k] for k,p in original['source_paths'].items()),'Original source drift')
    token=sha(bytes_json([result['namespace_id'],inv]))[:24]
    prefix='canon/domain/v11/updates/native-v5212-'+token+'/'
    paths={role:prefix+cfg[role].split('canon/domain/v11/',1)[1] for role in ROLE_CONTRACTS}
    artifacts=[{'role':role,'source':cfg[role],'target':paths[role],'sha256':inv[cfg[role]],'contract_id':contract,'artifact_id':'urn:kristal:'+result['slug']+':v5212:'+token+':'+role} for role,contract in ROLE_CONTRACTS.items()]
    layers=[]
    for loc in read(root/cfg['catalog'])['languages']:
        for l in loc['layers']:
            rel=(Path(cfg['catalog']).parent/l['path']).as_posix();target=(Path(paths['catalog']).parent/l['path']).as_posix();must(inv[rel]==l['sha256'],'Layer digest mismatch');layers.append({'source':rel,'target':target,'sha256':l['sha256']})
    return {'format':'koa.kristal-native-registration-plan/1.0','slug':result['slug'],'namespace_id':result['namespace_id'],'packet_sha256':sha(bytes_json(packet)),'candidate_inventory':inv,'state_index_sha256':digest(w/'canon/state.index.json'),'source_paths':original['source_paths'],'source_sha256':original['source_sha256'],'artifacts':artifacts,'layers':layers,'profile':{**cfg,**paths},'activation_authorized':False,'requires_independent_editorial_approval':True,'requires_epistemic_reader_contract':True,'status':'PRIVATE_REHEARSAL_ONLY'}

def rehearsal(root,w,plan,kit,framework,q,private):
    """Exercise the real recoverable registrar on an isolated state-index copy.
    Never run against the live workspace. Existing artifact bytes are not staged.
    """
    sys.path.insert(0,str(kit/'tools'));import kristal_v11_core as core
    must(inventory(root)==plan['candidate_inventory'],'Candidate drift before rehearsal')
    must(digest(w/'canon/state.index.json')==plan['state_index_sha256'],'Live state drift')
    with tempfile.TemporaryDirectory(prefix='v5212-rehearsal-',dir=private) as td:
        stage=Path(td);orig=(w/'canon/state.index.json').read_bytes();copy_bytes(stage/'canon/state.index.json',orig);before=json.loads(orig)
        for l in plan['layers']:
            data=member(root,l['source']).read_bytes();must(sha(data)==l['sha256'],'Layer changed');copy_bytes(member(stage,l['target']),data)
        for a in plan['artifacts']:
            data=member(root,a['source']).read_bytes();must(sha(data)==a['sha256'],'Artifact changed');core.register_artifact_recoverably(stage,rel=a['target'],payload=data,artifact_id=a['artifact_id'],contract_id=a['contract_id'])
        after=read(stage/'canon/state.index.json');old=before.get('canonical_artifacts',[]);must(after['canonical_artifacts'][:len(old)]==old and len(after['canonical_artifacts'])==len(old)+4,'Existing state entries changed')
        must({k:x for k,x in before.items() if k!='canonical_artifacts'}=={k:x for k,x in after.items() if k!='canonical_artifacts'},'Other state index fields changed')
        write(stage/'.kristal/v11/authoring.json',plan['profile']);qr=q.qualify(stage,framework)
        must(qr['valid'] and qr['reference_coverage_match'],'Rehearsed profile qualification failed')
        must(digest(w/'canon/state.index.json')==plan['state_index_sha256'],'Live workspace drift during rehearsal')
        return {'status':'ISOLATED_REGISTRATION_REHEARSED','registrations':4,'old_entries_preserved':len(old),'profile_valid':True,'framework_version':qr['framework_version'],'production_activation':False,'existing_artifact_bytes_not_revalidated':True}

def check_bound_approval(packet,plan,approval):
    approval_gate(packet,approval)
    must(plan['slug']==packet['slug'] and plan['packet_sha256']==sha(bytes_json(packet)) and plan['candidate_inventory']==packet['candidate_inventory'],'Plan not bound to packet')
    must(approval.get('registration_plan_sha256')==sha(bytes_json(plan)),'Approval not bound to registration plan')
    must(approval.get('epistemic_reader_contract_verified') is True,'Reader contract declaration missing')
    return 'DECLARATION_COMPLETE_NO_PRODUCTION_ACTIVATION'

def run(locals_root,private,kit,framework):
    locals_root,private,kit,framework=map(guard,(locals_root,private,kit,framework))
    must(not any(private==p or private in p.parents or p in private.parents for p in (locals_root,kit,framework,locals_root.parent/'kristal-public')),'Private path must be disjoint')
    src=member(private,BASE); report=check_generation(src)
    must(report['status']=='EXTENSION_QUALIFIED_EDITORIAL_REVIEW_PENDING' and report['database_sha256']==EXPECTED_DB,'Unexpected V5.21.1 baseline')
    first=member(private,e.BASE); initial=e.check_generation(first)
    must(initial['database_sha256']==e.EXPECTED_DB and report['source_database_sha256']==e.EXPECTED_DB,'Unexpected V5.21 ancestor')
    q=load_qualifier(kit,framework);pins=read(Path(__file__).with_name('native_extension_v5212_pins.json'))
    with closing(sqlite3.connect(uri(src/'active.sqlite'),uri=True)) as db:
        must(db.execute('PRAGMA integrity_check').fetchone()==('ok',) and not db.execute('PRAGMA foreign_key_check').fetchone(),'Baseline DB invalid')
        rows=db.execute('SELECT slug,local_directory,state_sha256 FROM workspace WHERE active=0 ORDER BY slug').fetchall();must(len(rows)==50,'Unexpected inactive scope')
        old={x[0]:json.loads(x[1]) for x in db.execute('SELECT slug,report_json FROM v521_native_candidate UNION ALL SELECT slug,report_json FROM v5211_native_candidate')}
        must(old=={x['slug']:x for x in initial['candidates']+report['candidates']},'Prior candidate SQL mismatch')
        reviews={x[0]:x[1] for x in db.execute('SELECT slug,packet_sha256 FROM v5211_editorial_review')}
        must(reviews=={x['slug']:x['packet_sha256'] for x in report['editorial_reviews']},'Prior review SQL mismatch')
        namespaces={x[0] for x in db.execute('SELECT namespace_id FROM workspace WHERE namespace_id IS NOT NULL')}
    workspace={s:member(locals_root,d) for s,d,h in rows}
    def preflight():
        for s,d,h in rows:
            w=workspace[s];must(digest(member(w,'canon/state.index.json'))==h and not member(w,'.kristal/v11/authoring.json').exists(),f'Inactive workspace drift: {s}')
    preflight()
    with tempfile.TemporaryDirectory(prefix='v5212-stage-',dir=private) as td:
        stage=Path(td);(stage/'candidates').mkdir();new=[];all_results=[];plans=[];preds=[];diagnostics=[]
        oldroots={r['slug']:first/'candidates'/r['slug'] for r in initial['candidates']};oldroots.update({r['slug']:src/'candidates'/r['slug'] for r in report['candidates']})
        for slug,r in sorted(old.items()):
            root=oldroots[slug];packet=read(src/'editorial'/f'{slug}.json');must(digest(src/'editorial'/f'{slug}.json')==reviews[slug] and inventory(root)==packet['candidate_inventory'],'Prior packet/candidate drift')
            must((v.verify_bridge(root) if slug in {x['slug'] for x in initial['candidates']} else e.verify_bridge(root)),'Prior bridge invalid')
            must(q.qualify(root,framework)['valid'],'Prior candidate validation failed');all_results.append((r,root,packet,'prior'))
            must(r['namespace_id'] not in namespaces,'Namespace collision');namespaces.add(r['namespace_id'])
        for a in report['audit']:
            slug=a['slug']
            if slug in old:continue
            w=workspace[slug];audit=e.corpus_audit(w,a);must(audit['files']==a['files'],f'Corpus drift: {slug}')
            if slug not in pins:
                audit['status']=a['status'];audit['reason']=a.get('reason','No reviewed adapter for this format')
                if slug=='aging':
                    f=next(x for x in audit['files'] if x.get('artifact_type')=='kristal_state');st=read(member(w,f['path']));audit['literal_anomalies']=[{'assertion_id':x['assertion_id'],'pointer':f'/assertions/{i}/statement/object','declared_kind':x['statement']['object']['kind'],'actual_type':'array','value':x['statement']['object']['value'],'source_sha256':f['sha256']} for i,x in enumerate(st['assertions']) if isinstance(x['statement']['object'].get('value'),list)]
                diagnostics.append(audit);continue
            print('V5.21.2 candidate:',slug,flush=True);root=stage/'candidates'/slug
            try:
                r=build_candidate(w,slug,root,pins[slug]);must(r['namespace_id'] not in namespaces,'Namespace collision');qr=q.qualify(root,framework);must(qr['valid'] and qr['reference_coverage_match'],'Framework qualification failed')
                r['technical_qualification']={k:qr[k] for k in ('valid','framework_version','reference_coverage_match','graph_sha256','catalog_sha256')}
                packet=review_packet(root,r);packet['additional_native_source_files']=sorted(set(r['source_sha256'])-{'index','registry','state','state_index','workspace'});packet['structural_without_evidence']=r['structural_without_evidence'];packet['formal_schema_entities_without_declared_label_language']=r['formal_schema_entities'];packet['required_attestations']+=['source_resolution_reviewed','unlabelled_formal_schema_entities_reviewed','structural_records_without_evidence_reviewed']
                new.append(r);all_results.append((r,root,packet,'V5.21.2'));namespaces.add(r['namespace_id']);audit['status']='CANDIDATE_TECHNICALLY_QUALIFIED'
            except (ValueError,KeyError,TypeError) as exc:
                if root.exists():shutil.rmtree(root)
                audit['status']='BLOCKED_NATIVE_ADAPTER';audit['reason']=str(exc)
            diagnostics.append(audit)
        must(len(diagnostics)==report['remaining_count'],'Pending scope mismatch')
        for r,root,packet,origin in all_results:
            slug=r['slug'];w=workspace[slug];print('V5.21.2 registration rehearsal:',slug,flush=True)
            observations=exact_predicate_observations(root,w,packet)
            plan=registration_plan(root,w,r,packet);plan['predicate_review_sha256']=sha(bytes_json(observations));rr=rehearsal(root,w,plan,kit,framework,q,private)
            preds.extend({'slug':slug,**x} for x in observations)
            write(stage/'editorial'/f'{slug}.json',packet);write(stage/'registration-plans'/f'{slug}.json',plan)
            approval=approval_template(packet);approval.update(registration_plan_sha256=sha(bytes_json(plan)),epistemic_reader_contract_verified=False);write(stage/'approval-templates'/f'{slug}.json',approval)
            write(stage/'predicate-review'/f'{slug}.json',observations)
            plans.append({'slug':slug,'origin':origin,'packet_sha256':sha(bytes_json(packet)),'plan_sha256':sha(bytes_json(plan)),**rr})
        preflight();must(check_generation(src)==report and check_generation(first)==initial,'Prior generation drift')
        for r,root,packet,origin in all_results:
            b=read(root/'bridge.json');must(all(digest(member(workspace[r['slug']],p))==b['source_sha256'][k] for k,p in b['source_paths'].items()),'Source drift before publication')
            must(exact_predicate_observations(root,workspace[r['slug']],packet)==read(stage/'predicate-review'/f"{r['slug']}.json"),'Predicate review drift')
        for a in diagnostics:must(e.corpus_audit(workspace[a['slug']],a)['files']==a['files'],'Corpus drift before publication')
        dbout=stage/'active.sqlite'
        with closing(sqlite3.connect(uri(src/'active.sqlite'),uri=True)) as inp,closing(sqlite3.connect(dbout)) as db:
            inp.backup(db)
            with db:
                db.execute('CREATE TABLE v5212_native_candidate (slug TEXT PRIMARY KEY, namespace_id TEXT UNIQUE NOT NULL, report_json TEXT NOT NULL)')
                db.execute('CREATE TABLE v5212_candidate_identity (namespace_id TEXT NOT NULL, semantic_id TEXT NOT NULL, slug TEXT NOT NULL, kind TEXT NOT NULL, native_ref TEXT NOT NULL, json_pointer TEXT NOT NULL, source_sha256 TEXT NOT NULL, PRIMARY KEY(namespace_id,semantic_id))')
                db.execute('CREATE TABLE v5212_candidate_lexical (namespace_id TEXT NOT NULL, semantic_id TEXT NOT NULL, language_tag TEXT NOT NULL, preferred_term TEXT NOT NULL, PRIMARY KEY(namespace_id,semantic_id,language_tag), FOREIGN KEY(namespace_id,semantic_id) REFERENCES v5212_candidate_identity(namespace_id,semantic_id))')
                db.execute('CREATE TABLE v5212_registration_plan (slug TEXT PRIMARY KEY, report_json TEXT NOT NULL)')
                db.execute('CREATE TABLE v5212_predicate_review (slug TEXT NOT NULL, semantic_id TEXT NOT NULL, report_json TEXT NOT NULL, PRIMARY KEY(slug,semantic_id))')
                db.execute('CREATE TABLE v5212_native_audit (slug TEXT PRIMARY KEY, report_json TEXT NOT NULL)')
                for r in new:
                    root=stage/'candidates'/r['slug'];ns=r['namespace_id'];b=read(root/'bridge.json');db.execute('INSERT INTO v5212_native_candidate VALUES (?,?,?)',(r['slug'],ns,json.dumps(r,ensure_ascii=False,sort_keys=True)))
                    db.executemany('INSERT INTO v5212_candidate_identity VALUES (?,?,?,?,?,?,?)',[(ns,x['semantic_id'],r['slug'],x['kind'],x['native_ref'],x['json_pointer'],x['source_sha256']) for x in b['entries']])
                    for loc in read(root/'canon/domain/v11/dictionaries/catalog.json')['languages']:
                        for layer in loc['layers']:
                            d=read(member(root/'canon/domain/v11/dictionaries',layer['path']));db.executemany('INSERT INTO v5212_candidate_lexical VALUES (?,?,?,?)',[(ns,x['semantic_id'],loc['tag'],x['preferred_term']) for x in d['entries']])
                db.executemany('INSERT INTO v5212_registration_plan VALUES (?,?)',[(x['slug'],json.dumps(x,ensure_ascii=False,sort_keys=True)) for x in plans]);db.executemany('INSERT INTO v5212_predicate_review VALUES (?,?,?)',[(x['slug'],x['semantic_id'],json.dumps(x,ensure_ascii=False,sort_keys=True)) for x in preds]);db.executemany('INSERT INTO v5212_native_audit VALUES (?,?)',[(x['slug'],json.dumps(x,ensure_ascii=False,sort_keys=True)) for x in diagnostics])
            must(db.execute('PRAGMA integrity_check').fetchone()==('ok',) and not db.execute('PRAGMA foreign_key_check').fetchone(),'Result DB invalid')
            counts={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('identity','lexical','candidate_wikidata')};must(counts==report['active_counts'],'Active counts changed')
        dest=member(private,'SEMANTIC_V5212_'+sha(bytes_json(['5.21.2',EXPECTED_DB,new,plans,preds,diagnostics]))[:16]);keys=('native_referents','implicit_predicates','assertion_occurrences','duplicate_assertion_ids','sources','identities','labels')
        result={'format':'koa.kristal-native-extension/1.1','status':'EXTENSION_AND_REGISTRATION_REHEARSAL_COMPLETE_EDITORIAL_PENDING','source_database_sha256':EXPECTED_DB,'database':str(dest/'active.sqlite'),'database_sha256':digest(dbout),'prior_generation':str(src),'new_candidates':new,'counts':{k:sum(r[k] for r in new) for k in keys},'cumulative_counts':{k:sum(r[k] for r,_,_,_ in all_results) for k in keys},'new_candidate_count':len(new),'cumulative_candidate_count':len(all_results),'remaining_count':50-len(all_results),'active_counts':counts,'registration_plans':plans,'predicate_review_counts':dict(collections.Counter(x['status'] for x in preds)),'audit':diagnostics,'policy':{'canonical_modified':False,'profiles_activated':0,'public_modified':False,'network_used':False,'production_activation_implemented':False,'independent_editorial_approval_required':True,'epistemic_reader_contract_required':True}}
        write(stage/'report.json',result);write(stage/'manifest.sha256.json',inventory(stage))
        if dest.exists():
            prev=check_generation(dest);must(prev==result,'Existing generation differs');return prev
        publish=stage/'publish';publish.mkdir()
        for p in list(stage.iterdir()):
            if p!=publish:os.replace(p,publish/p.name)
        os.rename(publish,dest);return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('locals','private-dir','kit','framework'):p.add_argument('--'+k,type=Path)
    p.add_argument('--apply',action='store_true');p.add_argument('--check-approval',nargs=3,type=Path,metavar=('PACKET','PLAN','APPROVAL'));a=p.parse_args()
    if a.check_approval:
        must(not a.apply,'Approval check cannot apply');print(check_bound_approval(*(read(x) for x in a.check_approval)));return
    must(a.apply and all((a.locals,a.private_dir,a.kit,a.framework)),'--apply and four paths required (private output only)')
    r=run(a.locals,a.private_dir,a.kit,a.framework);print(json.dumps(r,ensure_ascii=True,indent=2));print('V5.21.2 ONE-SHOT:',r['status'])
if __name__=='__main__':main()
