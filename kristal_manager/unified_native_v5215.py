"""V5.21.5 private unified reader/index; no writes to workspaces or public."""
from __future__ import annotations
import argparse, collections, importlib.util, json, os, sqlite3,tempfile
from contextlib import closing
from pathlib import Path
from .native_migration_v521 import must,guard,member,sha,digest,read,bytes_json,write,uri
from .native_extension_v5211 import inventory,check_generation
PINFILE=Path(__file__).with_name('unified_v5215_pins.json')
STATUS='UNIFIED_PRIVATE_READER_QUALIFIED_ACTIVATION_PENDING'

def load_kit(kit):
    s=importlib.util.spec_from_file_location('kristal_unified_kit',member(kit,'tools/unified_native_v5215.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def verify_generations(private,pins):
    out=[]
    for p in pins['generations']:
        g=member(private,p['name']);must(digest(g/'report.json')==p['report_sha256'],'Report drift: '+p['name']);r=check_generation(g);must(r['database_sha256']==p['database_sha256'] and r['status']==p['status'],'Generation mismatch');out.append((g,r))
    for (_,a),(_,b) in zip(out,out[1:]):must(b['source_database_sha256']==a['database_sha256'],'Broken generation chain')
    return out

def run(private,kit,framework):
    private,kit,framework=map(guard,(private,kit,framework));must(all(private!=p and private not in p.parents and p not in private.parents for p in (kit,framework,kit.parent/'locals',kit.parent/'kristal-public',kit.parent/'Kristal-Manager')),'Private path overlaps repository');pins=read(PINFILE);generations=verify_generations(private,pins);base,report=generations[-1];k=load_kit(kit);reader=k.framework_reader(framework);f=reader.f
    profiles=[];assertions=[];artifacts=[];records=[];by_slug={};candidate_counts=collections.Counter();native_counts=collections.Counter()
    with closing(sqlite3.connect(uri(base/'active.sqlite'),uri=True)) as inp:
        must(inp.execute('PRAGMA integrity_check').fetchone()==('ok',) and not inp.execute('PRAGMA foreign_key_check').fetchone(),'Invalid baseline database');workspaces={s:(n,a) for s,n,a in inp.execute('SELECT slug,namespace_id,active FROM workspace')};must(len(workspaces)==127 and sum(a for n,a in workspaces.values())==77,'Unexpected workspace scope')
        for slug,(ns,active) in sorted(workspaces.items()):
            if active:profiles.append((slug,'active',ns,base.name,None,None))
        for idx,(g,r) in enumerate(generations[:-1]):
            prefix=('v521','v5211','v5212','v5213')[idx]
            for c in r.get('new_candidates',r.get('candidates',[])):
                slug=c['slug'];ns=c['namespace_id'];root=member(g,'candidates/'+slug);inv=pins['candidate_inventory'][slug];must(slug not in by_slug and workspaces[slug][1]==0 and inventory(root)==inv,'Candidate scope/inventory drift: '+slug)
                ii,ll,aa=k.candidate_rows(reader,root,c,inv);must(sorted(ii)==sorted(inp.execute(f'SELECT * FROM {prefix}_candidate_identity WHERE namespace_id=?',(ns,)).fetchall()),'Candidate identity index mismatch');must(sorted(ll)==sorted(inp.execute(f'SELECT * FROM {prefix}_candidate_lexical WHERE namespace_id=?',(ns,)).fetchall()),'Candidate lexical index mismatch');assertions+=aa;profiles.append((slug,'candidate',ns,g.name,None,json.dumps(inv,sort_keys=True)));by_slug[slug]=ns;candidate_counts.update({'identities':len(ii),'labels':len(ll),'assertions':len(aa)});print('V5.21.5 candidate reader:',slug,flush=True)
        must(len(by_slug)==37 and len(set(by_slug.values()))==37 and not set(by_slug.values())&{n for n,a in workspaces.values() if a},'Candidate namespace collision')
        for p in report['packets']:
            slug=p['slug'];root=member(base,'structured/'+slug);packet=f.decode(reader.verified(root,'packet.json',p['packet_sha256']));state,rr=f.validate_packet(root,packet);must(packet['slug']==slug and slug not in by_slug and workspaces[slug][1]==0,'Structured scope mismatch');layer='structured' if state is not None else 'discovery';profiles.append((slug,layer,None,base.name,p['packet_sha256'],None));by_slug[slug]=None
            actual=[(x['occurrence_id'],slug,p['source_path'],x['pointer'],x['native_assertion_id'],x['native_status'],x['subject_ref'],x['predicate_ref'],x['object']['native_kind'],x['object']['shape'],x['object']['form'],x['object']['anomaly']) for x in rr];must(sorted(actual)==sorted(inp.execute('SELECT * FROM v5214_occurrence WHERE slug=?',(slug,)).fetchall()),'Structured index mismatch');qs=[(x['occurrence_id'],i,q['object']['pointer'],q['predicate_ref'],q['object']['native_kind'],q['object']['shape'],q['object']['form']) for x in rr for i,q in enumerate(x['qualifiers'])];must(sorted(qs)==sorted(inp.execute('SELECT q.* FROM v5214_qualifier q JOIN v5214_occurrence o USING(occurrence_id) WHERE o.slug=?',(slug,)).fetchall()),'Qualifier index mismatch');must(sorted(packet['files'].items())==sorted(inp.execute('SELECT path,sha256 FROM v5214_source_file WHERE slug=?',(slug,)).fetchall()),'Source index mismatch')
            if layer=='discovery':
                for a in packet['registered_artifacts']:
                    path=a['path'];h=packet['files'][path];raw=reader.verified(root/'originals',path,h);media='json' if path.endswith('.json') else 'metadata_only';artifacts.append((slug,path,a['artifact_id'],a['contract_id'],a['contract_version'],h,media));native_counts[media]+=1
                    if media=='json':records+=k.native_rows(reader,slug,path,f.decode(raw))
            print('V5.21.5 packet reader:',slug,flush=True)
        must(len(profiles)==127 and len(by_slug)==50 and len(artifacts)==77 and len(records)==189,'Reader scope/count mismatch');must(candidate_counts=={'identities':35953,'labels':9732,'assertions':25565},'Candidate totals mismatch')
    with tempfile.TemporaryDirectory(prefix='v5215-stage-',dir=private) as td:
        stage=Path(td);dbout=stage/'active.sqlite'
        with closing(sqlite3.connect(uri(base/'active.sqlite'),uri=True)) as inp,closing(sqlite3.connect(dbout)) as db:
            inp.backup(db);db.execute('PRAGMA foreign_keys=ON')
            with db:
                db.execute('CREATE TABLE v5215_profile(slug TEXT PRIMARY KEY, layer TEXT NOT NULL CHECK(layer IN (\'active\',\'candidate\',\'structured\',\'discovery\')), namespace_id TEXT, generation TEXT NOT NULL, packet_sha256 TEXT, inventory_json TEXT, FOREIGN KEY(slug) REFERENCES workspace(slug))')
                db.execute('CREATE TABLE v5215_candidate_assertion(namespace_id TEXT NOT NULL, semantic_id TEXT NOT NULL, slug TEXT NOT NULL, json_pointer TEXT NOT NULL, native_status TEXT, native_role TEXT, PRIMARY KEY(namespace_id,semantic_id), FOREIGN KEY(slug) REFERENCES v5215_profile(slug))')
                db.execute('CREATE TABLE v5215_native_artifact(slug TEXT NOT NULL,path TEXT NOT NULL,artifact_id TEXT NOT NULL,contract_id TEXT NOT NULL,contract_version TEXT NOT NULL,sha256 TEXT NOT NULL,media_kind TEXT NOT NULL,PRIMARY KEY(slug,path),FOREIGN KEY(slug) REFERENCES v5215_profile(slug))')
                db.execute('CREATE TABLE v5215_native_record(slug TEXT NOT NULL,path TEXT NOT NULL,collection TEXT NOT NULL,native_id TEXT NOT NULL,id_field TEXT NOT NULL,json_pointer TEXT NOT NULL,PRIMARY KEY(slug,path,collection,native_id),FOREIGN KEY(slug,path) REFERENCES v5215_native_artifact(slug,path))')
                db.executemany('INSERT INTO v5215_profile VALUES (?,?,?,?,?,?)',sorted(profiles));db.executemany('INSERT INTO v5215_candidate_assertion VALUES (?,?,?,?,?,?)',assertions);db.executemany('INSERT INTO v5215_native_artifact VALUES (?,?,?,?,?,?,?)',artifacts);db.executemany('INSERT INTO v5215_native_record VALUES (?,?,?,?,?,?)',records)
                for suffix in ('identity','lexical'):db.execute('CREATE VIEW v5215_candidate_'+suffix+' AS '+' UNION ALL '.join('SELECT * FROM '+p+'_candidate_'+suffix for p in ('v521','v5211','v5212','v5213')))
            must(db.execute('PRAGMA integrity_check').fetchone()==('ok',) and not db.execute('PRAGMA foreign_key_check').fetchone(),'Invalid output database')
        # Verify same inputs after building before publishing (no production changes).
        must(verify_generations(private,pins)==generations,'Generation drift');dest=member(private,'SEMANTIC_V5215_'+sha(bytes_json([pins['generations'][-1],profiles,records]))[:16]);result={'format':'koa.kristal-unified-reader/0.1','status':STATUS,'database':str(dest/'active.sqlite'),'database_sha256':digest(dbout),'source_database_sha256':report['database_sha256'],'source_report_sha256':pins['generations'][-1]['report_sha256'],'prior_generation':str(base),'required_generations':[x['name'] for x in pins['generations']],'active_counts':report['active_counts'],'profiles':dict(collections.Counter(x[1] for x in profiles)),'candidate_counts':dict(candidate_counts),'structured_counts':report['counts'],'native_artifacts':dict(native_counts),'native_records_by_slug':dict(collections.Counter(x[0] for x in records)),'native_record_count':len(records),'policy':{'canonical_modified':False,'profiles_activated':0,'public_modified':False,'network_used':False,'production_reader_integrated':False,'editorial_approval_granted':False,'new_v11_candidates':0,'active_payload_metadata_only':True,'registered_scripts_executed':False}}
        write(stage/'report.json',result);write(stage/'manifest.sha256.json',inventory(stage));
        if dest.exists():prev=check_generation(dest);must(prev==result,'Existing generation differs');return prev
        pub=stage/'publish';pub.mkdir()
        for p in list(stage.iterdir()):
            if p!=pub:os.replace(p,pub/p.name)
        os.rename(pub,dest);return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for x in ('private-dir','kit','framework'):p.add_argument('--'+x,type=Path,required=True)
    p.add_argument('--apply',action='store_true');a=p.parse_args();must(a.apply,'--apply required (private reader only)');r=run(a.private_dir,a.kit,a.framework);print(json.dumps(r,ensure_ascii=True,indent=2));print('V5.21.5 ONE-SHOT:',r['status'])
if __name__=='__main__':main()
