"""Build a resumable, operational private dictionary without changing canon."""
import argparse,collections,hashlib,json,os,re,sqlite3,sys,unicodedata,zipfile
from pathlib import Path
from contextlib import closing
from .maintenance_scan import Tree,guard,digest,parse,sha_bytes,safe

def j(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def require(x,m):
    if not x:raise ValueError(m)
def ro(p):return sqlite3.connect(guard(p).as_uri()+'?mode=ro',uri=True)
def pointer(d,p):
    for x in p.split('/')[1:]:
        x=x.replace('~1','/').replace('~0','~');d=d[int(x)] if isinstance(d,list) else d[x]
    return d

def catalog_records(doc,ns):
    # Only explicit namespace-scoped V11 dictionary records, not arbitrary textual fields.
    if not isinstance(doc,dict) or doc.get('namespace_id')!=ns or doc.get('artifact_type')!='kristal_curated_dictionary':return
    if not isinstance(doc.get('language'),str) or not isinstance(doc.get('entries'),list):return
    for i,r in enumerate(doc.get('entries',[])):
        if isinstance(r,dict) and isinstance(r.get('semantic_id'),str) and isinstance(r.get('preferred_term'),str):
            yield r['semantic_id'],doc['language'],r['preferred_term'],f'/entries/{i}/preferred_term'

def files(tree,owner):
    prefixes=(owner+'/knowledge-base/corpus/',owner+'/.kristal/v8/',owner+'/canon/domain/',owner+'/.kristal/v11/')
    if tree.z:
        yield from sorted(n for n in tree.names if n.startswith(prefixes) and n.endswith(('.json','.jsonl')))
    else:
        for prefix in prefixes:
            root=guard(tree.root/prefix)
            if not root.is_dir():continue
            for current,dirs,fs in os.walk(root,followlinks=False):
                guard(current)
                dirs[:]=sorted(d for d in dirs if not d.startswith('.'))
                for f in sorted(fs):
                    if f.endswith(('.json','.jsonl')):yield guard(Path(current)/f).relative_to(tree.root).as_posix()

def scan_doc(raw,path,ns,targets,anchor,obs):
    from kristalizer.maintenance_evidence import observations,LANG
    h=sha_bytes(raw)
    def emit(sid,lang,term,p,method):
        if sid in targets and isinstance(lang,str) and LANG.fullmatch(lang) and isinstance(term,str) and term.strip():obs.append((ns,sid,lang,term,path,h,p,method))
    if path.endswith('.jsonl'):
        # An explicit external id is not a lexical anchor without an accepted crosswalk.
        # No imported Wikidata records in this broader recovery pass.
        return
    d=parse(raw)
    if not isinstance(d,dict):return
    at=d.get('artifact_type')
    if at=='kristall_lexicon' or (isinstance(at,str) and at.endswith('referent_registry')) or (at is None and path.endswith('/referents.json')):
        for native,lang,term,p,method in observations(d):emit(anchor.get(native),lang,term,p,method)
    # V11 dictionary schema uses language_tag? Accept only the exact historical contract below.
    if '/dictionaries/' in path:
        for sid,lang,term,p in catalog_records(d,ns):emit(sid,lang,term,p,'SCOPED_HISTORICAL_DICTIONARY')

def run(root,base,scan,out,kristalizer,diag,index=None,dump=None):
    root,base,scan,out=map(guard,(root,base,scan,out));sys.path.insert(0,str(guard(kristalizer)));sys.path.insert(0,str(guard(diag)))
    from kristaldiag.maintenance_check import check
    from kristalizer.maintenance_evidence import anchors
    from kristalizer.maintenance_external_v5217 import lookup
    for s in (root,base,scan):require(out!=s and s not in out.parents and out not in s.parents,'Output overlaps source')
    require(check(scan,base,root)['source_bytes_and_pointers_checked'],'Source proof required')
    br=parse((base/'report.json').read_bytes());mr=parse((scan/'report.json').read_bytes());bh=digest(base/'active.sqlite');mh=digest(scan/'maintenance.sqlite')
    require(br['database_sha256']==bh and mr['base_database_sha256']==bh and mr['maintenance_database_sha256']==mh,'Baseline mismatch')
    out.mkdir(parents=True,exist_ok=True);p=guard(out/'repair.sqlite');tree=Tree(root)
    require(not (out/'COMPLETE').exists(),'Completed output is immutable; choose new directory')
    with closing(ro(base/'active.sqlite')) as src,closing(ro(scan/'maintenance.sqlite')) as prior,closing(sqlite3.connect(p)) as db:
        db.executescript('''CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS scanned(path TEXT PRIMARY KEY,sha256 TEXT,status TEXT,detail TEXT);
CREATE TABLE IF NOT EXISTS evidence(ns TEXT,sid TEXT,lang TEXT,term TEXT,path TEXT,sha256 TEXT,pointer TEXT,method TEXT,PRIMARY KEY(ns,sid,lang,path,pointer));
CREATE TABLE IF NOT EXISTS display_ref(ns TEXT,sid TEXT,kind TEXT,native_json TEXT,PRIMARY KEY(ns,sid));
CREATE TABLE IF NOT EXISTS effective(ns TEXT,sid TEXT,lang TEXT,term TEXT,status TEXT,PRIMARY KEY(ns,sid,lang));
CREATE TABLE IF NOT EXISTS graph_scope(slug TEXT PRIMARY KEY,ns TEXT,status TEXT,assertions INTEGER,record_json TEXT);
CREATE TABLE IF NOT EXISTS external_record(wid TEXT PRIMARY KEY,record_json TEXT);
CREATE TABLE IF NOT EXISTS alias_review(slug TEXT,path TEXT,line INTEGER,status TEXT,record_json TEXT,PRIMARY KEY(slug,path,line));
CREATE TABLE IF NOT EXISTS unresolved(ns TEXT,sid TEXT,kind TEXT,reason TEXT,PRIMARY KEY(ns,sid));
''')
        binding=j([bh,mh,str(root),str(index),str(dump)]);old=db.execute("SELECT v FROM meta WHERE k='binding'").fetchone();require(not old or old[0]==binding,'Resume inputs changed');db.execute("INSERT OR IGNORE INTO meta VALUES('binding',?)",(binding,));db.commit()
        # Recheck the exact live selected graph/profile/state and lexical bytes, not merely counts.
        for slug,ns,status,rj in src.execute('SELECT * FROM v52161_active_graph'):
            r=json.loads(rj);owner=src.execute('SELECT local_directory FROM workspace WHERE slug=?',(slug,)).fetchone()[0]
            require(r['core_graph_registry_crosswalk_qualified'],'Graph not structurally qualified: '+slug)
            for rel,h in r['source_pins'].items():require(sha_bytes(tree.read(owner+'/'+rel))==h,'Live source drift: '+slug+'/'+rel)
            db.execute('INSERT OR REPLACE INTO graph_scope VALUES (?,?,?,?,?)',(slug,ns,status,r['assertions'],rj))
        db.commit()
        # Preserve the validated recovery set, including every pointer.
        db.executemany('INSERT OR IGNORE INTO evidence VALUES (?,?,?,?,?,?,?,?)',prior.execute('SELECT ns,sid,lang,term,path,sha256,pointer,method FROM observation'));db.commit()
        seen=set()
        for slug,owner,ns in src.execute('SELECT slug,local_directory,namespace_id FROM workspace WHERE active=1 ORDER BY slug'):
            print('REPAIR SCAN',slug,flush=True)
            ids=dict(src.execute('SELECT semantic_id,kind FROM identity WHERE namespace_id=? AND kind IN (\'entity\',\'property\')',(ns,)))
            targets={x[0] for x in prior.execute('SELECT sid FROM target WHERE ns=?',(ns,))}; mp=owner+'/.kristal/v11/identity-migration-map.json';a={}
            if tree.exists(mp):
                mapraw=tree.read(mp);maphash=sha_bytes(mapraw);a=anchors(parse(mapraw),ns,ids)
                prev=db.execute('SELECT sha256 FROM scanned WHERE path=?',(mp,)).fetchone()
                require(not prev or prev[0]==maphash,'Migration map drift: '+mp)
                db.execute('INSERT OR REPLACE INTO scanned VALUES (?,?,?,?)',(mp,maphash,'ANCHOR',''))
            inv=collections.defaultdict(list)
            for native,sid in a.items():inv[sid].append(native)
            db.executemany('INSERT OR REPLACE INTO display_ref VALUES (?,?,?,?)',((ns,sid,kind,j(sorted(inv[sid]))) for sid,kind in ids.items()));db.commit()
            for path in files(tree,owner):
                seen.add(path)
                # Skip unrelated large graph/state artifacts; never execute archive content.
                if not (('/dictionaries/' in path and path.endswith('.json')) or '/knowledge-base/corpus/' in path or '/.kristal/v8/' in path):continue
                try:raw=tree.read(path);h=sha_bytes(raw)
                except (OSError,ValueError,KeyError) as e:
                    db.execute('INSERT OR REPLACE INTO scanned VALUES (?,?,?,?)',(path,'','ERROR',str(e)));db.commit();continue
                row=db.execute('SELECT sha256,status FROM scanned WHERE path=?',(path,)).fetchone()
                if row==(h,'OK'):continue
                # Any changed evidence source is rejected rather than mixed across runs.
                # Prior checked recovery evidence must never be replaced by drifted bytes.
                require(not db.execute('SELECT 1 FROM evidence WHERE path=? AND sha256<>?',(path,h)).fetchone(),'Recovery source drift: '+path)
                rows=[]
                try:scan_doc(raw,path,ns,targets,a,rows);status='OK';detail=''
                except (ValueError,KeyError,TypeError,UnicodeError) as e:status='ERROR';detail=str(e);rows=[]
                for item in rows:
                    existing=db.execute('SELECT term,sha256 FROM evidence WHERE ns=? AND sid=? AND lang=? AND path=? AND pointer=?',(item[0],item[1],item[2],item[4],item[6])).fetchone()
                    require(not existing or existing==(item[3],item[5]),'Evidence conflict');db.execute('INSERT OR IGNORE INTO evidence VALUES (?,?,?,?,?,?,?,?)',item)
                db.execute('INSERT OR REPLACE INTO scanned VALUES (?,?,?,?)',(path,h,status,detail));db.commit()
        # A removed file cannot silently contribute an observation on resume.
        for path,h in db.execute('SELECT DISTINCT path,sha256 FROM evidence'):
            require(sha_bytes(tree.read(path))==h,'Evidence drift: '+path)
        db.execute('DELETE FROM effective');db.executemany("INSERT INTO effective VALUES (?,?,?,?,'ACTIVE_CANONICAL')",src.execute('SELECT namespace_id,semantic_id,language_tag,preferred_term FROM lexical'))
        db.execute("INSERT OR IGNORE INTO effective SELECT ns,sid,lang,min(term),'RECOVERED_EXACT_PRIVATE' FROM evidence GROUP BY ns,sid,lang HAVING count(DISTINCT term)=1")
        db.execute('DELETE FROM unresolved');db.execute("INSERT INTO unresolved SELECT ns,sid,kind,'NO_ATTESTED_LABEL' FROM display_ref d WHERE NOT EXISTS(SELECT 1 FROM effective e WHERE e.ns=d.ns AND e.sid=d.sid)")
        db.execute('DELETE FROM external_record');fp=None;external_status='NOT_AVAILABLE'
        if index and guard(index).is_file():
            try:
                data,fp=lookup(index,[r[0] for r in prior.execute('SELECT wid FROM alias_target UNION SELECT external_id FROM ambiguous')]);db.executemany('INSERT INTO external_record VALUES (?,?)',((k,j(v)) for k,v in data.items()));external_status='EXACT_LANGUAGE_OBSERVATIONS_NOT_AUTHENTICATED'
            except (OSError,ValueError,sqlite3.Error) as e:external_status='BLOCKED: '+str(e)
        dump_status='NOT_REQUESTED';dump_fingerprint=None
        if dump:
            from kristalizer.maintenance_dump_v5217 import extract
            dump_fingerprint=extract(guard(dump),db,[r[0] for r in prior.execute('SELECT wid FROM alias_target UNION SELECT external_id FROM ambiguous')]);dump_status='LOCAL_DUMP_OBSERVATIONS_NOT_AUTHENTICATED'
        db.execute('DELETE FROM alias_review')
        for slug,path,line,status,rj in src.execute('SELECT * FROM v52161_alias_review'):
            r=json.loads(rj);row=db.execute('SELECT record_json FROM external_record WHERE wid=?',(r['external_id'],)).fetchone();v=json.loads(row[0]) if row else {};lang=r['language'];r['compact_exact_language_label']=v.get('label_'+lang) if lang in ('en','fr') else None;r['compact_observation_present']=bool(v);r['canonical_repair_authorized']=False
            if dump:
                dr=db.execute('SELECT record_json FROM dump_record WHERE wid=?',(r['external_id'],)).fetchone()
                if dr:
                    fresh=json.loads(dr[0]);r['fresh_dump_revision']=fresh['source_revision'];r['fresh_dump_aliases']=fresh['aliases'].get(lang) if lang!='und' else None;r['fresh_dump_label']=fresh['labels'].get(lang) if lang!='und' else None
            db.execute('INSERT INTO alias_review VALUES (?,?,?,?,?)',(slug,path,line,'HISTORICAL_ALIAS_UNKNOWN',j(r)))
        db.commit();require(db.execute('pragma integrity_check').fetchone()==('ok',),'Repair DB integrity');require(digest(base/'active.sqlite')==bh and digest(scan/'maintenance.sqlite')==mh,'Baseline drift')
        count=lambda q:db.execute(q).fetchone()[0]
        report={'format':'koa.kristal-operational-repair/0.1','status':'PRIVATE_OPERATIONAL_DICTIONARY_READY','baseline_sha256':bh,'maintenance_sha256':mh,'counts':{'active_cells':count("SELECT count(*) FROM effective WHERE status='ACTIVE_CANONICAL'"),'recovered_cells':count("SELECT count(*) FROM effective WHERE status='RECOVERED_EXACT_PRIVATE'"),'labeled_identities':count('SELECT count(*) FROM (SELECT DISTINCT ns,sid FROM effective)'),'unlabeled_identities':count('SELECT count(*) FROM unresolved'),'displayable_identities':count('SELECT count(*) FROM display_ref'),'graph_scopes':count('SELECT count(*) FROM graph_scope'),'assertions':count('SELECT sum(assertions) FROM graph_scope'),'conflicting_cells':count('SELECT count(*) FROM (SELECT ns,sid,lang FROM evidence GROUP BY 1,2,3 HAVING count(DISTINCT term)>1)'),'scan_errors':count("SELECT count(*) FROM scanned WHERE status='ERROR'"),'external_records':count('SELECT count(*) FROM external_record'),'aliases_still_unknown':count('SELECT count(*) FROM alias_review')},'external_index':fp,'external_status':external_status,'dump_status':dump_status,'dump_fingerprint':dump_fingerprint,'dump_records':count('SELECT count(*) FROM dump_record') if dump else 0,'policy':{'canonical_modified':False,'public_modified':False,'new_accepted_links':0,'historical_ka_restored':0,'canonical_lexical_repairs':0,'private_recovery_enabled':True}}
    tree.close();report['database_sha256']=digest(p);(out/'report.json').write_text(j(report),encoding='utf8')
    from kristaldiag.maintenance_repair_check_v5217 import verify
    result=verify(out,base,scan,root);(out/'diagnostic.json').write_text(j(result),encoding='utf8');(out/'COMPLETE').write_text(report['database_sha256'],encoding='ascii');return report

def main():
    p=argparse.ArgumentParser()
    for k in ('locals','baseline','scan','output','kristalizer','diag'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--index',type=Path);p.add_argument('--dump',type=Path);a=p.parse_args();print(json.dumps(run(a.locals,a.baseline,a.scan,a.output,a.kristalizer,a.diag,a.index,a.dump),indent=2,ensure_ascii=True))
if __name__=='__main__':main()
