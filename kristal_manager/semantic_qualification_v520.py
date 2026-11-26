"""Local-first V5.20: source qualification, exact legacy inventory, verified catalog evolution."""
from __future__ import annotations
import argparse, collections, datetime, hashlib, json, os, re, sqlite3, sys, time, unicodedata
from pathlib import Path, PurePosixPath
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import URLError, HTTPError
from email.utils import parsedate_to_datetime
from .local_first_audit import ReadOnlyTree
from .semantic_recovery_v519 import guard, verify, report_counts, TARGET_LOCALES, js, build as recovery_build
from .active_semantic_federation_v518 import build_active_federation, _hash_file
from .local_semantic_evolution_v516 import evolve as refresh_v516

FORMAT='koa.kristal-semantic-qualification/1.0'
ENDPOINT='https://www.wikidata.org/w/api.php'
EXT=re.compile(r'^[QP][1-9][0-9]*$')

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kw): return None

def _fetch_once(ids):
    if not ids or len(ids)>50 or any(not EXT.fullmatch(x) for x in ids):raise ValueError('invalid Wikidata batch')
    url=ENDPOINT+'?'+urlencode({'action':'wbgetentities','ids':'|'.join(ids),'props':'info|labels|descriptions|aliases','languages':'|'.join(TARGET_LOCALES),'format':'json','maxlag':5})
    req=Request(url,headers={'User-Agent':'Kristal-diK/5.20 (local lexical qualification; Python urllib)','Accept':'application/json'})
    with build_opener(NoRedirect()).open(req,timeout=30) as response:
        if response.geturl()!=url:raise ValueError('unexpected response URL')
        raw=response.read(12*1024*1024+1)
    if len(raw)>12*1024*1024:raise ValueError('oversize Wikidata response')
    return raw

# Sequential polite requests; bounded retries and server-directed delays.
INTER_BATCH_SECONDS=15
MAX_RETRY_WAIT=600

def retry_delay(header,attempt):
    delay=60*(2**attempt)
    if header:
        try: seconds=float(header)
        except (ValueError,TypeError):
            try: seconds=(parsedate_to_datetime(header)-datetime.datetime.now(datetime.timezone.utc)).total_seconds()
            except (ValueError,TypeError,OverflowError): seconds=0
        if seconds>delay:delay=seconds
    return delay

def fresh_fetch(ids):
    for attempt in range(3):
        header=None
        try:
            raw=_fetch_once(ids)
            d=json.loads(raw)
            error=d.get('error',{}) if isinstance(d,dict) else {}
            if not isinstance(error,dict) or error.get('code') not in ('maxlag','ratelimited'):return raw
            reason='Wikidata API '+str(error['code'])
        except HTTPError as exc:
            if exc.code not in (429,503):raise
            header=exc.headers.get('Retry-After') if exc.headers else None
            reason=f'HTTP {exc.code}'
            exc.close()
        if attempt==2:raise OSError(reason+'; retry budget exhausted')
        delay=retry_delay(header,attempt)
        if delay>MAX_RETRY_WAIT:raise OSError(reason+'; Retry-After exceeds wait budget: '+str(delay))
        print(f'Wikidata: {reason}; retry in {delay:.0f}s',file=sys.stderr,flush=True)
        time.sleep(delay)
    raise AssertionError('unreachable')

def latest_resume_report(private):
    for p in sorted(private.glob('SEMANTIC_V520_*.json'),key=lambda p:p.stat().st_mtime,reverse=True):
        if not re.fullmatch(r'SEMANTIC_V520_[0-9a-f]{12}\.json',p.name):continue
        d=json.loads(guard(p).read_text(encoding='utf-8'))
        if d.get('format')==FORMAT and d.get('status')=='COMPLETE_WITH_NETWORK_BLOCKER' and d.get('network_completed') is False:
            return p
        if d.get('format')==FORMAT and d.get('status') in ('COMPLETE','COMPLETE_WITH_WORKSPACE_BLOCKERS'):return None
    return None

