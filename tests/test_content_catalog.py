from pathlib import Path
import hashlib,json,sqlite3,os,shutil
import pytest
from kristal_manager.content_catalog import build_catalog,summaries,search_catalog,write_overview
from kristal_manager.core import ManagerError
from kristal_manager.cli import main

def put(root,rel,data):
 p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data),encoding='utf-8');return p

def fixture(root,name='Earth'):
 p=root/name;p.mkdir(parents=True)
 put(p,'kristal.workspace.json',{'format':'kristal.local-workspace/3.2.0','title':name,'state_ref':'urn:'+name,'native_model':{'kind':'planet_graph'},'subject':{'domain':'astronomy'}})
 names=['registry','graph','crosswalk','dictionaries/catalog','structured-model','source-ledger'];put(p,'canon/state.index.json',{'canonical_artifacts':[{'path':'canon/'+n+'.json','logical_contract':{'id':n}} for n in names]})
 put(p,'.kristal/v11/authoring.json',{'format':'kristal.authoring-v11-profile/1.0','registry':'canon/registry.json','graph':'canon/graph.json','crosswalk':'canon/crosswalk.json','catalog':'canon/dictionaries/catalog.json'})
 put(p,'canon/registry.json',{'namespace_id':'urn:'+name})
 put(p,'canon/graph.json',{'artifact_type':'kristal_semantic_graph','namespace_id':'urn:'+name,'entities':['KQ1','KQ2','KQ3'],'properties':['KP1','KP2'],'sources':['KS1'],'assertions':[{'id':'KA1','subject':'KQ1','predicate':'KP1','object':{'kind':'entity','id':'KQ3'},'sources':['KS1']},{'id':'KA2','subject':'KQ3','predicate':'KP2','object':{'kind':'literal','datatype':'string','value':'+123'},'sources':['KS1']}]})
 put(p,'canon/structured-model.json',{'node_shapes':{'KQ3':{'fields':[{'assertion_id':'KA2'}]}},'source_ledger':'canon/source-ledger.json'})
 put(p,'canon/source-ledger.json',{'records':{'KS1':{'record':{'wikidata_subject':'Q2','wikidata_property':'P1','full_source_claim':{'rank':'normal'}}}}})
 put(p,'canon/crosswalk.json',{'mappings':[{'status':'accepted','relation':'exactMatch','external_ref':{'id':e},'local_ref':{'id':k}} for e,k in [('Q2','KQ1'),('Q20','KQ2'),('P1','KP1')]]+ [{'status':'candidate','relation':'relatedMatch'}]})
 layer=put(p,'canon/dictionaries/fr.json',{'entries':[{'semantic_id':'KQ1','preferred_term':'Terre'},{'semantic_id':'KQ2','preferred_term':'Q20'},{'semantic_id':'KP1','preferred_term':'masse'}]})
 put(p,'canon/dictionaries/catalog.json',{'languages':[{'tag':'fr','layers':[{'kind':'curated','path':'fr.json','priority':1,'sha256':hashlib.sha256(layer.read_bytes()).hexdigest()}]}]})
 return p

def test_active_graph_and_descriptive_statistics(tmp_path):
 p=fixture(tmp_path/'sources');db=tmp_path/'catalog.db';result=build_catalog([p.parent],db)
 r=summaries(db)['records'][0];assert result['updated']==1 and r['mode']=='active_v11';m=r['metrics'];assert m['assertions']==2 and m['main_assertions']==1 and m['structured_components']==1;assert m['wikidata_source_claims']==1 and m['rank_counts']=={'normal':1};assert [{k:v for k,v in x.items() if k!='display_source'} for x in r['top_subjects']]==[{'id':'KQ1','label':'Terre','external_id':'Q2','assertions':1}];assert m['entities_with_descriptive_labels']==1
 if os.name!='nt':assert db.stat().st_mode&0o077==0

def test_exact_qid_not_substring_and_namespace_scoping(tmp_path):
 p=fixture(tmp_path/'sources','A');fixture(p.parent,'B');db=tmp_path/'c.db';build_catalog([p.parent],db)
 r=search_catalog(db,'Q2');assert len(r)==2 and {x['external_id'] for x in r}=={'Q2'};assert {x['namespace_id'] for x in r}=={'urn:A','urn:B'};assert len(search_catalog(db,'terre'))==2

