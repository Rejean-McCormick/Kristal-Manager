from __future__ import annotations
import json,os,shutil,subprocess,sys,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import VERSION,STANDARD_TARGET,SUMMARY_SCHEMA,VERDICT_SCHEMA
from .config import Config
from .models import Finding,LevelResult
from .profiles import PROFILES
from .manifest import LEVELS,CAMPAIGNS,ORDER,closure
from .report import write_reports
from .utils import run_id,utc_now,write_json,sha256_file,safe_copytree,fingerprint_tree,read_json
from .verdicts import combine,exit_code
from .runner_types import target_kind
from .discovery import discover, inventory_to_data

HARD_DEP_BLOCK={'BLOCKED','ERROR','INFRA_ERROR','CONFIG_ERROR'}

def _gate(profile,results,strict_warnings=False,require_external=False):
    by={r['level_id']:r for r in results};required=PROFILES.get(profile,list(by)) if profile else list(by)
    findings=[];vals=[]
    for lid in required:
        r=by.get(lid)
        if not r:
            findings.append({'level':lid,'verdict':'BLOCKED','reason':'missing level result'});vals.append('BLOCKED');continue
        v=r['verdict'];effective='BLOCKED' if profile and v=='SKIP' else v
        vals.append(effective);findings.append({'level':lid,'verdict':v,'effective_verdict':effective})
    final=combine(vals)
    if strict_warnings and final in {'WARN','PARTIAL'}:final='FAIL'
    if require_external and profile=='V7-Kristall' and by.get('K11',{}).get('verdict')!='PASS':final='BLOCKED'
    return final,required,findings

def _k14(results,profile,cfg):
    verdict,required,details=_gate(profile,results,bool(cfg.data.get('strict_warnings')),bool(cfg.data.get('require_external_interop_for_release')))
    fs=[]
    if profile and profile not in PROFILES:
        fs.append(Finding('K14-PROFILE-001','CONFIG_ERROR','conformance',f'Unknown conformance profile: {profile}',expected=list(PROFILES)));verdict='CONFIG_ERROR'
    else:
        fs.append(Finding('K14-GATE-002',verdict if verdict!='SKIP' else 'PASS','conformance',f'Conformance gate evaluated {len(required)} required levels for {profile or "diagnostic/campaign"}.',evidence=details,impact='This verdict qualifies evidence; it does not grant execution authority.'))
    now=utc_now();return LevelResult('K14',LEVELS['K14']['name'],verdict,fs,started_at=now,ended_at=now,metadata={'required_levels':required})

def _blocked(level,run_id,target,deps,profile):
    now=utc_now();r=LevelResult(level,LEVELS[level]['name'],'BLOCKED',[Finding(f'{level}-DEPENDENCY','BLOCKED','dependency','A required diagnostic dependency did not produce usable evidence.',evidence={'dependencies':deps})],started_at=now,ended_at=now)
    return r.to_dict(run_id=run_id,target_root=str(target),profile=profile)

def _select(profile=None,campaign=None,levels=None):
    if levels:return closure(levels)
    if campaign:
        if campaign not in CAMPAIGNS:raise ValueError(f'unknown campaign {campaign}')
        return closure(CAMPAIGNS[campaign])
    if profile:
        if profile not in PROFILES:raise ValueError(f'unknown profile {profile}')
        return closure(PROFILES[profile])
    return closure(CAMPAIGNS['deep'])

