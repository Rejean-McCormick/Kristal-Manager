"""Private-only diagnostic and compatibility rehearsal of legacy Wikidata lexical records.
Never edits a workspace, changes active index terms, or claims absent aliases were empty upstream.
"""
from __future__ import annotations
import argparse, collections, json, os, shutil, sqlite3, tempfile
from contextlib import closing
from pathlib import Path
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError, SchemaError
from .native_migration_v521 import must,guard,member,sha,digest,read,bytes_json,write,copy_bytes,uri
from .native_extension_v5211 import inventory,check_generation
from . import operational_native_v5216 as op
BASE='SEMANTIC_V5216_d17502c25ec28015'
DB_SHA='9e953dbef01401353553415defce8ab37677505fc240a1e7e5f5c99a13700fa1'
REPORT_SHA='41fb7e98ddccd432cbd01da5e89d9a3e07e2fdb2555bc5ca366c7cf100628c5f'
STATUS='LEXICAL_COMPATIBILITY_REVIEWED_CANONICAL_REPAIR_PENDING'
PINFILE=Path(__file__).with_name('lexical_compatibility_v52161_pins.json')
LEGACY='wikidata-20261026-rebuilt-v2'
LEGACY_FIELDS={'namespace_id','semantic_id','language','preferred_term','source_snapshot','external_id'}
ERRORS=(ValueError,KeyError,TypeError,OSError,RuntimeError,ValidationError,SchemaError)

def strict_json(raw):
    def unique(pairs):
        d={}
        for k,v in pairs:
            must(k not in d,'Duplicate JSON key');d[k]=v
        return d
    def invalid(s):raise ValueError('Nonfinite JSON: '+s)
    return json.loads(raw,object_pairs_hook=unique,parse_constant=invalid)

def verified_alias(db,record):
    """Same scoped cell and exact entire other payload, same source snapshot/revision only."""
    row=db.execute('SELECT external_id,source_snapshot,source_revision,record_json,status FROM v520_verified_record WHERE namespace_id=? AND semantic_id=? AND language_tag=?',(record['namespace_id'],record['semantic_id'],record['language'])).fetchone()
    if row is None:return None
    other=strict_json(row[3]);aliases=other.pop('aliases',None)
    if (row[4]=='ACTIVE_CANONICAL_SOURCE_LABEL' and row[0]==record['external_id'] and row[1]==record['source_snapshot'] and type(record.get('source_revision')) is int and record['source_revision']>0 and row[2]==record['source_revision'] and other==record and isinstance(aliases,list)):
        return aliases,sha(row[3].encode('utf8'))
    return None