def resume_batches(private,report,qids):
    if report is None:return {}
    report=guard(report);private=guard(private)
    if report.parent!=private or not re.fullmatch(r'SEMANTIC_V520_[0-9a-f]{12}\.json',report.name):raise ValueError('resume report outside private scope')
    d=json.loads(report.read_text(encoding='utf-8'))
    if d.get('format')!=FORMAT or d.get('status')!='COMPLETE_WITH_NETWORK_BLOCKER' or d.get('network_completed') is not False or d.get('network_requested') is not True or d.get('canonical_modified') is not False or d.get('canonical_changes')!=[]:raise ValueError('resume report not eligible')
    if d.get('target_distinct_external_ids')!=len(qids):return {}
    if d.get('request_languages',list(TARGET_LOCALES))!=list(TARGET_LOCALES):return {}
    evidence=guard(report.with_suffix('.evidence'))
    database=guard(report.with_suffix('.sqlite'))
    if Path(d['evidence_directory'])!=evidence or Path(d['database'])!=database or _hash_file(database)!=d.get('database_sha256'):raise ValueError('resume database or evidence path mismatch')
    batches=d['source_batches'];out={};now=datetime.datetime.now(datetime.timezone.utc)
    for i,b in enumerate(batches):
        ids=b['requested_ids'];sha=b['sha256']
        if not ids or ids!=qids[i*50:(i+1)*50]:return {} # current plan changed: start fresh
        if not re.fullmatch(r'[0-9a-f]{64}',sha) or b['file']!=sha+'.json' or b['source_snapshot']!='wbgetentities-sha256-'+sha or b['endpoint']!=ENDPOINT:raise ValueError('resume batch provenance mismatch')
        retrieved=datetime.datetime.fromisoformat(b['retrieved_utc'])
        if not datetime.timedelta(0)<=now-retrieved<=datetime.timedelta(hours=24):return {}
        with guard(evidence/b['file']).open('rb') as f:raw=f.read(12*1024*1024+1)
        if len(raw)>12*1024*1024 or hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('resume evidence hash mismatch')
        parse_batch(raw,ids)
        out[tuple(ids)]=(raw,b)
    return out

def parse_batch(raw,ids):
    d=json.loads(raw)
    if not isinstance(d,dict) or 'error' in d or d.get('success')!=1 or not isinstance(d.get('entities'),dict):raise ValueError('Wikidata API error or malformed response')
    # No redirect following: missing/merged IDs are explicitly unresolved.
    if d.get('redirects'):raise ValueError('redirected Wikidata batch; manual review required')
    entities=d['entities'];out={};unresolved=[]
    for qid in ids:
        e=entities.get(qid)
        if not isinstance(e,dict) or e.get('id')!=qid or 'missing' in e or 'redirect' in e or e.get('type')!=('item' if qid.startswith('Q') else 'property') or type(e.get('lastrevid')) is not int or e['lastrevid']<=0:
            unresolved.append(qid);continue
        out[qid]=e
    return out,unresolved

def exact_value(e,field,tag):
    group=e.get(field,{})
    val=group.get(tag) if isinstance(group,dict) else None
    if not isinstance(val,dict) or val.get('language')!=tag:return None
    s=val.get('value')
    return s if isinstance(s,str) and s.strip() and len(s)<=100000 and unicodedata.is_normalized('NFC',s) else None

def lexical_record(e,ns,sid,qid,tag,snapshot):
    term=exact_value(e,'labels',tag)
    if term is None:return None
    aliases=e.get('aliases',{}); ar=aliases.get(tag,[]) if isinstance(aliases,dict) else []
    vals=sorted({x['value'] for x in ar if isinstance(x,dict) and x.get('language')==tag and isinstance(x.get('value'),str) and x['value'].strip() and unicodedata.is_normalized('NFC',x['value'])}) if isinstance(ar,list) else []
    out={'namespace_id':ns,'semantic_id':sid,'external_id':qid,'language':tag,'preferred_term':term,'aliases':vals,'source_snapshot':snapshot,'source_revision':e['lastrevid']}
    desc=exact_value(e,'descriptions',tag)
    if desc is not None:out['description']=desc
    return out

