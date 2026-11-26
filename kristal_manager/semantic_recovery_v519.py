"""Private lexical evidence recovery; never changes canonical or public data."""
from __future__ import annotations
import argparse, hashlib, json, os, re, sqlite3, stat, unicodedata
from collections import Counter
from pathlib import Path, PurePosixPath
from .local_first_audit import ReadOnlyTree, LocalFirstAuditError
from .semantic_federation_inventory import _new_destination
from .active_semantic_federation_v518 import _hash_file, build_active_federation
from .local_semantic_evolution_v516 import evolve as refresh_v516

FORMAT='koa.kristal-lexical-recovery/1.0'
LANG=re.compile(r'^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$')
EXT=re.compile(r'^[QP][1-9][0-9]*$')
MAX_BYTES=64*1024*1024
TARGET_LOCALES=('en','fr','es','de','nl','sv','da','no','nn','fi','et','af','it','pt')

def fail(msg): raise LocalFirstAuditError('V5.19: '+msg)
def js(obj): return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def text(s): return isinstance(s,str) and bool(s.strip()) and len(s)<=100000
def fold(s): return unicodedata.normalize('NFKC',s).casefold().strip()
def guard(p):
    p=Path(p).absolute()
    for q in [*reversed(p.parents),p]:
        if q.exists() or q.is_symlink():
            st=q.lstat()
            if stat.S_ISLNK(st.st_mode) or getattr(st,'st_file_attributes',0)&0x400:
                fail('link/reparse point: '+str(q))
    return p

def source_class(path):
    parts=PurePosixPath(path).parts
    if len(parts)<3 or not path.endswith(('.json','.jsonl')): return None
    rel='/'.join(parts[1:])
    if '/dictionaries/' in '/'+rel and rel.startswith(('canon/','.kristal/v11/')) and parts[-1]!='catalog.json': return 'v11_dictionary'
    if rel.startswith('.kristal/v8/lexicon-') and rel.endswith('.json'): return 'legacy_v8'
    if rel.startswith('external-source-library/wikidata/') and '/entities/' in rel and EXT.fullmatch(PurePosixPath(rel).stem): return 'wikidata_cache'
    return None

def paths(tree,owner):
    if tree.zip:
        yield from sorted(p for p in tree._names if p.startswith(owner+'/') and source_class(p)); return
    for rel in ('canon','.kristal/v11','.kristal/v8','external-source-library/wikidata'):
        start=tree.root/owner/rel
        if not start.exists() and not start.is_symlink(): continue
        guard(start)
        for parent,dirs,files in os.walk(start,followlinks=False):
            dirs.sort(); files.sort()
            for d in dirs: guard(Path(parent)/d)
            for name in files:
                p=Path(parent)/name; path=p.relative_to(tree.root).as_posix()
                if source_class(path): guard(p); yield path

def load(tree,path):
    if not tree.zip: guard(tree.root/path)
    with tree.open(path) as f: raw=f.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES: fail('oversize source: '+path)
    return raw,hashlib.sha256(raw).hexdigest()

def rows(raw,path):
    if path.endswith('.jsonl'):
        for n,line in enumerate(raw.decode('utf-8-sig').splitlines(),1):
            if line.strip(): yield str(n),json.loads(line),{}
    else:
        doc=json.loads(raw.decode('utf-8-sig'))
        if isinstance(doc,dict) and isinstance(doc.get('entries'),list):
            for n,row in enumerate(doc['entries']): yield '/entries/'+str(n),row,doc

