"""V5.21.3: private, exact occurrence projections of specialized scalar corpora."""
from __future__ import annotations
import argparse, collections, json, math, os, shutil, sqlite3, tempfile, unicodedata
from contextlib import closing
from pathlib import Path
from . import native_migration_v521 as v
from . import native_extension_v5211 as e
from . import native_extension_v5212 as n
from .native_migration_v521 import must, guard, member, sha, digest, read, bytes_json, write, copy_bytes, uri, sid, load_qualifier
BASE='SEMANTIC_V5212_10a72c5c1be46d87'
EXPECTED_DB='4fac4a3ba001e1029c15e2c103d1a88ecfbfdf494fc2cb5e4b85aa42847e768b'
INSTITUTIONAL={'droit-international-global','pouvoirs-australie','pouvoirs-canada-quebec','pouvoirs-coree-du-sud','pouvoirs-finlande','pouvoirs-france','pouvoirs-japon','pouvoirs-pays-bas'}
SUPPORTED=INSTITUTIONAL|{'koa-ecosystem','mechanicalengineering','time','catho'}

def scalar(o,allowed):
    k=o['kind'];must(k in allowed and set(o)<= {'kind','value','language'},'Unsupported scalar envelope')
    val=o['value']; dt={str:'string',bool:'boolean',int:'integer',float:'number'}.get(type(val));must(dt is not None and (type(val)!=float or math.isfinite(val)),'Unsupported structured/nonfinite literal')
    must(k not in ('string','proposition') or dt=='string','Expected textual proposition/string');must(k!='boolean' or dt=='boolean','Expected boolean')
    x={'kind':'literal','datatype':dt,'value':val}
    if 'language' in o:
        must(dt=='string' and isinstance(o['language'],str),'Language on non-text');x['language']=o['language']
    return x

