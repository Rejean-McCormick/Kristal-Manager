#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,datetime,csv,collections,os,math,copy
ROOT=Path(__file__).resolve().parents[2]
KS=ROOT/'knowledge-base/sources'
VERSION=(ROOT/'VERSION').read_text().strip()
NOW=os.environ.get('KRISTAL_BUILD_TIMESTAMP') or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
CATALOGS=[
 ('components.json','components','component'),('capabilities.json','capabilities','capability'),('needs.json','needs','need'),
 ('operating-functions.json','functions','operating_function'),('invariants.json','invariants','invariant'),('domains.json','domains','domain'),
 ('contracts.json','contracts','contract'),('artifacts.json','artifacts','artifact'),('lifecycles.json','lifecycles','lifecycle'),
 ('repositories.json','repositories','repository'),('external-references.json','items','external_reference'),('utilities.json','utilities','utility'),
 ('workflow-patterns.json','patterns','workflow_pattern'),('problem-families.json','problem_families','problem_family'),
 ('scenario-archetypes.json','scenarios','scenario_archetype'),('scenario-mosaic.json','scenarios','scenario_mosaic'),
 ('selection-categories.json','categories','doc_selection_category'),('diagnostic-observations.json','observations','diagnostic_observation')]

def read(fn,key): return json.loads((KS/fn).read_text(encoding='utf-8'))[key]

# RFC 8785 / JCS helpers used by the v6 state identity boundary.
def _utf16_key(s):
    b=s.encode('utf-16-be','surrogatepass')
    return tuple(int.from_bytes(b[i:i+2],'big') for i in range(0,len(b),2))
def _jcs_string(s): return json.dumps(s,ensure_ascii=False,separators=(',',':'))
def _jcs_number(n):
    if isinstance(n,bool): return 'true' if n else 'false'
    if isinstance(n,int): return str(n)
    if not math.isfinite(n): raise ValueError('non-finite number is not I-JSON')
    if n==0:return '0'
    x=repr(float(n)).lower()
    if x.endswith('.0') and 'e' not in x:x=x[:-2]
    if 'e' in x:
        m,e=x.split('e',1);sign=''
        if e.startswith(('+','-')):sign,e=e[0],e[1:]
        e=e.lstrip('0') or '0';x=f'{m}e{sign}{e}'
    return x
def jcs(value):
    if value is None:return 'null'
    if value is True:return 'true'
    if value is False:return 'false'
    if isinstance(value,(int,float)) and not isinstance(value,bool):return _jcs_number(value)
    if isinstance(value,str):return _jcs_string(value)
    if isinstance(value,list):return '['+','.join(jcs(x) for x in value)+']'
    if isinstance(value,dict):
        keys=sorted(value,key=_utf16_key)
        return '{'+','.join(_jcs_string(k)+':'+jcs(value[k]) for k in keys)+'}'
    raise TypeError(type(value).__name__)
def v6_state_identity(state):
    target=copy.deepcopy(state)
    for k in ('state_id','content_hash','signatures'):target.pop(k,None)
    h=hashlib.sha256(jcs(target).encode('utf-8')).hexdigest()
    return 'sha256:'+h, {'alg':'sha256','value':h}