def test_incremental_detects_changed_bytes_with_same_stat(tmp_path):
 p=fixture(tmp_path/'sources');db=tmp_path/'c.db';build_catalog([p],db);assert build_catalog([p],db)['cached']==1
 f=p/'canon/graph.json';st=f.stat();blob=f.read_bytes();changed=blob.replace(b'+123',b'+124');assert len(changed)==len(blob);f.write_bytes(changed);os.utime(f,ns=(st.st_atime_ns,st.st_mtime_ns))
 assert build_catalog([p],db)['updated']==1
 with sqlite3.connect(db) as con:assert '+124' in con.execute("SELECT object FROM assertions WHERE id='KA2'").fetchone()[0]

def test_missing_or_unregistered_graph_is_unknown_not_zero(tmp_path):
 p=fixture(tmp_path/'sources');(p/'canon/graph.json').unlink();db=tmp_path/'c.db';build_catalog([p],db);r=summaries(db)['records'][0];assert r['content_status']=='unsupported' and r['metrics']['assertions'] is None

def test_invalid_dictionary_never_supplies_labels(tmp_path):
 p=fixture(tmp_path/'sources');put(p,'canon/dictionaries/fr.json',{'entries':[{'semantic_id':'KQ1','preferred_term':'wrong'}]});db=tmp_path/'c.db';build_catalog([p],db);r=summaries(db)['records'][0];assert r['content_status']=='partial' and r['top_subjects'][0]['label'] is None

def test_source_files_unchanged_and_project_code_not_executed(tmp_path):
 p=fixture(tmp_path/'sources');f=p/'tools/kristal.py';f.parent.mkdir();f.write_text("raise RuntimeError('must not execute')")
 before={str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()};db=tmp_path/'c.db';build_catalog([p],db)
 assert before=={str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}
 with pytest.raises(ManagerError):build_catalog([p],p/'canon/forbidden.db')
 with pytest.raises(ManagerError):write_overview(db,p/'forbidden.html')

def test_symlink_graph_blocked(tmp_path):
 p=fixture(tmp_path/'sources');f=p/'canon/graph.json';outside=tmp_path/'outside';outside.write_bytes(f.read_bytes());f.unlink()
 try:f.symlink_to(outside)
 except OSError:pytest.skip('symlinks unavailable')
 db=tmp_path/'c.db';build_catalog([p],db);assert summaries(db)['records'][0]['content_status']=='unsupported'

def test_legacy_native_v6_and_unsupported_adapter(tmp_path):
 p=tmp_path/'sources/Legacy';p.mkdir(parents=True);put(p,'kristal.workspace.json',{'title':'Legacy','state_ref':'urn:legacy'});put(p,'canon/state.index.json',{'canonical_artifacts':[{'path':'canon/state.json'}]});put(p,'canon/state.json',{'artifact_type':'kristal_state','assertions':[{'assertion_id':'a1','statement':{'subject':{'kind':'item','id':'s1'},'predicate':'rel','object':{'kind':'item','id':'s2'}},'evidence_refs':['src']}]})
 db=tmp_path/'c.db';build_catalog([p],db);r=summaries(db)['records'][0];assert r['mode']=='registered_legacy_v6' and r['metrics']['assertions']==1
 put(p,'canon/state.json',{'artifact_type':'unknown','assertions':['not a graph']});build_catalog([p],db);assert summaries(db)['records'][0]['metrics']['assertions'] is None

def test_snapshot_removes_only_stale_catalog_rows(tmp_path):
 p=fixture(tmp_path/'sources');db=tmp_path/'c.db';build_catalog([p.parent],db);shutil.rmtree(p);build_catalog([p.parent],db);assert summaries(db)['record_count']==0

