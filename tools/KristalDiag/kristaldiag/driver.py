from __future__ import annotations
import json, os, subprocess, tempfile
from pathlib import Path

ALLOWED_ACTIONS={'self_test','read_v6','parse_v7','build_mesh','project_v6','crystallize','read_v9','commit_v9_artifact','commit_v9_state','validate_v9_derivation','validate_v9_materialization','publish_v9_state','activate_v9_state','interop_export','interop_import'}

def load_driver(target:Path):
    p=(target if target.is_dir() else target.parent)/'kristaldiag-driver.json'
    if not p.is_file():return None
    d=json.loads(p.read_text(encoding='utf-8'))
    if d.get('schema')!='kristaldiag.driver.v1':raise ValueError('invalid driver schema')
    return d

def run_action(target:Path,driver:dict,action:str,*,timeout:int=120,input_path:Path|None=None):
    if action not in ALLOWED_ACTIONS:raise ValueError('unsupported driver action')
    spec=(driver.get('actions') or {}).get(action)
    if not spec:return None
    argv=spec.get('argv')
    if not isinstance(argv,list) or not argv or not all(isinstance(x,str) and x for x in argv):raise ValueError(f'invalid argv for {action}')
    env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH'}}
    if input_path:env['KRISTALDIAG_INPUT']=str(input_path)
    cp=subprocess.run(argv,cwd=str(target if target.is_dir() else target.parent),env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',timeout=timeout,shell=False,check=False)
    parsed=None
    if cp.stdout.strip():
        try:parsed=json.loads(cp.stdout)
        except Exception:parsed=None
    return {'returncode':cp.returncode,'stdout':cp.stdout[-20000:],'stderr':cp.stderr[-20000:],'json':parsed}