def build(w,slug,out,audit):
    must(slug in SUPPORTED,'No reviewed adapter');w=guard(w);out=guard(out)
    must(not member(w,'.kristal/v11/authoring.json').exists(),'Already active')
    files=[f for f in audit['files'] if f.get('artifact_type') in ('kristal_state','semantic_corpus')];must(len(files)==1,'Ambiguous native state')
    sf=files[0];paths={'state':sf['path'],'workspace':'kristal.workspace.json','state_index':'canon/state.index.json'}
    raws={k:member(w,p).read_bytes() for k,p in paths.items()}; hashes={k:sha(b) for k,b in raws.items()};must(hashes['state']==sf['sha256'],'State drift')
    s=json.loads(raws['state']);must(json.loads(raws['workspace'])['slug']==slug,'Owner mismatch')
    must((s['schema_version'],s['artifact_type'])==(('1.0','semantic_corpus') if slug=='catho' else ('6.0','kristal_state')),'Wrong envelope')
    ns='kristal:native-v6:'+slug if slug!='catho' else 'kristal:native-corpus-v1:catho'
    entries={};lookup={};bridge=[];labels={};observed=collections.defaultdict(set);assertions=[];refs={};seen=collections.Counter();missing=0;qualifiers=0;propositions=0
    def alloc(kind,ref,ptr,occ=None):
        must(isinstance(ref,str) and ref.strip(),'Invalid native ID')
        key=(kind,ref) if occ is None else (kind,ref,occ)
        if key in lookup:return lookup[key]
        ident=sid(ns,kind,ref if occ is None else [ref,occ]);must(ident not in entries,'Generated ID collision');lookup[key]=ident
        entries[ident]={'id':ident,'kind':kind,'status':'provisional'}
        bridge.append({'semantic_id':ident,'kind':kind,'native_ref':ref,'source':'state','source_sha256':hashes['state'],'json_pointer':ptr,'status':'CANDIDATE_EXACT_NATIVE_OCCURRENCE'})
        return ident
    source_rows=s['source_refs'];source_docs={}
    for i,row in enumerate(source_rows):
        ref=n.source_ref(row);must(ref not in source_docs,'Duplicate native source');source_docs[ref]=row;refs[ref]=alloc('source',ref,f'/source_refs/{i}')
    def embedded(kind,row,ptr):
        must(isinstance(row,dict) and set(row)=={'external_id','label'} and isinstance(row['label'],str),'Unsupported embedded reference')
        ident=alloc(kind,row['external_id'],ptr);observed[ident].add(row['label']);return ident
    def object_value(o,ptr):
        if slug=='catho':
            if o['kind']=='item':
                must(set(o)=={'kind','value'},'Unsupported embedded object');return {'kind':'entity','id':embedded('entity',o['value'],ptr+'/value')}
            return scalar(o,{'string'})
        if o['kind']=='item':
            must(set(o)=={'kind','id'} and slug in ('time','koa-ecosystem'),'Unsupported entity object');return {'kind':'entity','id':alloc('entity',o['id'],ptr)}
        allowed={'proposition'} if slug in INSTITUTIONAL else {'string','boolean'} if slug=='koa-ecosystem' else {'value'}
        return scalar(o,allowed)
    for i,a in enumerate(s['assertions']):
        ptr=f'/assertions/{i}';st=a['statement'];ref=a['assertion_id'];seen[ref]+=1;must(seen[ref]==1,'Repeated assertion ID requires separate reviewed adapter')
        must(a['assertion_status'] in ('sourced','claimed','reviewed'),'Unsupported status')
        if slug=='catho':
            must(set(st)=={'subject','predicate','object','qualifiers'},'Unsupported corpus statement')
            sub=embedded('entity',st['subject'],ptr+'/statement/subject');pred=embedded('property',st['predicate'],ptr+'/statement/predicate')
        else:
            must(set(st)=={'subject','predicate','object'},'Unsupported native statement');su=st['subject'];must(set(su)=={'kind','id'},'Unsupported subject')
            expected='international_law_entity' if slug=='droit-international-global' else 'actor_or_norm' if slug in INSTITUTIONAL else 'item';must(su['kind']==expected,'Unexpected subject kind')
            sub=alloc('entity',su['id'],ptr+'/statement/subject');pred=alloc('property',st['predicate'],ptr+'/statement/predicate')
        obj=object_value(st['object'],ptr+'/statement/object');propositions+=st['object']['kind']=='proposition'
        evidence=[]
        for ev in a.get('evidence_refs',[]):
            if slug=='catho':
                must(isinstance(ev,dict) and ev['evidence_status']=='provided','Unprovided evidence');sr=ev['source_ref'];key=sr['source_id'];must(source_docs.get(key)==sr,'Embedded source differs from declared source')
            else:key=ev
            must(isinstance(key,str) and key in refs,'Unresolved native evidence');evidence.append(refs[key])
        if not evidence:
            must(slug=='pouvoirs-japon' and a['assertion_status']=='reviewed' and a['record_role']=='organizational_rule','Missing native evidence');missing+=1
        ident=alloc('assertion',ref,ptr,1);g={'id':ident,'subject':sub,'predicate':pred,'object':obj,'sources':list(dict.fromkeys(evidence))}
        if slug=='catho':
            g['qualifiers']=[]
            for j,z in enumerate(st['qualifiers']):
                must(set(z)=={'predicate','object'},'Unsupported qualifier');zp=ptr+f'/statement/qualifiers/{j}';g['qualifiers'].append({'predicate':embedded('property',z['predicate'],zp+'/predicate'),'object':object_value(z['object'],zp+'/object')});qualifiers+=1
        if slug in ('time','mechanicalengineering') and st['predicate']==('time.label_fr' if slug=='time' else 'mechanical_engineering.label_fr'):
            term=st['object']['value'];must(isinstance(term,str) and term.strip() and unicodedata.is_normalized('NFC',term),'Invalid explicit French label');must(sub not in labels or labels[sub]['preferred_term']==term,'Conflicting native French label');labels[sub]={'semantic_id':sub,'preferred_term':term,'review':{'decision_id':'v5213-transcription-'+sha(bytes_json([hashes['state'],i]))[:24],'reviewer':'V5.21.3 deterministic transcription (candidate only)','reason':'Explicit native label_fr assertion; not independent editorial approval.'}}
        if slug=='koa-ecosystem' and st['predicate']=='rdfs:label':observed[sub].add(st['object']['value'])
        assertions.append(g)
    envelope=lambda k:{'schema_version':'11.0','artifact_type':'kristal_'+k,'namespace_id':ns}
    base=out/'canon/domain/v11';base.mkdir(parents=True,exist_ok=False)
    registry={**envelope('identity_registry'),'registry_id':slug+'-native-v5213','identities':sorted(entries.values(),key=lambda x:x['id'])}
    graph={**envelope('semantic_graph'),'graph_id':slug+'-native-v5213','entities':sorted(x for x in entries if x.startswith('KQ')),'properties':sorted(x for x in entries if x.startswith('KP')),'sources':sorted(refs.values()),'assertions':assertions}
    cross={'schema_version':'11.0','artifact_type':'kristal_external_crosswalk','crosswalk_id':slug+'-native-v5213','mappings':[]};cat={**envelope('dictionary_catalog'),'catalog_id':slug+'-native-v5213','languages':[]}
    for name,obj in [('registry',registry),('graph',graph),('crosswalk',cross)]:write(base/(name+'.json'),obj)
    if labels:
        layer=base/'dictionaries/native-fr.json';write(layer,{**envelope('curated_dictionary'),'language':'fr','entries':sorted(labels.values(),key=lambda x:x['semantic_id'])});cat['languages']=[{'tag':'fr','fallbacks':[],'layers':[{'layer_id':'native-fr','kind':'curated','priority':100,'path':layer.name,'sha256':digest(layer)}]}]
    if not labels:
        # Empty und layer declares no lexical assertion; needed for pinned coverage validator.
        layer=base/'dictionaries/native-und.json';write(layer,{**envelope('curated_dictionary'),'language':'und','entries':[]});cat['languages']=[{'tag':'und','fallbacks':[],'layers':[{'layer_id':'native-und-empty','kind':'curated','priority':100,'path':layer.name,'sha256':digest(layer)}]}]
    write(base/'dictionaries/catalog.json',cat)
    roles={'registry':'canon/domain/v11/registry.json','graph':'canon/domain/v11/graph.json','crosswalk':'canon/domain/v11/crosswalk.json','catalog':'canon/domain/v11/dictionaries/catalog.json'}
    write(out/'canon/state.index.json',{'canonical_artifacts':[{'path':p} for p in roles.values()]});write(out/'.kristal/v11/authoring.json',{'format':'kristal.authoring-v11-profile/1.0','semantic_profile':'kristal.semantic-identity/11.0',**roles})
    for k,b in raws.items():copy_bytes(out/'native-originals'/(k+'.json'),b)
    write(out/'bridge.json',{'format':'koa.kristal-native-bridge/1.0','slug':slug,'namespace_id':ns,'status':'UNAPPROVED_CANDIDATE','source_paths':paths,'source_sha256':hashes,'entries':bridge,'duplicate_native_assertion_ids':{},'implicit_predicates':sorted(x['native_ref'] for x in bridge if x['kind']=='property'),'preservation':'Exact native occurrence projection. Original proposition kind, source records, epistemic status, roles and qualifiers retained in original bytes; string projection is not a claim of legal validity.'})
    write(out/'unqualified-label-observations.json',[{'semantic_id':k,'terms':sorted(z),'status':'LANGUAGE_NOT_EXPLICIT_AT_LABEL_LEVEL_REVIEW_REQUIRED'} for k,z in sorted(observed.items())])
    return {'slug':slug,'namespace_id':ns,'identities':len(entries),'labels':len(labels),'assertion_occurrences':len(assertions),'sources':len(refs),'qualifiers':qualifiers,'proposition_projections':propositions,'without_evidence':missing,'unqualified_label_observations':len(observed),'entity_count':len(graph['entities']),'property_count':len(graph['properties']),'source_sha256':hashes,'candidate_files':{p:digest(out/p) for p in roles.values()},'status':'CANDIDATE_PENDING_EDITORIAL_QUALIFICATION'}

