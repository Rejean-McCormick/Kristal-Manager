"""V5.21.1: private extension of native candidate migration. No activation."""
from __future__ import annotations
import argparse, collections, json, os, re, sqlite3, tempfile, unicodedata
from contextlib import closing
from pathlib import Path
from . import native_migration_v521 as v
from .native_migration_v521 import must, guard, member, sha, digest, read, bytes_json, write, copy_bytes, uri, sid, literal, load_qualifier

BASE='SEMANTIC_V521_b790677e7c6b8956'
EXPECTED_DB='0ac89e0618ae6d8db7ef37d0c4fdfd8287acc3451f524b55bbcb140d764218e1'

def ref_id(r):
    keys=[k for k in ('ref','referent_id','id') if k in r]
    must(len(keys)==1,'Ambiguous native referent key')
    return r[keys[0]]

def ref_labels(r):
    if 'labels' in r:
        raw=r['labels']
        if isinstance(raw,dict): return list(raw.items())
        must(isinstance(raw,list),'Unsupported native labels')
        return [(x['lang'],x['text']) for x in raw]
    must(not ('label' in r and 'label_fr' in r),'Ambiguous French label')
    return [('fr',r.get('label_fr',r.get('label')))] + ([('en',r['label_en'])] if 'label_en' in r else [])

def source_id(r):
    if isinstance(r,str):return r
    must(isinstance(r,dict) and 'source_id' in r,'Unsupported native source')
    return r['source_id']

def extended_literal(o):
    if o['kind']=='text':
        must(isinstance(o['value'],str),'Non-string text')
        o={**o,'kind':'string'}
    return literal(o)

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
            entry={'semantic_id':ident,'preferred_term':term,'review':{'decision_id':'v5211-transcription-'+sha(bytes_json([hashes['registry'],i,j]))[:24],'reviewer':'V5.21.1 deterministic transcription (candidate only)','reason':'Exact native label; not an editorial or publication approval.'}}
            if lang=='fr' and isinstance(r.get('definition_fr'),str):entry['definition']=r['definition_fr']
            labels[lang].append(entry)
    for i,r in enumerate(state['source_refs']):
        ref=source_id(r);must(isinstance(ref,str) and ref and ref not in sources,'Invalid/duplicate source ID')
        sources[ref]=alloc('source',ref,'state',f'/source_refs/{i}',ref)
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
        evidence=a['evidence_refs'];must(evidence and all(x in sources for x in evidence),'Missing evidence source')
        must(len(set(evidence))==len(evidence),'Duplicate evidence ref')
        assertions.append({'id':ident,'subject':refs[sub['id']],'predicate':refs[pred],'object':obj,'sources':[sources[x] for x in evidence]})
    must(len(assertions)==len(state['assertions']),'Assertion loss')
    envelope=lambda t: {'schema_version':'11.0','artifact_type':'kristal_'+t,'namespace_id':ns}
    registry={**envelope('identity_registry'),'registry_id':slug+'-native-v5211','identities':sorted(entries.values(),key=lambda x:x['id'])}
    graph={**envelope('semantic_graph'),'graph_id':slug+'-native-v5211','entities':sorted(x for x in entries if x.startswith('KQ')),'properties':sorted(x for x in entries if x.startswith('KP')),'sources':sorted(sources.values()),'assertions':assertions}
    cross={'schema_version':'11.0','artifact_type':'kristal_external_crosswalk','crosswalk_id':slug+'-native-v5211','mappings':[]}
    cat={**envelope('dictionary_catalog'),'catalog_id':slug+'-native-v5211','languages':[]}
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
    return {'slug':slug,'namespace_id':ns,'native_referents':len(reg['referents']),'implicit_predicates':len(missing_preds),'assertion_occurrences':len(assertions),'duplicate_assertion_ids':sum(n>1 for n in seen.values()),'sources':len(sources),'identities':len(entries),'labels':sum(map(len,labels.values())),'source_sha256':hashes,'candidate_files':{v:digest(out/v) for v in paths.values()},'status':'CANDIDATE_PENDING_EDITORIAL_QUALIFICATION'}

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
        ref=source_id(doc) if kind=='source' else doc['assertion_id'] if kind=='assertion' else doc if isinstance(doc,str) else ref_id(doc)
        must(ref==row['native_ref'],'Bridge native reference mismatch');mapped[id]=doc;positions[id]=ptr
        if kind!='assertion':must((kind,ref) not in lookup,'Duplicate native reference');lookup[kind,ref]=id
    must(set(mapped)==set(by_id),'Bridge identity coverage mismatch')
    native=docs['state']['assertions'];must(len(native)==len(g['assertions']),'Assertion count mismatch')
    seen=set()
    for a in g['assertions']:
        old=mapped[a['id']];ptr=positions[a['id']];must(ptr not in seen,'Duplicate assertion occurrence');seen.add(ptr)
        s=old['statement'];o=s['object'];expected={'kind':'entity','id':lookup['entity',o['id']]} if o['kind'] in ('item','referent') else extended_literal(o)
        must(a['subject']==lookup['entity',s['subject']['id']] and a['predicate']==lookup['property',s['predicate']] and a['object']==expected and a['sources']==[lookup['source',x] for x in old['evidence_refs']],'Graph round-trip mismatch')
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



