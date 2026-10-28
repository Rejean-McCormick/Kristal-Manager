from __future__ import annotations
import copy,hashlib,json,math
from pathlib import Path
LOGICAL='kristal.logical/jcs-sha256-v1';STATE='kristal.state-commitment/jcs-sha256-v1';STANDARD='9.0.0-draft.1'
def _utf16(s):
 b=s.encode('utf-16-be','surrogatepass');return tuple(int.from_bytes(b[i:i+2],'big') for i in range(0,len(b),2))
def _num(n):
 if isinstance(n,int):return str(n)
 if not math.isfinite(n):raise ValueError('nonfinite')
 if n==0:return '0'
 s=repr(float(n)).lower();
 if s.endswith('.0') and 'e' not in s:s=s[:-2]
 if 'e'in s:
  m,e=s.split('e');sg='';
  if e[:1] in '+-':sg,e=e[0],e[1:]
  e=e.lstrip('0') or '0';s=f'{m}e{sg}{e}'
 return s
def jcs(v):
 if v is None:return 'null'
 if v is True:return 'true'
 if v is False:return 'false'
 if isinstance(v,(int,float)) and not isinstance(v,bool):return _num(v)
 if isinstance(v,str):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
 if isinstance(v,list):return '['+','.join(jcs(x) for x in v)+']'
 if isinstance(v,dict):return '{'+','.join(json.dumps(k,ensure_ascii=False)+':'+jcs(v[k]) for k in sorted(v,key=_utf16))+'}'
 raise TypeError(type(v))
def shab(b):return 'sha256:'+hashlib.sha256(b).hexdigest()
def jsha(v):return shab(jcs(v).encode())
def nref(r):
 o={'artifact_id':r['artifact_id'],'logical_commitment':copy.deepcopy(r['logical_commitment'])}
 if r.get('logical_contract'):o['logical_contract']=copy.deepcopy(r['logical_contract'])
 return o
def arefs(rs):return sorted([nref(r) for r in rs],key=lambda r:(r['artifact_id'],r['logical_commitment']['digest']))
def acomp(a):
 c=a['logical_contract'];p={'payload':copy.deepcopy(a['payload'])}
 if 'scope'in a:p['scope']=copy.deepcopy(a['scope'])
 if 'extensions'in a:p['extensions']=copy.deepcopy(a['extensions'])
 if a.get('dependencies'):p['dependencies']=arefs(a['dependencies'])
 dom='KRISTAL\x00LOGICAL-COMMITMENT\x00'+LOGICAL+'\x00'+c['id']+'\x00'+c['version']+'\x00';return {'profile':LOGICAL,'digest':shab(dom.encode()+jcs(p).encode())}
def scomp(s):
 p={'members':arefs(s.get('members',[])),'references':[]};
 if 'scope'in s:p['scope']=copy.deepcopy(s['scope'])
 dom='KRISTAL\x00STATE-COMMITMENT\x00'+STATE+'\x00';return {'profile':STATE,'digest':shab(dom.encode()+jcs(p).encode())}
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def blob(root,rel,media='application/json'):
 p=root/rel;return {'media_type':media,'digest':shab(p.read_bytes()),'size':p.stat().st_size,'locator':rel}