def targets(db):
    return list(db.execute("""SELECT i.owner_slug,i.namespace_id,i.semantic_id,i.accepted_wikidata FROM identity i WHERE i.kind IN ('entity','property') AND i.accepted_wikidata IS NOT NULL AND coalesce(i.lifecycle_status,'')!='deprecated' AND (NOT EXISTS(SELECT 1 FROM lexical l WHERE l.namespace_id=i.namespace_id AND l.semantic_id=i.semantic_id) OR EXISTS(SELECT 1 FROM recovery_resolution r WHERE r.namespace_id=i.namespace_id AND r.semantic_id=i.semantic_id AND r.status='UNREVIEWED_CONSENSUS')) ORDER BY 1,2,3"""))

def source_verify(tree,db):
    expected=list(db.execute('SELECT slug,local_directory,namespace_id,active,profile_sha256,state_sha256,projection_sha256,available_complete_revisions FROM workspace ORDER BY slug'))
    verify(tree,expected)
    for rel,h in db.execute('SELECT path,sha256 FROM recovery_source ORDER BY path'):
        if not tree.zip:guard(tree.root/rel)
        if tree.digest(rel)!=h:raise ValueError('recovery source changed: '+rel)
    return expected

def native_registry_paths(tree,owner):
    prefix=owner+'/knowledge-base/corpus/'
    if tree.zip:return sorted(x for x in tree._names if x.startswith(prefix) and x.endswith('.referent-registry.json'))
    p=guard(tree.root/prefix)
    if not p.is_dir():return []
    return sorted(x.relative_to(tree.root).as_posix() for x in p.glob('*.referent-registry.json') if guard(x).is_file())

def native_review(tree,db,expected):
    """Exact V6 ref within owner only. Never infer a V11 link from a name."""
    db.executescript('''CREATE TABLE v520_native_ref(owner_slug TEXT NOT NULL,legacy_id TEXT NOT NULL,source_path TEXT NOT NULL,source_sha256 TEXT NOT NULL,locator TEXT NOT NULL,record_json TEXT NOT NULL,PRIMARY KEY(owner_slug,source_path,locator));
    CREATE INDEX v520_native_ref_lookup ON v520_native_ref(owner_slug,legacy_id);
    CREATE TABLE v520_legacy_review(source_path TEXT NOT NULL,locator TEXT NOT NULL,owner_slug TEXT NOT NULL,legacy_id TEXT NOT NULL,status TEXT NOT NULL,native_refs_json TEXT NOT NULL,PRIMARY KEY(source_path,locator));
    CREATE TABLE v520_profile_review(owner_slug TEXT PRIMARY KEY,registered_artifacts INTEGER NOT NULL,registered_v11_artifacts INTEGER NOT NULL,native_registry_files INTEGER NOT NULL,native_referents INTEGER NOT NULL,status TEXT NOT NULL);
    CREATE TABLE v520_verified_record(namespace_id TEXT NOT NULL,semantic_id TEXT NOT NULL,language_tag TEXT NOT NULL,external_id TEXT NOT NULL,source_snapshot TEXT NOT NULL,source_revision INTEGER NOT NULL,record_json TEXT NOT NULL,status TEXT NOT NULL,PRIMARY KEY(namespace_id,semantic_id,language_tag));
    CREATE TABLE v520_candidate_review(namespace_id TEXT NOT NULL,semantic_id TEXT NOT NULL,language_tag TEXT NOT NULL,prior_status TEXT NOT NULL,status TEXT NOT NULL,source_snapshot TEXT,official_term TEXT,PRIMARY KEY(namespace_id,semantic_id,language_tag));
    CREATE VIEW v520_review_queue AS SELECT q.* FROM review_queue q LEFT JOIN identity i ON i.namespace_id=q.namespace_id AND i.semantic_id=q.semantic_id WHERE q.issue!='MISSING_ACTIVE_LABEL' OR i.kind IN ('entity','property');
    ''')
    errors=[]
    for slug,owner,ns,active,ph,st,pr,complete in expected:
        paths=native_registry_paths(tree,owner); n=0
        for path in paths:
            try:
                with tree.open(path) as f: raw=f.read(64*1024*1024+1)
                if len(raw)>64*1024*1024:raise ValueError('native registry exceeds size limit')
                doc=json.loads(raw.decode('utf-8-sig')); h=hashlib.sha256(raw).hexdigest()
                if not isinstance(doc,dict) or not isinstance(doc.get('referents'),list):raise ValueError('not a native referent registry')
                for i,r in enumerate(doc['referents']):
                    if isinstance(r,dict) and isinstance(r.get('ref'),str) and r['ref']:
                        db.execute('INSERT INTO v520_native_ref VALUES (?,?,?,?,?,?)',(slug,r['ref'],path,h,'/referents/'+str(i),js(r)));n+=1
            except (ValueError,OSError,TypeError) as exc:errors.append({'path':path,'error':str(exc)[:300]})
        if not active:
            state=tree.read_json(owner+'/canon/state.index.json',limit=64*1024*1024); arts=state.get('canonical_artifacts',[])
            v11=sum(1 for a in arts if isinstance(a,dict) and '/v11/' in a.get('path',''))
            db.execute('INSERT INTO v520_profile_review VALUES (?,?,?,?,?,?)',(slug,len(arts),v11,len(paths),n,'NO_COMPLETE_SELECTED_V11; MIGRATION_AND_QUALIFICATION_REQUIRED'))
    for path,loc,slug,space,lid in db.execute('SELECT source_path,locator,owner_slug,identity_space,legacy_id FROM recovery_legacy'):
        refs=[]
        if space=='kristal_v6':refs=[dict(source_path=a,source_sha256=b,locator=c) for a,b,c in db.execute('SELECT source_path,source_sha256,locator FROM v520_native_ref WHERE owner_slug=? AND legacy_id=? ORDER BY source_path,locator',(slug,lid))]
        status='EXACT_NATIVE_V6_REF_ONLY' if len(refs)==1 else 'MULTIPLE_NATIVE_REFS_NO_V11_LINK' if refs else 'NO_EXPLICIT_NATIVE_REF_OR_V11_BRIDGE'
        db.execute('INSERT INTO v520_legacy_review VALUES (?,?,?,?,?,?)',(path,loc,slug,lid,status,js(refs)))
    return errors