def inventory(root,exclude=()):
    return {p.relative_to(root).as_posix():digest(p) for p in sorted(root.rglob('*')) if guard(p).is_file() and p.relative_to(root).as_posix() not in exclude}

def check_generation(root):
    expected=read(root/'manifest.sha256.json')
    must(expected==inventory(root,('manifest.sha256.json',)),'Private generation manifest mismatch')
    r=read(root/'report.json');must(r['database_sha256']==digest(root/'active.sqlite'),'Database digest mismatch')
    return r

def corpus_audit(w,row):
    root=member(w,'knowledge-base/corpus'); records=[]
    if root.is_dir():
        for p in sorted(root.iterdir()):
            if not guard(p).is_file() or p.suffix.lower()!='.json':continue
            item={'path':p.relative_to(w).as_posix(),'sha256':digest(p),'size':p.stat().st_size}
            try:
                d=read(p)
                if isinstance(d,dict):
                    item.update({'schema_version':d.get('schema_version'),'artifact_type':d.get('artifact_type'),'top_level_keys':sorted(d),'list_counts':{k:len(x) for k,x in d.items() if isinstance(x,list)}})
                elif isinstance(d,list):item['list_count']=len(d)
                else:item['json_type']=type(d).__name__
            except (ValueError,UnicodeError) as e:item['parse_error']=str(e)
            records.append(item)
    return {'slug':row['slug'],'local_directory':row['local_directory'],'files':records,'status':'NEEDS_NATIVE_ADAPTER_REVIEW'}

def review_packet(root,result):
    b=read(root/'bridge.json');s=read(root/'native-originals/state.json');r=read(root/'native-originals/registry.json')
    counts=collections.Counter((str(a.get('assertion_status')),str(a.get('record_role'))) for a in s['assertions'])
    return {'format':'koa.kristal-migration-editorial-review/1.0','slug':result['slug'],'namespace_id':result['namespace_id'],'status':'PENDING_INDEPENDENT_EDITORIAL_REVIEW','candidate_inventory':inventory(root),'native_status_role_counts':[{'status':k[0],'role':k[1],'count':n} for k,n in sorted(counts.items())], 'native_assertion_fields':sorted({k for a in s['assertions'] for k in a}), 'native_referent_fields':sorted({k for x in r['referents'] for k in x}), 'implicit_predicates':b['implicit_predicates'],'duplicate_native_assertion_ids':b['duplicate_native_assertion_ids'],'assertion_review':[{ 'semantic_id':x['semantic_id'],'native_ref':x['native_ref'],'original_pointer':x['json_pointer'],'status':s['assertions'][int(x['json_pointer'].split('/')[-1])].get('assertion_status'),'role':s['assertions'][int(x['json_pointer'].split('/')[-1])].get('record_role')} for x in b['entries'] if x['kind']=='assertion'],'required_attestations':['original_status_roles_preserved','implicit_predicates_reviewed','duplicate_occurrences_reviewed','epistemic_fields_accessible_to_readers','source_provenance_reviewed','canonical_registration_plan_reviewed'],'activation_authorized':False,'notes':'Graph alone does not preserve all epistemic fields; original documents and pointers are required. No claim of independent editorial approval.'}

