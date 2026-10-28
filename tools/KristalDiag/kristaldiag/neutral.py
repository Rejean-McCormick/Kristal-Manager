from __future__ import annotations
import importlib.util, os, platform, re, shutil, subprocess, sys
from pathlib import Path
from .models import Finding,LevelResult
from .utils import utc_now,relpath,sha256_file
from .commands import run_command
from .manifest import LEVELS

MERGE_MARKERS=('<<<<<<<','=======','>>>>>>>')
SURFACES={
 'pyproject.toml':['python'],'requirements.txt':['python'],'package.json':['node'],'Cargo.toml':['cargo'],'go.mod':['go'],
 'pom.xml':['java','mvn'],'build.gradle':['java'],'build.gradle.kts':['java'],'composer.json':['php'],'Gemfile':['ruby'],
 'mix.exs':['elixir'],'Makefile':['make'],'CMakeLists.txt':['cmake']}
LOCK_NAMES={'uv.lock','poetry.lock','Pipfile.lock','package-lock.json','pnpm-lock.yaml','yarn.lock','bun.lockb','Cargo.lock','go.sum','composer.lock','Gemfile.lock'}
SECRET_PATTERNS=[
 ('private-key',re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----')),
 ('github-token',re.compile(r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b')),
 ('github-fine-grained-token',re.compile(r'\bgithub_pat_[A-Za-z0-9_]{30,}\b')),
 ('aws-access-key',re.compile(r'\bAKIA[0-9A-Z]{16}\b')),
 ('generic-secret-assignment',re.compile(r'(?i)\b(?:api[_-]?key|secret|access[_-]?token)\s*[:=]\s*[\'\"]?[A-Za-z0-9_./+=-]{20,}')),
]
SENSITIVE_NAMES={'.env','id_rsa','id_dsa','id_ecdsa','id_ed25519'}

def _f(fid,verdict,category,message,**kw): return Finding(fid,verdict,category,message,**kw)
def _result(level,findings,metadata=None,started=None):
    from .verdicts import combine
    return LevelResult(level,LEVELS[level]['name'],combine([x.verdict for x in findings]) if findings else 'SKIP',findings,[],started or utc_now(),utc_now(),0.0,metadata or {})

def _iter_files(ctx,max_files=None):
    root=ctx.scan_root;cfg=ctx.config.data;scan=cfg.get('scan',{});limit=int(max_files or scan.get('max_files',20000));exclude=set(scan.get('exclude_dirs',[]));count=0
    if root.is_file():
        yield root,root.name;return
    for base,dirs,files in os.walk(root,followlinks=False):
        b=Path(base);dirs[:]=[d for d in dirs if d not in exclude and not (b/d).is_symlink()]
        for name in sorted(files):
            p=b/name
            if p.is_symlink(): continue
            yield p,relpath(p,root);count+=1
            if count>=limit:return

def _bounded_text(p:Path,max_bytes:int):
    try:
        if p.stat().st_size>max_bytes:return None
        raw=p.read_bytes()
        if b'\x00' in raw:return None
        return raw.decode('utf-8','replace')
    except Exception:return None

def n00(ctx):
    s=utc_now();fs=[]
    fs.append(_f('N00-PYTHON-001','PASS' if sys.version_info>=(3,11) else 'CONFIG_ERROR','diagnostics',f'Python {sys.version.split()[0]} '+('is supported.' if sys.version_info>=(3,11) else 'is unsupported.'),remediation=None if sys.version_info>=(3,11) else 'Use Python 3.11 or newer.'))
    missing=[]
    for mod in ('kristaldiag.checks','kristaldiag.neutral','kristaldiag.evidence','kristaldiag.schemas'):
        if importlib.util.find_spec(mod) is None:missing.append(mod)
    fs.append(_f('N00-MODULES-002','CONFIG_ERROR' if missing else 'PASS','diagnostics','Required diagnostic modules are importable.' if not missing else 'Required diagnostic modules are missing.',evidence=missing or {'count':4}))
    req=['level-result.schema.json','summary.schema.json','conformance-verdict.schema.json']
    absent=[x for x in req if not (ctx.repo_root/'schemas'/x).is_file()]
    fs.append(_f('N00-SCHEMAS-003','CONFIG_ERROR' if absent else 'PASS','diagnostics','KristalDiag evidence schemas are present.' if not absent else 'KristalDiag evidence schemas are missing.',evidence=absent or {'count':len(req)}))
    return _result('N00',fs,started=s)

def _git_info(root:Path):
    if not (root/'.git').exists():return {'detected':False}
    def q(*args):
        cp=subprocess.run(['git','-C',str(root),*args],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',errors='replace',timeout=10,check=False)
        return cp.stdout.strip() if cp.returncode==0 else None
    return {'detected':True,'branch':q('rev-parse','--abbrev-ref','HEAD'),'commit':q('rev-parse','HEAD'),'dirty':bool(q('status','--porcelain'))}

def n01(ctx):
    s=utc_now();fs=[];target=ctx.target
    fs.append(_f('N01-TARGET-001','PASS' if target.exists() else 'CONFIG_ERROR','target','Target is available.' if target.exists() else 'Target does not exist.',path=str(target)))
    fs.append(_f('N01-RUNTIME-002','PASS','environment','Runtime platform detected.',evidence={'system':platform.system(),'release':platform.release(),'python':sys.version.split()[0]}))
    try:gi=_git_info(ctx.scan_root);fs.append(_f('N01-VCS-003','PASS','context','VCS context collected.',evidence=gi))
    except Exception as e:fs.append(_f('N01-VCS-003','WARN','context','VCS context could not be collected.',evidence=f'{type(e).__name__}: {e}'))
    control=ctx.config.control.resolve();inside=False
    try:control.relative_to(ctx.scan_root.resolve());inside=True
    except ValueError:pass
    fs.append(_f('N01-EVIDENCE-004','PASS','integrity','Evidence directory is inside the target but explicitly excluded from read-only fingerprinting.' if inside else 'Evidence directory is external to target tree.',evidence={'control':str(control),'target':str(ctx.scan_root),'excluded_from_fingerprint':True}))
    return _result('N01',fs,started=s)

def n02(ctx):
    s=utc_now();fs=[];scan=ctx.config.data.get('scan',{});limit=int(scan.get('max_files',20000));max_bytes=int(scan.get('max_file_bytes',1048576));count=0;ext={};bytes_total=0;unreadable=[]
    for p,rel in _iter_files(ctx,limit):
        count+=1;ext[p.suffix.lower() or '<none>']=ext.get(p.suffix.lower() or '<none>',0)+1
        try:bytes_total+=p.stat().st_size
        except OSError:unreadable.append(rel)
    fs.append(_f('N02-INVENTORY-001','PASS','inventory',f'Bounded repository inventory collected ({count} files).',evidence={'files':count,'bytes':bytes_total,'extensions':dict(sorted(ext.items(),key=lambda x:(-x[1],x[0]))[:30]),'max_file_bytes_for_text':max_bytes}))
    if count>=limit:fs.append(_f('N02-LIMIT-002','WARN','inventory','Inventory reached configured file limit.',evidence={'max_files':limit},remediation='Increase scan.max_files or narrow the target.'))
    if unreadable:fs.append(_f('N02-READ-003','WARN','inventory','Some files could not be stat-ed.',evidence=unreadable[:100]))
    return _result('N02',fs,metadata={'files_scanned':count,'bytes':bytes_total},started=s)

def n03(ctx):
    s=utc_now();fs=[];scan=ctx.config.data.get('scan',{});max_bytes=int(scan.get('max_file_bytes',1048576));large=int(scan.get('large_file_bytes',10485760));broken=[];merge=[];huge=[]
    root=ctx.scan_root
    for p,rel in _iter_files(ctx):
        try:
            if p.stat().st_size>large:huge.append({'path':rel,'bytes':p.stat().st_size})
        except OSError:continue
        txt=_bounded_text(p,max_bytes)
        if txt is not None and all(m in txt for m in MERGE_MARKERS):merge.append(rel)
    if root.is_dir():
        for base,dirs,files in os.walk(root,followlinks=False):
            for name in dirs+files:
                p=Path(base,name)
                if p.is_symlink() and not p.exists():broken.append(relpath(p,root))
    fs.append(_f('N03-SYMLINK-001','WARN' if broken else 'PASS','hygiene','Broken symbolic links detected.' if broken else 'No broken symbolic links detected.',evidence=broken[:100] if broken else None))
    fs.append(_f('N03-MERGE-002','WARN' if merge else 'PASS','hygiene','Possible unresolved merge markers detected.' if merge else 'No unresolved merge-marker pattern detected.',evidence=merge[:100] if merge else None))
    fs.append(_f('N03-LARGE-003','WARN' if huge else 'PASS','hygiene','Large repository files should be reviewed.' if huge else 'No files exceeded the large-file threshold.',evidence=huge[:100] if huge else None))
    return _result('N03',fs,started=s)

def n04(ctx):
    s=utc_now();fs=[];found=[];locks=[];candidates=set()
    for p,rel in _iter_files(ctx,10000):
        if p.name in SURFACES:found.append(rel);candidates.update(SURFACES[p.name])
        if p.name in LOCK_NAMES:locks.append(rel)
    avail={x:bool(shutil.which(x)) for x in sorted(candidates)};missing=[x for x,v in avail.items() if not v]
    fs.append(_f('N04-SURFACES-001','PASS','tooling','Project tooling surfaces discovered without executing them.',evidence={'manifests':found,'lock_files':locks,'availability':avail}))
    if missing:fs.append(_f('N04-CANDIDATES-002','WARN','tooling','Some inferred tools are not available on PATH; they are not assumed to be required.',evidence=missing))
    required=ctx.config.data.get('toolchain',{}).get('required',[]);rm=[x for x in required if not shutil.which(x)]
    fs.append(_f('N04-REQUIRED-003','BLOCKED' if rm else 'PASS','tooling','Configured required tools are missing.' if rm else 'Configured required tools are available.',evidence=rm or required))
    return _result('N04',fs,started=s)

def n05(ctx):
    s=utc_now();fs=[];vals=[v for v in ctx.config.data.get('validators',[]) if v.get('enabled',True)]
    if not vals:
        fs.append(_f('N05-DECLARED-001','PASS','validation','No external validators are declared; no target command was guessed or executed.'))
        return _result('N05',fs,started=s)
    if not ctx.allow_exec:
        fs.append(_f('N05-EXEC-002','BLOCKED','validation','External validators are declared but execution is disabled.',evidence={'validators':[v.get('id') for v in vals]},remediation='Re-run with --allow-exec only after reviewing the declared argv.'))
        return _result('N05',fs,started=s)
    ex=ctx.config.data.get('execution',{});limit=ex.get('capture_limit_kb',256)
    for v in vals:
        vid=v.get('id') or 'unnamed';required=bool(v.get('required',False));name=v.get('name') or vid
        if v.get('mutates_target',False) and not ex.get('allow_target_mutation',False):
            fs.append(_f(f'N05-{vid}-MUTATION','BLOCKED' if required else 'WARN','validation',f"Validator '{name}' declares target mutation while mutation is disabled."));continue
        if v.get('network',False) and not ex.get('allow_network',False):
            fs.append(_f(f'N05-{vid}-NETWORK','BLOCKED' if required else 'WARN','validation',f"Validator '{name}' requires network while network execution is disabled."));continue
        cwd=(ctx.scan_root/v.get('cwd','.')).resolve(strict=False)
        try:cwd.relative_to(ctx.scan_root.resolve())
        except ValueError:fs.append(_f(f'N05-{vid}-CWD','CONFIG_ERROR','validation',f"Validator '{name}' escapes target root.",evidence=str(cwd)));continue
        if not cwd.is_dir():fs.append(_f(f'N05-{vid}-CWD','CONFIG_ERROR','validation',f"Validator '{name}' working directory is invalid.",evidence=str(cwd)));continue
        try:r=run_command(v.get('command'),cwd=cwd,timeout_seconds=int(v.get('timeout_seconds',ex.get('default_timeout_seconds',120))),capture_limit_kb=limit,redact_output=ctx.config.data.get('redaction',{}).get('enabled',True))
        except Exception as e:fs.append(_f(f'N05-{vid}-RUN','BLOCKED' if required else 'WARN','validation',f"Validator '{name}' could not be launched.",evidence=f'{type(e).__name__}: {e}'));continue
        verdict='INFRA_ERROR' if r['timed_out'] else ('PASS' if r['exit_code']==0 else ('FAIL' if required else 'WARN'))
        fs.append(_f(f'N05-{vid}-RESULT',verdict,'validation',f"Validator '{name}' completed." if not r['timed_out'] else f"Validator '{name}' timed out.",evidence=r))
    return _result('N05',fs,started=s)

def n06(ctx):
    s=utc_now();fs=[];sec=ctx.config.data.get('security',{});scan=ctx.config.data.get('scan',{})
    if not sec.get('enabled',True):return _result('N06',[_f('N06-ENABLED-000','SKIP','security_hygiene','Security hygiene scan is disabled by configuration.')],started=s)
    patterns=list(SECRET_PATTERNS)
    for i,pat in enumerate(sec.get('additional_patterns',[])):
        try:patterns.append((f'custom-{i+1}',re.compile(pat)))
        except re.error as e:return _result('N06',[_f(f'N06-PATTERN-{i+1}','CONFIG_ERROR','security_hygiene','Invalid configured security regex.',evidence=str(e))],started=s)
    hits=[];names=[];max_files=int(scan.get('max_security_files',4000));max_bytes=min(int(scan.get('max_file_bytes',1048576)),1048576);scanned=0
    for p,rel in _iter_files(ctx,max_files):
        scanned+=1
        if p.name in SENSITIVE_NAMES:names.append(rel)
        txt=_bounded_text(p,max_bytes)
        if txt is None:continue
        for pid,rx in patterns:
            m=rx.search(txt)
            if m:hits.append({'pattern':pid,'path':rel,'line':txt.count('\n',0,m.start())+1});break
    fs.append(_f('N06-FILENAMES-001','WARN' if names else 'PASS','security_hygiene','Potentially sensitive filenames require review.' if names else 'No high-risk sensitive filenames were found.',evidence=names[:100] if names else None))
    fs.append(_f('N06-SECRETS-002','WARN' if hits else 'PASS','security_hygiene','Potential secret material matched conservative patterns; values were not copied into evidence.' if hits else 'No configured secret pattern matched.',evidence=hits[:100] if hits else None,remediation='Rotate exposed credentials and remove them from history if any match is genuine.' if hits else None))
    return _result('N06',fs,metadata={'files_scanned':scanned,'potential_secret_hits':len(hits)},started=s)

NEUTRAL_CHECKS={'N00':n00,'N01':n01,'N02':n02,'N03':n03,'N04':n04,'N05':n05,'N06':n06}
