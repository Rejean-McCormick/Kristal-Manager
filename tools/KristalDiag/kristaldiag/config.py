from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT={
 'control_dir':'.kristaldiag',
 'max_json_files':100000,
 'max_target_files':500000,
 'default_profile':None,
 'allow_exec':False,
 'strict_warnings':False,
 'require_external_interop_for_release':False,
 'execution':{
   'max_parallel':4,
   'default_timeout_seconds':120,
   'capture_limit_kb':256,
   'fail_fast':False,
   'protect_target':True,
   'allow_target_mutation':False,
   'allow_network':False,
 },
 'scan':{
   'exclude_dirs':['.git','.hg','.svn','.kristaldiag','.levelupdiag','node_modules','vendor','dist','build','target','.venv','venv','__pycache__','.cache','coverage','.tox','.mypy_cache','.pytest_cache'],
   'max_files':300000,
   'max_file_bytes':1048576,
   'max_security_files':4000,
   'large_file_bytes':10485760,
 },
 'toolchain':{'required':[],'optional':[]},
 'validators':[],
 'security':{'enabled':True,'additional_patterns':[],'additional_excluded_globs':[]},
 'redaction':{'enabled':True},
}

def _merge(dst,src):
    for k,v in src.items():
        if isinstance(v,dict) and isinstance(dst.get(k),dict): _merge(dst[k],v)
        else: dst[k]=v
    return dst

@dataclass
class Config:
    data:dict
    target:Path
    control:Path

def load_config(repo_root:Path,target:Path,config_path:Path|None=None,control_dir:Path|None=None)->Config:
    data=json.loads(json.dumps(DEFAULT))
    p=config_path or (repo_root/'kristaldiag.config.json')
    if p.is_file(): _merge(data,json.loads(p.read_text(encoding='utf-8')))
    # Optional local override, intentionally ignored by packaging/manifest workflows.
    local=repo_root/'kristaldiag.config.local.json'
    if config_path is None and local.is_file(): _merge(data,json.loads(local.read_text(encoding='utf-8')))
    t=target.resolve()
    c=(control_dir or (t if t.is_dir() else t.parent)/str(data['control_dir'])).resolve()
    return Config(data,t,c)