def packet_for(root,r):
    s=read(root/'native-originals/state.json');b=read(root/'bridge.json');c=collections.Counter((str(a.get('assertion_status')),str(a.get('record_role'))) for a in s['assertions'])
    return {'format':'koa.kristal-migration-editorial-review/1.0','slug':r['slug'],'namespace_id':r['namespace_id'],'status':'PENDING_INDEPENDENT_EDITORIAL_REVIEW','candidate_inventory':e.inventory(root),'native_status_role_counts':[{'status':k[0],'role':k[1],'count':count} for k,count in sorted(c.items())],'assertion_review':[{'semantic_id':x['semantic_id'],'native_ref':x['native_ref'],'original_pointer':x['json_pointer'],'status':s['assertions'][int(x['json_pointer'].split('/')[-1])].get('assertion_status'),'role':s['assertions'][int(x['json_pointer'].split('/')[-1])].get('record_role')} for x in b['entries'] if x['kind']=='assertion'],'required_attestations':['original_status_roles_preserved','implicit_predicates_reviewed','duplicate_occurrences_reviewed','epistemic_fields_accessible_to_readers','source_provenance_reviewed','canonical_registration_plan_reviewed','scalar_projection_and_qualifiers_reviewed','unqualified_labels_reviewed','missing_evidence_reviewed'],'activation_authorized':False,'notes':'Occurrence-derived identities are provisional. No external acceptance, no editorial approval. Exact native bytes must be accessible to readers.'}

