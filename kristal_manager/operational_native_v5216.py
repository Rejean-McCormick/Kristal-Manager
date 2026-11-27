"""Additive, private operational read qualification and activation readiness only."""
from __future__ import annotations
import argparse,collections,importlib.util,json,os,sqlite3,sys,tempfile
from pathlib import Path
from contextlib import closing
from jsonschema.exceptions import ValidationError, SchemaError
from .native_migration_v521 import must,guard,member,sha,digest,read,bytes_json,write,copy_bytes,uri
from .native_extension_v5211 import inventory,check_generation
from .unified_native_v5215 import verify_generations,PINFILE,load_kit
from .active_semantic_federation_v518 import _validated_projection,ReadOnlyTree
BASE='SEMANTIC_V5215_2e689339d7b13582'
DB_SHA='b246895016fb8ad40bcdb83f9bcef61b74dad20aabe3493f6cfbb48fbf69f8f3'
REPORT_SHA='9cd2d46b5ae2e7dac068b9a0160af3afc0b1e2592cca10c8b1b7c94fc8c87d6c'
STATUS='ACTIVE_GRAPH_READINESS_REVIEWED_ACTIVATION_PENDING'

def load(path,name):
    s=importlib.util.spec_from_file_location(name,guard(path));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def baseline(private):
    base=member(private,BASE);must(digest(base/'report.json')==REPORT_SHA,'V5215 report drift');r=check_generation(base);must(r['database_sha256']==DB_SHA and r['status']=='UNIFIED_PRIVATE_READER_QUALIFIED_ACTIVATION_PENDING','V5215 baseline mismatch');return base,r

def compare_projection(db,ns,slug,projection,registry):
    must(projection['namespace_id']==registry['namespace_id']==ns,'Namespace mismatch')
    actual={x[0]:(x[1],x[2],x[3],json.loads(x[4])) for x in db.execute('SELECT semantic_id,kind,lifecycle_status,accepted_wikidata,candidate_wikidata_json FROM identity WHERE namespace_id=? AND owner_slug=?',(ns,slug))}
    observed={x['id']:(x['kind'],x['status'],x['wikidata']['accepted_exact'],x['wikidata']['candidate_exact']) for x in projection['identities']}
    must(len(observed)==len(projection['identities']) and actual==observed,'Active identity/index drift')
    must(len(registry['identities'])==len(actual) and {x['id']:(x['kind'],x['status']) for x in registry['identities']}=={k:v[:2] for k,v in actual.items()},'Registry/index mismatch')
    labels={(sid,lang):(term,priority) for sid,lang,term,priority in db.execute('SELECT semantic_id,language_tag,preferred_term,priority FROM lexical WHERE namespace_id=?',(ns,))}
    expected={(x['id'],lang):(v['preferred'],v['priority']) for x in projection['identities'] for lang,v in x.get('labels',{}).items()}
    must(labels==expected,'Active lexical/index drift');return actual