def build(root:Path,catalog:dict,state:dict):
 v=root/'.kristal/v9';v.mkdir(parents=True,exist_ok=True);auth='urn:kristal:authority:registry-main'
 ca={'schema_version':'9.0','artifact_type':'kristal_logical_artifact','artifact_id':'urn:kristal:registry:catalog','logical_contract':{'id':'kristal-registry.catalog','version':'1.1'},'payload':{'catalog_path':'knowledge-base/registry/kristal-registry.catalog.json','catalog_logical_digest':jsha(catalog),'entry_count':len(catalog.get('entries') or []),'authority':'inventory_and_registry_relations_only'},'scope':{'domain':'kristal-registry'},'authority_ref':auth,'logical_commitment':{'profile':LOGICAL,'digest':'sha256:'+'0'*64}};ca['logical_commitment']=acomp(ca);save(v/'canonical.logical-artifact.json',ca)
 pa={'schema_version':'9.0','artifact_type':'kristal_logical_artifact','artifact_id':'urn:kristal:registry:portable-v6','logical_contract':{'id':'kristal.v6-state-reference','version':'1.0'},'payload':{'portable_contract':'kristal_state/6.0','path':'knowledge-base/projections/kristal/kristal-registry.kristal-state.json','state_id':state.get('state_id'),'content_hash':state.get('content_hash')},'scope':{'domain':'kristal-registry'},'authority_ref':auth,'dependencies':[{'artifact_id':ca['artifact_id'],'logical_contract':ca['logical_contract'],'logical_commitment':ca['logical_commitment']}],'logical_commitment':{'profile':LOGICAL,'digest':'sha256:'+'0'*64}};pa['logical_commitment']=acomp(pa);save(v/'portable-v6.logical-artifact.json',pa)
 ref=lambda a:{'artifact_id':a['artifact_id'],'logical_contract':a['logical_contract'],'logical_commitment':a['logical_commitment'],'authority_ref':auth}
 ss={'schema_version':'9.0','artifact_type':'kristal_state_snapshot','state_ref':'urn:kristal:state:registry-main','logical_commitment':{'profile':STATE,'digest':'sha256:'+'0'*64},'members':[ref(ca)],'references':[],'parents':[],'scope':{'domain':'kristal-registry'},'authority_ref':auth};ss['logical_commitment']=scomp(ss);save(v/'state-snapshot.json',ss)
 for fn,src,art,profile in [('materialization.canonical.json','knowledge-base/registry/kristal-registry.catalog.json',ca,'kristal.materialization/inline-json/1'),('materialization.portable-v6.json','knowledge-base/projections/kristal/kristal-registry.kristal-state.json',pa,'kristal.materialization/kristal-state-v6/1')]:
  m={'schema_version':'9.0','artifact_type':'kristal_materialization_manifest','source':ref(art),'profile':profile,'segments':[{'segment_key':'all','blob':blob(root,src)}],'reconstructability':{'lossless':True,'profile':art['logical_contract']['id']+'/'+art['logical_contract']['version']}};save(v/fn,m)
 der={'schema_version':'9.0','artifact_type':'kristal_derivation','transform':{'id':'kristal-registry.project-v6','version':'0.4.0','digest':shab((Path(__file__).resolve().parent/'registry-builder.py').read_bytes())},'inputs':[ref(ca)],'parameters':{'projection':'registry.* assertions'},'toolchain':{'name':'Kristal-Registry','version':'0.4.0'},'outputs':[ref(pa)],'determinism':{'claimed':True,'profile':'kristal.deterministic-build/1'}};save(v/'derivation.portable-v6.json',der)
 cap={'schema_version':'9.0','artifact_type':'kristal_v9_capabilities','compatibility':{'reads':['kristal_state/6.0','kristall/7.0','kristall/8.0','kristal.state/9.0'],'portable_state':'kristal_state/6.0','semantic_baseline':'kristall/7.0','query_baseline':'kristall/8.0'},'capabilities':{'state_architecture':{'logical_artifacts':True,'immutable_snapshots':True,'logical_commitments':True,'external_pinned_references':True},'materialization':{'profiles':['kristal.materialization/inline-json/1','kristal.materialization/kristal-state-v6/1'],'multiple_representations':True,'segmentation':False,'factorization':False},'lifecycle':{'build_publish_activate':True,'atomic_activation':False,'rollback':False}}};save(v/'capabilities.json',cap)
 return {'canonical_commitment':ca['logical_commitment']['digest'],'state_commitment':ss['logical_commitment']['digest']}