def test_html_inert_data_and_explicit_overwrite(tmp_path):
 p=fixture(tmp_path/'sources');ws=json.loads((p/'kristal.workspace.json').read_text());ws['title']='</script><script>alert(1)</script>';put(p,'kristal.workspace.json',ws);db=tmp_path/'c.db';build_catalog([tmp_path/'sources'],db);out=tmp_path/'overview.html';write_overview(db,out);text=out.read_text();assert '</script><script>alert(1)' not in text and '\\u003c' in text and 'textContent' in text
 with pytest.raises(ManagerError):write_overview(db,out)
 write_overview(db,out,overwrite=True)

def test_cli_catalog_and_query(tmp_path,capsys):
 p=fixture(tmp_path/'sources');db=tmp_path/'c.db';page=tmp_path/'overview.html';assert main(['catalog',str(p.parent),'--db',str(db),'--overview',str(page)])==0;capsys.readouterr();assert main(['catalog-query','Terre','--db',str(db)])==0;assert 'Terre' in capsys.readouterr().out

def test_other_database_not_overwritten(tmp_path):
 p=fixture(tmp_path/'sources');db=tmp_path/'other';db.write_bytes(b'not a catalog');before=db.read_bytes()
 with pytest.raises(ManagerError):build_catalog([p],db)
 assert db.read_bytes()==before


def test_concept_assertions_expand_values_without_merging_workspaces(tmp_path):
 from kristal_manager.content_catalog import show_concept
 p=fixture(tmp_path/'sources','A');fixture(p.parent,'B');db=tmp_path/'c.db';build_catalog([p.parent],db)
 records=show_concept(db,'Q2');assert len(records)==2
 assert all(r['assertions'][0]['structured_fields'][0]['object']['value']=='+123' for r in records)
 assert len(show_concept(db,'Q2',catalog_id=records[0]['catalog_id']))==1

def test_bad_model_does_not_block_other_workspaces(tmp_path):
 p=fixture(tmp_path/'sources','A');fixture(p.parent,'B');put(p,'canon/structured-model.json',{'node_shapes':{'broken':None}});db=tmp_path/'c.db';build_catalog([p.parent],db)
 records=summaries(db)['records'];assert {r['content_status'] for r in records}=={'error','observed'}
 assert next(r for r in records if r['content_status']=='error')['metrics']['assertions'] is None


def test_catalog_commit_is_atomic_on_failure(tmp_path,monkeypatch):
 import kristal_manager.content_catalog as cc
 p=fixture(tmp_path/'sources');db=tmp_path/'c.db';cc.build_catalog([p],db);before=db.read_bytes()
 def fail(*args,**kwargs):raise RuntimeError('interrupted scan')
 monkeypatch.setattr(cc,'inspect_content',fail)
 with pytest.raises(RuntimeError):cc.build_catalog([p],db,force=True)
 assert db.read_bytes()==before
 assert not list(tmp_path.glob('*.building'))


def test_unreadable_discovery_retains_catalog(tmp_path,monkeypatch):
 import kristal_manager.content_catalog as cc
 p=fixture(tmp_path/'sources');db=tmp_path/'c.db';cc.build_catalog([p],db);before=db.read_bytes()
 def denied(*args,**kwargs):
  kwargs['onerror'](PermissionError('directory unreadable'))
  yield None
 monkeypatch.setattr(cc.os,'walk',denied)
 with pytest.raises(ManagerError,match='Cannot complete source discovery'):cc.build_catalog([p],db)
 assert db.read_bytes()==before


def test_legacy_display_key_is_not_a_curated_label_or_identity_merge(tmp_path):
 p=fixture(tmp_path/'sources');put(p,'.kristal/v11/identity-migration-map.json',{'namespace_id':'urn:Earth','by_kind':{'P':{'native.amount':'KP2'},'Q':{'native.other':'KQ2'}}});db=tmp_path/'c.db';build_catalog([p],db)
 r=summaries(db)['records'][0];assert r['metrics']['entities_with_descriptive_labels']==1
 match=search_catalog(db,'native.other');assert len(match)==1 and match[0]['id']=='KQ2'
 put(p,'.kristal/v11/identity-migration-map.json',{'namespace_id':'wrong','by_kind':{'Q':{'spoof':'KQ2'}}});build_catalog([p],db);assert search_catalog(db,'spoof')==[]
