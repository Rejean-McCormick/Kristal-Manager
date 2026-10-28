from __future__ import annotations
import argparse,time
from pathlib import Path
from .checks import CHECKS
from .neutral import NEUTRAL_CHECKS
from .v9_checks import V9_CHECKS
from .v10_checks import V10_CHECKS
from .release_checks import RELEASE_CHECKS
from .config import load_config
from .discovery import discover, inventory_from_data
from .driver import load_driver
from .runner_types import Context,target_kind
from .schemas import SchemaStore
from .utils import utc_now,write_json,read_json
from .models import Finding,LevelResult
from .manifest import LEVELS

ALL_CHECKS={**NEUTRAL_CHECKS,**CHECKS,**V9_CHECKS,**V10_CHECKS,**RELEASE_CHECKS}

def execute_level(*,level:str,target:Path,repo:Path,config_path:Path,control_dir:Path,run_id:str,output:Path,profile:str|None=None,allow_exec:bool=False,interop_evidence:Path|None=None,inventory_cache:Path|None=None):
    target=target.resolve();repo=repo.resolve();cfg=load_config(repo,target,config_path=config_path,control_dir=control_dir)
    if inventory_cache and inventory_cache.is_file():
        inv=inventory_from_data(read_json(inventory_cache),target)
    else:
        inv=discover(target,max_files=int(cfg.data.get('max_json_files',100000) or 100000))
    scan_root=target if target.is_dir() else target.parent
    resource_root=(repo/'tck') if (repo/'tck').is_dir() else (Path(__file__).resolve().parent/'resources'/'tck')
    ctx=Context(repo,target,scan_root,inv,SchemaStore(repo),cfg,profile,allow_exec,load_driver(target),target_kind(inv),resource_root,interop_evidence.resolve() if interop_evidence else None)
    started=time.monotonic();fn=ALL_CHECKS.get(level)
    try:
        if fn is None:raise ValueError(f'unknown level {level}')
        r=fn(ctx);r.duration_seconds=time.monotonic()-started
    except Exception as e:
        now=utc_now();r=LevelResult(level,LEVELS.get(level,{}).get('name',level),'ERROR',[Finding(f'{level}-INTERNAL','ERROR','diagnostics',f'Unhandled diagnostic exception: {type(e).__name__}: {e}')],started_at=now,ended_at=now,duration_seconds=time.monotonic()-started)
    data=r.to_dict(run_id=run_id,target_root=str(target),profile=profile);write_json(output,data);return data

def main(argv=None):
    p=argparse.ArgumentParser(prog='kristaldiag-worker')
    p.add_argument('--level',required=True);p.add_argument('--target',required=True);p.add_argument('--repo-root',required=True)
    p.add_argument('--config',required=True);p.add_argument('--control-dir',required=True);p.add_argument('--run-id',required=True);p.add_argument('--output',required=True);p.add_argument('--inventory-cache')
    p.add_argument('--profile');p.add_argument('--allow-exec',action='store_true');p.add_argument('--interop-evidence')
    a=p.parse_args(argv)
    execute_level(level=a.level,target=Path(a.target),repo=Path(a.repo_root),config_path=Path(a.config),control_dir=Path(a.control_dir),run_id=a.run_id,output=Path(a.output),profile=a.profile,allow_exec=a.allow_exec,interop_evidence=Path(a.interop_evidence) if a.interop_evidence else None,inventory_cache=Path(a.inventory_cache) if a.inventory_cache else None)
    return 0

if __name__=='__main__':raise SystemExit(main())