def approval_template(packet):
    return {'format':'koa.kristal-migration-editorial-approval/1.0','slug':packet['slug'],'packet_sha256':sha(bytes_json(packet)),'reviewer':'','decision_id':'','decision':'pending','independence_declared':False,'attestations':{k:False for k in packet['required_attestations']}}

def approval_gate(packet,approval):
    """Validate scope and completeness of an externally supplied declaration only.
    Does not verify reviewer identity or independence, nor write any canon.
    """
    must(approval.get('format')=='koa.kristal-migration-editorial-approval/1.0','Invalid approval format')
    must(approval.get('slug')==packet['slug'] and approval.get('packet_sha256')==sha(bytes_json(packet)),'Approval not bound to this candidate')
    reviewer=approval.get('reviewer');must(isinstance(reviewer,str) and reviewer.strip(),'Named reviewer required')
    must(approval.get('decision')=='approve' and approval.get('independence_declared') is True,'Independent approval declaration required')
    must(approval.get('attestations')=={k:True for k in packet['required_attestations']},'Missing review attestations')
    must(isinstance(approval.get('decision_id'),str) and approval['decision_id'].strip(),'Decision identifier required')
    return 'DECLARATION_COMPLETE_INDEPENDENCE_NOT_VERIFIED_ACTIVATION_PENDING'