def compare_candidates(db,found,missing):
    """Compare historical consensus with the exact source; never confer alignment approval."""
    for ns,sid,tag,prior,term,qid in db.execute("SELECT r.namespace_id,r.semantic_id,r.language_tag,r.status,r.suggested_term,i.accepted_wikidata FROM recovery_resolution r JOIN identity i ON i.namespace_id=r.namespace_id AND i.semantic_id=r.semantic_id WHERE r.status IN ('UNREVIEWED_CONSENSUS','UNREVIEWED_CONFLICT','ACTIVE_PRECEDENCE_CONFLICT')"):
        source=None;official=None
        if prior=='ACTIVE_PRECEDENCE_CONFLICT':status='KEEP_ACTIVE_LABEL_REVIEW_CONFLICT'
        elif tag not in TARGET_LOCALES:status='OUTSIDE_TARGET_LANGUAGES'
        elif not qid:status='NO_ACCEPTED_ALIGNMENT'
        elif qid in missing:status='EXTERNAL_ID_UNRESOLVED'
        elif qid not in found:status='SOURCE_NOT_RETRIEVED'
        else:
            e,source=found[qid];official=exact_value(e,'labels',tag)
            if official is None:status='NO_EXACT_SOURCE_LABEL'
            elif prior=='UNREVIEWED_CONFLICT':status='HISTORICAL_CONFLICT_SOURCE_AVAILABLE'
            else:status='EXACT_SOURCE_AGREEMENT' if term==official else 'SOURCE_TERM_DIFFERS'
        db.execute('INSERT INTO v520_candidate_review VALUES (?,?,?,?,?,?,?)',(ns,sid,tag,prior,status,source,official))
    return dict(db.execute('SELECT status,count(*) FROM v520_candidate_review GROUP BY status'))