def diagnose(w,a):
    result={'slug':a['slug'],'status':'NEEDS_NATIVE_ADAPTER_REVIEW','files':a['files'],'reason':'No reviewed complete lossless scalar adapter'}
    counts=collections.Counter();total=0
    for f in a['files']:
        if f.get('artifact_type') not in ('kristal_state','structured_epistemic_state','semantic_corpus'):continue
        doc=read(member(w,f['path']))
        for x in doc.get('assertions',[]):
            total+=1;o=x.get('statement',{}).get('object',{});counts[(str(o.get('kind')),type(o.get('value')).__name__)]+=1
    result['assertions_inspected']=total;result['object_shapes']=[{'native_kind':k[0],'value_type':k[1],'count':c} for k,c in sorted(counts.items())]
    if not total:result['reason']='No assertion corpus identified by prior audit; specialized native discovery required'
    elif any(k[1] in ('list','dict') and k[0] not in ('item','referent') for k in counts):result['reason']='Structured literal lacks reviewed V11 representation; entire corpus held back'
    if a.get('literal_anomalies'):result['literal_anomalies']=a['literal_anomalies']
    return result

def validate_prior(private,src,report,workspace):
    generations=[member(private,'SEMANTIC_V521_b790677e7c6b8956'),member(private,'SEMANTIC_V5211_66f477e821a9df6d'),src]
    reports=[e.check_generation(x) for x in generations];must(reports[0]['database_sha256']==e.EXPECTED_DB and reports[1]['database_sha256']==n.EXPECTED_DB,'Prior ancestor hash mismatch')
    records=[(r,g/'candidates'/r['slug']) for g,rep in zip(generations,reports) for r in rep.get('new_candidates',rep.get('candidates',[]))]
    planmap={p['slug']:p for p in report['registration_plans']};must(len(records)==len(planmap)==25,'Prior scope mismatch')
    for r,root in records:
        slug=r['slug'];p=planmap[slug];packet=read(src/'editorial'/f'{slug}.json');plan=read(src/'registration-plans'/f'{slug}.json');b=read(root/'bridge.json')
        must(sha(bytes_json(packet))==p['packet_sha256'] and sha(bytes_json(plan))==p['plan_sha256'] and e.inventory(root)==packet['candidate_inventory'] and plan['candidate_inventory']==packet['candidate_inventory'],'Prior candidate/plan drift')
        must(all(digest(member(workspace[slug],path))==b['source_sha256'][k] for k,path in b['source_paths'].items()),'Prior native source drift: '+slug)
    return records