def run(target:Path,cfg:Config,*,profile:str|None=None,campaign:str|None=None,levels:list[str]|None=None,allow_exec:bool=False,repo_root:Path|None=None,interop_evidence:Path|None=None,jobs:int|None=None,fail_fast:bool|None=None):
    repo_root=(repo_root or Path(__file__).resolve().parents[1]).resolve();target=target.resolve();scan_root=target if target.is_dir() else target.parent
    rid=run_id();control=cfg.control;current=control/'current';archive=control/'runs'/rid
    if current.exists():shutil.rmtree(current)
    current.mkdir(parents=True,exist_ok=True)
    started=utc_now();selected=_select(profile,campaign,levels)
    effective=current/'effective_config.json';write_json(effective,cfg.data)
    max_target=int(cfg.data.get('max_target_files',500000) or 500000)
    before,fp_limit=fingerprint_tree(target,exclude_roots=(cfg.control,),max_files=max_target)
    # Discover JSON once per run. Isolated workers load this transient cache instead
    # of walking/parsing a large GitHub collection independently for every level.
    inventory=discover(target,max_files=int(cfg.data.get('max_json_files',100000) or 100000))
    cache_dir=control/'.cache'/rid;cache_dir.mkdir(parents=True,exist_ok=True)
    inventory_cache=cache_dir/'inventory.json';write_json(inventory_cache,inventory_to_data(inventory,scan_root))
    try:os.chmod(inventory_cache,0o600)
    except OSError:pass
    ex=cfg.data.get('execution',{});max_jobs=max(1,min(int(jobs or ex.get('max_parallel',4) or 1),16));ff=ex.get('fail_fast',False) if fail_fast is None else fail_fast
    pending=set(selected);results={};active={};pool=ThreadPoolExecutor(max_workers=max_jobs)

    def launch(lid):
        meta=LEVELS[lid];level_dir=current/'levels'/lid;level_dir.mkdir(parents=True,exist_ok=True);out=level_dir/'result.json'
        cmd=[sys.executable,'-m','kristaldiag.worker','--level',lid,'--target',str(target),'--repo-root',str(repo_root),'--config',str(effective),'--control-dir',str(cfg.control),'--run-id',rid,'--output',str(out),'--inventory-cache',str(inventory_cache)]
        if profile:cmd+=['--profile',profile]
        if allow_exec:cmd+=['--allow-exec']
        if interop_evidence:cmd+=['--interop-evidence',str(interop_evidence.resolve())]
        timeout=int(meta.get('timeout_seconds') or ex.get('default_timeout_seconds',120))
        started_mono=time.monotonic()
        try:
            if os.environ.get('KRISTALDIAG_TEST_IN_PROCESS')=='1' or ex.get('isolate_levels') is False:
                from .worker import execute_level
                data=execute_level(level=lid,target=target,repo=repo_root,config_path=effective,control_dir=cfg.control,run_id=rid,output=out,profile=profile,allow_exec=allow_exec,interop_evidence=interop_evidence,inventory_cache=inventory_cache)
                cp=None
            else:
                env=dict(os.environ);env['PYTHONPATH']=str(repo_root)+(os.pathsep+env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
                cp=subprocess.run(cmd,cwd=str(scan_root),env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',timeout=timeout,shell=False,check=False)
                if out.is_file():data=read_json(out)
                else:
                    now=utc_now();v='INFRA_ERROR' if cp.returncode!=0 else 'ERROR'
                    data=LevelResult(lid,meta['name'],v,[Finding(f'{lid}-WORKER','ERROR','diagnostics','Isolated level worker did not produce result.json.',evidence={'returncode':cp.returncode,'stdout_tail':(cp.stdout or '')[-8000:],'stderr_tail':(cp.stderr or '')[-8000:]})],started_at=now,ended_at=now,duration_seconds=time.monotonic()-started_mono).to_dict(run_id=rid,target_root=str(target),profile=profile)
                    write_json(out,data)
        except subprocess.TimeoutExpired as e:
            now=utc_now();data=LevelResult(lid,meta['name'],'INFRA_ERROR',[Finding(f'{lid}-TIMEOUT','INFRA_ERROR','diagnostics',f'Isolated level exceeded timeout of {timeout}s.',evidence={'timeout_seconds':timeout})],started_at=now,ended_at=now,duration_seconds=time.monotonic()-started_mono).to_dict(run_id=rid,target_root=str(target),profile=profile);write_json(out,data)
        return data

    try:
        while pending or active:
            progressed=False
            # Resolve levels whose selected dependencies are final.
            for lid in [x for x in selected if x in pending]:
                deps=[d for d in LEVELS[lid].get('depends_on',[]) if d in selected]
                if not all(d in results for d in deps):continue
                hard={d:results[d]['verdict'] for d in deps if results[d]['verdict'] in HARD_DEP_BLOCK}
                if hard:
                    data=_blocked(lid,rid,target,hard,profile);results[lid]=data;write_json(current/'levels'/lid/'result.json',data);pending.remove(lid);progressed=True;continue
                meta=LEVELS[lid]
                if not meta.get('parallel_safe',True):
                    if active:continue
                    fut=pool.submit(launch,lid);active[fut]=lid;pending.remove(lid);progressed=True;break
                if any(not LEVELS[x].get('parallel_safe',True) for x in active.values()):continue
                if len(active)<max_jobs:
                    fut=pool.submit(launch,lid);active[fut]=lid;pending.remove(lid);progressed=True
            done=[f for f in active if f.done()]
            if not done and active and not progressed:
                # Block until at least one worker completes.
                while not done:
                    time.sleep(0.02);done=[f for f in active if f.done()]
            for f in done:
                progressed=True
                lid=active.pop(f)
                try:data=f.result()
                except Exception as e:
                    now=utc_now();data=LevelResult(lid,LEVELS[lid]['name'],'INFRA_ERROR',[Finding(f'{lid}-SCHEDULER','INFRA_ERROR','diagnostics',f'Level scheduler failure: {type(e).__name__}: {e}')],started_at=now,ended_at=now).to_dict(run_id=rid,target_root=str(target),profile=profile)
                results[lid]=data
                if ff and data['verdict'] in {'FAIL','BLOCKED','ERROR','INFRA_ERROR','CONFIG_ERROR'}:
                    for rem in list(pending):
                        b=_blocked(rem,rid,target,{'fail_fast':data['verdict']},profile);results[rem]=b;write_json(current/'levels'/rem/'result.json',b);pending.remove(rem)
            if pending and not active and not progressed:
                # Dependency graph error / impossible scheduling.
                for rem in list(pending):
                    b=_blocked(rem,rid,target,{'scheduler':'unresolved dependencies'},profile);results[rem]=b;write_json(current/'levels'/rem/'result.json',b);pending.remove(rem)
    finally:
        pool.shutdown(wait=True,cancel_futures=True)
        try:shutil.rmtree(cache_dir)
        except OSError:pass

    ordered=[results[x] for x in selected if x in results]
    k14=_k14(ordered,profile,cfg);k14d=k14.to_dict(run_id=rid,target_root=str(target),profile=profile);ordered.append(k14d);write_json(current/'levels/K14/result.json',k14d)
    after,fp_limit_after=fingerprint_tree(target,exclude_roots=(cfg.control,),max_files=max_target);mutation={k:{'before':before.get(k),'after':after.get(k)} for k in sorted(set(before)|set(after)) if before.get(k)!=after.get(k)}
    final=k14d['verdict']
    if fp_limit or fp_limit_after:
        final='ERROR';k14d['verdict']='ERROR';k14d['findings'].append(Finding('K14-FINGERPRINT-004','ERROR','integrity','Target fingerprint exceeded max_target_files; read-only mutation guarantee is incomplete.',evidence={'max_target_files':max_target,'before_limit_reached':fp_limit,'after_limit_reached':fp_limit_after},remediation='Increase max_target_files or narrow the diagnostic target.').to_dict());write_json(current/'levels/K14/result.json',k14d);ordered[-1]=k14d
    if mutation and (profile is not None or not ex.get('allow_target_mutation',False)):
        final='ERROR';k14d['verdict']='ERROR';k14d['findings'].append(Finding('K14-MUTATION-003','ERROR','integrity','Diagnostic target changed while KristalDiag was running.',evidence=mutation,impact='Evidence cannot be trusted as a read-only qualification.').to_dict());write_json(current/'levels/K14/result.json',k14d);ordered[-1]=k14d
    counts={}
    for r in ordered:counts[r['verdict']]=counts.get(r['verdict'],0)+1
    # Reuse the run inventory for target-kind labeling; do not rescan a large collection.
    inv=inventory
    summary={'schema':SUMMARY_SCHEMA,'tool':'KristalDiag','tool_version':VERSION,'kristal_standard_target':STANDARD_TARGET,'run_id':rid,'target_root':str(target),'target_kind':target_kind(inv),'profile':profile,'campaign':campaign,'started_at':started,'ended_at':utc_now(),'verdict':final,'counts':counts,'levels':[{'id':r['level_id'],'name':r['level_name'],'verdict':r['verdict'],'result':f"levels/{r['level_id']}/result.json"} for r in ordered]}
    verdict={'schema':VERDICT_SCHEMA,'tool':'KristalDiag','tool_version':VERSION,'kristal_standard_target':STANDARD_TARGET,'run_id':rid,'subject':{'target_root':str(target),'kind':summary['target_kind']},'profile':profile,'campaign':campaign,'verdict':final,'qualification_only':True,'authority_granted':False,'required_levels':k14d.get('metadata',{}).get('required_levels',[]),'evidence_root':'levels/','issued_at':utc_now()}
    write_reports(current,summary,ordered,verdict)
    hashes={}
    for p in sorted(current.rglob('*')):
        if p.is_file() and p.name!='evidence-manifest.json':hashes[p.relative_to(current).as_posix()]=sha256_file(p)
    write_json(current/'evidence-manifest.json',{'schema':'kristaldiag.evidence-manifest.v1','run_id':rid,'tool_version':VERSION,'files':hashes})
    safe_copytree(current,archive);write_json(control/'current-run.json',{'run_id':rid,'path':str(archive),'verdict':final,'profile':profile,'campaign':campaign})
    return summary,exit_code(final),current
