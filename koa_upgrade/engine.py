"""Non-destructive kOA Kristal local update orchestrator.

All evidence is observational and no publication or maturity promotion occurs.
One-way flow: plan -> stage -> validate -> optional diag -> explicit install -> rollback.
Only Python standard library; consumes external owner tools without vendoring.
"""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
from zipfile import ZipFile

DEFAULTS = {
    'kristal': r'C:\mycode\Kristal\locals\Kristal-kOA-Ecosystem',
    'manager': r'C:\mycode\Kristal\Kristal-Manager',
    'kristalizer': r'C:\mycode\Kristal\Kristalizer',
    'kit': r'C:\mycode\Kristal\Kristal-Authoring-Kit',
    'framework': r'C:\mycode\Kristal\Kristal-Framework',
    'kristaldiag': r'C:\mycode\Kristal\KristalDiag',
    'koadiag': r'C:\mycode\kOA_Digital_Ecosystem\kOADiag',
    'c0': r'C:\mycode\kOA_Digital_Ecosystem\kOA_Digital_Ecosystem',
    'audit': r'C:\mycode\kOA-Digital-Ecosystem-GitHub-Audit',
    'arketype': r'C:\mycode\Kristal\Arketype',
    'integration_pack': r'C:\mycode\Kristal\Kristal-Integration-Pack',
}
ROOT = Path(__file__).resolve().parent
BASELINE = ROOT / 'snapshot.lock.json'
IGNORED = {'.git', '__pycache__', '.pytest_cache', '.mypy_cache', '.tox'}
MAX_CANDIDATE_BYTES = 500 * 1024 * 1024
MAX_FILES = 100000

class UpgradeError(RuntimeError):
    pass

def now():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