def verify_prior_index(db,report,records):
    prior={r['slug']:r for r,_ in records}
    got={x[0]:json.loads(x[1]) for x in db.execute('SELECT slug,report_json FROM v521_native_candidate UNION ALL SELECT slug,report_json FROM v5211_native_candidate UNION ALL SELECT slug,report_json FROM v5212_native_candidate')}
    must(prior==got,'Prior candidate index mismatch')
    plans={x[0]:json.loads(x[1]) for x in db.execute('SELECT slug,report_json FROM v5212_registration_plan')};must(plans=={x['slug']:x for x in report['registration_plans']},'Prior registration plan index mismatch')

def run(locals_root,private,kit,framework):
    locals_root,private,kit,framework=map(guard,(locals_root,private,kit,framework));must(not any(private==p or private in p.parents or p in private.parents for p in (locals_root,kit,framework,locals_root.parent/'kristal-public')),'Private path must be disjoint')
    src=member(private,BASE);report=e.check_generation(src);must(report['database_sha256']==EXPECTED_DB and report['status']=='EXTENSION_AND_REGISTRATION_REHEARSAL_COMPLETE_EDITORIAL_PENDING','Wrong prior generation')
    q=load_qualifier(kit,framework)
    with closing(sqlite3.connect(uri(src/'active.sqlite'),uri=True)) as db:
        must(db.execute('PRAGMA integrity_check').fetchone()==('ok',) and not db.execute('PRAGMA foreign_key_check').fetchone(),'Invalid baseline database')
        rows=db.execute('SELECT slug,local_directory,state_sha256 FROM workspace WHERE active=0 ORDER BY slug').fetchall();must(len(rows)==50,'Inactive scope drift')
        namespaces={x[0] for x in db.execute('SELECT namespace_id FROM workspace WHERE namespace_id IS NOT NULL')}
    workspace={slug:member(locals_root,d) for slug,d,h in rows}
    def preflight():
        for slug,d,h in rows:
            w=workspace[slug];must(digest(member(w,'canon/state.index.json'))==h and not member(w,'.kristal/v11/authoring.json').exists(),'Inactive workspace drift: '+slug)
    preflight();records=validate_prior(private,src,report,workspace)
    with closing(sqlite3.connect(uri(src/'active.sqlite'),uri=True)) as db:verify_prior_index(db,report,records)
    old={r['slug'] for r,_ in records};namespaces.update(r['namespace_id'] for r,_ in records)
    pending=[a for a in report['audit'] if a['slug'] not in old];must(len(pending)==25 and {a['slug'] for a in pending}==set(workspace)-old,'Pending scope mismatch')
    with tempfile.TemporaryDirectory(prefix='v5213-stage-',dir=private) as td:
        stage=Path(td);new=[];plans=[];audit=[]
        for a in pending:
            slug=a['slug'];w=workspace[slug];actual=e.corpus_audit(w,a);must(actual['files']==a['files'],'Corpus drift: '+slug)
            diag=diagnose(w,a)
            if slug in SUPPORTED:
                print('V5.21.3 candidate:',slug,flush=True);root=stage/'candidates'/slug
                r=build(w,slug,root,a);must(r['namespace_id'] not in namespaces,'Namespace collision');namespaces.add(r['namespace_id'])
                qr=q.qualify(root,framework);must(qr['valid'] and qr['reference_coverage_match'],'Qualification failed: '+slug);r['technical_qualification']={k:qr[k] for k in ('valid','framework_version','reference_coverage_match','graph_sha256','catalog_sha256')}
                packet=packet_for(root,r);plan=n.registration_plan(root,w,r,packet);plan['status']='PRIVATE_REHEARSAL_ONLY';rr=n.rehearsal(root,w,plan,kit,framework,q,private)
                write(stage/'editorial'/f'{slug}.json',packet);write(stage/'registration-plans'/f'{slug}.json',plan);approval=e.approval_template(packet);approval.update(registration_plan_sha256=sha(bytes_json(plan)),epistemic_reader_contract_verified=False);write(stage/'approval-templates'/f'{slug}.json',approval)
                new.append(r);plans.append({'slug':slug,'packet_sha256':sha(bytes_json(packet)),'plan_sha256':sha(bytes_json(plan)),**rr});diag['status']='CANDIDATE_TECHNICALLY_QUALIFIED';diag['reason']='Exact occurrence projection; editorial and reader qualification pending'
            audit.append(diag)
        must({r['slug'] for r in new}==SUPPORTED,'Expected reviewed candidate scope not produced')
        preflight();must(e.check_generation(src)==report,'Prior generation changed');validate_prior(private,src,report,workspace)
        for a in pending:must(e.corpus_audit(workspace[a['slug']],a)['files']==a['files'],'Corpus changed before output')
        for r in new:
            b=read(stage/'candidates'/r['slug']/'bridge.json');must(all(digest(member(workspace[r['slug']],p))==b['source_sha256'][k] for k,p in b['source_paths'].items()),'Source changed before output')
        dbout=stage/'active.sqlite'
        with closing(sqlite3.connect(uri(src/'active.sqlite'),uri=True)) as inp, closing(sqlite3.connect(dbout)) as db:
            inp.backup(db)
            with db:
                db.execute('CREATE TABLE v5213_native_candidate(slug TEXT PRIMARY KEY, namespace_id TEXT UNIQUE NOT NULL, report_json TEXT NOT NULL)')
                db.execute('CREATE TABLE v5213_candidate_identity(namespace_id TEXT NOT NULL, semantic_id TEXT NOT NULL, slug TEXT NOT NULL, kind TEXT NOT NULL, native_ref TEXT NOT NULL, json_pointer TEXT NOT NULL, source_sha256 TEXT NOT NULL, PRIMARY KEY(namespace_id,semantic_id))')
                db.execute('CREATE TABLE v5213_candidate_lexical(namespace_id TEXT NOT NULL, semantic_id TEXT NOT NULL, language_tag TEXT NOT NULL, preferred_term TEXT NOT NULL, PRIMARY KEY(namespace_id,semantic_id,language_tag), FOREIGN KEY(namespace_id,semantic_id) REFERENCES v5213_candidate_identity(namespace_id,semantic_id))')
                db.execute('CREATE TABLE v5213_registration_plan(slug TEXT PRIMARY KEY, report_json TEXT NOT NULL)')
                db.execute('CREATE TABLE v5213_native_audit(slug TEXT PRIMARY KEY, report_json TEXT NOT NULL)')
                for r in new:
                    slug=r['slug'];root=stage/'candidates'/slug;ns=r['namespace_id'];b=read(root/'bridge.json');db.execute('INSERT INTO v5213_native_candidate VALUES (?,?,?)',(slug,ns,json.dumps(r,ensure_ascii=False,sort_keys=True)))
                    db.executemany('INSERT INTO v5213_candidate_identity VALUES (?,?,?,?,?,?,?)',[(ns,x['semantic_id'],slug,x['kind'],x['native_ref'],x['json_pointer'],x['source_sha256']) for x in b['entries']]);cat=root/'canon/domain/v11/dictionaries'
                    for loc in read(cat/'catalog.json')['languages']:
                        for l in loc['layers']:
                            d=read(member(cat,l['path']));db.executemany('INSERT INTO v5213_candidate_lexical VALUES (?,?,?,?)',[(ns,x['semantic_id'],loc['tag'],x['preferred_term']) for x in d['entries']])
                for table,items in [('v5213_registration_plan',plans),('v5213_native_audit',audit)]:db.executemany('INSERT INTO '+table+' VALUES (?,?)',[(x['slug'],json.dumps(x,ensure_ascii=False,sort_keys=True)) for x in items])
            must(db.execute('PRAGMA integrity_check').fetchone()==('ok',) and not db.execute('PRAGMA foreign_key_check').fetchone(),'Output DB invalid');counts={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('identity','lexical','candidate_wikidata')};must(counts==report['active_counts'],'Active counts changed')
        dest=member(private,'SEMANTIC_V5213_'+sha(bytes_json([EXPECTED_DB,new,plans,audit]))[:16]);keys=('identities','labels','assertion_occurrences','sources');delta={k:sum(x[k] for x in new) for k in keys};result={'format':'koa.kristal-native-specialized/1.0','status':'SPECIALIZED_CANDIDATES_REHEARSED_EDITORIAL_PENDING','source_database_sha256':EXPECTED_DB,'database':str(dest/'active.sqlite'),'database_sha256':digest(dbout),'prior_generation':str(src),'new_candidates':new,'counts':delta,'cumulative_counts':{k:report['cumulative_counts'][k]+delta[k] for k in keys},'new_candidate_count':len(new),'cumulative_candidate_count':25+len(new),'remaining_count':25-len(new),'active_counts':counts,'registration_plans':plans,'prior_registration_plan_count':25,'audit':audit,'policy':{'canonical_modified':False,'profiles_activated':0,'public_modified':False,'network_used':False,'production_activation_implemented':False,'independent_editorial_approval_required':True,'epistemic_reader_contract_required':True}}
        write(stage/'report.json',result);write(stage/'manifest.sha256.json',e.inventory(stage))
        if dest.exists():prev=e.check_generation(dest);must(prev==result,'Existing generation differs');return prev
        pub=stage/'publish';pub.mkdir()
        for p in list(stage.iterdir()):
            if p!=pub:os.replace(p,pub/p.name)
        os.rename(pub,dest);return result

