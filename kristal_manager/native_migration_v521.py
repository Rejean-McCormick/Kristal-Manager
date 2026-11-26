"""V5.21: offline native V6 -> V11 candidate construction, never activation.
Preserves exact original documents and per-occurrence bridges, separates candidate
registry from the active SQLite index; no writes to locals or public.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, os, re, sqlite3, stat, sys, tempfile, unicodedata
from contextlib import closing
from pathlib import Path
from datetime import datetime, timezone

FORMAT='koa.kristal-native-migration/1.0'
PRIORITY=('accounting','craft','cybersecurity','education','engineeringconstraints','manufacturing','soil','standards')
BASE='SEMANTIC_V520_879bcd3e8dea'
EXPECTED_DB='5dcdaaf457a0159a4df0928f71abb3b288d984e0c1e04803c0eee5bc0ccc7fe1'

def must(ok,msg):
    if not ok: raise ValueError(msg)
def guard(path):
    p=Path(path).absolute()
    for q in [*reversed(p.parents),p]:
        try: s=q.lstat()
        except FileNotFoundError: continue
        must(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&0x400,f'Link/reparse refused: {q}')
    return p

def member(root,rel):
    must(isinstance(rel,str) and rel and not any(x in rel for x in ('\\',':')) and not Path(rel).is_absolute() and '..' not in Path(rel).parts,'Unsafe member')
    return guard(root/rel)
def sha(b): return hashlib.sha256(b).hexdigest()
def digest(p):
    h=hashlib.sha256()
    with guard(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def read(p): return json.loads(guard(p).read_bytes())
def bytes_json(v): return (json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf8')
def write(p,v):
    p=guard(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f: f.write(bytes_json(v))
def copy_bytes(p,b):
    p=guard(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(b)
def uri(p): return guard(p).as_uri()+'?mode=ro'
def sid(ns,kind,key):
    return {'entity':'KQ','property':'KP','assertion':'KA','source':'KS'}[kind]+str(int(sha(bytes_json([ns,kind,key]))[:13],16)+1)

def native_inputs(w):
    base='knowledge-base/corpus/'
    idx=read(member(w,base+'index.json'))
    r=idx.get('registry',idx.get('referent_registry')); s=idx.get('state',idx.get('canonical_state'))
    for name in (r,s): must(isinstance(name,str) and re.fullmatch(r'[A-Za-z0-9_.-]+\.json',name) and name not in ('.','..'),'Invalid native corpus path')
    return {'index':base+'index.json','registry':base+r,'state':base+s,'state_index':'canon/state.index.json','workspace':'kristal.workspace.json'}

def literal(o):
    k=o['kind']; v=o['value']
    must(k in ('literal','string') and set(o)<= {'kind','value','language'},'Unsupported native literal')
    dt={str:'string',bool:'boolean',int:'integer',float:'number'}.get(type(v))
    must(dt is not None and (k!='string' or dt=='string'),'Unsupported literal type')
    ret={'kind':'literal','datatype':dt,'value':v}
    if 'language' in o:
        must(dt=='string','Language on non-string literal');ret['language']=o['language']
    return ret

def build_candidate(w,slug,out,expected=None):
    w=guard(w); out=guard(out)
    must(not member(w,'.kristal/v11/authoring.json').exists(),'Already active')
    inputs=native_inputs(w); raws={k:member(w,v).read_bytes() for k,v in inputs.items()}; hashes={k:sha(v) for k,v in raws.items()}
    if expected is not None: must(hashes==expected,'Native source changed since audited snapshot')
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
        ref=r['ref'];kind={'concept':'entity','predicate':'property'}.get(r['kind'])
        must(kind and isinstance(ref,str) and ref and ref not in refs,'Invalid or duplicate native referent')
        ident=alloc(kind,ref,'registry',f'/referents/{i}',ref);refs[ref]=ident
        seen_lang=set()
        for j,l in enumerate(r['labels']):
            lang=l['lang']; term=l['text'];must(lang in ('fr','en') and lang not in seen_lang and isinstance(term,str) and term.strip() and unicodedata.is_normalized('NFC',term),'Unsupported or duplicate native label');seen_lang.add(lang)
            entry={'semantic_id':ident,'preferred_term':term,'review':{'decision_id':'v521-transcription-'+sha(bytes_json([hashes['registry'],i,j]))[:24],'reviewer':'V5.21 deterministic transcription (candidate only)','reason':'Exact native label; not an editorial or publication approval.'}}
            if lang=='fr' and isinstance(r.get('definition_fr'),str):entry['definition']=r['definition_fr']
            labels[lang].append(entry)
    for i,r in enumerate(state['source_refs']):
        ref=r['source_id'];must(isinstance(ref,str) and ref and ref not in sources,'Invalid/duplicate source ID')
        sources[ref]=alloc('source',ref,'state',f'/source_refs/{i}',ref)
    for i,a in enumerate(state['assertions']):
        st=a['statement'];must(set(st)=={'subject','predicate','object'},'Unsupported statement/qualifier shape')
        must(a['assertion_status']=='reviewed' and a['record_role']=='reference_knowledge','Unsupported native epistemic status')
        sub=st['subject'];must(sub['kind']=='item' and refs.get(sub['id'],'').startswith('KQ'),'Unknown subject')
        pred=st['predicate'];must(isinstance(pred,str) and pred,'Invalid predicate')
        if pred not in refs:
            missing_preds.add(pred);refs[pred]=alloc('property',pred,'state',f'/assertions/{i}/statement/predicate',pred)
        must(refs[pred].startswith('KP'),'Predicate kind mismatch')
        o=st['object']
        if o['kind']=='item':
            must(refs.get(o['id'],'').startswith('KQ'),'Unknown target');obj={'kind':'entity','id':refs[o['id']]}
        else:obj=literal(o)
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
    registry={**envelope('identity_registry'),'registry_id':slug+'-native-v521','identities':sorted(entries.values(),key=lambda x:x['id'])}
    graph={**envelope('semantic_graph'),'graph_id':slug+'-native-v521','entities':sorted(x for x in entries if x.startswith('KQ')),'properties':sorted(x for x in entries if x.startswith('KP')),'sources':sorted(sources.values()),'assertions':assertions}
    cross={'schema_version':'11.0','artifact_type':'kristal_external_crosswalk','crosswalk_id':slug+'-native-v521','mappings':[]}
    cat={**envelope('dictionary_catalog'),'catalog_id':slug+'-native-v521','languages':[]}
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
        ref=doc if isinstance(doc,str) else doc[{'entity':'ref','property':'ref','source':'source_id','assertion':'assertion_id'}[kind]]
        must(ref==row['native_ref'],'Bridge native reference mismatch');mapped[id]=doc;positions[id]=ptr
        if kind!='assertion':must((kind,ref) not in lookup,'Duplicate native reference');lookup[kind,ref]=id
    must(set(mapped)==set(by_id),'Bridge identity coverage mismatch')
    native=docs['state']['assertions'];must(len(native)==len(g['assertions']),'Assertion count mismatch')
    seen=set()
    for a in g['assertions']:
        old=mapped[a['id']];ptr=positions[a['id']];must(ptr not in seen,'Duplicate assertion occurrence');seen.add(ptr)
        s=old['statement'];o=s['object'];expected={'kind':'entity','id':lookup['entity',o['id']]} if o['kind']=='item' else literal(o)
        must(a['subject']==lookup['entity',s['subject']['id']] and a['predicate']==lookup['property',s['predicate']] and a['object']==expected and a['sources']==[lookup['source',x] for x in old['evidence_refs']],'Graph round-trip mismatch')
    must(seen=={f'/assertions/{i}' for i in range(len(native))},'Occurrence coverage mismatch')
    expected_labels={(lookup[{'concept':'entity','predicate':'property'}[r['kind']],r['ref']],l['lang']):l['text'] for r in docs['registry']['referents'] for l in r['labels']}
    actual={}
    for loc in read(v/'dictionaries/catalog.json')['languages']:
        for layer in loc['layers']:
            p=member(v/'dictionaries',layer['path']);must(digest(p)==layer['sha256'],'Layer hash mismatch')
            for row in read(p)['entries']:
                key=(row['semantic_id'],loc['tag']);must(key not in actual,'Duplicate lexical cell');actual[key]=row['preferred_term']
    must(actual==expected_labels,'Native lexical round-trip mismatch')
    return True

def load_qualifier(kit,framework):
    sys.path.insert(0,str(guard(kit/'scripts')))
    import qualify_framework_v11 as q
    q.verify_pin(guard(framework))
    return q

def correct_queue(db):
    before=db.execute("SELECT count(*) FROM review_queue WHERE issue='MISSING_ACTIVE_LABEL'").fetchone()[0]
    db.execute("DELETE FROM review_queue WHERE issue='MISSING_ACTIVE_LABEL' AND EXISTS(SELECT 1 FROM identity i WHERE i.namespace_id=review_queue.namespace_id AND i.semantic_id=review_queue.semantic_id AND i.kind IN ('assertion','source'))")
    after=db.execute("SELECT count(*) FROM review_queue WHERE issue='MISSING_ACTIVE_LABEL'").fetchone()[0]
    return {'before':before,'after':after,'removed':before-after}

def run(locals_root,private,kit,framework,*,base_report=None,pins=None):
    locals_root,private,kit,framework=map(guard,(locals_root,private,kit,framework))
    must(not any(private==p or private in p.parents or p in private.parents for p in (locals_root,kit,framework,locals_root.parent/'kristal-public')),'Private path must be disjoint')
    base_report=guard(base_report or private/(BASE+'.json')); report=read(base_report)
    must(report['status']=='COMPLETE' and report['database_sha256']==EXPECTED_DB,'Unexpected V5.20 baseline report')
    src=member(private,BASE+'.active.sqlite');must(digest(src)==EXPECTED_DB,'Baseline database hash mismatch')
    qualifier=load_qualifier(kit,framework)
    pins=pins or read(Path(__file__).with_name('native_migration_v521_pins.json'))
    with closing(sqlite3.connect(uri(src),uri=True)) as db:
        must(db.execute('PRAGMA integrity_check').fetchone()==('ok',),'Baseline integrity failed')
        must(not db.execute('PRAGMA foreign_key_check').fetchone(),'Baseline foreign key failure')
        ws=db.execute('SELECT slug,local_directory,namespace_id,active,profile_sha256,state_sha256 FROM workspace ORDER BY slug').fetchall()
    must(len(ws)==127 and sum(row[3] for row in ws)==77,'Unexpected baseline workspace set')
    # Preflight every live workspace against the active V5.20 index.
    for slug,directory,ns,active,profile_hash,state_hash in ws:
        w=member(locals_root,directory);must(digest(member(w,'canon/state.index.json'))==state_hash,f'State drift: {slug}')
        profile=member(w,'.kristal/v11/authoring.json')
        must((profile.is_file() and digest(profile)==profile_hash) if active else not profile.exists(),f'Profile drift: {slug}')
    private.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='v521-stage-',dir=private) as tmp:
        stage=Path(tmp);bundle=stage/'candidates';bundle.mkdir();results=[];pending=[]
        namespaces={row[2] for row in ws if row[2]}
        for slug,directory,ns,active,profile_hash,state_hash in ws:
            if active:continue
            w=member(locals_root,directory)
            if slug not in PRIORITY:
                corpus=member(w,'knowledge-base/corpus'); files=[]
                if corpus.is_dir():files=sorted(x.name for x in corpus.iterdir() if guard(x).is_file() and x.suffix.lower()=='.json')
                pending.append({'slug':slug,'local_directory':directory,'corpus_json_files':files,'status':'NEEDS_NATIVE_ADAPTER_REVIEW'});continue
            print('V5.21 candidate:',slug,flush=True)
            r=build_candidate(w,slug,bundle/slug,pins[slug]);must(r['namespace_id'] not in namespaces,'Namespace collision');namespaces.add(r['namespace_id'])
            q=qualifier.qualify(bundle/slug,framework,locales=['fr','en']);must(q['valid'] and q['reference_coverage_match'],'Qualification failed')
            r['technical_qualification']={k:q[k] for k in ('valid','framework_version','reference_coverage_match','graph_sha256','catalog_sha256')};results.append(r)
        must(len(results)==8 and len(pending)==42,'Unexpected candidate scope')
        write(bundle/'PENDING.json',pending)
        dbout=stage/'active.sqlite'
        with closing(sqlite3.connect(uri(src),uri=True)) as inp, closing(sqlite3.connect(dbout)) as db:
            inp.backup(db)
            with db:
                queue=correct_queue(db)
                db.execute('CREATE TABLE v521_native_candidate (slug TEXT PRIMARY KEY, namespace_id TEXT UNIQUE NOT NULL, report_json TEXT NOT NULL)')
                db.executemany('INSERT INTO v521_native_candidate VALUES (?,?,?)',[(r['slug'],r['namespace_id'],json.dumps(r,ensure_ascii=False,sort_keys=True)) for r in results])
                db.execute('CREATE TABLE v521_candidate_identity (namespace_id TEXT NOT NULL, semantic_id TEXT NOT NULL, slug TEXT NOT NULL, kind TEXT NOT NULL, native_ref TEXT NOT NULL, json_pointer TEXT NOT NULL, source_sha256 TEXT NOT NULL, PRIMARY KEY(namespace_id,semantic_id))')
                db.execute('CREATE TABLE v521_candidate_lexical (namespace_id TEXT NOT NULL, semantic_id TEXT NOT NULL, language_tag TEXT NOT NULL, preferred_term TEXT NOT NULL, PRIMARY KEY(namespace_id,semantic_id,language_tag), FOREIGN KEY(namespace_id,semantic_id) REFERENCES v521_candidate_identity(namespace_id,semantic_id))')
                db.execute('CREATE INDEX v521_candidate_native_ref ON v521_candidate_identity(native_ref)')
                db.execute('CREATE INDEX v521_candidate_term ON v521_candidate_lexical(preferred_term)')
                for r in results:
                    root=bundle/r['slug']; b=read(root/'bridge.json');ns=r['namespace_id']
                    db.executemany('INSERT INTO v521_candidate_identity VALUES (?,?,?,?,?,?,?)',[(ns,x['semantic_id'],r['slug'],x['kind'],x['native_ref'],x['json_pointer'],x['source_sha256']) for x in b['entries']])
                    for lang in ('fr','en'):
                        d=read(root/'canon/domain/v11/dictionaries'/f'native-{lang}.json')
                        db.executemany('INSERT INTO v521_candidate_lexical VALUES (?,?,?,?)',[(ns,x['semantic_id'],lang,x['preferred_term']) for x in d['entries']])
                db.execute('CREATE TABLE v521_native_pending (slug TEXT PRIMARY KEY, report_json TEXT NOT NULL)')
                db.executemany('INSERT INTO v521_native_pending VALUES (?,?)',[(r['slug'],json.dumps(r,ensure_ascii=False,sort_keys=True)) for r in pending])
            must(db.execute('PRAGMA integrity_check').fetchone()==('ok',) and not db.execute('PRAGMA foreign_key_check').fetchone(),'Result SQLite integrity failed')
            active_counts={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('identity','lexical','candidate_wikidata')}
        for slug,directory,ns,active,profile_hash,state_hash in ws:
            w=member(locals_root,directory);must(digest(member(w,'canon/state.index.json'))==state_hash,f'State drift during scan: {slug}')
            profile=member(w,'.kristal/v11/authoring.json');must((profile.is_file() and digest(profile)==profile_hash) if active else not profile.exists(),f'Profile drift during scan: {slug}')
            if slug in PRIORITY:must({k:digest(member(w,v)) for k,v in native_inputs(w).items()}==pins[slug],f'Native drift during scan: {slug}')
        must(digest(src)==EXPECTED_DB,'Baseline database changed during scan')
        name='SEMANTIC_V521_'+sha(bytes_json([EXPECTED_DB,results,pending]))[:16]
        dest=guard(private/name)
        summary={'format':FORMAT,'status':'CANDIDATES_QUALIFIED_ACTIVATION_PENDING','source_database_sha256':EXPECTED_DB,'database':str(dest/'active.sqlite'),'database_sha256':digest(dbout),'candidates_directory':str(dest/'candidates'),'candidates':results,'pending_workspaces':pending,'counts':{k:sum(r[k] for r in results) for k in ('native_referents','implicit_predicates','assertion_occurrences','duplicate_assertion_ids','sources','identities','labels')},'review_queue':queue,'active_counts':active_counts,'policy':{'canonical_modified':False,'profiles_activated':0,'public_modified':False,'network_used':False,'candidate_identities_are_active':False,'independent_editorial_approval_required':True}}
        write(stage/'report.json',summary)
        # Pin every staged byte, then publish the private generation atomically.
        inventory={p.relative_to(stage).as_posix():digest(p) for p in sorted(stage.rglob('*')) if p.is_file()};write(stage/'manifest.sha256.json',inventory)
        if dest.exists():
            old=read(dest/'manifest.sha256.json');must(old=={p.relative_to(dest).as_posix():digest(p) for p in sorted(dest.rglob('*')) if p.is_file() and p.name!='manifest.sha256.json'},'Existing private generation drift')
            prior=read(dest/'report.json');must(prior['candidates']==results and prior['pending_workspaces']==pending and prior['source_database_sha256']==EXPECTED_DB,'Existing generation mismatch');return prior
        # Rename child directory rather than TemporaryDirectory root (Windows cleanup).
        publish=stage/'publish';publish.mkdir()
        for p in list(stage.iterdir()):
            if p!=publish:os.replace(p,publish/p.name)
        os.rename(publish,dest)
        return summary

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('locals','private-dir','kit','framework'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--apply',action='store_true');a=p.parse_args();must(a.apply,'--apply required (private candidates only)')
    result=run(a.locals,a.private_dir,a.kit,a.framework);print(json.dumps(result,ensure_ascii=True,indent=2));print('V5.21 ONE-SHOT:',result['status'])
if __name__=='__main__':main()