def sha(path:Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def dump(path, value):
    path=Path(path);path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    tmp.replace(path)

def resolve_conf(conf_path=None):
    custom=load(conf_path) if conf_path else {}
    if not isinstance(custom,dict):raise UpgradeError('Configuration: objet JSON attendu')
    paths={k:Path(custom.get(k,v)).expanduser().resolve() for k,v in DEFAULTS.items()}
    workspace=custom.get('workspace') or str(paths['manager']/'koa_upgrade_runs')
    paths['workspace']=Path(workspace).expanduser().resolve()
    return paths

def walk(root:Path):
    if not root.exists():return {}
    if root.is_symlink():raise UpgradeError('Un chemin racine symbolique est interdit: '+str(root))
    result={}
    for parent,dirs,files in os.walk(root):
        base=Path(parent)
        for d in dirs[:]:
            p=base/d
            if p.is_symlink():raise UpgradeError('Lien symbolique dans source: '+str(p))
            if d in IGNORED:dirs.remove(d)
        for name in files:
            f=base/name
            if f.is_symlink():raise UpgradeError('Lien symbolique dans source: '+str(f))
            rel=f.relative_to(root).as_posix()
            result[rel]=sha(f)
    return result

def fingerprint(files:dict):
    b='\n'.join(k+' '+v for k,v in sorted(files.items())).encode('utf8')
    return hashlib.sha256(b).hexdigest()

def inventory(conf):
    baseline=load(BASELINE)
    rows=[]
    for key in DEFAULTS:
        path=conf[key]
        entry=baseline['sources'].get(key,{})
        sentinels=entry.get('sentinels',{})
        checks=[]
        for name, expected in sentinels.items():
            f=path/name
            actual=sha(f) if f.is_file() else None
            checks.append({'file':name,'status':'MATCH' if actual==expected else 'MISSING' if actual is None else 'CHANGED'})
        version=''
        if (path/'VERSION').is_file():version=(path/'VERSION').read_text('utf-8-sig').strip()
        rows.append({'key':key,'path':str(path),'exists':path.is_dir(),'version':version,
                     'snapshot_checks':checks})
    return {'format':'koa.upgrade.inventory.v1','observed_at':now(),'items':rows,
            'warning':'Snapshot fingerprints are not a maturity certification.'}

def choose_zip_root(names):
    files=[n for n in names if not n.endswith('/')]
    if not files:raise UpgradeError('Archive vide')
    # Full project ZIP may have one container directory or none; never accept arbitrary nesting.
    if 'kristal.workspace.json' in files and 'knowledge-base/tools/validate.py' in files:return ''
    roots=sorted({n.split('/')[0] for n in files})
    if len(roots)==1 and roots[0] not in ('.','..'):
        prefix=roots[0]+'/'
        if prefix+'kristal.workspace.json' in files and prefix+'knowledge-base/tools/validate.py' in files:return prefix
    raise UpgradeError('Archive candidate: racine de Kristal introuvable ou ambiguë')

def read_candidate(candidate:Path):
    if not candidate.is_file() or candidate.stat().st_size>MAX_CANDIDATE_BYTES:
        raise UpgradeError('ZIP candidat absent ou trop grand')
    with ZipFile(candidate) as z:
        infos=z.infolist()
        if len(infos)>MAX_FILES:raise UpgradeError('Archive trop volumineuse en nombres de fichiers')
        names=[i.filename for i in infos]
        if len(names)!=len(set(names)):raise UpgradeError('Entrées ZIP dupliquées')
        root=choose_zip_root(names)
        plan=[];total=0
        for i in infos:
            n=i.filename
            p=PurePosixPath(n)
            if p.is_absolute() or '..' in p.parts or '\\' in n or ':' in n or n.startswith('//'):
                raise UpgradeError('Chemin ZIP interdit: '+n)
            if stat.S_IFMT(i.external_attr>>16)==stat.S_IFLNK:
                raise UpgradeError('Lien symbolique ZIP interdit: '+n)
            if i.is_dir():continue
            if not n.startswith(root):raise UpgradeError('ZIP avec fichier hors de la racine')
            rel=n[len(root):]
            if not rel or PurePosixPath(rel).parts[0] in IGNORED:continue
            total+=i.file_size
            if total>MAX_CANDIDATE_BYTES:raise UpgradeError('Taille décompressée excessive')
            plan.append((i,rel))
        return root,plan

def stage(conf,candidate:Path):
    target=conf['kristal']; work=conf['workspace'];candidate=candidate.expanduser().resolve()
    if not target.is_dir() or not (target/'kristal.workspace.json').is_file():
        raise UpgradeError('Kristal actif introuvable: '+str(target))
    for path in (work,candidate.parent):
        if target == path or target.is_relative_to(path):
            # It is safe for the candidate zip to be elsewhere in Kristal's parent,
            # but work itself cannot live inside the source workspace.
            if path==work:raise UpgradeError('Travail interdit dans le dossier source')
    # Fail closed if the files controlling the historical Kristal differ from
    # the SmartDump baseline. This protects newer local edits from a stale overlay.
    lock=load(BASELINE)
    for relative, expected in lock['sources']['kristal']['sentinels'].items():
        observed=target/relative
        if not observed.is_file() or sha(observed)!=expected:
            raise UpgradeError('Kristal local diverge du SmartDump: '+relative+'; nouveau snapshot requis')
    current=walk(target)
    with ZipFile(candidate) as z:
        _,entries=read_candidate(candidate)
        if not entries:raise UpgradeError('Aucun fichier candidate')
        # Collect content bytes once into staging with no traversal and no deletions.
        buildid='run-'+now();run=work/'runs'/buildid;root=run/'staging'/'Kristal-kOA-Ecosystem'
        if run.exists():raise UpgradeError('Collision de campagne')
        root.parent.mkdir(parents=True,exist_ok=False)
        try:
            shutil.copytree(target,root,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache'),symlinks=False)
            changes=[]
            for info,rel in entries:
                p=root.joinpath(*PurePosixPath(rel).parts)
                p.parent.mkdir(parents=True,exist_ok=True)
                old=sha(p) if p.is_file() else None
                raw=z.read(info)
                new=hashlib.sha256(raw).hexdigest()
                if old==new:continue
                p.write_bytes(raw)
                changes.append({'file':rel,'action':'MODIFIED' if old else 'ADDED','before':old,'after':new})
            if not (root/'kristal.workspace.json').is_file():raise UpgradeError('Candidate workspace invalide')
            meta={'format':'koa.upgrade.campaign.v1','id':buildid,'created_at':now(),
                  'target':str(target),'candidate_sha256':sha(candidate),'candidate_filename':candidate.name,
                  'source_snapshot_sha256':fingerprint(current),'changed_files':changes,
                  'note':'No source or validated evidence modified; staging is a working copy.',
                  'validation':'NOT_RUN','diagnostics':'NOT_RUN'}
            dump(run/'campaign.json',meta)
        except Exception:
            shutil.rmtree(run,ignore_errors=True)
            raise
    return {'campaign':buildid,'stage':str(root),'changed_files':len(changes),'run_dir':str(run)}

def run_checked(argv,cwd,timeout=600,env=None):
    try:
        p=subprocess.run([str(x) for x in argv],cwd=str(cwd),text=True,encoding='utf-8',errors='replace',
                         capture_output=True,timeout=timeout,env=env,shell=False)
        return {'command':[str(x) for x in argv],'returncode':p.returncode,
                'stdout':p.stdout[-20000:],'stderr':p.stderr[-12000:]}
    except (OSError,subprocess.TimeoutExpired) as e:
        return {'command':[str(x) for x in argv],'returncode':-1,'stdout':'','stderr':str(e)}

def campaign(conf,runid):
    if not runid.startswith('run-') or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for c in runid):
        raise UpgradeError('Identifiant de campagne invalide')
    run=conf['workspace']/'runs'/runid
    meta=load(run/'campaign.json')
    stagepath=run/'staging'/'Kristal-kOA-Ecosystem'
    if meta['id']!=runid or meta['target']!=str(conf['kristal']) or not stagepath.is_dir():
        raise UpgradeError('Campagne incompatible avec la configuration')
    return run,meta,stagepath

def validate(conf,runid):
    run,meta,staging=campaign(conf,runid)
    steps=[]
    if not (staging/'knowledge-base/tools/build.py').is_file() or not (staging/'knowledge-base/tools/validate.py').is_file():
        raise UpgradeError('Constructeur historique absent du staging')
    # This executes trusted user-selected Kristal code, isolated to staging,
    # NOT a restricted sandbox. Only run on known, trusted snapshots.
    build=run_checked([sys.executable,'knowledge-base/tools/build.py'],staging,timeout=900);steps.append(build)
    if build['returncode']==0:
        check=run_checked([sys.executable,'knowledge-base/tools/validate.py'],staging,timeout=450);steps.append(check)
    else:check={'returncode':-1,'stderr':'Builder failed'}
    manager=conf['manager']
    if (manager/'kristal_manager/__main__.py').is_file() and check['returncode']==0:
        env=dict(os.environ);env['PYTHONPATH']=str(manager)+os.pathsep+env.get('PYTHONPATH','')
        observed=run_checked([sys.executable,'-m','kristal_manager','verify',staging],manager,timeout=450,env=env)
        steps.append(observed)
    else:observed={'returncode':-2,'stderr':'Manager unavailable or native validation failed'}
    # Manager is independently descriptive, and can return attention (3).
    assessment=None
    try:assessment=json.loads(observed.get('stdout') or '{}')
    except ValueError:pass
    result={'format':'koa.upgrade.validation.v1','campaign':runid,'timestamp':now(),
            'native_ok':build['returncode']==0 and check['returncode']==0,
            'manager_code':observed['returncode'],'manager_assessment':assessment,'staging_files_sha256':fingerprint(walk(staging)),
            'steps':steps,'qualification':'NOT_ESTABLISHED',
            'warning':'Manager checks do not certify maturity, v11 migration or production.'}
    dump(run/'validation.json',result)
    meta['validation']='NATIVE_PASSED' if result['native_ok'] else 'FAILED';dump(run/'campaign.json',meta)
    return result

def diagnose(conf,runid):
    run,meta,staging=campaign(conf,runid)
    manager=conf['manager']
    if not (manager/'kristal_manager/unified/cli.py').is_file():raise UpgradeError('Manager Centre unifie non trouve')
    if meta['validation']!='NATIVE_PASSED':raise UpgradeError('Validation native requise avant diagnostics')
    # Run only against a parent containing this ONE staged Kristal, not all of locals.
    env=dict(os.environ);env['PYTHONPATH']=str(manager)+os.pathsep+env.get('PYTHONPATH','')
    result=run_checked([sys.executable,'-m','kristal_manager.unified.cli','scan-global',
                        '--root',staging.parent,'--out',run/'reports','--avec-diag','--sans-catalogue'],
                       manager,timeout=1800,env=env)
    rec={'format':'koa.upgrade.diag-observation.v1','campaign':runid,'timestamp':now(),
         'status':'OBSERVED' if result['returncode']==0 else 'DIAGNOSTIC_ERROR',
         'result':result,'promotion':'NONE','reference_maturity_changed':False}
    dump(run/'diagnostic.json',rec)
    meta['diagnostics']=rec['status'];dump(run/'campaign.json',meta)
    return rec

def discovery_stale_only(validation):
    """Allow an explicit local install exception for one read-only Discovery warning.

    This is not a maturity qualification or repair. Any other issue, severity,
    readiness, or missing evidence fails closed. Independent technical validation
    must have succeeded. The install path still verifies staging/current hashes.
    """
    if validation.get('native_ok') is not True or validation.get('manager_code') != 3:
        return False
    a=validation.get('manager_assessment')
    if not isinstance(a,dict) or a.get('local_readiness')!='READY' or a.get('structural_status')!='PRESENT':
        return False
    if a.get('operational_result')!='ATTENTION_REQUIRED' or a.get('qualification')!='NOT_ESTABLISHED':
        return False
    if any(a.get(k)!='NOT_ESTABLISHED' for k in ('publication','activation','reader_authorization','hosting_verification')):
        return False
    fw=a.get('framework_state_verification')
    if not isinstance(fw,dict) or fw.get('status')!='NOT_EVALUATED':
        return False
    discovery=a.get('discovery')
    if not isinstance(discovery,dict) or discovery.get('status')!='stale' or discovery.get('integrity')!='mismatch':
        return False
    issues=a.get('issues')
    return (isinstance(issues,list) and len(issues)==1 and isinstance(issues[0],dict)
            and issues[0].get('code')=='DISCOVERY_STALE'
            and issues[0].get('scope')=='discovery'
            and issues[0].get('severity')=='warning')

def install(conf,runid,confirm=False,accept_legacy=False,accept_discovery=False):
    if not confirm:raise UpgradeError('Installation exige --confirm')
    run,meta,staging=campaign(conf,runid)
    vpath=run/'validation.json'
    if not vpath.is_file():raise UpgradeError('Validation absente')
    val=load(vpath)
    if not val.get('native_ok'):raise UpgradeError('Validation native non réussie')
    if val['manager_code']!=0:
        assessment=val.get('manager_assessment') or {}
        issue_codes={x.get('code') for x in assessment.get('issues',[]) if isinstance(x,dict)}
        legacy_only=(val['manager_code']==3 and assessment.get('local_readiness')=='LEGACY STATE'
                     and issue_codes=={'LOCAL_STATE_NOT_READY','DISCOVERY_STALE'}
                     and assessment.get('qualification')=='NOT_ESTABLISHED'
                     and assessment.get('framework_state_verification',{}).get('status')=='NOT_EVALUATED')
        # An independent, narrowly-scoped exception: native checks passed,
        # Manager READY/PRESENT, with the sole warning DISCOVERY_STALE.
        discovery_only=discovery_stale_only(val)
        if not ((accept_legacy and legacy_only) or (accept_discovery and discovery_only)):
            raise UpgradeError('Manager non validé (code '+str(val['manager_code'])+', '+str(assessment.get('operational_result'))+
                               '). Seules les exceptions précisément revues sont permises: LEGACY STATE (--accepter-heritage-v6)'
                               ' ou READY avec seul avertissement DISCOVERY_STALE (--accepter-discovery-perimee).')
    if meta.get('installed_at'):raise UpgradeError('Campagne déjà installée')
    if fingerprint(walk(staging))!=val['staging_files_sha256']:
        raise UpgradeError('Staging modifié depuis la validation')
    target=conf['kristal']
    if fingerprint(walk(target))!=meta['source_snapshot_sha256']:
        raise UpgradeError('Kristal actif modifié depuis la préparation. Nouvelle campagne obligatoire.')
    # Backup and swap on same parent/volume; rollback on any failure.
    backup=target.parent/('_'+target.name+'_backup_'+runid)
    if backup.exists():raise UpgradeError('Backup existe déjà: '+str(backup))
    try:
        target.rename(backup)
        try:staging.rename(target)
        except Exception:
            backup.rename(target)
            raise
    except Exception as e:raise UpgradeError('Installation non effectuée: '+str(e)) from e
    receipt={'format':'koa.upgrade.install.v1','campaign':runid,'date':now(),
             'target':str(target),'backup':str(backup),'installed_sha256':fingerprint(walk(target)),
             'original_sha256':meta['source_snapshot_sha256'],'promoted_evidence':False,
             'legacy_exception':bool(val['manager_code']!=0 and not discovery_stale_only(val)),
              'discovery_stale_exception':bool(discovery_stale_only(val)),
             'qualification':'NOT_ESTABLISHED' if val['manager_code']!=0 else 'OPERATIONAL_PRECHECK_ONLY'}
    dump(run/'install.json',receipt)
    meta['installed_at']=receipt['date'];dump(run/'campaign.json',meta)
    return receipt

def rollback(conf,runid,confirm=False):
    if not confirm:raise UpgradeError('Restauration exige --confirm')
    run,meta,_=campaign_for_rollback(conf,runid)
    receipt=load(run/'install.json');target=conf['kristal'];backup=Path(receipt['backup'])
    if not backup.is_dir():raise UpgradeError('Sauvegarde absente')
    if not target.is_dir() or fingerprint(walk(target))!=receipt['installed_sha256']:
        raise UpgradeError('Installation modifiée depuis; restauration automatique bloquée')
    retired=target.parent/('_'+target.name+'_retire_'+runid)
    if retired.exists():raise UpgradeError('Dossier de retrait existe')
    target.rename(retired)
    try:backup.rename(target)
    except Exception:
        retired.rename(target)
        raise
    result={'format':'koa.upgrade.rollback.v1','campaign':runid,'date':now(),
            'restored':str(target),'retired_new_version':str(retired), 'qualification_untouched':True}
    dump(run/'rollback.json',result)
    return result

def campaign_for_rollback(conf,runid):
    if not runid.startswith('run-') or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for c in runid):
        raise UpgradeError('Identifiant campagne invalide')
    run=conf['workspace']/'runs'/runid
    meta=load(run/'campaign.json')
    if meta['target']!=str(conf['kristal']):raise UpgradeError('Cible incompatible')
    return run,meta,None

def kit_status(conf):
    source=conf['kristalizer'];kit=conf['kit'];fw=conf['framework']
    if not (source/'kristalizer.py').is_file():raise UpgradeError('Kristalizer absent')
    cmd=[sys.executable,'kristalizer.py','kit-status','--kit',str(kit)]
    if fw.is_dir():cmd.extend(['--framework',str(fw)])
    return run_checked(cmd,source,timeout=180)