def run(locals_root,private,kit,framework):
    locals_root,private,kit,framework=map(guard,(locals_root,private,kit,framework))
    must(not any(private==p or private in p.parents or p in private.parents for p in (locals_root,kit,framework,locals_root.parent/'kristal-public')),'Private path must be disjoint')
    src=member(private,BASE);report=check_generation(src)
    must(report['status']=='CANDIDATES_QUALIFIED_ACTIVATION_PENDING' and report['database_sha256']==EXPECTED_DB,'Unexpected V5.21 baseline')
    source_db=src/'active.sqlite';pins=read(Path(__file__).with_name('native_extension_v5211_pins.json'));q=load_qualifier(kit,framework)
    with closing(sqlite3.connect(uri(source_db),uri=True)) as db:
        must(db.execute('PRAGMA integrity_check').fetchone()==('ok',) and not db.execute('PRAGMA foreign_key_check').fetchone(),'Baseline DB integrity failed')
        rows=db.execute('SELECT slug,local_directory,active,state_sha256 FROM workspace WHERE active=0 ORDER BY slug').fetchall()
        namespaces={x[0] for x in db.execute('SELECT namespace_id FROM workspace WHERE namespace_id IS NOT NULL')}
        must(len(rows)==50 and db.execute('SELECT count(*) FROM v521_native_candidate').fetchone()[0]==8,'Unexpected baseline scope')
        old_index={x[0]:json.loads(x[1]) for x in db.execute('SELECT slug,report_json FROM v521_native_candidate')}
    must(old_index=={x['slug']:x for x in report['candidates']},'Baseline candidate report mismatch')
    workspace={s:member(locals_root,d) for s,d,a,h in rows}
    def preflight():
        for s,d,a,h in rows:
            w=workspace[s];must(digest(member(w,'canon/state.index.json'))==h and not member(w,'.kristal/v11/authoring.json').exists(),f'Inactive workspace drift: {s}')
        for r in report['candidates']:
            s=r['slug'];must({k:digest(member(workspace[s],p)) for k,p in v.native_inputs(workspace[s]).items()}==r['source_sha256'],f'Original candidate drift: {s}')
    preflight()
    with tempfile.TemporaryDirectory(prefix='v5211-stage-',dir=private) as td:
        stage=Path(td);bundle=stage/'candidates';bundle.mkdir();results=[];audits=[];reviews=[]
        # Revalidate the exact first-generation files, do not regenerate or replace them.
        for r in report['candidates']:
            s=r['slug'];root=member(src/'candidates',s);must(read(root/'bridge.json')['source_sha256']==r['source_sha256'],'Original bridge source pins mismatch');must(v.verify_bridge(root),'Original bridge invalid');must(all(digest(member(root,p))==h for p,h in r['candidate_files'].items()),'Original candidate hash mismatch')
            qr=q.qualify(root,framework,locales=['fr','en']);must(qr['valid'] and qr['reference_coverage_match'],'Original candidate no longer technically valid')
            # No validator is allowed to change the original generation.
            packet=review_packet(root,r);write(stage/'editorial'/f'{s}.json',packet);reviews.append({'slug':s,'packet_sha256':digest(stage/'editorial'/f'{s}.json'),'origin':'V5.21'})
            namespaces.add(r['namespace_id'])
        for row in report['pending_workspaces']:
            s=row['slug'];w=workspace[s];audit=corpus_audit(w,row);audits.append(audit)
            if s not in pins:continue
            try:
                print('V5.21.1 candidate:',s,flush=True)
                r=build_candidate(w,s,bundle/s,pins[s]);must(r['namespace_id'] not in namespaces,'Namespace collision')
                locales=[x['tag'] for x in read(bundle/s/'canon/domain/v11/dictionaries/catalog.json')['languages']]
                qr=q.qualify(bundle/s,framework,locales=locales);must(qr['valid'] and qr['reference_coverage_match'],'Framework qualification failed')
                r['technical_qualification']={k:qr[k] for k in ('valid','framework_version','reference_coverage_match','graph_sha256','catalog_sha256')}
                packet=review_packet(bundle/s,r);write(stage/'editorial'/f'{s}.json',packet);reviews.append({'slug':s,'packet_sha256':digest(stage/'editorial'/f'{s}.json'),'origin':'V5.21.1'});results.append(r);namespaces.add(r['namespace_id']);audit['status']='CANDIDATE_TECHNICALLY_QUALIFIED'
            except (ValueError,KeyError,TypeError) as e:
                # A blocked corpus cannot leak partial candidate files into the output.
                import shutil
                if (bundle/s).exists():shutil.rmtree(bundle/s)
                audit['status']='BLOCKED_NATIVE_ADAPTER';audit['reason']=str(e)
        must(len(audits)==42,'Incomplete pending audit')
        for item in reviews:
            slug=item['slug'];write(stage/'approval-templates'/f'{slug}.json',approval_template(read(stage/'editorial'/f'{slug}.json')))
        # Validate every live input again; fail closed if the run saw drift.
        preflight()
        for a in audits:
            must(corpus_audit(workspace[a['slug']],a)['files']==a['files'],f"Corpus changed during scan: {a['slug']}")
        for r in results:
            must({k:digest(member(workspace[r['slug']],p)) for k,p in pins[r['slug']]['paths'].items()}==r['source_sha256'],'Native source changed during scan')
        must(check_generation(src)==report,'Baseline changed during scan')
        dbout=stage/'active.sqlite'
        with closing(sqlite3.connect(uri(source_db),uri=True)) as inp,closing(sqlite3.connect(dbout)) as db:
            inp.backup(db)
            with db:
                db.execute('CREATE TABLE v5211_native_candidate (slug TEXT PRIMARY KEY, namespace_id TEXT UNIQUE NOT NULL, report_json TEXT NOT NULL)')
                db.execute('CREATE TABLE v5211_candidate_identity (namespace_id TEXT NOT NULL, semantic_id TEXT NOT NULL, slug TEXT NOT NULL, kind TEXT NOT NULL, native_ref TEXT NOT NULL, json_pointer TEXT NOT NULL, source_sha256 TEXT NOT NULL, PRIMARY KEY(namespace_id,semantic_id))')
                db.execute('CREATE TABLE v5211_candidate_lexical (namespace_id TEXT NOT NULL, semantic_id TEXT NOT NULL, language_tag TEXT NOT NULL, preferred_term TEXT NOT NULL, PRIMARY KEY(namespace_id,semantic_id,language_tag), FOREIGN KEY(namespace_id,semantic_id) REFERENCES v5211_candidate_identity(namespace_id,semantic_id))')
                db.execute('CREATE TABLE v5211_native_audit (slug TEXT PRIMARY KEY, report_json TEXT NOT NULL)')
                db.execute('CREATE TABLE v5211_editorial_review (slug TEXT PRIMARY KEY, packet_sha256 TEXT NOT NULL, origin TEXT NOT NULL)')
                for r in results:
                    root=bundle/r['slug'];ns=r['namespace_id'];b=read(root/'bridge.json')
                    db.execute('INSERT INTO v5211_native_candidate VALUES (?,?,?)',(r['slug'],ns,json.dumps(r,ensure_ascii=False,sort_keys=True)))
                    db.executemany('INSERT INTO v5211_candidate_identity VALUES (?,?,?,?,?,?,?)',[(ns,x['semantic_id'],r['slug'],x['kind'],x['native_ref'],x['json_pointer'],x['source_sha256']) for x in b['entries']])
                    for loc in read(root/'canon/domain/v11/dictionaries/catalog.json')['languages']:
                        for layer in loc['layers']:
                            d=read(member(root/'canon/domain/v11/dictionaries',layer['path']))
                            db.executemany('INSERT INTO v5211_candidate_lexical VALUES (?,?,?,?)',[(ns,x['semantic_id'],loc['tag'],x['preferred_term']) for x in d['entries']])
                db.executemany('INSERT INTO v5211_native_audit VALUES (?,?)',[(a['slug'],json.dumps(a,ensure_ascii=False,sort_keys=True)) for a in audits])
                db.executemany('INSERT INTO v5211_editorial_review VALUES (?,?,?)',[(a['slug'],a['packet_sha256'],a['origin']) for a in reviews])
            must(db.execute('PRAGMA integrity_check').fetchone()==('ok',) and not db.execute('PRAGMA foreign_key_check').fetchone(),'Result DB integrity failed')
            active_counts={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('identity','lexical','candidate_wikidata')}
            must(active_counts==report['active_counts'],'Active data counts changed')
        dest=member(private,'SEMANTIC_V5211_'+sha(bytes_json(['5.21.1',EXPECTED_DB,results,audits,reviews]))[:16])
        summary={'format':'koa.kristal-native-extension/1.0','status':'EXTENSION_QUALIFIED_EDITORIAL_REVIEW_PENDING','source_database_sha256':EXPECTED_DB,'database':str(dest/'active.sqlite'),'database_sha256':digest(dbout),'prior_generation':str(src),'candidates':results,'audit':audits,'editorial_reviews':reviews,'counts':{k:sum(r[k] for r in results) for k in ('native_referents','implicit_predicates','assertion_occurrences','duplicate_assertion_ids','sources','identities','labels')},'prior_candidate_count':8,'new_candidate_count':len(results),'remaining_count':42-len(results),'active_counts':active_counts,'policy':{'canonical_modified':False,'profiles_activated':0,'public_modified':False,'network_used':False,'independent_editorial_approval_required':True,'activation_implemented':False}}
        write(stage/'report.json',summary);write(stage/'manifest.sha256.json',inventory(stage))
        if dest.exists():
            previous=check_generation(dest);must(previous['candidates']==results and previous['audit']==audits and previous['editorial_reviews']==reviews,'Private generation drift');return previous
        publish=stage/'publish';publish.mkdir()
        for p in list(stage.iterdir()):
            if p!=publish:os.replace(p,publish/p.name)
        os.rename(publish,dest);return summary

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('locals','private-dir','kit','framework'):p.add_argument('--'+k,type=Path)
    p.add_argument('--apply',action='store_true');p.add_argument('--check-approval',nargs=2,type=Path,metavar=('PACKET','APPROVAL'));a=p.parse_args()
    if a.check_approval:
        must(not a.apply,'Approval check cannot apply');print(approval_gate(*(read(x) for x in a.check_approval)));return
    must(a.apply and all((a.locals,a.private_dir,a.kit,a.framework)),'--apply and four paths required (private output only)')
    r=run(a.locals,a.private_dir,a.kit,a.framework);print(json.dumps(r,ensure_ascii=True,indent=2));print('V5.21.1 ONE-SHOT:',r['status'])
if __name__=='__main__':main()