def schema(db):
    db.executescript('''
    CREATE TABLE recovery_source(path TEXT PRIMARY KEY,owner_slug TEXT NOT NULL,kind TEXT NOT NULL,sha256 TEXT NOT NULL,status TEXT NOT NULL,detail TEXT);
    CREATE TABLE recovery_evidence(namespace_id TEXT NOT NULL,semantic_id TEXT NOT NULL,language_tag TEXT NOT NULL,preferred_term TEXT NOT NULL,term_folded TEXT NOT NULL,source_path TEXT NOT NULL,locator TEXT NOT NULL,method TEXT NOT NULL,external_id TEXT,description TEXT,aliases_json TEXT NOT NULL,record_json TEXT NOT NULL,PRIMARY KEY(source_path,locator,namespace_id,semantic_id,language_tag));
    CREATE INDEX recovery_cell ON recovery_evidence(namespace_id,semantic_id,language_tag);
    CREATE INDEX recovery_term ON recovery_evidence(term_folded);
    CREATE TABLE recovery_legacy(owner_slug TEXT NOT NULL,identity_space TEXT,legacy_id TEXT NOT NULL,language_tag TEXT NOT NULL,preferred_term TEXT NOT NULL,source_path TEXT NOT NULL,locator TEXT NOT NULL,record_json TEXT NOT NULL,PRIMARY KEY(source_path,locator));
    CREATE TABLE recovery_resolution(namespace_id TEXT NOT NULL,semantic_id TEXT NOT NULL,language_tag TEXT NOT NULL,status TEXT NOT NULL,suggested_term TEXT,variants_json TEXT NOT NULL,PRIMARY KEY(namespace_id,semantic_id,language_tag));
    CREATE TABLE recovery_profile_review(owner_slug TEXT PRIMARY KEY,reason TEXT NOT NULL,available_complete_revisions INTEGER NOT NULL);
    CREATE VIEW recovery_lookup AS SELECT namespace_id,semantic_id,language_tag,preferred_term AS term,'ACTIVE_CANONICAL' AS status FROM lexical UNION ALL SELECT namespace_id,semantic_id,language_tag,suggested_term,status FROM recovery_resolution WHERE status='UNREVIEWED_CONSENSUS';
    ''')