def repair_catalog(db,root,config,slug,ns,pins,validator):
    cat_path=member(root,config['catalog']);cat=strict_json(cat_path.read_bytes());must(cat['namespace_id']==ns,'Catalog namespace mismatch')
    patches={};reviews=[];unknown=0
    for lang in cat['languages']:
        for layer in lang['layers']:
            if layer['kind']!='wikidata':continue
            f=member(cat_path.parent,layer['path']);rel=f.relative_to(root).as_posix();raw=f.read_bytes();h=sha(raw);must(h==layer['sha256'],'Layer hash mismatch')
            lines=raw.splitlines(keepends=True);changed=False;missing=0;seen=set()
            for i,line in enumerate(lines):
                if not line.strip():continue
                row=strict_json(line);must(row['namespace_id']==ns and row['language']==lang['tag'] and row['source_snapshot']==layer['source_snapshot'],'Lexical layer scope mismatch');must(row['semantic_id'] not in seen,'Duplicate lexical ID');seen.add(row['semantic_id'])
                if 'aliases' in row:continue
                missing+=1;key=(row['namespace_id'],row['semantic_id'],row['language']);match=verified_alias(db,row);evidence=None
                if match is not None:
                    aliases,evidence=match;status='EXACT_V520_ALIAS_EVIDENCE';replacement=dict(row,aliases=aliases)
                elif h in pins.get(slug,{}) and set(row)==LEGACY_FIELDS and row['source_snapshot']==LEGACY and pins[slug][h]['language']==row['language'] and pins[slug][h]['source_snapshot']==LEGACY:
                    # Only a private validator adapter: no source says the alias set was empty.
                    status='LEGACY_ALIASES_NOT_RECORDED_PRIVATE_PLACEHOLDER';replacement=dict(row,aliases=[])
                else:
                    status='UNRESOLVED_MISSING_ALIAS';replacement=None;unknown+=1
                item={'slug':slug,'namespace_id':ns,'semantic_id':row['semantic_id'],'language':row['language'],'external_id':row['external_id'],'source_snapshot':row['source_snapshot'],'path':rel,'line':i+1,'source_sha256':h,'line_sha256':sha(line),'status':status,'evidence_record_sha256':evidence,'historical_snapshot_path':pins.get(slug,{}).get(h,{}).get('source_path'),'original_record':row,'private_replacement':replacement,'canonical_repair_authorized':False}
                reviews.append(item)
                if replacement is not None:
                    validator.validate(replacement);must({k:v for k,v in replacement.items() if k!='aliases'}==row,'Nonalias change refused');lines[i]=(json.dumps(replacement,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode('utf8');changed=True
            if h in pins.get(slug,{}):must(missing==pins[slug][h]['missing'],'Pinned legacy layer count drift')
            if changed:
                b=b''.join(lines);patches[rel]=b;layer['sha256']=sha(b)
    if patches:
        cat['catalog_id']+=':private-v52161:'+sha(bytes_json(sorted((k,sha(v)) for k,v in patches.items())))[:16]
        patches[config['catalog']]=bytes_json(cat)
    return patches,reviews,unknown

def capture(db,locals_root,row,out,check_pending):
    slug,directory,ns,p_sha,s_sha,pr_sha=row;w=member(locals_root,directory);profile_rel='.kristal/v11/authoring.json';state_rel='canon/state.index.json';pointer_rel='derived/semantic/active-resolution.json'
    check_pending(w,member);must(not member(w,'.kristal/v11/transactions/writer.lock').exists(),'Active writer lock')
    must(digest(member(w,profile_rel))==p_sha and digest(member(w,state_rel))==s_sha,'Profile/state differs from frozen active index')
    pointer=read(member(w,pointer_rel));must(pointer['projection_sha256']==pr_sha,'Projection differs from frozen index');tree=op.ReadOnlyTree(locals_root)
    try:projection=op._validated_projection(tree,directory,slug,s_sha)
    finally:tree.close()
    must(projection is not None,'No active projection');config=read(member(w,profile_rel));roles=projection['active_roles'];must(all(config[k]==a['path'] for k,a in roles.items()),'Projection/profile role mismatch')
    pins={profile_rel:p_sha,state_rel:s_sha,pointer_rel:digest(member(w,pointer_rel)),pointer['projection']:pr_sha}
    for a in roles.values():pins[a['path']]=a['sha256']
    for lang in projection['languages'].values():
        for a in lang['layers']:pins[a['path']]=a['sha256']
    for rel,h in pins.items():
        raw=member(w,rel).read_bytes();must(sha(raw)==h,'Source drift during capture: '+rel);copy_bytes(member(out,rel),raw)
    registry=read(member(out,config['registry']));graph=read(member(out,config['graph']));actual=op.compare_projection(db,ns,slug,projection,registry)
    must(graph['namespace_id']==ns,'Graph namespace mismatch');aa=[(ns,a['id'],slug,'/assertions/'+str(i)) for i,a in enumerate(graph['assertions'])];must(len(aa)==len(set(x[1] for x in aa)) and all(actual.get(x[1],('',))[0]=='assertion' for x in aa),'Graph assertion/index mismatch')
    return w,config,pins,graph,actual,aa

def history_audit(w,state,graph_path,ns,gaps,validator):
    evidence={sid:[] for sid in gaps};pins={};errors=[]
    if not gaps:return [],pins,errors
    for a in state['canonical_artifacts']:
        if a.get('logical_contract',{}).get('id')!='kristal.v11.semantic-graph' or a['path']==graph_path:continue
        rel=a['path']
        try:
            raw=member(w,rel).read_bytes();h=sha(raw);pins[rel]=h;g=strict_json(raw);validator.validate(g);must(g['namespace_id']==ns,'Historical graph namespace mismatch');seen=set()
            for i,x in enumerate(g['assertions']):
                must(x['id'] not in seen,'Duplicate historical KA');seen.add(x['id'])
            for i,x in enumerate(g['assertions']):
                if x['id'] in evidence:evidence[x['id']].append({'path':rel,'sha256':h,'pointer':'/assertions/'+str(i),'record_sha256':sha(bytes_json(x)),'record_digest_encoding':'sorted-json-python-v52161','record':x})
        except ERRORS as e:errors.append({'path':rel,'reason':str(e).replace(str(w),'[workspace]')})
    rr=[]
    for sid,ev in sorted(evidence.items()):
        status='HISTORICAL_NOT_FOUND_IN_REGISTERED_GRAPHS' if not ev else ('HISTORICAL_RECORDS_CONFLICT' if len({x['record_sha256'] for x in ev})>1 else 'HISTORICAL_RECORD_FOUND_NOT_SELECTED')
        if errors:status='HISTORICAL_AUDIT_INCOMPLETE_'+status
        rr.append({'namespace_id':ns,'semantic_id':sid,'status':status,'observations':ev,'restoration_authorized':False})
    return rr,pins,errors

def lexical_schema_issues(root,config,slug,validators):
    """Audit every selected layer, not just the first failing Framework row."""
    cat_path=member(root,config['catalog']);cat=strict_json(cat_path.read_bytes());issues=[]
    for lang in cat['languages']:
        for layer in lang['layers']:
            f=member(cat_path.parent,layer['path']);raw=f.read_bytes();h=sha(raw);rel=f.relative_to(root).as_posix();must(h==layer['sha256'],'Layer digest mismatch')
            if layer['kind']=='curated':items=[(None,strict_json(raw),None)]
            else:items=[(i+1,strict_json(line),sha(line)) for i,line in enumerate(raw.splitlines(keepends=True)) if line.strip()]
            for line,rec,linehash in items:
                errs=sorted(validators[layer['kind']].iter_errors(rec),key=lambda e:(e.json_path,e.message))
                for e in errs:
                    issues.append({'slug':slug,'path':rel,'line':line,'sha256':h,'line_sha256':linehash,'kind':layer['kind'],'language':lang['tag'],'semantic_id':rec.get('semantic_id'),'json_path':e.json_path,'validator':e.validator,'message':e.message})
    return issues

def qualify_core(root,config,kit_module,official):
    # The three core documents are checked independently of dictionary conformance.
    # The Kit also checks registration, graph references, and existing preferred terms.
    data=kit_module.validate(root);files=data['files'];reg=read(files['registry']);g=read(files['graph']);cw=read(files['crosswalk']);official.validate_documents(registry=reg,graph=g,crosswalk=cw,lexicons=[])
    return {'namespace_id':data['namespace_id'],'graph_sha256':digest(files['graph']),'framework_version':'11.0.0-draft.4'}

def qualify_one(db,locals_root,row,stage,qualify,check_pending,legacy_pins,lex_validator,graph_validator,core_qualify,layer_validators):
    slug,directory,ns,p_sha,s_sha,pr_sha=row;out=member(stage,'active-graphs/'+slug);compat=member(stage,'compatibility/'+slug);reviews=[];hist=[];issues=[];aa=[]
    result={'slug':slug,'namespace_id':ns,'profile_sha256':p_sha,'state_sha256':s_sha,'projection_sha256':pr_sha,'status':'BLOCKED_ACTIVE_GRAPH','assertions':0}
    try:
        w,config,pins,graph,actual,aa=capture(db,locals_root,row,out,check_pending);result['source_pins']=pins;result['graph_path']='active-graphs/'+slug+'/'+config['graph'];result['graph_sha256']=pins[config['graph']];result['registry_assertion_ids']=sum(x[0]=='assertion' for x in actual.values());result['registry_ids']=len(actual)
        core=core_qualify(out,config);must(core['namespace_id']==ns and core['graph_sha256']==result['graph_sha256'],'Core qualification mismatch')
        patches,reviews,unknown=repair_catalog(db,out,config,slug,ns,legacy_pins,lex_validator)
        issues=lexical_schema_issues(out,config,slug,layer_validators)
        if reviews and not unknown:
            must(patches,'Missing compatibility payload');shutil.copytree(out,compat)
            for rel,b in patches.items():member(compat,rel).write_bytes(b)
            result['compatibility_catalog_sha256']=digest(member(compat,config['catalog']));result['compatibility_patches']={rel:sha(b) for rel,b in patches.items()}
            remaining=lexical_schema_issues(compat,config,slug,layer_validators);result['compatibility_remaining_schema_issue_count']=len(remaining)
            if remaining:
                result.update(status='PRIVATE_GRAPH_ONLY_LEXICAL_BLOCKED',reason='Lexical schema defects remain after private alias rehearsal; no editorial field fabricated')
            else:
                # Full qualification applies only to a synthetic private copy.
                q=qualify(compat);must(q['valid'] and q['namespace_id']==ns and q['graph_sha256']==result['graph_sha256'] and q['reference_coverage_match'],'Qualification mismatch');result['status']='PRIVATE_LEXICAL_COMPATIBILITY_GRAPH'
            shutil.rmtree(compat)
            for rel,b in patches.items():copy_bytes(member(compat,rel),b)
        elif issues:
            result.update(status='PRIVATE_GRAPH_ONLY_LEXICAL_BLOCKED',reason='Original lexical records fail schema checks; no correction inferred')
        else:
            q=qualify(out);must(q['valid'] and q['namespace_id']==ns and q['graph_sha256']==result['graph_sha256'] and q['reference_coverage_match'],'Qualification mismatch');result['status']='QUALIFIED_ACTIVE_GRAPH'
        gaps={sid for sid,val in actual.items() if val[0]=='assertion'}-{x[1] for x in aa}
        hist,hpins,herrors=history_audit(w,read(member(out,'canon/state.index.json')),config['graph'],ns,gaps,graph_validator)
        result.update(assertions=len(aa),framework_version=core['framework_version'],historical_source_pins=hpins,historical_audit_errors=herrors,missing_registry_assertions=len(gaps),original_canonical_lexical_qualified=result['status']=='QUALIFIED_ACTIVE_GRAPH',core_graph_registry_crosswalk_qualified=True)
    except ERRORS as e:
        result.update(status='BLOCKED_ACTIVE_GRAPH',reason=str(e).replace(str(locals_root),'[locals]').replace(str(stage),'[stage]'),assertions=0,original_canonical_lexical_qualified=False);aa=[];hist=[]
        for p in (out,compat):
            if p.exists():shutil.rmtree(p)
    result['alias_review_counts']=dict(collections.Counter(x['status'] for x in reviews));result['lexical_schema_issue_counts']=dict(collections.Counter(x['kind']+': '+x['message'] for x in issues));return result,aa,reviews,hist,issues

def write_index(db,dbout,results,index,reviews,history,issues):
    must(not dbout.exists(),'Output already exists')
    with closing(sqlite3.connect(dbout)) as out:
        db.backup(out);out.execute('PRAGMA foreign_keys=ON')
        with out:
            out.execute('CREATE TABLE v52161_active_graph(slug TEXT PRIMARY KEY,namespace_id TEXT UNIQUE NOT NULL,status TEXT NOT NULL,report_json TEXT NOT NULL,FOREIGN KEY(slug) REFERENCES workspace(slug))')
            out.execute('CREATE TABLE v52161_active_assertion(namespace_id TEXT NOT NULL,semantic_id TEXT NOT NULL,slug TEXT NOT NULL,json_pointer TEXT NOT NULL,PRIMARY KEY(namespace_id,semantic_id),FOREIGN KEY(slug) REFERENCES v52161_active_graph(slug),FOREIGN KEY(namespace_id,semantic_id) REFERENCES identity(namespace_id,semantic_id))')
            out.execute('CREATE TABLE v52161_alias_review(slug TEXT NOT NULL,path TEXT NOT NULL,line INTEGER NOT NULL,status TEXT NOT NULL,record_json TEXT NOT NULL,PRIMARY KEY(slug,path,line),FOREIGN KEY(slug) REFERENCES workspace(slug))')
            out.execute('CREATE TABLE v52161_lexical_issue(issue_id INTEGER PRIMARY KEY,slug TEXT NOT NULL,path TEXT NOT NULL,line INTEGER,kind TEXT NOT NULL,record_json TEXT NOT NULL,FOREIGN KEY(slug) REFERENCES workspace(slug))')
            out.execute('CREATE TABLE v52161_ka_history(namespace_id TEXT NOT NULL,semantic_id TEXT NOT NULL,status TEXT NOT NULL,record_json TEXT NOT NULL,PRIMARY KEY(namespace_id,semantic_id),FOREIGN KEY(namespace_id,semantic_id) REFERENCES identity(namespace_id,semantic_id))')
            j=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=True)
            out.executemany('INSERT INTO v52161_active_graph VALUES(?,?,?,?)',[(r['slug'],r['namespace_id'],r['status'],j(r)) for r in results]);out.executemany('INSERT INTO v52161_active_assertion VALUES(?,?,?,?)',index);out.executemany('INSERT INTO v52161_alias_review VALUES(?,?,?,?,?)',[(r['slug'],r['path'],r['line'],r['status'],j(r)) for r in reviews]);out.executemany('INSERT INTO v52161_lexical_issue VALUES(?,?,?,?,?,?)',[(i+1,r['slug'],r['path'],r['line'],r['kind'],j(r)) for i,r in enumerate(issues)]);out.executemany('INSERT INTO v52161_ka_history VALUES(?,?,?,?)',[(r['namespace_id'],r['semantic_id'],r['status'],j(r)) for r in history])
        must(out.execute('PRAGMA integrity_check').fetchone()==('ok',) and not out.execute('PRAGMA foreign_key_check').fetchone(),'Output integrity failure')

def run(private,locals_root,kit,framework):
    private,locals_root,kit,framework=map(guard,(private,locals_root,kit,framework));must(all(private!=p and private not in p.parents and p not in private.parents for p in (locals_root,kit,framework,kit.parent/'Kristal-Manager',kit.parent/'kristal-public')),'Private directory overlaps source');base=member(private,BASE)
    def verify_base():
        must(digest(base/'report.json')==REPORT_SHA,'Baseline report drift');r=check_generation(base);must(r['database_sha256']==DB_SHA and r['status']==op.STATUS,'Baseline mismatch');return r
    prior=verify_base();prior_base,prior_report=op.baseline(private);anc=op.verify_generations(private,read(op.PINFILE));must([g.name for g,r in anc]+[prior_base.name]==prior['required_generations'],'Ancestor mismatch')
    q=op.load(kit/'scripts/qualify_framework_v11.py','v52161_qualification');q.verify_pin(framework);a=op.load(kit/'tools/operational_native_v5216.py','v52161_pending');schemas=member(framework,'schemas/v11');lex=Draft202012Validator(read(member(schemas,'kristal-wikidata-lexical-record.schema.json')));gv=Draft202012Validator(read(member(schemas,'kristal-semantic-graph.schema.json')));legacy=read(PINFILE)
    official,_,_=q._load_framework(framework);import sys;sys.path.insert(0,str(kit/'tools'));import kristal_v11_core as kc
    layer_validators={'wikidata':lex,'external':Draft202012Validator(read(member(schemas,'kristal-external-lexical-record.schema.json'))),'curated':Draft202012Validator(read(member(schemas,'kristal-curated-dictionary.schema.json')))}
    results=[];index=[];reviews=[];history=[];issues=[]
    with tempfile.TemporaryDirectory(prefix='v52161-stage-',dir=private) as td:
        stage=Path(td);dbout=stage/'active.sqlite'
        with closing(sqlite3.connect(uri(base/'active.sqlite'),uri=True)) as db:
            must(db.execute('PRAGMA integrity_check').fetchone()==('ok',) and not db.execute('PRAGMA foreign_key_check').fetchone(),'Baseline integrity failure');rows=db.execute('SELECT slug,local_directory,namespace_id,profile_sha256,state_sha256,projection_sha256 FROM workspace WHERE active=1 ORDER BY slug').fetchall();must(len(rows)==77,'Active scope mismatch')
            for row in rows:
                r,aa,rr,hh,ii=qualify_one(db,locals_root,row,stage,lambda p:q.qualify(p,framework),a.check_pending,legacy,lex,gv,lambda p,c:qualify_core(p,c,kc,official),layer_validators);results.append(r);index+=aa;reviews+=rr;history+=hh;issues+=ii;print('V5.21.6.1',row[0],r['status'],r['assertions'],r['alias_review_counts'],flush=True)
            write_index(db,dbout,results,index,reviews,history,issues)
        for r in results:
            if not r.get('source_pins'):continue
            w=member(locals_root,next(x[1] for x in rows if x[0]==r['slug']));a.check_pending(w,member);must(not member(w,'.kristal/v11/transactions/writer.lock').exists(),'Active writer lock')
            for rel,h in {**r['source_pins'],**r.get('historical_source_pins',{})}.items():must(digest(member(w,rel))==h,'Live source drift before publication')
        must(verify_base()==prior and op.baseline(private)==(prior_base,prior_report) and op.verify_generations(private,read(op.PINFILE))==anc,'Generation drift');dest=member(private,'SEMANTIC_V52161_'+sha(bytes_json([DB_SHA,results,reviews,history,issues]))[:16]);summary={'format':'koa.kristal-lexical-compatibility/0.1','status':STATUS,'database':str(dest/'active.sqlite'),'database_sha256':digest(dbout),'source_database_sha256':DB_SHA,'source_report_sha256':REPORT_SHA,'prior_generation_name':BASE,'required_generations':prior['required_generations']+[BASE],'active_counts':prior['active_counts'],'active_graph_status_counts':dict(collections.Counter(r['status'] for r in results)),'assertions_by_graph_status':{s:sum(r['assertions'] for r in results if r['status']==s) for s in sorted({r['status'] for r in results})},'active_graphs':results,'alias_review_counts':dict(collections.Counter(r['status'] for r in reviews)),'lexical_schema_issue_counts':dict(collections.Counter(x['kind']+': '+x['message'] for x in issues)),'lexical_schema_issue_count':len(issues),'historical_ka_counts':dict(collections.Counter(r['status'] for r in history)),'historical_ka_count':len(history),'historical_ka_review_sha256':sha(bytes_json(history)),'readiness_counts_inherited':prior['readiness_counts'],'policy':{'canonical_modified':False,'public_modified':False,'network_used':False,'profiles_activated':0,'production_reader_integrated':False,'editorial_approval_granted':False,'new_v11_candidates':0,'canonical_alias_repair_implemented':False,'private_empty_alias_means_not_recorded':True,'compatibility_graph_requires_private_review':True,'historical_assertions_restored':0}}
        write(stage/'historical-ka-review.json',history);write(stage/'alias-review.json',reviews);write(stage/'lexical-issues.json',issues);write(stage/'report.json',summary);write(stage/'manifest.sha256.json',inventory(stage))
        if dest.exists():prev=check_generation(dest);must(prev==summary,'Existing generation differs');return prev
        pub=stage/'publish';pub.mkdir()
        for p in list(stage.iterdir()):
            if p!=pub:os.replace(p,pub/p.name)
        os.rename(pub,dest);return summary

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for x in ('private-dir','locals','kit','framework'):p.add_argument('--'+x,type=Path,required=True)
    p.add_argument('--apply',action='store_true');a=p.parse_args();must(a.apply,'--apply required (private output only)');r=run(a.private_dir,a.locals,a.kit,a.framework);print(json.dumps(r,ensure_ascii=True,indent=2));print('V5.21.6.1 ONE-SHOT:',r['status'])
if __name__=='__main__':main()
