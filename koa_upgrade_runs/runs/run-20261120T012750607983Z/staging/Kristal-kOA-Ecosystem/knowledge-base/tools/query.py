#!/usr/bin/env python3
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
files={'component':('components.json','components'),'capability':('capabilities.json','capabilities'),'need':('needs.json','needs'),'function':('operating-functions.json','functions'),'invariant':('invariants.json','invariants'),'contract':('contracts.json','contracts'),'artifact':('artifacts.json','artifacts'),'lifecycle':('lifecycles.json','lifecycles'),'repository':('repositories.json','repositories'),'utility':('utilities.json','utilities'),'pattern':('workflow-patterns.json','patterns'),'problem':('problem-families.json','problem_families'),'scenario36':('scenario-archetypes.json','scenarios'),'scenario120':('scenario-mosaic.json','scenarios')}
if len(sys.argv)<3:
 print('usage: query.py <'+ '|'.join(list(files)+['scenario']) +'> <id-or-text>');raise SystemExit(2)
kind,q=sys.argv[1],sys.argv[2].lower()
rels=json.loads((ROOT/'knowledge-base/sources/relations.json').read_text(encoding='utf-8'))['relations']
if kind=='scenario':
 sets=[('scenario36',*files['scenario36']),('scenario120',*files['scenario120'])]
 found=False
 for source_kind,fn,key in sets:
  items=json.loads((ROOT/'knowledge-base/sources'/fn).read_text(encoding='utf-8'))[key]
  for x in [x for x in items if q in json.dumps(x,ensure_ascii=False).lower()]:
   found=True; print(json.dumps({'scenario_corpus':source_kind,**x},ensure_ascii=False,indent=2));print(json.dumps({'relations':[r for r in rels if r['subject']==x['id'] or r['object']==x['id']]},ensure_ascii=False,indent=2))
 raise SystemExit(0 if found else 1)
if kind not in files:
 print('usage: query.py <'+ '|'.join(list(files)+['scenario']) +'> <id-or-text>');raise SystemExit(2)
fn,key=files[kind];items=json.loads((ROOT/'knowledge-base/sources'/fn).read_text(encoding='utf-8'))[key]
found=False
for x in [x for x in items if q in json.dumps(x,ensure_ascii=False).lower()]:
 found=True; print(json.dumps(x,ensure_ascii=False,indent=2));print(json.dumps({'relations':[r for r in rels if r['subject']==x['id'] or r['object']==x['id']]},ensure_ascii=False,indent=2))
raise SystemExit(0 if found else 1)