def scan_owner(db,tree,slug,owner,ns,ids,counts):
    accepted={qid:sid for sid,(kind,qid) in ids.items() if qid and kind in ('entity','property')}
    def add(sid,tag,term,path,loc,method,record,external=None):
        if not isinstance(sid,str) or sid not in ids or ids[sid][0] not in ('entity','property') or not isinstance(tag,str) or not LANG.fullmatch(tag) or not text(term):
            counts['invalid_or_unmatched_rows']+=1; return
        if external is not None and (not isinstance(external,str) or not EXT.fullmatch(external) or ids[sid][1]!=external):
            counts['external_reference_not_active_accepted']+=1; return
        aliases=record.get('aliases',[]); aliases=[x for x in aliases if text(x)] if isinstance(aliases,list) else []
        desc=record.get('description')
        db.execute('INSERT INTO recovery_evidence VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(ns,sid,tag,term,fold(term),path,loc,method,external,desc if text(desc) else None,js(aliases),js(record)))
        counts['evidence_rows']+=1
    for path in paths(tree,owner):
        kind=source_class(path); raw,digest=load(tree,path)
        db.execute('INSERT INTO recovery_source VALUES (?,?,?,?,?,?)',(path,slug,kind,digest,'SCANNED_UNREVIEWED',None)); counts['source_files']+=1
        before=counts.copy(); db.execute('SAVEPOINT source_scan')
        try:
            if kind=='wikidata_cache':
                doc=json.loads(raw.decode('utf-8-sig')); qid=doc.get('id')
                if qid!=PurePosixPath(path).stem or qid not in accepted: counts['cache_without_active_accepted_anchor']+=1
                else:
                    # Preserve declared source assurance, never infer it from a local hash.
                    catalog_path=str(PurePosixPath(path).parent.parent/'source-catalog.json')
                    assurance={'source_catalog_path':catalog_path,'source_catalog_sha256':None,'checksum_verification_declared':None}
                    if tree.exists(catalog_path):
                        catalog_raw,catalog_sha=load(tree,catalog_path)
                        catalog=json.loads(catalog_raw.decode('utf-8-sig'))
                        assurance.update(source_catalog_sha256=catalog_sha,checksum_verification_declared=catalog.get('checksum_verification'))
                    for tag,label in doc.get('labels',{}).items():
                        if not isinstance(label,dict) or label.get('language')!=tag: continue
                        desc=doc.get('descriptions',{}).get(tag,{}); aliases=doc.get('aliases',{}).get(tag,[])
                        row={'preferred_term':label.get('value'),'description':desc.get('value') if isinstance(desc,dict) and desc.get('language')==tag else None,'aliases':[a.get('value') for a in aliases if isinstance(a,dict) and a.get('language')==tag],'external_id':qid,'source_revision':doc.get('lastrevid'),'language':tag,'source_assurance':assurance}
                        add(accepted[qid],tag,row['preferred_term'],path,'/labels/'+tag,'LOCAL_WIKIDATA_CACHE_ACTIVE_ACCEPTED_ANCHOR',row,qid)
            else:
                for loc,row,parent in rows(raw,path):
                    if not isinstance(row,dict): continue
                    if kind=='legacy_v8':
                        if parent.get('artifact_type')!='kristall_lexicon': continue
                        ref=row.get('semantic_ref',{}); tag,term=parent.get('language'),row.get('preferred_term')
                        if isinstance(ref,dict) and text(ref.get('id')) and text(tag) and LANG.fullmatch(tag) and text(term):
                            db.execute('INSERT INTO recovery_legacy VALUES (?,?,?,?,?,?,?,?)',(slug,ref.get('identity_space'),ref['id'],tag,term,path,loc,js(row))); counts['legacy_unmapped_rows']+=1
                        continue
                    if not ns: continue
                    row_ns=row.get('namespace_id',parent.get('namespace_id'))
                    if row_ns!=ns or (parent.get('namespace_id') is not None and parent['namespace_id']!=ns): counts['out_of_scope_rows']+=1; continue
                    add(row.get('semantic_id'),row.get('language',parent.get('language')),row.get('preferred_term'),path,loc,'HISTORICAL_SCOPED_RECORD_UNREVIEWED',row,row.get('external_id'))
            db.execute('RELEASE source_scan')
        except (ValueError,TypeError,AttributeError,KeyError,UnicodeError) as exc:
            db.execute('ROLLBACK TO source_scan'); db.execute('RELEASE source_scan'); counts.clear(); counts.update(before); counts['malformed_source_files']+=1
            db.execute('UPDATE recovery_source SET status=?,detail=? WHERE path=?',('REJECTED_MALFORMED',str(exc)[:500],path))

def resolve(db):
    for ns,sid,tag,variants in db.execute('SELECT namespace_id,semantic_id,language_tag,json_group_array(DISTINCT preferred_term) FROM recovery_evidence GROUP BY namespace_id,semantic_id,language_tag'):
        terms=sorted(json.loads(variants)); current=db.execute('SELECT preferred_term FROM lexical WHERE namespace_id=? AND semantic_id=? AND language_tag=?',(ns,sid,tag)).fetchone()
        if current: status='ACTIVE_CONFIRMED_BY_OBSERVATION' if terms==[current[0]] else 'ACTIVE_PRECEDENCE_CONFLICT'; suggestion=None
        else: status='UNREVIEWED_CONSENSUS' if len(terms)==1 else 'UNREVIEWED_CONFLICT'; suggestion=terms[0] if len(terms)==1 else None
        db.execute('INSERT INTO recovery_resolution VALUES (?,?,?,?,?,?)',(ns,sid,tag,status,suggestion,js(terms)))

def verify(tree,expected):
    if set(tree.workspace_roots())!={w[1] for w in expected}: fail('workspace list changed since V5.18')
    def digest(path):
        if not tree.zip: guard(tree.root/path)
        return tree.digest(path)
    for slug,owner,ns,active,ph,st,pr,complete in expected:
        if digest(owner+'/canon/state.index.json')!=st: fail('state drift: '+slug)
        profile=owner+'/.kristal/v11/authoring.json'; pointer=owner+'/derived/semantic/active-resolution.json'
        if not tree.zip: guard(tree.root/profile); guard(tree.root/pointer)
        if tree.exists(profile)!=bool(active): fail('profile drift: '+slug)
        if not active: continue
        if digest(profile)!=ph: fail('profile hash drift: '+slug)
        p=tree.read_json(pointer)
        if (p.get('profile_sha256'),p.get('state_index_sha256'),p.get('projection_sha256'))!=(ph,st,pr): fail('pointer drift: '+slug)
        proj_path=p['projection']
        if not proj_path.startswith('derived/semantic/v516/active-'): fail('unexpected projection path')
        if digest(owner+'/'+proj_path)!=pr: fail('projection hash drift: '+slug)
        proj=tree.read_json(owner+'/'+proj_path,limit=MAX_BYTES)
        if proj.get('namespace_id')!=ns or proj.get('owner_slug')!=slug: fail('projection scope mismatch')
        for role in proj['active_roles'].values():
            if digest(owner+'/'+role['path'])!=role['sha256']: fail('active role drift: '+slug)
        for lang in proj['languages'].values():
            for layer in lang['layers']:
                if digest(owner+'/'+layer['path'])!=layer['sha256']: fail('active layer drift: '+slug)

def report_counts(db):
    def s(q): return db.execute(q).fetchone()[0]
    return {'active_identities':s('SELECT count(*) FROM identity'), 'lexically_eligible_KQ_KP':s("SELECT count(*) FROM identity WHERE kind IN ('entity','property')"), 'KQ_KP_with_active_label':s("SELECT count(*) FROM identity i WHERE kind IN ('entity','property') AND EXISTS(SELECT 1 FROM lexical l WHERE l.namespace_id=i.namespace_id AND l.semantic_id=i.semantic_id)"), 'active_language_labels':s('SELECT count(*) FROM lexical'), 'recorded_accepted_wikidata':s('SELECT count(*) FROM identity WHERE accepted_wikidata IS NOT NULL'), 'active_profiles':s('SELECT count(*) FROM workspace WHERE active=1'), 'missing_profiles':s('SELECT count(*) FROM workspace WHERE active=0'), 'recovery_consensus_cells':s("SELECT count(*) FROM recovery_resolution WHERE status='UNREVIEWED_CONSENSUS'"), 'recovery_conflicting_cells':s("SELECT count(*) FROM recovery_resolution WHERE status='UNREVIEWED_CONFLICT'"), 'active_precedence_conflicts':s("SELECT count(*) FROM recovery_resolution WHERE status='ACTIVE_PRECEDENCE_CONFLICT'"), 'unlabelled_KQ_KP_with_recovery_hint':s("SELECT count(*) FROM identity i WHERE NOT EXISTS(SELECT 1 FROM lexical l WHERE l.namespace_id=i.namespace_id AND l.semantic_id=i.semantic_id) AND EXISTS(SELECT 1 FROM recovery_resolution r WHERE r.namespace_id=i.namespace_id AND r.semantic_id=i.semantic_id AND r.status='UNREVIEWED_CONSENSUS')")}

def build(locals_root,private_dir,source_db):
    locals_root=guard(locals_root); private_dir=guard(private_dir); source_db=guard(source_db)
    token='SEMANTIC_V519_'+os.urandom(6).hex(); output=_new_destination(private_dir/(token+'.sqlite'),locals_root); report=_new_destination(private_dir/(token+'.json'),locals_root)
    tree=ReadOnlyTree(locals_root); src=sqlite3.connect(source_db.resolve().as_uri()+'?mode=ro',uri=True); db=None; created=False; counts=Counter()
    try:
        source_sha=_hash_file(source_db)
        if src.execute('PRAGMA quick_check').fetchone()!=('ok',): fail('V5.18 SQLite integrity failed')
        meta=json.loads(src.execute("SELECT value FROM metadata WHERE key='summary_json'").fetchone()[0])
        if meta.get('status')!='ACTIVE_DERIVED_FEDERATION_BUILT': fail('not V5.18 active federation')
        expected=list(src.execute('SELECT slug,local_directory,namespace_id,active,profile_sha256,state_sha256,projection_sha256,available_complete_revisions FROM workspace ORDER BY slug'))
        verify(tree,expected)
        fd=os.open(output,os.O_CREAT|os.O_EXCL|os.O_RDWR,0o600); os.close(fd); created=True
        db=sqlite3.connect(output); src.backup(db); schema(db)
        for slug,owner,ns,active,ph,st,pr,complete in expected:
            if not active: db.execute('INSERT INTO recovery_profile_review VALUES (?,?,?)',(slug,'NO_ACTIVE_V11_PROFILE_REQUIRES_QUALIFICATION',complete))
            ids={sid:(kind,qid) for sid,kind,qid in db.execute('SELECT semantic_id,kind,accepted_wikidata FROM identity WHERE owner_slug=?',(slug,))}
            scan_owner(db,tree,slug,owner,ns,ids,counts)
        resolve(db); verify(tree,expected)
        if _hash_file(source_db)!=source_sha: fail('source database drift during scan')
        result={'format':FORMAT,'status':'PRIVATE_LEXICAL_RECOVERY_BUILT','database':str(output),'report':str(report),'source_v518_database':str(source_db),'source_v518_sha256':source_sha,'counts':{**dict(counts),**report_counts(db)},'policy':{'canonical_modified':False,'profiles_activated':0,'wikidata_acceptance_added':0,'public_modified':False,'legacy_mapped_by_similarity':False,'recovered_terms_are_canonical':False,'source_authentication_performed':False},'coverage_by_language':[{'language':r[0],'active_cells':r[1],'unreviewed_consensus_cells':r[2]} for r in db.execute("SELECT tag,sum(a),sum(h) FROM (SELECT language_tag tag,count(*) a,0 h FROM lexical GROUP BY language_tag UNION ALL SELECT language_tag,0,count(*) FROM recovery_resolution WHERE status='UNREVIEWED_CONSENSUS' GROUP BY language_tag) GROUP BY tag ORDER BY tag")]}
        result['target_14_languages']=[next((x for x in result['coverage_by_language'] if x['language']==tag),{'language':tag,'active_cells':0,'unreviewed_consensus_cells':0}) for tag in TARGET_LOCALES]
        result['counts']['target_14_recovery_cells']=sum(x['unreviewed_consensus_cells'] for x in result['target_14_languages'])
        db.execute('INSERT INTO metadata VALUES (?,?)',('v519_summary_json',js(result))); db.commit()
        if db.execute('PRAGMA quick_check').fetchone()!=('ok',): fail('output integrity failed')
        db.close(); db=None
        with report.open('x',encoding='utf8') as f: json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
        return result
    except BaseException:
        if db is not None: db.close()
        if created: output.unlink(missing_ok=True)
        raise
    finally: src.close(); tree.close()

def main():
    p=argparse.ArgumentParser(); p.add_argument('--locals',required=True,type=Path); p.add_argument('--private-dir',required=True,type=Path); p.add_argument('--public',type=Path); p.add_argument('--source-v518',type=Path); p.add_argument('--apply',action='store_true'); a=p.parse_args()
    if not a.apply: p.error('--apply required (private output only)')
    try:
        if a.source_v518 is None:
            if a.public is None: p.error('--public required for fresh federation')
            for path in (a.locals,a.private_dir,a.public): guard(path)
            if not a.locals.is_dir() or not a.public.is_dir(): fail('live refresh requires directory roots')
            for root in (a.locals,a.public):
                for parent,dirs,files in os.walk(root,followlinks=False):
                    for name in dirs+files:
                        q=Path(parent)/name
                        st=q.lstat()
                        if stat.S_ISLNK(st.st_mode) or getattr(st,'st_file_attributes',0)&0x400: fail('link/reparse point in live tree: '+str(q))
            refresh=refresh_v516(a.locals,a.private_dir,apply=True)
            source=build_active_federation(a.locals,a.private_dir,Path(refresh['source_db']),public_root=a.public)
            a.source_v518=Path(source['database'])
        result=build(a.locals,a.private_dir,a.source_v518)
    except (LocalFirstAuditError,OSError,ValueError,KeyError,TypeError,sqlite3.Error) as exc: p.exit(2,'BLOCKED: '+str(exc)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