def assertion_id(a):
 b=json.dumps(a,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode();return 'urn:koa:assertion:'+hashlib.sha256(b).hexdigest()[:24]
def sval(v):
 if isinstance(v,bool): return {'kind':'boolean','value':v}
 if isinstance(v,(int,float)): return {'kind':'number','value':v}
 return {'kind':'string','value':str(v)}
def add_assertion(arr,subject,pred,obj,status='sourced',sources=None,role='structural_record',valuations=None,coordinates=None,notes=None):
 a={'statement':{'subject':{'kind':'item','id':subject},'predicate':pred,'object':({'kind':'item','id':obj[1]} if isinstance(obj,tuple) and obj[0]=='item' else sval(obj))},'assertion_status':status if status in ['hypothesis','claimed','sourced','disputed','reviewed','validated','rejected','retracted','superseded'] else 'sourced','record_role':role,'actionability':{'mode':'not_applicable'}}
 if sources:a['evidence_refs']=sources
 if valuations:a['valuations']=valuations
 if coordinates:a['coordinates']=coordinates
 if notes:a['notes']=notes
 a['assertion_id']=assertion_id(a);arr.append(a)

def item_label(x): return x.get('label') or x.get('name') or x.get('title') or x['id']
assertions=[];by_kind={};counts={}
for fn,key,kind in CATALOGS:
 items=read(fn,key);counts[kind+'s' if not kind.endswith('y') else kind[:-1]+'ies']=len(items);by_kind[kind]=sorted(x['id'] for x in items)
 for x in items:
  st=x.get('assertion_status','sourced');src=x.get('source_refs',[]);sid=x['id']
  add_assertion(assertions,sid,'rdf:type',('item','koa:type:'+kind),st,src)
  add_assertion(assertions,sid,'rdfs:label',item_label(x),st,src)
  if x.get('description'): add_assertion(assertions,sid,'schema:description',x['description'],st,src)
  # selected scalar/set metadata
  for field in ['kind','scope','family','scenario_id','scale','urgency','evidence_status','runtime_status','runtime_evidence','loop','continuity_gap','full_name','url','discovery_status','architectural_membership','pattern','repository_role','local_path','observed_at','readme_file','readme_sha256','declared_version','current_local_observation','public_remote_status','public_remote_url','public_remote_label','local_observation_status','repository_locator_status','c0_inventory_registered','c0_inventory_scope','c0_inventory_status','c0_inventory_snapshot_date','campaign_id','verdict','reference_status','promotion_status','source_summary_sha256','default_selected']:
   if field in x and x[field] not in (None,''):
    add_assertion(assertions,sid,'koa:'+field,x[field],st,src)
  for field in ['aliases','tags','stakes','domains','failure_mechanisms','usage_palette','transferable_to','utility_refs','workflow_pattern_refs','component_refs']:
   if x.get(field):
    add_assertion(assertions,sid,'koa:'+field,json.dumps(x[field],ensure_ascii=False),st,src)
  if x.get('placement'):
   for k,v in x['placement'].items(): add_assertion(assertions,sid,'koa:placement_'+k,v,st,src)
# relations
rels=json.loads((KS/'relations.json').read_text(encoding='utf-8'))['relations'];counts['relations']=len(rels)
for r in rels:
 vals=[]
 if r.get('role'): vals=[{'dimension':'relationship_role','value_semantics':'categorical','value_state':'known','value':r['role']}]
 add_assertion(assertions,r['subject'],r['predicate'],('item',r['object']),r.get('assertion_status','sourced'),r.get('source_refs',[]),valuations=vals or None,coordinates=r.get('coordinates') or None,notes=r.get('notes'))
# source registry
sources=[x['source_id'] for x in json.loads((ROOT/'knowledge-base/sources/source-registry/source-registry.json').read_text(encoding='utf-8'))['sources']]
state={'schema_version':'6.0','artifact_type':'kristal_state','artifact_status':'working','created_at':'2026-10-02T12:45:00Z','updated_at':NOW,'created_by':{'agent_id':'urn:openai:chatgpt:gpt-5.6-sol','name':'ChatGPT','agent_type':'assistant','purpose':'Map kOA components, utilities and potential workflows while preserving authority and evidence boundaries.'},'canonicalization_profile':'kristal.v6:jcs-rfc8785','canonicalization_version':'1','applicability':{'domain':'kOA','subdomain':'ecosystem-map','language':'fr'},'source_refs':sources,'assertions':assertions,'provenance':[{'provenance_id':'prov:evolution-v'+VERSION,'kind':'compiled_from_editorial_catalogs','generated_at':NOW,'inputs':['knowledge-sources/'+fn for fn,_,_ in CATALOGS]+['knowledge-sources/relations.json'],'notes':'Graph-first working map baseline 2026-10-03, additively reconciled with 155 kOA inventory rows dated 2026-10-27 and user-supplied component snapshots. Repository locator metadata (recorded public remote + local observation) is canonicalized in repositories.json; missing remotes are not guessed. Owner/project evidence is used within scope; project folders are not silently promoted to repository authority; scenarios remain editorial composition unless separately verified.'}],'reader_policy_refs':['reader-profiles/component-capability-map.json','reader-profiles/operating-function-map.json','reader-profiles/need-capability-map.json','reader-profiles/utility-map.json','reader-profiles/workflow-pattern-map.json','reader-profiles/problem-pattern-map.json','reader-profiles/scenario-map.json','reader-profiles/peripheral-app-map.json','reader-profiles/repository-map.json','reader-profiles/contract-map.json','reader-profiles/lifecycle-map.json','reader-profiles/support-boundary-map.json'],'warnings':['2026-10-27 snapshot reconciliation is not a GitHub reachability check, runtime activation, nor approval to push.','Working synthesis; owner repositories retain implementation authority. Current local observation does not prove production activation.','Scenario composition is not production deployment evidence.','Business-plan finance/monetization is not imported as architectural truth.','Prepared integration is not activated integration.','Repository or offer identity never transfers domain authority.','Support/reference status never implies kOA Digital Ecosystem membership or domain authority.'],'extensions':{'package':'Kristal-kOA-Ecosystem','package_version':VERSION,'map_model':'graph-first; utilities and workflow patterns are derived/use-oriented layers over component × capability','primary_axes':['component','capability'],'organizing_axis':'operating_function','use_axis':'utility','workflow_axis':'workflow_pattern','secondary_axes':['need','problem_family','scenario','scope','placement','domain','contract','artifact','lifecycle','invariant','authority','repository','evidence-state']}}
state['state_id'],state['content_hash']=v6_state_identity(state)
(ROOT/'knowledge-base/corpus/koa-ecosystem.kristal-state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# index
idx={'format':'koa.kristal-index.v3','generated_at':NOW,'package_version':VERSION,'counts':{'assertions':len(assertions),**{k:len(v) for k,v in by_kind.items()},'relations':len(rels)},'by_kind':by_kind}
(ROOT/'knowledge-base/corpus/index.json').write_text(json.dumps(idx,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Views
labels={}
for fn,key,kind in CATALOGS:
 for x in read(fn,key): labels[x['id']]=item_label(x)
utilities=read('utilities.json','utilities');patterns=read('workflow-patterns.json','patterns');probs=read('problem-families.json','problem_families');sc36=read('scenario-archetypes.json','scenarios');sc120=read('scenario-mosaic.json','scenarios')
rel_by_pred=collections.defaultdict(list)
for r in rels:rel_by_pred[r['predicate']].append(r)
# utility map
lines=['# Utility map','','Les utilités ne sont pas des produits : elles regroupent des workflows transférables.','']
for u in utilities:
 lines += [f"## {u['label']}",u['description'],'']
 for r in rel_by_pred['koa:includes_workflow_pattern']:
  if r['subject']==u['id']: lines.append(f"- **{labels.get(r['object'],r['object'])}** — {next((p['description'] for p in patterns if p['id']==r['object']), '')}")
 lines.append('')
(ROOT/'views/utility-map.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
# workflow map
lines=['# Workflow pattern map','','Chaque pattern est une composition potentielle; les capacités liées décrivent ce qu’il faut mobiliser, pas une preuve de déploiement.','']
for p in patterns:
 lines += [f"## {p['label']}",p['description'],'',f"**Utilité(s):** {', '.join(labels.get(x,x) for x in p['utility_refs'])}",'','**Capacités habilitantes :**']
 for r in rel_by_pred['koa:enabled_by_capability']:
  if r['subject']==p['id']: lines.append('- '+labels.get(r['object'],r['object']))
 pf=[labels.get(r['subject'],r['subject']) for r in rel_by_pred['koa:addressed_by_workflow_pattern'] if r['object']==p['id']]
 if pf: lines += ['', '**Familles de problèmes observées :** '+', '.join(sorted(set(pf)))]
 lines.append('')
(ROOT/'views/workflow-pattern-map.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
# problem map
lines=['# Problem → workflow map','','Les 36 archétypes regroupent des ruptures récurrentes; elles orientent vers des patterns, pas vers un produit obligatoire.','']
for p in probs:
 lines += [f"## {p['label']}",p['description'],'','**Patterns observés :**']
 rr=[r for r in rel_by_pred['koa:addressed_by_workflow_pattern'] if r['subject']==p['id']]
 rr.sort(key=lambda r:-(next((c['value'] for c in r.get('coordinates',[]) if c['axis']=='archetype_count'),0)))
 for r in rr:
  count=next((c['value'] for c in r.get('coordinates',[]) if c['axis']=='archetype_count'),None)
  lines.append(f"- {labels.get(r['object'],r['object'])}"+(f" — {count} archétype(s)" if count else ''))
 reps=[s['title'] for s in sc36 if s['problem_family_ref']==p['id']][:5]
 if reps: lines += ['', '**Exemples :** '+ ' · '.join(reps)]
 lines.append('')
(ROOT/'views/problem-pattern-map.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
# component utility derived map: component->capabilities->patterns->utility; overlay scenario observation
comp_caps=collections.defaultdict(set)
for r in rel_by_pred['koa:contributes_to']:comp_caps[r['subject']].add(r['object'])
pat_caps=collections.defaultdict(set)
for r in rel_by_pred['koa:enabled_by_capability']:pat_caps[r['subject']].add(r['object'])
util_pats=collections.defaultdict(set)
for r in rel_by_pred['koa:includes_workflow_pattern']:util_pats[r['subject']].add(r['object'])
observed={}
for r in rel_by_pred['koa:observed_in_utility_scenarios']:
 coords={c['axis']:c['value'] for c in r.get('coordinates',[])};observed[(r['subject'],r['object'])]=coords
components=read('components.json','components')
lines=['# Component × utility map','','Cette vue est **dérivée** : un composant soutient une utilité lorsqu’une de ses capacités habilite au moins un pattern de cette utilité. `observed` indique en plus une présence explicite dans le corpus des 120 scénarios.','']
for u in utilities:
 lines += [f"## {u['label']}",'','| Component | Pattern matches | Scenario evidence |','|---|---:|---|']
 rows=[]
 for c in components:
  pats=[p for p in util_pats[u['id']] if comp_caps[c['id']] & pat_caps[p]]
  if pats:
   ob=observed.get((c['id'],u['id']))
   ev=f"{ob.get('scenario_count')} scenarios; mean {ob.get('mean_role_weight_1_5')}/5" if ob else 'architectural path only'
   rows.append((len(pats),c['label'],ev))
 for n,label,ev in sorted(rows,key=lambda x:(-x[0],x[1])):
  lines.append(f"| {label} | {n} | {ev} |")
 lines.append('')
(ROOT/'views/component-utility-map.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
# long CSV utility matrix
with (ROOT/'views/component-utility-matrix.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.writer(f);w.writerow(['component_id','component','utility_id','utility','pattern_matches','scenario_count','mean_role_weight_1_5','evidence_mode'])
 for c in components:
  for u in utilities:
   pats=[p for p in util_pats[u['id']] if comp_caps[c['id']] & pat_caps[p]]
   if not pats: continue
   ob=observed.get((c['id'],u['id']))
   w.writerow([c['id'],c['label'],u['id'],u['label'],len(pats),ob.get('scenario_count') if ob else '',ob.get('mean_role_weight_1_5') if ob else '','scenario_observed+architectural' if ob else 'architectural_path'])
# scenario index
with (ROOT/'views/scenario-workflow-index.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.writer(f);w.writerow(['corpus','scenario_id','title','utility_or_problem_family','workflow_pattern','loop_or_scale','components','runtime_status'])
 for s in sc36:
  w.writerow(['36-archetypes',s['scenario_id'],s['title'],labels.get(s['problem_family_ref'],s['problem_family_ref']),' | '.join(labels.get(x,x) for x in s['workflow_pattern_refs']),s.get('scale',''),' | '.join(labels.get(x,x) for x in s['component_refs']),s.get('runtime_status','')])
 for s in sc120:
  w.writerow(['120-mosaic',s['scenario_id'],s['title'],labels.get(s['utility_ref'],s['utility_ref']),labels.get(s['workflow_pattern_ref'],s['workflow_pattern_ref']),s.get('loop',''),' | '.join(labels.get(x['component_ref'],x['component_ref']) for x in s['component_roles']),s.get('runtime_status','')])
# promoted apps view
promoted=['koa:ekole','koa:ekole-pastorale','koa:ekole-quebec','koa:akor','koa:kompose','koa:kontexte','koa:inkuisite','koa:bokristal','koa:spek','koa:dik','koa:kristalizer','koa:kristal-authoring-kit','koa:arketype','koa:skope','koa:kor','koa:koali-control-panel','koa:konnaxion-capsule-manager','koa:konnaxion-worlds','koa:orgo-worlds','koa:kintsugi-kompendio','koa:qualification-tooling','koa:konnaxion-securitydiag','koa:levelupdiag-koa-linux','koa:levelupdiag-konnaxion','koa:levelupdiag-kristal','koa:levelupdiag-orgo','koa:levelupdiag-semantik','koa:levelupdiag-medikristal','koa:ariane-diagnostics','koa:levelupdiag-ariane','koa:konnaxion-universe-worlds-manager','koa:konnaxiondiag','koa:konstellation-publisher','koa:semantik-phrase-ops-console','koa:kristaldiag','koa:repodiag','koa:uckk-securitydiag','koa:uckk-publisher','koa:editorial-figure-engine','koa:formulator','koa:kristal-grand-challenges','koa:astro-signals','koa:voxtral-audiobook-studio']
lines=[f'# Supporting applications / tooling — v{VERSION}','','Ces pièces sont reconnues comme composants fonctionnels, mais leur autorité reste bornée.','']
byid={x['id']:x for x in components}
for cid in promoted:
 x=byid[cid];lines += [f"## {x['label']}",x['description'],f"- scope: `{x['scope']}`",f"- placement: `{x.get('placement',{}).get('tier','')}` / `{x.get('placement',{}).get('integration_state','')}`",'']
(ROOT/'views/supporting-apps-map.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
# canonical repository map generated from repositories.json + repo relations
repositories=read('repositories.json','repositories')
repo_targets=collections.defaultdict(list)
for r in rel_by_pred['koa:realizes_or_supports']:
 repo_targets[r['subject']].append((r['object'],r.get('role','')))
lines=['# Repository map — canonical remotes + local observations','',
       '> This view is generated from `knowledge-base/sources/repositories.json`. Public remotes are shown only when a URL is recorded in the canonical registry; missing remotes remain unresolved and are not guessed. Local paths are observations, not architectural authority.','',
       '| Repository | Public remote | Locator status | Membership | Role | Realizes / supports | Local path | Evidence |',
       '|---|---|---|---|---|---|---|---|']
for r in sorted(repositories,key=lambda x:(x.get('name') or '').casefold()):
 name=r.get('name') or r['id']
 url=r.get('public_remote_url') or r.get('url')
 remote=(f"[{r.get('public_remote_label') or name}]({url})" if url else '—')
 targets=[]
 for oid,role in repo_targets.get(r['id'],[]):
  lab=labels.get(oid,oid)
  targets.append(f"{lab}"+(f" (`{role}`)" if role else ''))
 target_text='<br>'.join(targets) if targets else '—'
 local=f"`{r['local_path']}`" if r.get('local_path') else '—'
 evidence=r.get('readme_file') or ('source/index evidence' if r.get('source_refs') else '—')
 lines.append('| '+ ' | '.join([
  f"`{name}`",remote,f"`{r.get('repository_locator_status','unresolved')}`",
  f"`{r.get('architectural_membership','')}`",f"`{r.get('repository_role','')}`",
  target_text,local,f"`{evidence}`" if evidence!='—' else '—'])+' |')
(ROOT/'views/repository-map.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

# compact public repository directory generated from the same canonical registry
public=[r for r in repositories if (r.get('public_remote_url') or r.get('url')) and r.get('public_remote_status') not in ('unverified_local_origin_only','unverified_no_public_remote')]
lines=['# Public repository directory','',
       'This directory is generated from the canonical repository registry. It lists recorded public remotes only; it is not a claim that every local repository has a public remote.','',
       '| Repository | Public remote | Boundary | Role | Local observation |',
       '|---|---|---|---|---|']
for r in sorted(public,key=lambda x:(x.get('name') or '').casefold()):
 url=r.get('public_remote_url') or r.get('url')
 label=r.get('public_remote_label') or r.get('full_name') or r.get('name')
 local='current' if r.get('current_local_observation') else r.get('local_observation_status','—')
 lines.append(f"| `{r.get('name')}` | [{label}]({url}) | `{r.get('architectural_membership','')}` | `{r.get('repository_role','')}` | `{local}` |")
(ROOT/'views/public-repository-directory.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

# Application / toolchain coverage derived from canonical component and repository records.
selected_app_ids = {
 'koa:astro-signals','koa:ame-artificielle','koa:formulator','koa:kristal-grand-challenges','koa:kristal-math',
 'koa:levelupdiag-koa-linux','koa:levelupdiag-orgo','koa:levelupdiag-semantik','koa:mathchallenges',
 'koa:orphee-walk-straight','koa:pi-theory','koa:power-dynamics','koa:votingmachine','koa:voxtral-audiobook-studio',
 'koa:ekole','koa:ekole-pastorale','koa:ekole-quebec','koa:akor','koa:kompose','koa:kontexte',
 'koa:inkuisite','koa:bokristal','koa:spek','koa:dik','koa:kristalizer','koa:kristal-authoring-kit',
 'koa:arketype','koa:skope','koa:kor','koa:kristaldiag'
}
lines=['# Current application / tooling / corpus coverage', '',
       'Derived from `knowledge-base/sources/components.json` and `repositories.json`. Inclusion here means **mapped**; the integration state in the last column is the explicit qualification boundary, not evidence of runtime interoperability.', '',
       '| Component | Kind | Scope | Repository or local evidence | Placement / integration state |',
       '|---|---|---|---|---|']
repo_byid={x['id']:x for x in repositories}
for x in sorted([c for c in components if c['id'] in selected_app_ids],key=lambda c:c['label'].casefold()):
 ref=repo_byid.get(x.get('repository_ref',''))
 rep=(f"`{ref.get('name','')}` ({ref.get('repository_locator_status','unresolved')})" if ref else '—')
 place=x.get('placement',{})
 lines.append('| '+ ' | '.join([x['label'].replace('|','/'),f"`{x.get('kind','')}`",f"`{x.get('scope','')}`",rep,
              f"`{place.get('tier','')}` / `{place.get('integration_state','')}`"])+ ' |')
lines.extend(['', '> La présence d’un `repository_ref` ne confirme ni remote GitHub disponible, ni autorisation GitSink. Les composants historiques non repris ici restent dans `components.json`.'])
(ROOT/'views/current-application-map.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

# Derived, read-only Doc Server catalogue; all memberships come from relations.json.
doc_cats=read('selection-categories.json','categories')
doc_repos={x['id']:x for x in repositories}
doc_rel=[r for r in rels if r['predicate']=='koa:doc_scope_includes_repository']
doc_diag=[r for r in rels if r['predicate']=='koa:doc_scope_includes_diagnostic']
view={'format':'koa.doc-server.catalog.v1','kristal_version':VERSION,
 'authority':{'categories':'Kristal-kOA-Ecosystem','inventory':'kOA Digital Ecosystem','maturity':'GitHub Audit and evidence owners'},
 'warnings':['A selection is not a runtime qualification','Diagnostic observations are not promoted evidence'],
 'categories':[], 'observations':[{'campaign_id':x['campaign_id'],'observed_at':x['observed_at'],'verdict':x['verdict'],
 'reference_status':x['reference_status'],'source_summary_sha256':x['source_summary_sha256']} for x in read('diagnostic-observations.json','observations')]}
for cat in doc_cats:
 ids=sorted(set(r['object'] for r in doc_rel if r['subject']==cat['id']))
 view['categories'].append({'id':cat['id'],'label':cat['label'],'default_selected':False,
  'repositories':[{'id':x,'full_name':doc_repos[x].get('full_name'),'url':doc_repos[x].get('url')} for x in ids],
  'diagnostic_components':sorted(set(r['object'] for r in doc_diag if r['subject']==cat['id']))})
(ROOT/'views/doc-server').mkdir(parents=True,exist_ok=True)
(ROOT/'views/doc-server/catalog.v1.json').write_text(json.dumps(view,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

# manifest last, excluding itself
manifest={'format':'koa.kristal.package-manifest.v1','package':'Kristal-kOA-Ecosystem','version':VERSION,'generated_at':NOW,'files':[]}
for p in sorted(ROOT.rglob('*')):
 if not p.is_file() or p.name=='manifest.sha256.json':continue
 rel=p.relative_to(ROOT).as_posix();b=p.read_bytes();manifest['files'].append({'path':rel,'sha256':hashlib.sha256(b).hexdigest(),'size_bytes':len(b)})
(ROOT/'manifest.sha256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'version':VERSION,'assertions':len(assertions),'relations':len(rels),'state_hash':state['content_hash']['value'],'counts':idx['counts']},ensure_ascii=False,indent=2))
