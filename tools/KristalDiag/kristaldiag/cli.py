from __future__ import annotations
import argparse,json,sys,tempfile,shutil
from pathlib import Path
from . import VERSION,STANDARD_TARGET,FRAMEWORK_REPOSITORY,FRAMEWORK_COMMIT,FRAMEWORK_SNAPSHOT_SHA256,FRAMEWORK_PIN_STATUS
from .config import load_config
from .profiles import PROFILES
from .manifest import CAMPAIGNS,LEVELS
from .runner import run
from .utils import read_json
from .verdicts import exit_code
from .evidence import verify_run

def parser():
    p=argparse.ArgumentParser(prog='kristaldiag',description='Independent Kristal Standard v10 diagnostics, publication verification and conformance harness')
    p.add_argument('--version',action='version',version=f'KristalDiag {VERSION} (target {STANDARD_TARGET})')
    sub=p.add_subparsers(dest='cmd',required=True)
    d=sub.add_parser('doctor');d.add_argument('--target',default='.')
    sub.add_parser('list')
    c=sub.add_parser('check');c.add_argument('target');c.add_argument('--control-dir');c.add_argument('--allow-exec',action='store_true');c.add_argument('--jobs',type=int);c.add_argument('--json',action='store_true')
    r=sub.add_parser('run',help='Run a named diagnostic campaign (LevelUpDiag-compatible surface)');r.add_argument('campaign',choices=list(CAMPAIGNS));r.add_argument('target',nargs='?',default='.');r.add_argument('--control-dir');r.add_argument('--allow-exec',action='store_true');r.add_argument('--jobs',type=int);r.add_argument('--fail-fast',action='store_true');r.add_argument('--json',action='store_true')
    co=sub.add_parser('conform');co.add_argument('target');co.add_argument('--profile',choices=list(PROFILES),required=True);co.add_argument('--control-dir');co.add_argument('--allow-exec',action='store_true');co.add_argument('--interop-evidence');co.add_argument('--jobs',type=int);co.add_argument('--json',action='store_true')
    l=sub.add_parser('run-level');l.add_argument('level',choices=list(LEVELS));l.add_argument('target');l.add_argument('--profile',choices=list(PROFILES));l.add_argument('--control-dir');l.add_argument('--allow-exec',action='store_true');l.add_argument('--json',action='store_true')
    t=sub.add_parser('triage-current');t.add_argument('target',nargs='?',default='.')
    v=sub.add_parser('verify-run');v.add_argument('summary');v.add_argument('--require-pass',action='store_true',help='Reject valid-but-non-PASS evidence (still not a signed C1 receipt)')
    io=sub.add_parser('interop');io.add_argument('producer');io.add_argument('consumer');io.add_argument('--output',required=True);io.add_argument('--allow-exec',action='store_true')
    st=sub.add_parser('self-test');st.add_argument('--standard-root')
    return p

def _print(summary,current,json_mode=False):
    if json_mode:print(json.dumps(summary,ensure_ascii=False,indent=2))
    else:
        print((current/'summary.txt').read_text(encoding='utf-8'),end='');print(f'Evidence: {current}')

