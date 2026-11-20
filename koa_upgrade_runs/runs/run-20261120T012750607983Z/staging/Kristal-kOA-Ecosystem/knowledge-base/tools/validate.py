#!/usr/bin/env python3
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; errors=[]
state=json.loads((ROOT/'knowledge-base/corpus/koa-ecosystem.kristal-state.json').read_text(encoding='utf-8'))
try:
 import jsonschema
 schema=json.loads((ROOT/'knowledge-base/schemas/kristal-state.schema.json').read_text(encoding='utf-8'));jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).validate(state)
except ImportError: print('WARN: jsonschema not installed; schema validation skipped')
except Exception as e: errors.append('Kristal state schema: '+str(e))
CAT=[('components.json','components'),('capabilities.json','capabilities'),('needs.json','needs'),('operating-functions.json','functions'),('invariants.json','invariants'),('domains.json','domains'),('contracts.json','contracts'),('artifacts.json','artifacts'),('lifecycles.json','lifecycles'),('repositories.json','repositories'),('external-references.json','items'),('utilities.json','utilities'),('workflow-patterns.json','patterns'),('problem-families.json','problem_families'),('scenario-archetypes.json','scenarios'),('scenario-mosaic.json','scenarios'),('selection-categories.json','categories'),('diagnostic-observations.json','observations')]
ids=set();components=[]
for fn,key in CAT:
 for x in json.loads((ROOT/'knowledge-base/sources'/fn).read_text(encoding='utf-8'))[key]:
  if x['id'] in ids: errors.append('Duplicate id '+x['id'])
  ids.add(x['id']);components.append(x) if fn=='components.json' else None
rels=json.loads((ROOT/'knowledge-base/sources/relations.json').read_text(encoding='utf-8'))['relations']
for r in rels:
 if r['subject'] not in ids: errors.append('Unknown relation subject '+r['subject'])
 if r['object'] not in ids: errors.append('Unknown relation object '+r['object'])
placed={r['subject'] for r in rels if r['predicate']=='koa:fulfills_function'}
for c in components:
 if c['id'] not in placed: errors.append('Component without operating-function placement '+c['id'])
# scenario refs
for s in json.loads((ROOT/'knowledge-base/sources/scenario-archetypes.json').read_text(encoding='utf-8'))['scenarios']:
 for ref in [s['problem_family_ref'],*s['workflow_pattern_refs'],*s['component_refs']]:
  if ref not in ids: errors.append('Unknown scenario archetype ref '+ref+' in '+s['id'])
for s in json.loads((ROOT/'knowledge-base/sources/scenario-mosaic.json').read_text(encoding='utf-8'))['scenarios']:
 for ref in [s['utility_ref'],s['workflow_pattern_ref'],*[x['component_ref'] for x in s['component_roles']]]:
  if ref not in ids: errors.append('Unknown scenario mosaic ref '+ref+' in '+s['id'])
manifest=json.loads((ROOT/'manifest.sha256.json').read_text(encoding='utf-8'))
for x in manifest['files']:
 p=ROOT/x['path']
 if not p.exists(): errors.append('Missing '+x['path']);continue
 if hashlib.sha256(p.read_bytes()).hexdigest()!=x['sha256']: errors.append('Hash mismatch '+x['path'])
print(json.dumps({'status':'PASS' if not errors else 'FAIL','assertions':len(state['assertions']),'relations':len(rels),'referents':len(ids),'components':len(components),'utilities':len(json.loads((ROOT/'knowledge-base/sources/utilities.json').read_text(encoding='utf-8'))['utilities']),'workflow_patterns':len(json.loads((ROOT/'knowledge-base/sources/workflow-patterns.json').read_text(encoding='utf-8'))['patterns']),'scenario_archetypes':len(json.loads((ROOT/'knowledge-base/sources/scenario-archetypes.json').read_text(encoding='utf-8'))['scenarios']),'scenario_mosaic':len(json.loads((ROOT/'knowledge-base/sources/scenario-mosaic.json').read_text(encoding='utf-8'))['scenarios']),'errors':errors},ensure_ascii=False,indent=2));sys.exit(1 if errors else 0)