def read_occurrence(generation,slug,semantic_id):
    """Private diagnostic reader for newly constructed candidates; not a production reader contract."""
    generation=guard(generation);rep=e.check_generation(generation);must(rep['status']=='SPECIALIZED_CANDIDATES_REHEARSED_EDITORIAL_PENDING','Wrong generation');r=next((x for x in rep['new_candidates'] if x['slug']==slug),None);must(r is not None,'Unknown candidate')
    root=member(generation,'candidates/'+slug);b=read(root/'bridge.json');packet=read(generation/'editorial'/f'{slug}.json');must(e.inventory(root)==packet['candidate_inventory'],'Candidate inventory mismatch');entry=next((x for x in b['entries'] if x['semantic_id']==semantic_id and x['kind']=='assertion'),None);must(entry is not None,'Unknown candidate assertion')
    source=root/'native-originals/state.json';must(digest(source)==entry['source_sha256'],'Original source digest mismatch');index=int(entry['json_pointer'].split('/')[-1]);old=read(source)['assertions'][index];must(old['assertion_id']==entry['native_ref'],'Native assertion mismatch');graph=read(root/'canon/domain/v11/graph.json');projection=next(x for x in graph['assertions'] if x['id']==semantic_id)
    return {'status':'PRIVATE_CANDIDATE_NOT_ACTIVE','slug':slug,'semantic_id':semantic_id,'source_sha256':entry['source_sha256'],'json_pointer':entry['json_pointer'],'original':old,'projection':projection}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('locals','private-dir','kit','framework'):p.add_argument('--'+k,type=Path)
    p.add_argument('--apply',action='store_true');p.add_argument('--read-assertion',nargs=3,metavar=('GENERATION','SLUG','KA'));a=p.parse_args()
    if a.read_assertion:
        must(not a.apply,'Reader cannot apply');print(json.dumps(read_occurrence(Path(a.read_assertion[0]),*a.read_assertion[1:]),ensure_ascii=True,indent=2));return
    must(a.apply and all((a.locals,a.private_dir,a.kit,a.framework)),'--apply and four paths required (private output only)');r=run(a.locals,a.private_dir,a.kit,a.framework);print(json.dumps(r,ensure_ascii=True,indent=2));print('V5.21.3 ONE-SHOT:',r['status'])
if __name__=='__main__':main()
