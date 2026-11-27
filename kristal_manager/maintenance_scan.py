"""Permanent, read-only maintenance scanner. Private observations, not canon."""
import argparse,collections,hashlib,json,os,re,sqlite3,stat,sys,uuid,zipfile
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone

def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def guard(p):
    p=Path(p).absolute()
    for x in [*reversed(p.parents),p]:
        if x.exists() or x.is_symlink():
            s=x.lstat()
            if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('Link/reparse point: '+str(x))
    return p

def unique(pairs):
    d={}
    for k,v in pairs:
        if k in d:raise ValueError('Duplicate JSON key: '+k)
        d[k]=v
    return d
def parse(raw):return json.loads(raw.decode('utf-8-sig'),object_pairs_hook=unique,parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Non-finite JSON')))
def safe(rel):
    p=PurePosixPath(rel)
    if p.is_absolute() or '..' in p.parts or '\\' in rel or ':' in rel or not p.parts:raise ValueError('Unsafe path: '+rel)
    return p
class Tree:
    def __init__(self,root):
        self.root=guard(root);self.z=None
        if self.root.is_file():
            self.z=zipfile.ZipFile(self.root);self.names={}
            for i in self.z.infolist():
                if i.is_dir():continue
                safe(i.filename)
                if i.filename in self.names:raise ValueError('Duplicate ZIP member')
                if stat.S_ISLNK(i.external_attr>>16):raise ValueError('ZIP symlink')
                self.names[i.filename]=i
        elif not self.root.is_dir():raise ValueError('Missing locals')
    def exists(self,rel):
        safe(rel);return rel in self.names if self.z else guard(self.root/rel).is_file()
    def read(self,rel):
        safe(rel)
        if self.z:
            info=self.names[rel]
            if info.file_size>64*1024*1024:raise ValueError('Oversize JSON')
            return self.z.read(info)
        p=guard(self.root/rel)
        if p.stat().st_size>64*1024*1024:raise ValueError('Oversize JSON')
        return p.read_bytes()
    def files(self,owner):
        for sub in ('knowledge-base/corpus','.kristal/v8'):
            prefix=owner+'/'+sub+'/'
            if self.z:
                for n in sorted(self.names):
                    if n.startswith(prefix) and '/' not in n[len(prefix):] and n.endswith('.json'):yield n
            else:
                p=guard(self.root/owner/sub)
                if p.is_dir():
                    for f in sorted(p.glob('*.json')):
                        if guard(f).is_file():yield f.relative_to(self.root).as_posix()
    def close(self):
        if self.z:self.z.close()

def run(locals_root,base,output,kristalizer,diag,index=None):
    sys.path.insert(0,str(guard(kristalizer)))
    from kristalizer.maintenance_evidence import anchors,observations
    from kristalizer.core import EncyIndex
    base=guard(base);output=guard(output);root=guard(locals_root)
    if output==root or root in output.parents or output in root.parents or output==base or base in output.parents or output in base.parents:raise ValueError('Output must be disjoint from sources and generation')
    report=parse((base/'report.json').read_bytes());source=guard(base/'active.sqlite');h=digest(source)
    if report.get('database_sha256')!=h:raise ValueError('Base database hash mismatch')
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True); dbpath=output/'maintenance.sqlite';tree=Tree(root)
    src=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True); db=sqlite3.connect(dbpath)
    errors=[]; drift=[]; counts=collections.Counter(); observed={}
    try:
        if src.execute('pragma integrity_check').fetchone()!=('ok',):raise ValueError('Source integrity')
        db.executescript('''CREATE TABLE target(ns TEXT,sid TEXT,slug TEXT,kind TEXT,PRIMARY KEY(ns,sid));
CREATE TABLE anchor(ns TEXT,native_id TEXT,sid TEXT,path TEXT,sha256 TEXT,PRIMARY KEY(ns,native_id));
CREATE TABLE observation(ns TEXT,sid TEXT,lang TEXT,term TEXT,native_id TEXT,path TEXT,sha256 TEXT,pointer TEXT,method TEXT,PRIMARY KEY(ns,sid,lang,path,pointer));
CREATE TABLE resolution(ns TEXT,sid TEXT,lang TEXT,status TEXT,term TEXT,variants_json TEXT,PRIMARY KEY(ns,sid,lang));
CREATE TABLE source(path TEXT PRIMARY KEY,sha256 TEXT,status TEXT);
CREATE TABLE external_observation(wid TEXT PRIMARY KEY,record_json TEXT);
CREATE TABLE alias_target(wid TEXT,lang TEXT,occurrences INTEGER,PRIMARY KEY(wid,lang));
CREATE TABLE editorial_issue(issue_id TEXT PRIMARY KEY,record_json TEXT);
CREATE TABLE ambiguous(ns TEXT,sid TEXT,external_id TEXT,source_status TEXT,PRIMARY KEY(ns,sid,external_id));
CREATE TABLE scan_error(path TEXT,detail TEXT);''')
        targets=list(src.execute("SELECT namespace_id,semantic_id,owner_slug,kind FROM identity i WHERE kind IN ('entity','property') AND NOT EXISTS(SELECT 1 FROM lexical l WHERE l.namespace_id=i.namespace_id AND l.semantic_id=i.semantic_id) ORDER BY 1,2"));db.executemany('INSERT INTO target VALUES (?,?,?,?)',targets)
        for slug,owner,ns,active,state,profile in src.execute('SELECT slug,local_directory,namespace_id,active,state_sha256,profile_sha256 FROM workspace ORDER BY slug'):
            if not active:continue
            print('SCAN',slug,flush=True)
            try:
                if sha_bytes(tree.read(owner+'/canon/state.index.json'))!=state or sha_bytes(tree.read(owner+'/.kristal/v11/authoring.json'))!=profile:drift.append(slug)
            except Exception:drift.append(slug)
            ids=dict(src.execute('SELECT semantic_id,kind FROM identity WHERE namespace_id=?',(ns,)))
            target={sid for (sid,) in db.execute('SELECT sid FROM target WHERE ns=?',(ns,))}
            if not target:continue
            mp=owner+'/.kristal/v11/identity-migration-map.json'
            try:
                raw=tree.read(mp); mh=sha_bytes(raw);m=anchors(parse(raw),ns,ids);m={k:v for k,v in m.items() if v in target}
                db.execute('INSERT INTO source VALUES (?,?,?)',(mp,mh,'MIGRATION_MAP_OBSERVED'))
                db.executemany('INSERT INTO anchor VALUES (?,?,?,?,?)',((ns,k,v,mp,mh) for k,v in m.items()))
            except (OSError,KeyError,ValueError,TypeError) as e:errors.append((mp,str(e)));continue
            for path in tree.files(owner):
                db.execute('SAVEPOINT scan_file')
                try:
                    raw=tree.read(path); d=parse(raw); sh=sha_bytes(raw)
                    if not isinstance(d,dict):
                        db.execute('RELEASE scan_file');continue
                    at=d.get('artifact_type')
                    if not (at=='kristall_lexicon' or (isinstance(at,str) and at.endswith('referent_registry')) or (at is None and path.endswith('/referents.json'))):
                        db.execute('RELEASE scan_file');continue
                    db.execute('INSERT INTO source VALUES (?,?,?)',(path,sh,'PARSED_OBSERVATION'))
                    for native,lang,term,pointer,method in observations(d):
                        sid=m.get(native)
                        if sid:db.execute('INSERT INTO observation VALUES (?,?,?,?,?,?,?,?,?)',(ns,sid,lang,term,native,path,sh,pointer,method))
                    db.execute('RELEASE scan_file')
                except (OSError,KeyError,ValueError,TypeError,sqlite3.Error) as e:
                    db.execute('ROLLBACK TO scan_file');db.execute('RELEASE scan_file');errors.append((path,str(e)))
            db.commit()
        for ns,sid,lang,variants in db.execute('SELECT ns,sid,lang,json_group_array(DISTINCT term) FROM observation GROUP BY ns,sid,lang'):
            v=sorted(json.loads(variants));db.execute('INSERT INTO resolution VALUES (?,?,?,?,?,?)',(ns,sid,lang,'PRIVATE_EXACT_ANCHOR_CONSENSUS' if len(v)==1 else 'CONFLICT',v[0] if len(v)==1 else None,json.dumps(v,ensure_ascii=False)))
        for (r,) in src.execute('SELECT record_json FROM v52161_alias_review'):
            d=json.loads(r);wid=d.get('external_id');lang=d.get('language')
            if isinstance(wid,str) and re.fullmatch('[QP][1-9][0-9]*',wid) and isinstance(lang,str):db.execute('INSERT INTO alias_target VALUES (?,?,1) ON CONFLICT(wid,lang) DO UPDATE SET occurrences=occurrences+1',(wid,lang))
        db.executemany('INSERT INTO editorial_issue VALUES (?,?)',src.execute("SELECT issue_id,record_json FROM v52161_lexical_issue WHERE kind='external'"))
        db.executemany('INSERT INTO ambiguous VALUES (?,?,?,?)',src.execute("SELECT c.namespace_id,c.semantic_id,c.external_qid,c.source_status FROM candidate_wikidata c JOIN review_queue q ON q.namespace_id=c.namespace_id AND q.semantic_id=c.semantic_id WHERE q.issue='AMBIGUOUS_WIKIDATA_CANDIDATES'"))
        index_status='NOT_AVAILABLE'; index_fingerprint=None
        if index and guard(index).is_file():
            ip=guard(index); st=ip.stat();index_fingerprint={'path':str(ip),'size':st.st_size,'mtime_ns':st.st_mtime_ns,'source_authentication':False}
            try:
                with EncyIndex(ip) as enc:
                    if enc.db:
                        index_status='READ_ONLY_COMPACT_INDEX_OBSERVATIONS_ONLY'
                        for (wid,) in db.execute('SELECT wid FROM alias_target UNION SELECT external_id FROM ambiguous ORDER BY 1'):
                            val=enc.details(wid);db.execute('INSERT INTO external_observation VALUES (?,?)',(wid,json.dumps(val,ensure_ascii=False,sort_keys=True)))
                if (ip.stat().st_size,ip.stat().st_mtime_ns)!=(st.st_size,st.st_mtime_ns):raise ValueError('External index drift')
            except (OSError,ValueError,sqlite3.Error) as e:
                db.execute('DELETE FROM external_observation');index_status='BLOCKED';errors.append((str(ip),str(e)))
        db.executemany('INSERT INTO scan_error VALUES (?,?)',errors);db.commit()
        if digest(source)!=h:raise ValueError('Baseline changed')
        # Recheck every source used for recovery before issuing a receipt.
        for path,sh in db.execute('SELECT path,sha256 FROM source'):
            if sha_bytes(tree.read(path))!=sh:raise ValueError('Source changed: '+path)
        cnt=lambda q:db.execute(q).fetchone()[0]
        result={'format':'koa.kristal-maintenance-scan/0.1','status':'PRIVATE_MAINTENANCE_SCAN_COMPLETE','base_database_sha256':h,'source_kind':'historical_snapshot' if tree.z else 'live_tree','profile_or_state_drift':drift,'source_errors':len(errors),'counts':{ 'targets':len(targets),'anchored_targets':cnt('SELECT count(*) FROM (SELECT DISTINCT ns,sid FROM anchor)'),'observations':cnt('SELECT count(*) FROM observation'),'observed_targets':cnt('SELECT count(*) FROM (SELECT DISTINCT ns,sid FROM observation)'),'consensus_targets':cnt("SELECT count(*) FROM (SELECT DISTINCT ns,sid FROM resolution WHERE status='PRIVATE_EXACT_ANCHOR_CONSENSUS')"),'consensus_cells':cnt("SELECT count(*) FROM resolution WHERE status='PRIVATE_EXACT_ANCHOR_CONSENSUS'"),'conflicting_cells':cnt("SELECT count(*) FROM resolution WHERE status='CONFLICT'"),'alias_pairs':cnt('SELECT count(*) FROM alias_target'),'external_observations':cnt('SELECT count(*) FROM external_observation'),'ambiguous_targets':cnt('SELECT count(*) FROM (SELECT DISTINCT ns,sid FROM ambiguous)'),'editorial_issue_rows':cnt('SELECT count(*) FROM editorial_issue'),'source_files':cnt('SELECT count(*) FROM source')},'external_index_status':index_status,'external_index_fingerprint':index_fingerprint,'policy':{'canonical_modified':False,'public_modified':False,'external_links_accepted':0,'labels_promoted':0,'network_used':False,'historical_aliases_invented':False}}
        db.close();src.close();tree.close();result['maintenance_database_sha256']=digest(dbpath);(output/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        import subprocess
        subprocess.run([sys.executable,str(guard(diag)/'kristaldiag/maintenance_check.py'),str(output),str(base),str(root)],check=True)
        (output/'COMPLETE').write_text('Private maintenance scan and independent receipt check completed.\n',encoding='utf8')
        return result
    finally:
        db.close();src.close();tree.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--locals',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--kristalizer',type=Path,required=True);p.add_argument('--diag',type=Path,required=True);p.add_argument('--index',type=Path);a=p.parse_args();print(json.dumps(run(a.locals,a.baseline,a.output,a.kristalizer,a.diag,a.index),indent=2,ensure_ascii=True))
if __name__=='__main__':main()