def refresh(locals_root,public,private):
    r=refresh_v516(locals_root,private,apply=True)
    a=build_active_federation(locals_root,private,Path(r['source_db']),public_root=public)
    return recovery_build(locals_root,private,Path(a['database']))

def write_report(path,result):
    tmp=path.with_suffix('.tmp');guard(tmp)
    with tmp.open('w',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)

def run(locals_root,private,source,*,public=None,kit=None,framework=None,online=False,apply_catalogs=False,fetch=fresh_fetch,resume_report=None):
    locals_root=guard(locals_root);private=guard(private);source=guard(source)
    if private==locals_root or private in locals_root.parents or locals_root in private.parents:raise ValueError('private output must be separate')
    if public is not None:
        public=guard(public)
        if private==public or private in public.parents or public in private.parents or locals_root==public or locals_root in public.parents or public in locals_root.parents:raise ValueError('local, public and private roots must be separate')
    if apply_catalogs and (not online or public is None or kit is None or framework is None or not locals_root.is_dir()):raise ValueError('live source and repository paths required for canonical apply')
    tree=ReadOnlyTree(locals_root); h=_hash_file(source)
    src=sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)
    token='SEMANTIC_V520_'+os.urandom(6).hex();out=private/(token+'.sqlite');rp=private/(token+'.json');evidence=private/(token+'.evidence');evidence.mkdir(exist_ok=False)
    result={'format':FORMAT,'status':'IN_PROGRESS','database':str(out),'report':str(rp),'source_v519':str(source),'source_v519_sha256':h,'evidence_directory':str(evidence),'canonical_changes':[],'blocked_workspaces':[],'policy':{'public_modified':False,'wikidata_acceptance_added':0,'profiles_activated':0,'legacy_v11_links_invented':0,'existing_labels_overwritten':0,'remote_query_contains_only_public_external_ids_and_language_tags':True}}
    write_report(rp,result);db=None
    try:
        if src.execute('PRAGMA quick_check').fetchone()!=('ok',) or src.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('input SQLite invalid')
        summary=json.loads(src.execute("SELECT value FROM metadata WHERE key='v519_summary_json'").fetchone()[0]);
        if summary['status']!='PRIVATE_LEXICAL_RECOVERY_BUILT':raise ValueError('not V5.19')
        expected=source_verify(tree,src)
        with out.open('xb'):pass
        db=sqlite3.connect(out);src.backup(db);db.execute('PRAGMA foreign_keys=ON')
        errors=native_review(tree,db,expected); planned=targets(db); qids=sorted({r[3] for r in planned});
        if any(not EXT.fullmatch(q) for q in qids):raise ValueError('bad accepted external ID')
        result['native_scan_errors']=errors
        result['before']=report_counts(db);result['target_identities']=len(planned);result['target_distinct_external_ids']=len(qids)
        result['legacy_review_counts']=dict(db.execute('SELECT status,count(*) FROM v520_legacy_review GROUP BY status'))
        result['native_referents']=db.execute('SELECT count(*) FROM v520_native_ref').fetchone()[0]
        result['missing_label_queue_KQ_KP']=db.execute("SELECT count(*) FROM v520_review_queue WHERE issue='MISSING_ACTIVE_LABEL'").fetchone()[0]
        result['ambiguous_candidate_ids']=db.execute("SELECT count(*) FROM v520_review_queue WHERE issue='AMBIGUOUS_WIKIDATA_CANDIDATES'").fetchone()[0]
        existing={(a,b,c) for a,b,c in db.execute('SELECT namespace_id,semantic_id,language_tag FROM lexical')}
        by_qid=collections.defaultdict(list)
        for slug,ns,sid,q in planned:by_qid[q].append((slug,ns,sid))
        records=collections.defaultdict(list);batches=[];unresolved=[];network_error=None;found={}
        cached=resume_batches(private,resume_report,qids) if online else {}
        result['request_languages']=list(TARGET_LOCALES)
        result['reused_source_batches']=0
        result['fresh_source_batches']=0
        if online:
            for pos in range(0,len(qids),50):
                batch=qids[pos:pos+50]
                try:
                    prior=cached.get(tuple(batch))
                    if prior:
                        raw,meta=prior
                    else:
                        if result['fresh_source_batches']:time.sleep(INTER_BATCH_SECONDS)
                        print(f'Wikidata: requesting batch {pos//50+1}/{(len(qids)+49)//50}',file=sys.stderr,flush=True)
                        raw=fetch(batch);meta=None
                    entities,missing=parse_batch(raw,batch)
                    sha=hashlib.sha256(raw).hexdigest();snapshot='wbgetentities-sha256-'+sha
                    p=evidence/(sha+'.json');
                    if p.exists():
                        if _hash_file(p)!=sha:raise ValueError('evidence hash mismatch')
                    else:
                        with p.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
                    batches.append(dict(meta) if meta else {'source_snapshot':snapshot,'sha256':sha,'file':p.name,'requested_ids':batch,'endpoint':ENDPOINT,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
                    result['reused_source_batches' if prior else 'fresh_source_batches']+=1
                    unresolved.extend(missing)
                    for q,e in entities.items():
                        found[q]=(e,snapshot)
                        for slug,ns,sid in by_qid[q]:
                            for tag in TARGET_LOCALES:
                                if (ns,sid,tag) in existing:continue
                                r=lexical_record(e,ns,sid,q,tag,snapshot)
                                if r:
                                    records[slug].append(r);db.execute('INSERT INTO v520_verified_record VALUES (?,?,?,?,?,?,?,?)',(ns,sid,tag,q,snapshot,r['source_revision'],js(r),'FRESH_SOURCE_LABEL_RECORDED_NOT_NEW_ALIGNMENT'))
                except (OSError,ValueError,TypeError,KeyError,URLError) as exc:
                    network_error=str(exc)[:500];break
        result.update({'source_batches':batches,'unresolved_external_ids':unresolved,'network_error':network_error,'verified_new_cells':sum(map(len,records.values())),'network_requested':online,'network_completed':online and network_error is None})
        result['candidate_review_counts']=compare_candidates(db,found,set(unresolved))
        db.commit(); source_verify(tree,src)
        if _hash_file(source)!=h:raise ValueError('source database drift')
        if db.execute('PRAGMA quick_check').fetchone()!=('ok',) or db.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('output SQLite invalid')
        result['status']='PRIVATE_QUALIFICATION_COMPLETE';write_report(rp,result)
        if apply_catalogs and network_error is None:
            from jsonschema.exceptions import ValidationError
            sys.path.insert(0,str(guard(kit/'tools')));import v520_verified_catalog as writer
            plans=[]
            for slug,owner,ns,active,ph,st,pr,complete in expected:
                if not records.get(slug):continue
                try:
                    plan=writer.prepare(locals_root/owner,records[slug],(ph,st),framework/'schemas/v11')
                    if plan:plans.append((slug,plan))
                except (ValueError,OSError,KeyError,TypeError,ValidationError) as exc:result['blocked_workspaces'].append({'slug':slug,'reason':str(exc)[:500]})
            result['planned_catalogs']=len(plans);result['status']='CANONICAL_APPLY_IN_PROGRESS';write_report(rp,result)
            # Plan all workspaces before changing any profile. No public writes.
            for slug,plan in plans:
                result['in_progress_workspace']=slug;write_report(rp,result)
                event=writer.apply(plan,evidence,slug);result['canonical_changes'].append(event);result.pop('in_progress_workspace',None);write_report(rp,result)
            if result['canonical_changes']:
                post=refresh(locals_root,public,private);result['post_v519_database']=post['database'];result['post_v519_report']=post['report'];result['after']=post['counts']
                # Rebase qualification tables on the new federation. Retain the old evidence DB.
                final=private/(token+'.active.sqlite')
                with final.open('xb'):pass
                current=sqlite3.connect(Path(post['database']).resolve().as_uri()+'?mode=ro',uri=True)
                final_db=sqlite3.connect(final)
                try:
                    current.backup(final_db);final_db.execute('PRAGMA foreign_keys=ON')
                    final_expected=list(final_db.execute('SELECT slug,local_directory,namespace_id,active,profile_sha256,state_sha256,projection_sha256,available_complete_revisions FROM workspace ORDER BY slug'))
                    native_review(tree,final_db,final_expected)
                    for row in db.execute('SELECT * FROM v520_candidate_review'):
                        final_db.execute('INSERT INTO v520_candidate_review VALUES (?,?,?,?,?,?,?)',row)
                    for row in db.execute('SELECT * FROM v520_verified_record'):
                        r=json.loads(row[6]); label=final_db.execute('SELECT preferred_term FROM lexical WHERE namespace_id=? AND semantic_id=? AND language_tag=?',row[:3]).fetchone()
                        status='ACTIVE_CANONICAL_SOURCE_LABEL' if label==(r['preferred_term'],) else row[7]
                        final_db.execute('INSERT INTO v520_verified_record VALUES (?,?,?,?,?,?,?,?)',(*row[:7],status))
                    actual=final_db.execute("SELECT count(*) FROM v520_verified_record WHERE status='ACTIVE_CANONICAL_SOURCE_LABEL'").fetchone()[0]
                    if actual!=sum(x['new_cells'] for x in result['canonical_changes']):raise ValueError('post-apply active lexical delta does not match applied catalog plan')
                    result['new_active_cells']=actual
                    final_db.commit()
                    if final_db.execute('PRAGMA quick_check').fetchone()!=('ok',) or final_db.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('post-apply database invalid')
                finally:final_db.close();current.close()
                result['qualification_database_before_apply']=str(out);result['database']=str(final)
                result['database_role']='CURRENT_ACTIVE_WITH_QUALIFICATION';result['active_database']=str(final)
            else:result['database_role']='CURRENT_ACTIVE_WITH_QUALIFICATION';result['active_database']=str(out);result['after']=result['before']
        else:
            result['database_role']='CURRENT_ACTIVE_WITH_QUALIFICATION';result['active_database']=str(out);result['after']=result['before']
        result['status']='COMPLETE_WITH_NETWORK_BLOCKER' if network_error else 'COMPLETE_WITH_WORKSPACE_BLOCKERS' if result['blocked_workspaces'] else 'COMPLETE';result['canonical_modified']=bool(result['canonical_changes'])
        result['database_sha256']=_hash_file(Path(result['database']));write_report(rp,result)
        return result
    except BaseException as exc:
        result['status']='BLOCKED_OR_PARTIAL';result['error']=str(exc)[:500];write_report(rp,result);raise
    finally:
        if db is not None:db.close()
        src.close();tree.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--locals',type=Path,required=True);p.add_argument('--public',type=Path,required=True);p.add_argument('--private-dir',type=Path,required=True);p.add_argument('--kit',type=Path,required=True);p.add_argument('--framework',type=Path,required=True);p.add_argument('--apply',action='store_true');p.add_argument('--offline',action='store_true');p.add_argument('--resume-latest',action='store_true');a=p.parse_args()
    if not a.apply:p.error('--apply required')
    # Same live-tree protections as V5.19, including Windows junctions.
    for root in (a.locals,a.public):
        guard(root)
        if not root.is_dir():p.error('live directory required')
        for parent,dirs,files in os.walk(root,followlinks=False):
            for name in dirs+files:guard(Path(parent)/name)
    guard(a.private_dir)
    roots=[x.resolve() for x in (a.locals,a.public,a.private_dir)]
    for i,x in enumerate(roots):
        for y in roots[i+1:]:
            if x==y or x in y.parents or y in x.parents:p.error('local, public and private paths must be disjoint')
    a.private_dir.mkdir(parents=True,exist_ok=True)
    if not a.offline:
        import jsonschema # preflight dependency before canonical operations
    resume=latest_resume_report(a.private_dir) if a.resume_latest and not a.offline else None
    source=refresh(a.locals,a.public,a.private_dir)
    r=run(a.locals,a.private_dir,Path(source['database']),public=a.public,kit=a.kit,framework=a.framework,online=not a.offline,apply_catalogs=not a.offline,resume_report=resume)
    print(json.dumps(r,ensure_ascii=False,indent=2));print('V5.20 ONE-SHOT: '+r['status'],flush=True)
if __name__=='__main__':main()