def qualify_active(db,locals_root,row,out,qualify,check_pending):
    slug,directory,ns,p_sha,s_sha,pr_sha=row;w=member(locals_root,directory);profile_rel='.kristal/v11/authoring.json';state_rel='canon/state.index.json';pointer_rel='derived/semantic/active-resolution.json'
    check_pending(w,member)
    must(digest(member(w,profile_rel))==p_sha and digest(member(w,state_rel))==s_sha,'Profile/state differs from frozen active index')
    pointer=read(member(w,pointer_rel));must(pointer['projection_sha256']==pr_sha,'Projection differs from frozen index');projection=_validated_projection(ReadOnlyTree(locals_root),directory,slug,s_sha);must(projection is not None,'No active projection')
    config=read(member(w,profile_rel));roles=projection['active_roles'];must(all(config[k]==a['path'] for k,a in roles.items()),'Projection/profile role mismatch')
    pins={profile_rel:p_sha,state_rel:s_sha,pointer_rel:digest(member(w,pointer_rel)),pointer['projection']:pr_sha}
    for a in roles.values():pins[a['path']]=a['sha256']
    for lang in projection['languages'].values():
        for a in lang['layers']:pins[a['path']]=a['sha256']
    # Work on exact private copies. No historical entries' bytes are copied or requalified.
    for rel,h in pins.items():
        raw=member(w,rel).read_bytes();must(sha(raw)==h,'Source drift during capture: '+rel);copy_bytes(member(out,rel),raw)
    registry=read(member(out,config['registry']));graph=read(member(out,config['graph']));actual=compare_projection(db,ns,slug,projection,registry)
    must(graph['namespace_id']==ns,'Graph namespace mismatch');q=qualify(out);must(q['valid'] and q['namespace_id']==ns and q['graph_sha256']==roles['graph']['sha256'] and q['reference_coverage_match'],'Kit/Framework disagreement')
    assertions=[(ns,a['id'],slug,'/assertions/'+str(i)) for i,a in enumerate(graph['assertions'])]
    must(len(assertions)==len(set(x[1] for x in assertions)) and all(actual[x[1]][0]=='assertion' for x in assertions),'Graph assertion/index mismatch')
    for rel,h in pins.items():must(digest(member(w,rel))==h,'Live source drift during qualification: '+rel)
    return {'slug':slug,'namespace_id':ns,'status':'QUALIFIED_ACTIVE_GRAPH','graph_path':'active-graphs/'+slug+'/'+config['graph'],'graph_sha256':roles['graph']['sha256'],'profile_sha256':p_sha,'state_sha256':s_sha,'projection_sha256':pr_sha,'assertions':len(assertions),'registry_ids':len(actual),'registry_assertion_ids':sum(x[0]=='assertion' for x in actual.values()),'source_pins':pins,'framework_version':q['framework_version'],'historical_artifact_bytes_revalidated':False},assertions

def registration_readiness(private,locals_root,db,profile,plan_report,preflight):
    slug,ns,generation,inv_json,directory=profile;inv=json.loads(inv_json);pgen,summary=plan_report
    plan_path=member(pgen,'registration-plans/'+slug+'.json');packet_path=member(pgen,'editorial/'+slug+'.json');must(digest(plan_path)==summary['plan_sha256'] and digest(packet_path)==summary['packet_sha256'],'Plan or packet digest mismatch');plan=read(plan_path);packet=read(packet_path)
    must(plan['slug']==slug and plan['namespace_id']==ns and plan['packet_sha256']==summary['packet_sha256'],'Plan scope mismatch');must(inventory(member(private,generation+'/candidates/'+slug))==inv,'Candidate inventory drift')
    if 'predicate_review_sha256' in plan:must(digest(member(pgen,'predicate-review/'+slug+'.json'))==plan['predicate_review_sha256'],'Predicate review drift')
    result=preflight(member(locals_root,directory),plan,packet,inv,safe=member,digest=digest)
    return {'slug':slug,'layer':'candidate','plan_sha256':summary['plan_sha256'],'packet_sha256':summary['packet_sha256'],'generation':pgen.name,**result}

