"""Read-only, local descriptive content catalogue; never a semantic authority."""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import hashlib,json,os,sqlite3,time,re
from .core import ManagerError
FORMAT='kristal.manager-content-catalog/0.1-candidate'
SCHEMA=1
ENGINE_VERSION='0.1.0a15'
PRUNE={'.git','node_modules','__pycache__','.venv','external-source-library','build','derived','canon','.kristal','knowledge-base','ai','state','release','projections','runtime','HISTORY','OPTIMIZATION_TOOLS','FINALIZATION_TOOLS'}
def encoded(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'),sort_keys=True)
def candidates(roots):
    seen=set()
    def walk_error(exc):raise ManagerError('Cannot complete source discovery: '+str(exc))
    for source in roots:
        root=Path(source).expanduser().resolve()
        if not root.is_dir():raise ManagerError(f'Root does not exist: {root}')
        for base,dirs,files in os.walk(root,followlinks=False,onerror=walk_error):
            dirs[:]=sorted(d for d in dirs if d not in PRUNE and not (Path(base)/d).is_symlink())
            p=Path(base)
            if p in seen:continue
            seen.add(p)
            if 'kristal.workspace.json' in files and not (p/'kristal.workspace.json').is_symlink():yield p
class Reader:
    def __init__(self,root,max_bytes=64*1024*1024):self.root=root;self.max_bytes=max_bytes;self.deps={};self.issues=[];self.bytes=0
    def path(self,rel):
        rel=str(rel);q=Path(rel)
        if q.is_absolute() or '..' in q.parts or '\\' in rel:raise ValueError('Unsafe reference: '+rel)
        target=self.root/q
        if any(p.is_symlink() for p in [target,*list(target.parents)[:len(q.parts)-1]]):raise ValueError('Symlink reference: '+rel)
        if not target.resolve().is_relative_to(self.root):raise ValueError('Reference escapes workspace')
        return target
    def blob(self,rel,optional=False):
        key=str(rel)
        if key not in self.deps and len(self.deps)>=256:
            if 'Scan dependency limit reached' not in self.issues:self.issues.append('Scan dependency limit reached')
            return None
        try:
            p=self.path(key)
            if not p.is_file():
                self.deps[key]={'status':'missing'}
                if not optional:self.issues.append('Missing selected file: '+key)
                return None
            size=p.stat().st_size
            if size>self.max_bytes or self.bytes+size>self.max_bytes*4:self.deps[key]={'status':'over_limit','size':size};self.issues.append('Selected file exceeds scan limit: '+key);return None
            blob=p.read_bytes();self.bytes+=len(blob);self.deps[key]={'status':'read','size':len(blob),'sha256':hashlib.sha256(blob).hexdigest()};return blob
        except (OSError,ValueError) as exc:self.deps[key]={'status':'blocked'};self.issues.append(str(exc));return None
    def obj(self,rel,optional=False):
        blob=self.blob(rel,optional)
        if blob is None:return {}
        try:
            d=json.loads(blob)
            if not isinstance(d,dict):raise ValueError('expected JSON object')
            return d
        except (ValueError,UnicodeError) as exc:self.issues.append(f'Invalid {rel}: {exc}');return {}
    def unchanged(self,deps):
        for rel,want in deps.items():
            self.blob(rel,True)
            if self.deps.get(rel)!=want:return False
        return True

def inspect_content(root,max_bytes=64*1024*1024):
    root=Path(root).resolve();r=Reader(root,max_bytes);ws=r.obj('kristal.workspace.json');idx=r.obj('canon/state.index.json',True);registered={x.get('path'):x for x in idx.get('canonical_artifacts',[]) if isinstance(x,dict) and isinstance(x.get('path'),str)}
    states=[r.obj(rel,True) for rel in ('state/state-snapshot.json','build/v9/state-snapshot.json')]
    states=[s for s in states if s.get('state_ref')]
    distinct={(s.get('state_ref'),(s.get('logical_commitment') or {}).get('digest')) for s in states}
    conflict=len(distinct)>1 or any(ws.get('state_ref') and ws['state_ref']!=s.get('state_ref') for s in states)
    meta={'state_commitment':(states[0].get('logical_commitment') or {}).get('digest') if states else None,'native_kind':(ws.get('native_model') or {}).get('kind'),'readiness':'STATE CONFLICT' if conflict else 'READY' if states else 'NO STATE'}
    if conflict:r.issues.append('Current state descriptors disagree')
    cfg=r.obj('.kristal/v11/authoring.json',True);graph={};namespace=None;mode='unsupported';graph_path=None;ledgerrel=None;labels={};label_origins={};terms=[];mappings=[];shapes={};components=set();ledger={}
    if cfg:
        graph_path=cfg.get('graph');required=[cfg.get(k) for k in ('graph','registry','catalog','crosswalk')]
        if any(not isinstance(p,str) or p not in registered for p in required):r.issues.append('Active profile references unregistered artifacts')
        elif cfg.get('format')!='kristal.authoring-v11-profile/1.0':r.issues.append('Unsupported authoring profile')
        else:
            graph=r.obj(graph_path);registry=r.obj(cfg['registry']);cross=r.obj(cfg['crosswalk']);mappings=cross.get('mappings',[]);namespace=graph.get('namespace_id');mode='active_v11'
            if namespace!=registry.get('namespace_id'):r.issues.append('Graph and registry namespaces disagree')
            catalog=r.obj(cfg['catalog']);base=Path(cfg['catalog']).parent
            for loc in catalog.get('languages',[]):
                lang=loc.get('tag')
                for layer in loc.get('layers',[]):
                    rel=(base/str(layer.get('path',''))).as_posix();blob=r.blob(rel)
                    if blob is None:continue
                    if hashlib.sha256(blob).hexdigest()!=layer.get('sha256'):r.issues.append('Dictionary digest mismatch: '+rel);continue
                    try:entries=json.loads(blob).get('entries',[]) if layer.get('kind')=='curated' else [json.loads(s) for s in blob.decode('utf-8').splitlines() if s.strip()]
                    except (ValueError,UnicodeError,AttributeError):r.issues.append('Invalid dictionary: '+rel);continue
                    for entry in entries:
                        kid=entry.get('semantic_id');term=entry.get('preferred_term')
                        if not isinstance(kid,str) or not isinstance(term,str):continue
                        score=({'fr':300,'en':200,'und':0}.get(lang,100),layer.get('priority',0))
                        if kid not in labels or score>labels[kid][0]:labels[kid]=(score,term);label_origins[kid]={'kind':'dictionary','path':rel}
                        terms.append((kid,str(lang),term))
            modelrel=(Path(graph_path).parent/'structured-model.json').as_posix()
            if modelrel in registered:
                model=r.obj(modelrel);shapes=model.get('node_shapes',{});components={f['assertion_id'] for shape in shapes.values() for f in shape.get('fields',[]) if 'assertion_id' in f}
                ledgerrel=model.get('source_ledger')
            else:ledgerrel=(Path(graph_path).parent/'source-ledger.json').as_posix()
            if ledgerrel in registered:ledger=r.obj(ledgerrel).get('records',{})
    else:
        # Recognized native v6 assertion shape only; arbitrary JSON is not guessed into a graph.
        for rel,entry in registered.items():
            if not rel.endswith('.json'):continue
            d=r.obj(rel)
            if d.get('artifact_type')=='kristal_state' and isinstance(d.get('assertions'),list):
                graph=d;graph_path=rel;namespace=ws.get('state_ref');mode='registered_legacy_v6';break
    if mode=='active_v11' and (graph.get('artifact_type')!='kristal_semantic_graph' or not all(isinstance(graph.get(k),list) for k in ('entities','properties','sources','assertions'))):
        r.issues.append('Selected v11 graph is missing or structurally unsupported');mode='unsupported'
    assertions=[]
    if mode=='active_v11' and graph.get('artifact_type')=='kristal_semantic_graph':
        for a in graph.get('assertions',[]):
            if not isinstance(a,dict) or not all(isinstance(a.get(k),str) for k in ('id','subject','predicate')):r.issues.append('Malformed assertion in selected graph');continue
            assertions.append({'id':a['id'],'subject':a['subject'],'predicate':a['predicate'],'object':a.get('object'),'sources':a.get('sources',[]),'qualifiers':a.get('qualifiers',[]),'component':a['id'] in components})
        entity_ids=set(graph.get('entities',[]));property_ids=set(graph.get('properties',[]));source_ids=set(graph.get('sources',[]))
    elif mode=='registered_legacy_v6':
        entity_ids=set();property_ids=set();source_ids=set()
        for a in graph['assertions']:
            statement=a.get('statement',{});subject=statement.get('subject',{});subject=subject.get('id') if isinstance(subject,dict) else subject;predicate=statement.get('predicate');obj=statement.get('object',{})
            if not isinstance(subject,str) or not isinstance(predicate,str):r.issues.append('Unsupported legacy assertion shape');continue
            entity_ids.add(subject);property_ids.add(predicate)
            if isinstance(obj,dict) and obj.get('kind')=='item' and isinstance(obj.get('id'),str):entity_ids.add(obj['id'])
            sources=a.get('evidence_refs',[]);source_ids.update(x for x in sources if isinstance(x,str));assertions.append({'id':a.get('assertion_id') or 'legacy:'+str(len(assertions)),'subject':subject,'predicate':predicate,'object':obj,'sources':sources,'qualifiers':a.get('coordinates',[]),'component':False})
    else:
        entity_ids=set();property_ids=set();source_ids=set()
        r.issues.append('No supported selected canonical content adapter; unknown is not zero')
    unique={}
    for a in assertions:
        if a['id'] in unique:r.issues.append('Duplicate assertion ID in selected content: '+str(a['id']))
        else:unique[a['id']]=a
    assertions=list(unique.values())
    accepted={m.get('external_ref',{}).get('id'):m.get('local_ref',{}).get('id') for m in mappings if m.get('status')=='accepted' and m.get('relation')=='exactMatch'};external={v:k for k,v in accepted.items()};rank=Counter();regimes=Counter();subjects=Counter();relations=Counter();known_source_claims=0
    for a in assertions:
        record=next((ledger[s].get('record') for s in a['sources'] if s in ledger and isinstance(ledger[s],dict) and ledger[s].get('record')),None)
        primary=record is not None and a['subject']==accepted.get(record.get('wikidata_subject')) and a['predicate']==accepted.get(record.get('wikidata_property'))
        a['rank']=record.get('full_source_claim',{}).get('rank') if primary else None;a['regime']='wikidata_source_report' if primary else 'structured_component' if a['component'] else 'graph_assertion'
        if primary:rank[a['rank'] or 'unknown']+=1;known_source_claims+=1
        regimes[a['regime']]+=1
        if not a['component'] and a['subject'] not in shapes:subjects[a['subject']]+=1;relations[a['predicate']]+=1
    legacy_map=r.obj('.kristal/v11/identity-migration-map.json',True) if mode=='active_v11' else {}
    if legacy_map and legacy_map.get('namespace_id')==namespace:
        for kind,allowed in [('Q',entity_ids),('P',property_ids)]:
            for legacy,kid in legacy_map.get('by_kind',{}).get(kind,{}).items():
                if kid in allowed and isinstance(legacy,str):
                    terms.append((kid,'und',legacy))
                    if kid not in labels or labels[kid][1] in {kid,external.get(kid)}:
                        labels[kid]=((-1,-1),legacy);label_origins[kid]={'kind':'reported_legacy_key','path':'.kristal/v11/identity-migration-map.json'}
    def label(k):return labels.get(k,((0,0),None))[1]
    def described(k):return bool(label(k) and label(k) not in {k,external.get(k)} and label_origins.get(k,{}).get('kind')!='reported_legacy_key')
    def top(counter):return [{'id':k,'label':label(k),'external_id':external.get(k),'display_source':label_origins.get(k),'assertions':n} for k,n in counter.most_common(20)]
    metrics={'entities':len(entity_ids),'properties':len(property_ids),'sources':len(source_ids),'assertions':len(assertions),'structured_values':len(shapes),'structured_components':len(components),'main_assertions':sum(not a['component'] for a in assertions),'wikidata_source_claims':known_source_claims if ledger else None,'wikidata_accepted_exact':sum(m.get('status')=='accepted' and m.get('relation')=='exactMatch' for m in mappings),'wikidata_candidates':sum(m.get('status')=='candidate' for m in mappings),'rank_counts':dict(rank),'regime_counts':dict(regimes),'entities_with_descriptive_labels':sum(described(k) for k in entity_ids),'properties_with_descriptive_labels':sum(described(k) for k in property_ids),'dictionary_languages':sorted({lang for _,lang,_ in terms})} if mode!='unsupported' else {k:None for k in ('entities','properties','sources','assertions','main_assertions','wikidata_source_claims','structured_values')}
    descriptor={k:ws.get(k) for k in ('subject','state_scope','native_model','semantic_ownership','invariants') if k in ws}
    summary={'format':FORMAT,'title':ws.get('title') or root.name,'state_ref':ws.get('state_ref'),'state_commitment':meta.get('state_commitment'),'namespace_id':namespace,'native_kind':meta.get('native_kind'),'readiness':meta.get('readiness'),'mode':mode,'content_status':'unsupported' if mode=='unsupported' else 'partial' if r.issues else 'observed','graph_path':graph_path,'canonical_binding':'registered_selector_only_not_independent_state_verification','structure':{'registered_artifacts':len(registered),'declared_contracts':sorted({str(v.get('logical_contract',{}).get('id')) for v in registered.values()}),'declared_targets':ws.get('target',{}),'source_ledger':ledgerrel if ledger else None,'scan_inputs':len(r.deps)},'descriptors':descriptor,'metrics':metrics,'top_subjects':top(subjects),'top_relations':top(relations),'issues':r.issues,'coverage_note':'Counts describe only the selected recognized graph, not every file or factual completeness. Top subjects are ranked by assertion count, not semantic importance. Wikidata and lexical decisions are reported, not independently certified.'}
    nodes=[(k,'entity' if k in entity_ids else 'property',label(k),external.get(k)) for k in sorted(entity_ids|property_ids)]
    return summary,nodes,assertions,terms,r.deps

DDL='''CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT); CREATE TABLE workspaces(id TEXT PRIMARY KEY,path TEXT UNIQUE,summary TEXT,deps TEXT); CREATE TABLE nodes(workspace TEXT,id TEXT,kind TEXT,label TEXT,external_id TEXT,PRIMARY KEY(workspace,id)); CREATE INDEX node_label ON nodes(label); CREATE INDEX node_external ON nodes(external_id); CREATE TABLE terms(workspace TEXT,id TEXT,language TEXT,term TEXT,search TEXT); CREATE INDEX term_search ON terms(search); CREATE TABLE assertions(workspace TEXT,id TEXT,subject TEXT,predicate TEXT,object TEXT,sources TEXT,qualifiers TEXT,rank TEXT,regime TEXT,PRIMARY KEY(workspace,id)); CREATE INDEX assertion_subject ON assertions(workspace,subject,predicate); CREATE INDEX assertion_predicate ON assertions(workspace,predicate);'''
def _populate_catalog(roots,destination,force=False,max_bytes=64*1024*1024):
    roots=[Path(p).expanduser().resolve() for p in roots];projects=list(candidates(roots));dest=Path(destination).expanduser().absolute()
    if dest.is_symlink() or any(dest.resolve().is_relative_to(p) for p in projects):raise ManagerError('The derived database must be outside source Kristal workspaces')
    dest.parent.mkdir(parents=True,exist_ok=True);exists=dest.exists()
    if not exists:
        fd=os.open(dest,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    db=sqlite3.connect(dest);changed=0;cached=0
    try:
        if not exists:db.executescript(DDL);db.execute('INSERT INTO meta VALUES (?,?)',('format',FORMAT));db.commit()
        if db.execute('SELECT value FROM meta WHERE key=?',('format',)).fetchone()!=(FORMAT,):raise ManagerError('Not a Manager content catalog; refusing to overwrite')
        seen=set();db.execute('BEGIN IMMEDIATE')
        for p in projects:
            key=hashlib.sha256(str(p).encode()).hexdigest();seen.add(key);old=db.execute('SELECT summary,deps FROM workspaces WHERE id=?',(key,)).fetchone()
            if old and not force and json.loads(old[0]).get('content_status')!='error' and json.loads(old[0]).get('catalog_engine')==ENGINE_VERSION and json.loads(old[0]).get('scan_max_file_bytes')==max_bytes and Reader(p,max_bytes).unchanged(json.loads(old[1])):cached+=1;continue
            try:summary,nodes,assertions,terms,deps=inspect_content(p,max_bytes)
            except (ValueError,TypeError,KeyError,AttributeError) as exc:
                reader=Reader(p,max_bytes);ws=reader.obj('kristal.workspace.json')
                summary={'format':FORMAT,'title':ws.get('title') or p.name,'state_ref':ws.get('state_ref'),'namespace_id':None,'native_kind':None,'readiness':'NOT EVALUATED','content_status':'error','mode':'unsupported','graph_path':None,'descriptors':{},'metrics':{'assertions':None,'entities':None,'properties':None,'wikidata_source_claims':None},'top_subjects':[],'top_relations':[],'issues':['Malformed selected content: '+str(exc)],'coverage_note':'Content is unknown; no zero count or semantic completeness is inferred.'}
                nodes=[];assertions=[];terms=[];deps=reader.deps
            changed+=1
            # Store cache version/options with its observed fingerprint in the meta envelope.
            summary['scan_max_file_bytes']=max_bytes;summary['catalog_engine']=ENGINE_VERSION;summary['observed_at_epoch']=time.time()
            for table in ('nodes','assertions','terms'):db.execute(f'DELETE FROM {table} WHERE workspace=?',(key,))
            db.execute('INSERT OR REPLACE INTO workspaces VALUES (?,?,?,?)',(key,str(p),encoded(summary),encoded(deps)))
            db.executemany('INSERT INTO nodes VALUES (?,?,?,?,?)',[(key,*n) for n in nodes]);db.executemany('INSERT INTO terms VALUES (?,?,?,?,?)',[(key,k,lang,t,t.casefold()) for k,lang,t in set(terms)])
            db.executemany('INSERT INTO assertions VALUES (?,?,?,?,?,?,?,?,?)',[(key,a['id'],a['subject'],a['predicate'],encoded(a['object']),encoded(a['sources']),encoded(a['qualifiers']),a['rank'],a['regime']) for a in assertions])
        for (key,) in db.execute('SELECT id FROM workspaces').fetchall():
            if key not in seen:
                for table in ('nodes','assertions','terms'):db.execute(f'DELETE FROM {table} WHERE workspace=?',(key,))
                db.execute('DELETE FROM workspaces WHERE id=?',(key,))
        db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',('roots',encoded([str(p) for p in roots])));db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',('last_scan_epoch',str(time.time())));db.commit()
        return {'format':FORMAT,'database':str(dest),'workspaces':len(projects),'updated':changed,'cached':cached,'source_workspaces_modified':False}
    except sqlite3.DatabaseError as exc:db.rollback();raise ManagerError('Invalid or inaccessible catalog: '+str(exc)) from exc
    finally:db.close()
def summaries(database):
    p=Path(database).resolve()
    if not p.is_file():raise ManagerError('Catalog database does not exist')
    db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
    try:
        if db.execute('SELECT value FROM meta WHERE key=?',('format',)).fetchone()!=(FORMAT,):raise ManagerError('Unsupported catalog')
        records=[{'catalog_id':key,**json.loads(s)} for key,s in db.execute('SELECT id,summary FROM workspaces ORDER BY path')];counts=Counter(r['state_ref'] for r in records if r['state_ref'])
        for r in records:r['identity_collision']=bool(r['state_ref'] and counts[r['state_ref']]>1)
        return {'format':FORMAT,'mode':'local-descriptive-content','records':records,'record_count':len(records)}
    finally:db.close()
def search_catalog(database,text,limit=100):
    p=Path(database).resolve()
    if not p.is_file():raise ManagerError('Catalog database does not exist')
    db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
    try:
        exact=bool(re.fullmatch(r'(?:[QP]|K[QP])[1-9][0-9]*',text,re.IGNORECASE))
        word=text.upper() if exact else text
        where='n.id=? OR n.external_id=?' if exact else 'n.id=? OR n.external_id=? OR instr(t.search,?)>0'
        params=[word,word] if exact else [word,word,text.casefold()]
        params.append(max(1,min(limit,1000)))
        rows=db.execute('SELECT DISTINCT n.workspace,n.id,n.kind,n.label,n.external_id,w.summary FROM nodes n JOIN workspaces w ON w.id=n.workspace LEFT JOIN terms t ON t.workspace=n.workspace AND t.id=n.id WHERE '+where+' ORDER BY n.workspace,n.id LIMIT ?',params).fetchall()
        return [{'catalog_id':w,'kristal':json.loads(s)['title'],'namespace_id':json.loads(s)['namespace_id'],'id':i,'kind':k,'label':l,'external_id':e} for w,i,k,l,e,s in rows]
    finally:db.close()

def write_overview(database,destination,overwrite=False):
    # HTML embeds JSON as inert data and renders every source string with textContent.
    payload=summaries(database);data=json.dumps(payload,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    page='''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kristal — catalogue du contenu</title><style>body{font:16px system-ui;background:#f2f6f5;color:#173630;margin:0}header,main{max-width:1150px;margin:auto;padding:26px}h1{margin:0}input{box-sizing:border-box;width:100%;padding:13px;border:1px solid #9ebcb4;border-radius:10px;margin:18px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:16px}article{background:white;padding:20px;border-radius:14px;border:1px solid #d7e5df}h2{margin:0 0 8px}.muted{color:#526e65;font-size:14px}.counts{font-weight:650;margin:14px 0}details{margin-top:12px}li{margin:5px 0}pre{white-space:pre-wrap;word-break:break-word;font-size:12px}.issue{color:#8b430f}</style><header><h1>Les cristaux, côté contenu</h1><p>Catalogue local descriptif · sources en lecture seule · aucun statut de vérité déduit</p><input id="filter" placeholder="Filtrer les aperçus : cristal, domaine, sujets présentés…"><div id="status"></div></header><main><div class="grid" id="grid"></div></main><script id="data" type="application/json">DATA</script><script>const records=JSON.parse(document.getElementById('data').textContent).records;const q=document.getElementById('filter'),grid=document.getElementById('grid');function el(tag,text,cls){const n=document.createElement(tag);n.textContent=text;if(cls)n.className=cls;return n}function render(){grid.replaceChildren();let shown=0;for(const r of records){if(q.value&&!JSON.stringify(r).toLocaleLowerCase().includes(q.value.toLocaleLowerCase()))continue;shown++;const c=el('article','');c.append(el('h2',r.title),el('div',`${r.content_status} · ${r.mode} · ${r.native_kind||'modèle non déclaré'}`,'muted'));if(r.identity_collision)c.append(el('p','Identité partagée avec une autre copie : les entrées restent distinctes.','issue'));const desc=r.descriptors.subject||{};c.append(el('p',desc.description||desc.orientation||desc.domain||r.descriptors.state_scope?.domain||'Domaine non déclaré'));const m=r.metrics;const fmt=x=>x==null?'non mesuré':Number(x).toLocaleString('fr');c.append(el('p',`${fmt(m.entities)} entités · ${fmt(m.properties)} propriétés · ${fmt(m.assertions)} assertions`,'counts'));c.append(el('p',`${fmt(m.main_assertions)} assertions principales · ${fmt(m.structured_components)} composantes de valeurs`,'muted'));c.append(el('p',`Libellés descriptifs : ${fmt(m.entities_with_descriptive_labels)} entités, ${fmt(m.properties_with_descriptive_labels)} propriétés`,'muted'));c.append(el('p',`Wikidata : ${fmt(m.wikidata_source_claims)} déclarations identifiées · ${fmt(m.wikidata_candidates)} correspondances candidates`,'muted'));for(const [title,rows]of [['Sujets les plus décrits',r.top_subjects],['Relations les plus fréquentes',r.top_relations]]){const d=el('details','');d.append(el('summary',title));const ul=el('ul','');for(const x of rows)ul.append(el('li',`${x.label||x.external_id||x.id} — ${x.assertions} assertions${x.display_source?.kind==='reported_legacy_key'?' · clé native déclarée':''}`));d.append(ul);c.append(d)}if(r.issues.length)c.append(el('p',r.issues.join(' · '),'issue'));const d=el('details','');d.append(el('summary','Structure, sources et limites observées'),el('pre',JSON.stringify({state_ref:r.state_ref,graph:r.graph_path,structure:r.structure,descriptors:r.descriptors,metrics:r.metrics,coverage:r.coverage_note},null,2)));c.append(d);grid.append(c)}document.getElementById('status').textContent=`${shown} / ${records.length} cristaux · importance éditoriale non évaluée`;}q.addEventListener('input',render);render();</script></html>'''.replace('DATA',data)
    dest=Path(destination)
    db=sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True)
    try:
        if any(dest.resolve().is_relative_to(Path(p)) for (p,) in db.execute('SELECT path FROM workspaces')):raise ManagerError('Overview must be outside source workspaces')
    finally:db.close()
    if dest.is_symlink() or (dest.exists() and not overwrite):raise ManagerError('Overview exists; use overwrite explicitly')
    dest.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(dest,os.O_WRONLY|os.O_CREAT|(os.O_TRUNC if overwrite else os.O_EXCL),0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as f:f.write(page)
    return dest

def show_concept(database,text,catalog_id=None,limit=50):
    """Show scoped outgoing assertions, with one level of structured-value fields."""
    matches=search_catalog(database,text,1000)
    if catalog_id:matches=[m for m in matches if m['catalog_id']==catalog_id]
    db=sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True);results=[]
    try:
        for match in matches:
            w=match['catalog_id'];kid=match['id']
            def named(i):
                row=db.execute('SELECT label,external_id FROM nodes WHERE workspace=? AND id=?',(w,i)).fetchone();return {'id':i,'namespace_id':match['namespace_id'],'label':row[0] if row else None,'external_id':row[1] if row else None}
            rows=db.execute('SELECT id,predicate,object,sources,qualifiers,rank,regime FROM assertions WHERE workspace=? AND subject=? ORDER BY id LIMIT ?',(w,kid,max(1,min(limit,1000)))).fetchall();items=[]
            for aid,pred,obj,sources,quals,rank,regime in rows:
                obj=json.loads(obj);item={'id':aid,'predicate':named(pred),'object':obj,'sources':json.loads(sources),'qualifiers':json.loads(quals),'rank':rank,'regime':regime}
                if isinstance(obj,dict) and obj.get('kind')=='entity':
                    target=obj.get('id');item['object_ref']=named(target)
                    fields=db.execute("SELECT predicate,object,sources FROM assertions WHERE workspace=? AND subject=? AND regime='structured_component' ORDER BY predicate LIMIT 100",(w,target)).fetchall()
                    if fields:item['structured_fields']=[{'predicate':named(p),'object':json.loads(o),'sources':json.loads(s)} for p,o,s in fields]
                items.append(item)
            results.append({**match,'assertions':items,'limit':max(1,min(limit,1000)),'limit_reached':bool(len(items)>=max(1,min(limit,1000)))})
        return results
    finally:db.close()


def build_catalog(roots,destination,force=False,max_bytes=64*1024*1024):
    """Publish a complete SQLite snapshot atomically; failed scans retain the old DB."""
    import uuid
    roots=[Path(p).expanduser().resolve() for p in roots]
    if not roots:raise ManagerError('Supply at least one source root')
    projects=list(candidates(roots));dest=Path(destination).expanduser().absolute()
    if dest.is_symlink() or any(dest.resolve().is_relative_to(p) for p in projects):raise ManagerError('The derived database must be outside source Kristal workspaces')
    dest.parent.mkdir(parents=True,exist_ok=True)
    stage=dest.parent/(dest.name+'.'+uuid.uuid4().hex+'.building')
    try:
        if dest.exists():
            original=sqlite3.connect(dest.resolve().as_uri()+'?mode=ro',uri=True)
            try:
                if original.execute('SELECT value FROM meta WHERE key=?',('format',)).fetchone()!=(FORMAT,):raise ManagerError('Not a Manager content catalog; refusing to overwrite')
                fd=os.open(stage,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
                copy=sqlite3.connect(stage)
                try:original.backup(copy)
                finally:copy.close()
            finally:original.close()
        result=_populate_catalog(roots,stage,force,max_bytes)
        check=sqlite3.connect(stage)
        try:
            if check.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ManagerError('Catalog integrity check failed; previous database retained')
        finally:check.close()
        with stage.open('rb') as f:os.fsync(f.fileno())
        os.replace(stage,dest)
        result['database']=str(dest.resolve());result['atomic_snapshot']=True
        return result
    except sqlite3.DatabaseError as exc:raise ManagerError('Invalid or inaccessible catalog; previous database retained: '+str(exc)) from exc
    finally:stage.unlink(missing_ok=True)