def main(argv=None):
    a=parser().parse_args(argv);repo=Path(__file__).resolve().parents[1]
    try:
        if a.cmd=='list':
            for k,m in LEVELS.items():print(f'{k}  {m["name"]}')
            print('\nCampaigns:');[print(f'{k}: '+', '.join(v)) for k,v in CAMPAIGNS.items()]
            print('\nProfiles:');[print(f'{k}: '+', '.join(v)) for k,v in PROFILES.items()];return 0
        if a.cmd=='doctor':
            target=Path(a.target).resolve();resources=Path(__file__).resolve().parent/'resources';contracts=(repo/'contracts') if (repo/'contracts'/'v7').is_dir() else (resources/'contracts')
            print(f'KristalDiag {VERSION}');print(f'Kristal target: {STANDARD_TARGET}');print(f'Target: {target}')
            print('scheduler: isolated-process / bounded-parallel')
            try:import jsonschema;print('jsonschema: OK')
            except Exception:print('jsonschema: MISSING');return 30
            print(f'framework-pin: {FRAMEWORK_REPOSITORY}@{FRAMEWORK_COMMIT}' if FRAMEWORK_COMMIT else f'framework-pin: {FRAMEWORK_PIN_STATUS} {FRAMEWORK_SNAPSHOT_SHA256}');print(f'contracts/v10: {(contracts/"v10").is_dir()}');print(f'contracts/github: {(contracts/"github").is_dir()}');print(f'contracts/v9: {(contracts/"v9").is_dir()}');print(f'contracts/v8: {(contracts/"v8").is_dir()}');print(f'contracts/v7: {(contracts/"v7").is_dir()}');print(f'contracts/v6: {(contracts/"v6/kristal-state.schema.json").is_file()}')
            from .utils import sha256_file
            try:
                cm=read_json(resources/'contract-manifest.json');bad=[]
                for rel,hx in (cm.get('files') or {}).items():
                    q=resources/rel
                    if not q.is_file() or sha256_file(q)!=hx:bad.append(rel)
                print('vendored-contract-integrity: '+('OK' if not bad else 'FAIL'))
                if bad:return 30
            except Exception as exc:
                print(f'vendored-contract-integrity: ERROR ({type(exc).__name__}: {exc})');return 30
            return 0
        if a.cmd in {'check','conform','run','run-level'}:
            target=Path(a.target);control=Path(a.control_dir).resolve() if getattr(a,'control_dir',None) else None;cfg=load_config(repo,target,control_dir=control)
            profile=getattr(a,'profile',None);campaign=getattr(a,'campaign',None);levels=[a.level] if a.cmd=='run-level' else None
            summary,code,current=run(target,cfg,profile=profile,campaign=campaign,levels=levels,allow_exec=getattr(a,'allow_exec',False),repo_root=repo,interop_evidence=Path(a.interop_evidence) if getattr(a,'interop_evidence',None) else None,jobs=getattr(a,'jobs',None),fail_fast=getattr(a,'fail_fast',None))
            _print(summary,current,getattr(a,'json',False));return code
        if a.cmd=='triage-current':
            target=Path(a.target).resolve();cfg=load_config(repo,target);p=cfg.control/'current'/'summary.json'
            if not p.is_file():print('No current KristalDiag evidence.');return 20
            s=read_json(p);found=False
            for row in s.get('levels',[]):
                if row['verdict'] in {'PASS','SKIP'}:continue
                found=True;print(f"{row['id']} {row['verdict']} {row['name']}")
                rp=p.parent/row['result']
                if rp.is_file():
                    for f in read_json(rp).get('findings',[]):
                        if f.get('verdict') not in {'PASS','SKIP'}:print(f"  {f.get('verdict')} {f.get('id')}: {f.get('message')}")
            if not found:print('Current run has no non-PASS findings.')
            return exit_code(s.get('verdict','ERROR'))
        if a.cmd=='verify-run':
            ok,detail=verify_run(Path(a.summary),repo);print('VALID' if ok else 'INVALID')
            if not ok:
                for problem in detail.get('problems',[]):print(' - '+json.dumps(problem,ensure_ascii=False,sort_keys=True))
            if not ok:
                return 30
            if a.require_pass:
                verdict = read_json(Path(a.summary)).get('verdict')
                if verdict != 'PASS':
                    print(f'NOT QUALIFIED: evidence integrity is valid, but verdict is {verdict}.')
                    return 20
            return 0
        if a.cmd=='interop':
            from .interop import run_interop
            r=run_interop(Path(a.producer),Path(a.consumer),repo_root=repo,output=Path(a.output),allow_exec=a.allow_exec);print(json.dumps(r,ensure_ascii=False,indent=2));return exit_code(r.get('verdict','ERROR'))
        if a.cmd=='self-test':
            if a.standard_root:
                target=Path(a.standard_root).resolve();cfg=load_config(repo,target,control_dir=target.parent/'.kristaldiag-selftest')
                summary,code,current=run(target,cfg,profile='V10-Standard',repo_root=repo);print((current/'summary.txt').read_text());return code
            resources=Path(__file__).resolve().parent/'resources'
            with tempfile.TemporaryDirectory(prefix='kristaldiag-selftest-') as td:
                base=Path(td);target=base/'reference-v10';target.mkdir()
                # Frozen v9 semantic fixtures provide the inherited state/build surfaces.
                for q in sorted((resources/'tck'/'v9'/'vectors').glob('*.json')):
                    if q.name!='logical-commitment-vectors.json':shutil.copy2(q,target/q.name)
                for q in sorted((resources/'tck'/'v9'/'workloads').glob('*.json')):shutil.copy2(q,target/q.name)
                # V10 node/binding/capability/directory surfaces use their canonical repository paths.
                kr=target/'.kristal';(kr/'bindings').mkdir(parents=True)
                shutil.copy2(resources/'tck'/'v10'/'vectors'/'node-manifest.example.json',kr/'node.json')
                shutil.copy2(resources/'tck'/'v10'/'vectors'/'github-binding.example.json',kr/'bindings'/'github.json')
                shutil.copy2(resources/'tck'/'v10'/'vectors'/'v10-capabilities.example.json',kr/'capabilities.json')
                shutil.copy2(resources/'tck'/'v10'/'vectors'/'directory.example.json',kr/'directory.json')
                shutil.copytree(resources/'tck'/'v10'/'bundle',target/'publication')
                cfg=load_config(repo,target,control_dir=base/'evidence');summary,code,current=run(target,cfg,profile='V10-Full',repo_root=repo)
                print((current/'summary.txt').read_text());return code
    except Exception as e:
        print(f'KristalDiag error: {type(e).__name__}: {e}',file=sys.stderr);return 30
    return 64
