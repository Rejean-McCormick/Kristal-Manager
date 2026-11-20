#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, json, math, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
V9=Path(__file__).resolve().parent
LOGICAL='kristal.logical/jcs-sha256-v1'
STATE='kristal.state-commitment/jcs-sha256-v1'

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def utf16key(s):
    b=s.encode('utf-16-be','surrogatepass');return tuple(int.from_bytes(b[i:i+2],'big') for i in range(0,len(b),2))
def js(s):return json.dumps(s,ensure_ascii=False,separators=(',',':'))
def num(n):
    if isinstance(n,int) and not isinstance(n,bool):return str(n)
    if not math.isfinite(n):raise ValueError('non-finite number')
    if n==0:return '0'
    x=repr(float(n)).lower()
    if x.endswith('.0') and 'e' not in x:x=x[:-2]
    if 'e' in x:
        m,e=x.split('e',1);sg=''
        if e.startswith(('+','-')):sg,e=e[0],e[1:]
        e=e.lstrip('0') or '0';x=f'{m}e{sg}{e}'
    return x
def jcs(v):
    if v is None:return 'null'
    if v is True:return 'true'
    if v is False:return 'false'
    if isinstance(v,(int,float)) and not isinstance(v,bool):return num(v)
    if isinstance(v,str):return js(v)
    if isinstance(v,list):return '['+','.join(jcs(x) for x in v)+']'
    if isinstance(v,dict):return '{'+','.join(js(k)+':'+jcs(v[k]) for k in sorted(v,key=utf16key))+'}'
    raise TypeError(type(v).__name__)
def sha(b):return 'sha256:'+hashlib.sha256(b).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def artifact_ref(r):
    return {'artifact_id':r['artifact_id'],'logical_contract':copy.deepcopy(r['logical_contract']),'logical_commitment':copy.deepcopy(r['logical_commitment'])}
def logical_commitment(a):
    p={'payload':copy.deepcopy(a['payload'])}
    if 'scope' in a:p['scope']=copy.deepcopy(a['scope'])
    if 'extensions' in a:p['extensions']=copy.deepcopy(a['extensions'])
    if a.get('dependencies'):
        ds=[artifact_ref(x) for x in a['dependencies']];ds.sort(key=lambda x:(x['artifact_id'],x['logical_commitment']['digest']));p['dependencies']=ds
    c=a['logical_contract'];dom=f'KRISTAL\0LOGICAL-COMMITMENT\0{LOGICAL}\0{c["id"]}\0{c["version"]}\0'.encode()
    return {'profile':LOGICAL,'digest':sha(dom+jcs(p).encode())}
def state_commitment(s):
    ms=[artifact_ref(x) for x in s.get('members',[])];ms.sort(key=lambda x:(x['artifact_id'],x['logical_commitment']['digest']))
    rs=[]
    for r in s.get('references',[]):
        if 'artifact_id' in r:rs.append({'kind':'artifact','value':artifact_ref(r)})
        else:rs.append({'kind':'state','value':{'state_ref':r['state_ref'],'logical_commitment':copy.deepcopy(r['logical_commitment'])}})
    rs.sort(key=jcs);p={'members':ms,'references':rs}
    if 'scope' in s:p['scope']=copy.deepcopy(s['scope'])
    dom=f'KRISTAL\0STATE-COMMITMENT\0{STATE}\0'.encode();return {'profile':STATE,'digest':sha(dom+jcs(p).encode())}
def v6_identity(d):
    t=copy.deepcopy(d)
    for k in ('state_id','content_hash','signatures'):t.pop(k,None)
    h=hashlib.sha256(jcs(t).encode()).hexdigest();return 'sha256:'+h,{'alg':'sha256','value':h}
def check_blob(desc,p,errors,label):
    p=Path(p)
    if not p.is_file():errors.append(f'{label}: missing {p}');return
    if desc.get('digest')!=file_sha(p):errors.append(f'{label}: digest mismatch')
    if desc.get('size')!=p.stat().st_size:errors.append(f'{label}: size mismatch')

def main():
    errors=[];arts={}
    for p in sorted((V9/'artifacts').glob('*.json')):
        a=load(p);arts[a['artifact_id']]=a
        if a.get('schema_version')!='9.0' or a.get('artifact_type')!='kristal_logical_artifact':errors.append(f'{p.name}: invalid v9 artifact header')
        if a.get('logical_commitment')!=logical_commitment(a):errors.append(f'{p.name}: logical commitment mismatch')
    state=load(V9/'state-snapshot.json')
    if state.get('logical_commitment')!=state_commitment(state):errors.append('state-snapshot: logical commitment mismatch')
    for r in state.get('members',[]):
        a=arts.get(r.get('artifact_id'))
        if not a or r.get('logical_commitment')!=a.get('logical_commitment'):errors.append('state-snapshot: member binding mismatch')
    canonical=load(ROOT/'knowledge-base/corpus/koa-ecosystem.kristal-state.json');sid,ch=v6_identity(canonical)
    if canonical.get('state_id')!=sid or canonical.get('content_hash')!=ch:errors.append('canonical v6 state identity mismatch')
    for p in sorted((V9/'materializations').glob('*.json')):
        m=load(p);a=arts.get((m.get('source') or {}).get('artifact_id'))
        if not a or m['source'].get('logical_commitment')!=a.get('logical_commitment'):errors.append(f'{p.name}: source binding mismatch')
        if (m.get('reconstructability') or {}).get('lossless') is not True:errors.append(f'{p.name}: not declared lossless')
        for seg in m.get('segments',[]):check_blob(seg['blob'],ROOT/seg['segment_key'],errors,p.name+':'+seg['segment_key'])
    ex=load(V9/'exchange.json')
    if ex.get('state',{}).get('logical_commitment')!=state.get('logical_commitment'):errors.append('exchange: state binding mismatch')
    check_blob(ex['state_blob'],V9/'state-snapshot.json',errors,'exchange:state_blob')
    mats={load(p)['source']['artifact_id']:p for p in (V9/'materializations').glob('*.json')}
    for x in ex.get('materializations',[]):
        p=mats.get(x['artifact_id'])
        if not p:errors.append('exchange: unknown materialization artifact')
        else:check_blob(x['manifest_blob'],p,errors,'exchange:materialization')
    for x in ex.get('derivations',[]):check_blob(x,V9/'derivation.json',errors,'exchange:derivation')
    act=load(V9/'activation.json')
    if act.get('active_state',{}).get('logical_commitment')!=state.get('logical_commitment'):errors.append('activation: state binding mismatch')
    vm=load(V9/'manifest.sha256.json');listed={x['path']:x for x in vm.get('files',[])}
    actual={p.relative_to(V9).as_posix():p for p in V9.rglob('*') if p.is_file() and p.name!='manifest.sha256.json'}
    if set(listed)!=set(actual):errors.append('v9 package manifest file set mismatch')
    for rel,p in actual.items():
        row=listed.get(rel,{})
        if row.get('sha256')!=hashlib.sha256(p.read_bytes()).hexdigest() or row.get('bytes')!=p.stat().st_size:errors.append(f'v9 package manifest mismatch: {rel}')
    out={'status':'PASS' if not errors else 'FAIL','standard_target':'9.0.0-draft.1','state_id':sid,'state_commitment':state['logical_commitment']['digest'],'logical_artifacts':len(arts),'errors':errors}
    print(json.dumps(out,ensure_ascii=False,indent=2));return 0 if not errors else 1
if __name__=='__main__':raise SystemExit(main())
