from __future__ import annotations
import hashlib,json,os,re,subprocess,tempfile,zipfile
from pathlib import Path
from .models import Finding,LevelResult
from .utils import utc_now,relpath,sha256_file,read_json
from .verdicts import combine
from .manifest import LEVELS

MD_LINK=re.compile(r'\[[^\]]*\]\(([^)]+)\)')

def _f(fid,v,c,m,**kw):return Finding(fid,v,c,m,**kw)
def _result(level,fs,meta=None,s=None):return LevelResult(level,LEVELS[level]['name'],combine([x.verdict for x in fs]) if fs else 'SKIP',fs,[],s or utc_now(),utc_now(),0.0,meta or {})

def r00(ctx):
    s=utc_now();fs=[];root=ctx.scan_root;broken=[];checked=0
    if root.is_dir():
        for p in root.rglob('*.md'):
            if any(part in {'.git','.kristaldiag','.levelupdiag','node_modules','.venv','venv','dist','build','site'} for part in p.parts):continue
            try:text=p.read_text(encoding='utf-8')
            except Exception:continue
            for raw in MD_LINK.findall(text):
                link=raw.strip().split('#',1)[0]
                if not link or link.startswith(('http://','https://','mailto:','#','data:')):continue
                if link.startswith('<') and link.endswith('>'):link=link[1:-1]
                q=(p.parent/link).resolve(strict=False);checked+=1
                if not q.exists():broken.append({'file':relpath(p,root),'link':raw})
    fs.append(_f('R00-LINKS-001','FAIL' if broken else 'PASS','docs','Local Markdown links are resolvable.' if not broken else 'Broken local Markdown links were found.',evidence=broken[:100] if broken else {'checked':checked}))
    mk=(root/'mkdocs.yml') if root.is_dir() else None
    if mk and mk.is_file():
        if not ctx.allow_exec:
            fs.append(_f('R00-MKDOCS-002','SKIP','docs','mkdocs.yml exists but strict docs execution is disabled; static link checks still ran.',remediation='Use --allow-exec to run mkdocs build --strict.'))
        else:
            try:
                cp=subprocess.run([os.environ.get('PYTHON',os.sys.executable),'-m','mkdocs','build','--strict','--site-dir',str(ctx.config.control/'mkdocs-site')],cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',timeout=180,shell=False,check=False)
                fs.append(_f('R00-MKDOCS-002','PASS' if cp.returncode==0 else 'FAIL','docs','Strict MkDocs build passes.' if cp.returncode==0 else 'Strict MkDocs build fails.',evidence=(cp.stdout+cp.stderr)[-6000:]))
            except Exception as e:fs.append(_f('R00-MKDOCS-002','INFRA_ERROR','docs','Strict MkDocs build could not be executed.',evidence=f'{type(e).__name__}: {e}'))
    return _result('R00',fs,s=s)

def _snapshot_zip(root:Path,out:Path):
    excludes={'.git','.kristaldiag','.levelupdiag','node_modules','.venv','venv','__pycache__','dist','build','site'}
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(root.rglob('*'),key=lambda x:x.relative_to(root).as_posix()):
            if not p.is_file() or p.is_symlink():continue
            rel=p.relative_to(root)
            if any(x in excludes for x in rel.parts):continue
            info=zipfile.ZipInfo(rel.as_posix(),date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(0o100644&0xFFFF)<<16
            z.writestr(info,p.read_bytes())

def r01(ctx):
    s=utc_now();fs=[];root=ctx.scan_root
    if not root.is_dir():return _result('R01',[_f('R01-ROOT-000','SKIP','reproducibility','Archive reproducibility applies to repository targets.')],s=s)
    with tempfile.TemporaryDirectory(prefix='kristaldiag-r01-') as td:
        a=Path(td)/'a.zip';b=Path(td)/'b.zip';_snapshot_zip(root,a);_snapshot_zip(root,b);ha=sha256_file(a);hb=sha256_file(b)
        fs.append(_f('R01-SNAPSHOT-001','PASS' if ha==hb else 'FAIL','reproducibility','Two independent deterministic diagnostic snapshots are byte-identical.' if ha==hb else 'Deterministic diagnostic snapshot bytes differ.',evidence={'sha_a':ha,'sha_b':hb}))
    manifest=root/'REPO_MANIFEST.json'
    if manifest.is_file():
        try:
            d=read_json(manifest);files=d.get('files') if isinstance(d,dict) else None;bad=[]
            if isinstance(files,dict):
                for rel,hx in files.items():
                    p=root/rel
                    if not p.is_file():bad.append({'path':rel,'reason':'missing'})
                    else:
                        expected=hx.get('sha256') if isinstance(hx,dict) else hx
                        if isinstance(expected,str) and len(expected.replace('sha256:',''))>=64 and sha256_file(p)!=expected.replace('sha256:',''):
                            bad.append({'path':rel,'reason':'hash_mismatch'})
                fs.append(_f('R01-MANIFEST-002','FAIL' if bad else 'PASS','reproducibility','Repository manifest matches tracked files.' if not bad else 'Repository manifest mismatches current files.',evidence=bad[:100] if bad else {'entries':len(files)}))
            else:fs.append(_f('R01-MANIFEST-002','WARN','reproducibility','REPO_MANIFEST.json exists but is not in a recognized hash-map form.'))
        except Exception as e:fs.append(_f('R01-MANIFEST-002','WARN','reproducibility','REPO_MANIFEST.json could not be interpreted.',evidence=f'{type(e).__name__}: {e}'))
    return _result('R01',fs,s=s)

def r02(ctx):
    s=utc_now();fs=[];root=ctx.scan_root
    if not root.is_dir() or not (root/'.git').exists():return _result('R02',[_f('R02-GIT-000','SKIP','release_identity','Target is not a Git worktree; Git release identity is not applicable to this evidence.')],s=s)
    def git(*args):
        cp=subprocess.run(['git','-C',str(root),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',timeout=15,check=False)
        return cp.returncode,cp.stdout.strip(),cp.stderr.strip()
    rc,head,_=git('rev-parse','HEAD');rc2,status,_=git('status','--porcelain=v1')
    fs.append(_f('R02-HEAD-001','PASS' if rc==0 else 'BLOCKED','release_identity','Git HEAD resolved.' if rc==0 else 'Git HEAD could not be resolved.',evidence={'head':head or None}))
    fs.append(_f('R02-CLEAN-002','WARN' if status else 'PASS','release_identity','Git worktree is dirty.' if status else 'Git worktree is clean.',evidence=status.splitlines()[:100] if status else None))
    version_file=root/'VERSION'
    if version_file.is_file():
        version=version_file.read_text(encoding='utf-8').strip();rc3,tag,_=git('tag','--points-at','HEAD');tags=tag.splitlines() if tag else []
        matched=any(t==f'v{version}' or t==version for t in tags)
        fs.append(_f('R02-TAG-003','PASS' if matched else 'WARN','release_identity','HEAD has a tag matching VERSION.' if matched else 'No tag matching VERSION points at HEAD.',evidence={'version':version,'head_tags':tags}))
    return _result('R02',fs,s=s)

def r03(ctx):
    s=utc_now();fs=[];states=ctx.inv.get('kristal_state')
    signed=0;bad=[]
    for a in states:
        sig=a.data.get('signatures')
        if sig:
            signed+=1
            if not isinstance(sig,list):bad.append({'path':a.rel,'reason':'signatures_not_array'})
    if bad:fs.append(_f('R03-SIGNATURES-001','FAIL','signature_trust','Signature surfaces are malformed.',evidence=bad))
    elif signed:fs.append(_f('R03-SIGNATURES-001','PASS','signature_trust','Signed portable states expose structurally recognizable signature arrays.',evidence={'signed_states':signed}))
    else:fs.append(_f('R03-SIGNATURES-001','SKIP','signature_trust','No signed portable state is present; cryptographic trust is not claimed by this diagnostic.'))
    if ctx.driver and (ctx.driver.get('actions') or {}).get('self_test'):
        fs.append(_f('R03-DRIVER-002','PASS' if ctx.allow_exec else 'SKIP','signature_trust','Trusted implementation driver is available.' if ctx.allow_exec else 'Implementation driver exists but target execution is disabled.'))
    return _result('R03',fs,s=s)

def r04(ctx):
    s=utc_now();fs=[]
    from .profiles import PROFILES
    from .manifest import LEVELS
    unknown={p:[x for x in ls if x not in LEVELS] for p,ls in PROFILES.items()};unknown={k:v for k,v in unknown.items() if v}
    fs.append(_f('R04-PROFILES-001','FAIL' if unknown else 'PASS','contract_consistency','All conformance profiles reference known diagnostic levels.' if not unknown else 'Conformance profiles reference unknown levels.',evidence=unknown or {'profiles':list(PROFILES)}))
    cm=Path(__file__).resolve().parent/'resources'/'contract-manifest.json'
    try:
        d=read_json(cm);bad=[];base=cm.parent
        for rel,hx in (d.get('files') or {}).items():
            p=base/rel
            if not p.is_file() or sha256_file(p)!=hx:bad.append(rel)
        fs.append(_f('R04-CONTRACTS-002','FAIL' if bad else 'PASS','contract_consistency','Vendored contract/TCK mirror hashes are consistent.' if not bad else 'Vendored contract/TCK mirror drift detected.',evidence=bad or {'entries':len(d.get('files') or {})}))
    except Exception as e:fs.append(_f('R04-CONTRACTS-002','ERROR','contract_consistency','Contract manifest could not be verified.',evidence=f'{type(e).__name__}: {e}'))
    return _result('R04',fs,s=s)

RELEASE_CHECKS={'R00':r00,'R01':r01,'R02':r02,'R03':r03,'R04':r04}