def run(private,locals_root,kit,framework):
    private,locals_root,kit,framework=map(guard,(private,locals_root,kit,framework));must(all(private!=p and private not in p.parents and p not in private.parents for p in (locals_root,kit,framework,kit.parent/'Kristal-Manager',kit.parent/'kristal-public')),'Private path overlaps source')
    base,report=baseline(private);anc=verify_generations(private,read(PINFILE));must([g.name for g,r in anc]==report['required_generations'],'Ancestor scope mismatch');k=load_kit(kit);u=k.framework_reader(framework);reader=u.Reader(base,REPORT_SHA)
    q=load(kit/'scripts/qualify_framework_v11.py','v5216_qualification');q.verify_pin(framework);a=load(kit/'tools/operational_native_v5216.py','v5216_preflight');plans={s['slug']:(g,s) for g,r in anc for s in r.get('registration_plans',[])};must(len(plans)==37,'Expected 37 rehearsal plans')
    import shutil
    results=[];index=[];readiness=[]
    with tempfile.TemporaryDirectory(prefix='v5216-stage-',dir=private) as td:
        stage=Path(td);dbout=stage/'active.sqlite'
        with closing(sqlite3.connect(uri(base/'active.sqlite'),uri=True)) as db:
            must(db.execute('PRAGMA integrity_check').fetchone()==('ok',) and not db.execute('PRAGMA foreign_key_check').fetchone(),'Baseline integrity failure')
            rows=db.execute('SELECT slug,local_directory,namespace_id,profile_sha256,state_sha256,projection_sha256 FROM workspace WHERE active=1 ORDER BY slug').fetchall();must(len(rows)==77,'Active scope mismatch')
            for row in rows:
                slug=row[0];out=member(stage,'active-graphs/'+slug)
                try:
                    result,aa=qualify_active(db,locals_root,row,out,lambda p:q.qualify(p,framework),a.check_pending);index+=aa
                except (ValueError,KeyError,TypeError,OSError,RuntimeError,ValidationError,SchemaError) as e:
                    if out.exists():shutil.rmtree(out)
                    # Keep failures explicit and do not serve any graph for that workspace.
                    result={'slug':slug,'namespace_id':row[2],'status':'BLOCKED_ACTIVE_GRAPH','reason':str(e).replace(str(locals_root),'[locals]').replace(str(stage),'[stage]'),'profile_sha256':row[3],'state_sha256':row[4],'projection_sha256':row[5],'assertions':0}
                results.append(result);print('V5.21.6 active:',slug,result['status'],flush=True)
            for profile in db.execute("SELECT p.slug,p.namespace_id,p.generation,p.inventory_json,w.local_directory FROM v5215_profile p JOIN workspace w USING(slug) WHERE p.layer='candidate' ORDER BY p.slug"):
                slug=profile[0]
                try:r=registration_readiness(private,locals_root,db,profile,plans[slug],a.preflight)
                except (ValueError,KeyError,TypeError,OSError,RuntimeError,ValidationError,SchemaError) as e:r={'slug':slug,'layer':'candidate','status':'BLOCKED_PREFLIGHT','reason':str(e).replace(str(locals_root),'[locals]'),'production_activation':False}
                readiness.append(r);print('V5.21.6 readiness:',slug,r['status'],flush=True)
            for slug,layer in db.execute("SELECT slug,layer FROM v5215_profile WHERE layer IN ('structured','discovery') ORDER BY slug"):
                root,packet,_=reader.packet(slug);state,rr=u.f.validate_packet(root,packet);must((state is None)==(layer=='discovery'),'Packet layer mismatch')
                readiness.append({'slug':slug,'layer':layer,'status':'NATIVE_PACKET_REVALIDATED_NOT_V11','occurrences':len(rr),'registered_artifacts':len(packet['registered_artifacts']),'production_activation':False,'formal_v11_contract_qualified':False})
            must(len(readiness)==50,'Readiness scope mismatch')
            with closing(sqlite3.connect(dbout)) as outdb:
                db.backup(outdb);outdb.execute('PRAGMA foreign_keys=ON')
                with outdb:
                    outdb.execute('CREATE TABLE v5216_active_graph(slug TEXT PRIMARY KEY,namespace_id TEXT UNIQUE NOT NULL,status TEXT NOT NULL,graph_path TEXT,graph_sha256 TEXT,profile_sha256 TEXT NOT NULL,state_sha256 TEXT NOT NULL,projection_sha256 TEXT NOT NULL,assertions INTEGER NOT NULL,report_json TEXT NOT NULL,FOREIGN KEY(slug) REFERENCES workspace(slug))')
                    outdb.execute('CREATE TABLE v5216_active_assertion(namespace_id TEXT NOT NULL,semantic_id TEXT NOT NULL,slug TEXT NOT NULL,json_pointer TEXT NOT NULL,PRIMARY KEY(namespace_id,semantic_id),FOREIGN KEY(slug) REFERENCES v5216_active_graph(slug),FOREIGN KEY(namespace_id,semantic_id) REFERENCES identity(namespace_id,semantic_id))')
                    outdb.execute('CREATE TABLE v5216_activation_readiness(slug TEXT PRIMARY KEY,layer TEXT NOT NULL,status TEXT NOT NULL,report_json TEXT NOT NULL,FOREIGN KEY(slug) REFERENCES workspace(slug))')
                    outdb.executemany('INSERT INTO v5216_active_graph VALUES(?,?,?,?,?,?,?,?,?,?)',[(r['slug'],r['namespace_id'],r['status'],r.get('graph_path'),r.get('graph_sha256'),r['profile_sha256'],r['state_sha256'],r['projection_sha256'],r['assertions'],json.dumps(r,sort_keys=True,ensure_ascii=True)) for r in results]);outdb.executemany('INSERT INTO v5216_active_assertion VALUES(?,?,?,?)',index);outdb.executemany('INSERT INTO v5216_activation_readiness VALUES(?,?,?,?)',[(r['slug'],r['layer'],r['status'],json.dumps(r,sort_keys=True,ensure_ascii=True)) for r in readiness])
                must(outdb.execute('PRAGMA integrity_check').fetchone()==('ok',) and not outdb.execute('PRAGMA foreign_key_check').fetchone(),'Output integrity failure')
        # Recheck live bytes and prior immutable manifests before publication.
        for r in results:
            if r['status']=='QUALIFIED_ACTIVE_GRAPH':
                directory=next(x[1] for x in rows if x[0]==r['slug']);w=member(locals_root,directory)
                a.check_pending(w,member)
                for rel,h in r['source_pins'].items():must(digest(member(w,rel))==h,'Live active drift before publication')
        with closing(sqlite3.connect(uri(base/'active.sqlite'),uri=True)) as recheck:
            for p in recheck.execute("SELECT p.slug,p.namespace_id,p.generation,p.inventory_json,w.local_directory FROM v5215_profile p JOIN workspace w USING(slug) WHERE p.layer='candidate' ORDER BY p.slug"):
                prev=next(x for x in readiness if x['slug']==p[0])
                if prev['status']=='PREFLIGHT_PASSED_EDITORIAL_AND_TRANSACTION_PENDING':must(registration_readiness(private,locals_root,recheck,p,plans[p[0]],a.preflight)==prev,'Candidate readiness drift before publication')
        must(baseline(private)==(base,report) and verify_generations(private,read(PINFILE))==anc,'Generation drift')
        dest=member(private,'SEMANTIC_V5216_'+sha(bytes_json([DB_SHA,results,readiness]))[:16]);counts=dict(collections.Counter(r['status'] for r in results));rc=dict(collections.Counter(r['status'] for r in readiness));ret={'format':'koa.kristal-operational-readiness/0.1','status':STATUS,'database':str(dest/'active.sqlite'),'database_sha256':digest(dbout),'source_database_sha256':DB_SHA,'source_report_sha256':REPORT_SHA,'prior_generation_name':BASE,'required_generations':report['required_generations']+[BASE],'active_counts':report['active_counts'],'active_graph_status_counts':counts,'active_assertion_count':len(index),'active_graphs':results,'readiness_counts':rc,'readiness':readiness,'policy':{'canonical_modified':False,'public_modified':False,'network_used':False,'profiles_activated':0,'production_reader_integrated':False,'editorial_approval_granted':False,'transaction_executor_implemented':False,'new_v11_candidates':0,'registered_scripts_executed':False,'partial_active_graph_scope_possible':True}}
        write(stage/'report.json',ret);write(stage/'manifest.sha256.json',inventory(stage))
        if dest.exists():prev=check_generation(dest);must(prev==ret,'Existing generation differs');return prev
        pub=stage/'publish';pub.mkdir()
        for p in list(stage.iterdir()):
            if p!=pub:os.replace(p,pub/p.name)
        os.rename(pub,dest);return ret

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for x in ('private-dir','locals','kit','framework'):p.add_argument('--'+x,type=Path,required=True)
    p.add_argument('--apply',action='store_true');a=p.parse_args();must(a.apply,'--apply required (private output only)');r=run(a.private_dir,a.locals,a.kit,a.framework);print(json.dumps(r,ensure_ascii=True,indent=2));print('V5.21.6 ONE-SHOT:',r['status'])
if __name__=='__main__':main()
