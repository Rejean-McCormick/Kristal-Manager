"""V5.21.4 private structured representation; no V11 graph or activation changes."""
from __future__ import annotations
import argparse,collections,importlib.util,json,os,sqlite3,tempfile
from contextlib import closing
from pathlib import Path
from .native_migration_v521 import must,guard,member,sha,digest,read,bytes_json,write,uri
from . import native_extension_v5211 as e
BASE='SEMANTIC_V5213_7d54755944d67053'
EXPECTED_DB='50e7f8663d9a99c9dd986f9fd6c5099a507e3337a189cc2ede29506c43222619'
EXPECTED_REPORT='0bfa45576971efbb748710ceece98407e047ac3524c489733d084326bf001af5'
PINFILE=Path(__file__).with_name('structured_v5214_pins.json')
STATUS='STRUCTURED_REPRESENTATION_DRAFT_VALIDATED_MIGRATION_PENDING'
def load_kit(kit):
    spec=importlib.util.spec_from_file_location('kristal_structured_kit_v5214',member(kit,'tools/structured_native_v5214.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def run(locals_root,private,kit,framework):
    locals_root,private,kit,framework=map(guard,(locals_root,private,kit,framework));must(all(private!=p and private not in p.parents and p not in private.parents for p in (locals_root,kit,framework,locals_root.parent/'kristal-public',locals_root.parent/'Kristal-Manager')),'Private path overlaps repository')
    src=member(private,BASE);must(digest(src/'report.json')==EXPECTED_REPORT,'Prior report digest mismatch');report=e.check_generation(src);must(report['database_sha256']==EXPECTED_DB and report['status']=='SPECIALIZED_CANDIDATES_REHEARSED_EDITORIAL_PENDING','Wrong prior generation')
    pins=read(PINFILE);pending={a['slug']:a for a in report['audit'] if a['status']!='CANDIDATE_TECHNICALLY_QUALIFIED'};must(set(pins)==set(pending) and len(pins)==13,'Pending scope mismatch')
    builder=load_kit(kit);f=builder.load_framework(framework)
    with closing(sqlite3.connect(uri(src/'active.sqlite'),uri=True)) as db:
        must(db.execute('PRAGMA integrity_check').fetchone()==('ok',) and not db.execute('PRAGMA foreign_key_check').fetchone(),'Invalid prior database')
        rows={s:(d,h) for s,d,h in db.execute('SELECT slug,local_directory,state_sha256 FROM workspace WHERE active=0')};must(len(rows)==50,'Inactive scope changed')
    def preflight():
        for slug,pin in pins.items():
            must(rows[slug]==(pin['directory'],pin['files']['canon/state.index.json']),'Workspace scope mismatch: '+slug);w=member(locals_root,pin['directory']);must(not member(w,'.kristal/v11/authoring.json').exists(),'Unexpected active profile: '+slug)
            must(pending[slug]['assertions_inspected']==pin['assertions'] and all(pin['files'].get(x['path'])==x['sha256'] for x in pending[slug]['files']),'Audit pin mismatch: '+slug)
            for rel,h in pin['files'].items():must(digest(member(w,rel))==h,'Native drift: '+slug+'/'+rel)
    preflight()
    with tempfile.TemporaryDirectory(prefix='v5214-stage-',dir=private) as td:
        stage=Path(td);dbout=stage/'active.sqlite';summaries=[];forms=collections.Counter();qforms=collections.Counter()
        with closing(sqlite3.connect(uri(src/'active.sqlite'),uri=True)) as inp,closing(sqlite3.connect(dbout)) as db:
            inp.backup(db);db.execute('PRAGMA foreign_keys=ON')
            with db:
                db.execute('CREATE TABLE v5214_packet(slug TEXT PRIMARY KEY, packet_sha256 TEXT NOT NULL, report_json TEXT NOT NULL)')
                db.execute('CREATE TABLE v5214_source_file(slug TEXT NOT NULL, path TEXT NOT NULL, sha256 TEXT NOT NULL, PRIMARY KEY(slug,path), FOREIGN KEY(slug) REFERENCES v5214_packet(slug))')
                db.execute('CREATE TABLE v5214_occurrence(occurrence_id TEXT PRIMARY KEY, slug TEXT NOT NULL, source_path TEXT NOT NULL, json_pointer TEXT NOT NULL, native_assertion_id TEXT NOT NULL, native_status TEXT NOT NULL, subject_ref TEXT NOT NULL, predicate_ref TEXT NOT NULL, native_kind TEXT NOT NULL, value_shape TEXT NOT NULL, representation_form TEXT NOT NULL, anomaly TEXT, UNIQUE(slug,source_path,json_pointer), FOREIGN KEY(slug,source_path) REFERENCES v5214_source_file(slug,path))')
                db.execute('CREATE TABLE v5214_qualifier(occurrence_id TEXT NOT NULL, ordinal INTEGER NOT NULL, json_pointer TEXT NOT NULL, predicate_ref TEXT NOT NULL, native_kind TEXT NOT NULL, value_shape TEXT NOT NULL, representation_form TEXT NOT NULL, PRIMARY KEY(occurrence_id,ordinal), FOREIGN KEY(occurrence_id) REFERENCES v5214_occurrence(occurrence_id))')
                db.execute('CREATE INDEX v5214_occurrence_subject ON v5214_occurrence(slug,subject_ref)');db.execute('CREATE INDEX v5214_occurrence_predicate ON v5214_occurrence(slug,predicate_ref)')
                for slug,pin in sorted(pins.items()):
                    print('V5.21.4 private representation:',slug,flush=True);root=stage/'structured'/slug;packet=builder.build(member(locals_root,pin['directory']),slug,pin,root,f);rr=packet['records'];k=collections.Counter(r['object']['form'] for r in rr);qk=collections.Counter(q['object']['form'] for r in rr for q in r['qualifiers']);forms.update(k);qforms.update(qk)
                    row={'slug':slug,'status':'STRUCTURED_PACKET_VALIDATED_NOT_V11' if pin['state'] else 'REGISTERED_NATIVE_DISCOVERY_ONLY','packet_sha256':digest(root/'packet.json'),'source_path':pin['state'],'files_preserved':len(pin['files']),'registered_artifacts':len(packet['registered_artifacts']),'registered_non_json':sum(not x['path'].endswith('.json') for x in packet['registered_artifacts']),'occurrences':len(rr),'qualifiers':sum(qk.values()),'object_forms':dict(k),'qualifier_forms':dict(qk),'anomalies':sum(r['object']['anomaly'] is not None for r in rr),'native_status_counts':dict(collections.Counter(r['native_status'] for r in rr))}
                    summaries.append(row);db.execute('INSERT INTO v5214_packet VALUES (?,?,?)',(slug,row['packet_sha256'],json.dumps(row,sort_keys=True)));db.executemany('INSERT INTO v5214_source_file VALUES (?,?,?)',[(slug,p,h) for p,h in packet['files'].items()]);db.executemany('INSERT INTO v5214_occurrence VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',[(r['occurrence_id'],slug,pin['state'],r['pointer'],r['native_assertion_id'],r['native_status'],r['subject_ref'],r['predicate_ref'],r['object']['native_kind'],r['object']['shape'],r['object']['form'],r['object']['anomaly']) for r in rr]);db.executemany('INSERT INTO v5214_qualifier VALUES (?,?,?,?,?,?,?)',[(r['occurrence_id'],i,q['object']['pointer'],q['predicate_ref'],q['object']['native_kind'],q['object']['shape'],q['object']['form']) for r in rr for i,q in enumerate(r['qualifiers'])])
            must(db.execute('PRAGMA integrity_check').fetchone()==('ok',) and not db.execute('PRAGMA foreign_key_check').fetchone(),'Invalid output database');counts={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('identity','lexical','candidate_wikidata')};must(counts==report['active_counts'],'Active counts changed')
        preflight();must(e.check_generation(src)==report and digest(src/'report.json')==EXPECTED_REPORT,'Baseline changed')
        dest=member(private,'SEMANTIC_V5214_'+sha(bytes_json([EXPECTED_DB,summaries]))[:16]);result={'format':'koa.kristal-structured-representation/0.1','status':STATUS,'database':str(dest/'active.sqlite'),'database_sha256':digest(dbout),'source_database_sha256':EXPECTED_DB,'source_report_sha256':EXPECTED_REPORT,'prior_generation':str(src),'active_counts':counts,'v11_candidate_count':report['cumulative_candidate_count'],'v11_candidate_counts':report['cumulative_counts'],'remaining_v11_migrations':13,'structured_packet_count':sum(x['source_path'] is not None for x in summaries),'discovery_only_count':sum(x['source_path'] is None for x in summaries),'counts':{k:sum(x[k] for x in summaries) for k in ('occurrences','qualifiers','files_preserved','registered_artifacts','registered_non_json','anomalies')},'object_forms':dict(forms),'qualifier_forms':dict(qforms),'packets':summaries,'policy':{'framework_v11_existing_contract_modified':False,'new_v11_candidates':0,'new_canonical_identities':0,'canonical_modified':False,'profiles_activated':0,'public_modified':False,'network_used':False,'registered_scripts_executed':False,'production_reader_integrated':False,'editorial_approval_granted':False}}
        write(stage/'report.json',result);write(stage/'manifest.sha256.json',e.inventory(stage))
        if dest.exists():prev=e.check_generation(dest);must(prev==result,'Existing generation differs');return prev
        pub=stage/'publish';pub.mkdir()
        for p in list(stage.iterdir()):
            if p!=pub:os.replace(p,pub/p.name)
        os.rename(pub,dest);return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for x in ('locals','private-dir','kit','framework'):p.add_argument('--'+x,type=Path,required=True)
    p.add_argument('--apply',action='store_true');a=p.parse_args();must(a.apply,'--apply required (private representation only)');r=run(a.locals,a.private_dir,a.kit,a.framework);print(json.dumps(r,ensure_ascii=True,indent=2));print('V5.21.4 ONE-SHOT:',r['status'])
if __name__=='__main__':main()
