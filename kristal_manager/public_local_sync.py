"""Preview and copy C3-verified private candidates into a LOCAL public checkout.

No Git add, commit, push, network request, signature or publication authority.
The human operator separately reviews C1/C2/rights and runs their own Git sync.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

from .core import ManagerError
from .publication_flow import _assert_checkout, _candidate, _legacy_zoology_stub, _validate_c3


def _digest(value: object) -> str:
    text=json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _reject_symlinks(root: Path) -> None:
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise ManagerError('Dossier kristals non régulier ou lien symbolique')
    if root.exists():
        for parent, dirs, names in os.walk(root,followlinks=False):
            for name in dirs+names:
                if (Path(parent)/name).is_symlink():
                    raise ManagerError('Lien symbolique interdit dans kristals: '+name)


def _index(root: Path) -> dict:
    try:
        return json.loads((root/'kristals/index.json').read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:
        raise ManagerError('Index C3 illisible') from exc


def _inspect(*, candidate: Path, checkout: Path, retire_zoology_stub: bool) -> dict:
    try:
        candidate=Path(candidate).expanduser().resolve(strict=True)
        checkout=Path(checkout).expanduser().resolve(strict=True)
    except OSError as exc:
        raise ManagerError('Le candidat et le dossier public local doivent exister') from exc
    if candidate==checkout or candidate.is_relative_to(checkout) or checkout.is_relative_to(candidate):
        raise ManagerError('Le candidat privé et kristal-public doivent être deux dossiers séparés')
    if not checkout.is_dir() or checkout.is_symlink() or not candidate.is_dir() or candidate.is_symlink():
        raise ManagerError('Dossiers non valides ou liens symboliques')
    # Git is used for READ-ONLY identity checks only; dirty C3-consistent local
    # changes are allowed so a user can stage multiple selections before syncing.
    _assert_checkout(checkout,require_clean=False)
    slugs,_tracked=_candidate(candidate,tool_root=checkout)
    candidate_index=_index(candidate)
    collection=checkout/'kristals'
    _reject_symlinks(collection)
    current_index=collection/'index.json'
    existing=[]
    legacy_stub=False
    if current_index.is_file():
        _validate_c3(checkout)
        existing=[row['slug'] for row in _index(checkout)['kristals']]
    elif collection.exists():
        files=list(collection.iterdir())
        if files:
            if len(files)==1 and files[0].name=='zoology' and _legacy_zoology_stub(checkout):
                legacy_stub=True
                if 'zoology' not in slugs and not retire_zoology_stub:
                    raise ManagerError('Ancien Zoology sans manifeste : sélectionne Zoology avec les autres Kristals pour le remplacer. Aucun retrait automatique.')
            else:
                raise ManagerError('Collection publique existante sans index C3 valide : copie refusée')
    if current_index.exists() and not current_index.is_file():
        raise ManagerError('Index public non régulier')
    # The old one-file Zoology stub is not eligible for a C3 index; it is
    # replaced if Zoology was explicitly selected or retired only with opt-in.
    old_index = _index(checkout) if current_index.is_file() else None
    current_fingerprint = old_index['index_digest'] if old_index else (
        'zoology-stub:'+hashlib.sha256((collection/'zoology/state/state-snapshot.json').read_bytes()).hexdigest()
        if legacy_stub else 'empty')
    plan={
        'status':'LOCAL_PUBLIC_PREVIEW',
        'candidate':str(candidate),'checkout':str(checkout),
        'slugs':slugs,'new_slugs':sorted(set(slugs)-set(existing)),
        'updated_slugs':sorted(set(slugs)&set(existing)),
        'preserved_slugs':sorted(set(existing)-set(slugs)),
        'retire_legacy_zoology_stub':bool(legacy_stub and 'zoology' not in slugs),
        'candidate_files':sum(row['file_count'] for row in candidate_index['kristals']),
        'authorization':'C1_C2_NOT_VERIFIED',
        'git_add':False,'git_commit':False,'git_push':False,'upload':False,
        'public_exposure':False,
    }
    plan['plan_token']=_digest({'candidate':str(candidate),'checkout':str(checkout),
        'candidate_index_digest':candidate_index['index_digest'],
        'current_collection_fingerprint':current_fingerprint,
        'slugs':slugs,'retire_zoology_stub':retire_zoology_stub})
    return plan


def plan_local_public(*, candidate: Path, checkout: Path,
                      retire_zoology_stub: bool=False) -> dict:
    """Read-only inspection and exact preview token. No local write."""
    return _inspect(candidate=candidate,checkout=checkout,
                    retire_zoology_stub=retire_zoology_stub)


def _run_c3_index(checkout: Path, staging_root: Path) -> dict:
    script=checkout/'tools/c3_collection.py'
    if not script.is_file() or script.is_symlink():
        raise ManagerError('Outil C3 introuvable ou symbolique dans kristal-public')
    try:
        run=subprocess.run([sys.executable,str(script),'--repo',str(staging_root),'build-index'],
                           capture_output=True,text=True,timeout=150,
                           encoding='utf-8',errors='replace',check=False)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise ManagerError('Construction de l’index C3 impossible') from exc
    if run.returncode:
        raise ManagerError('Index C3 refusé: '+(run.stderr or run.stdout)[-900:])
    try:
        index=json.loads(run.stdout)
    except ValueError as exc:
        raise ManagerError('Index C3 non JSON') from exc
    (staging_root/'kristals/index.json').write_text(
        json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    _validate_c3(staging_root,tool_root=checkout)
    return index


def apply_local_public(*, candidate: Path, checkout: Path, expected_token: str,
                       retire_zoology_stub: bool=False, progress=None) -> dict:
    """Copy into LOCAL checkout, validate C3, roll back on failure. Never invoke Git write.

    A dated backup of the previous collection is kept OUTSIDE the Git checkout.
    The backup is NOT a Git revert or a public publication approval.
    """
    info=plan_local_public(candidate=candidate,checkout=checkout,
                           retire_zoology_stub=retire_zoology_stub)
    if not expected_token or info['plan_token']!=expected_token:
        raise ManagerError('Aperçu périmé : relancer la prévisualisation avant la copie')
    checkout=Path(checkout).expanduser().resolve(strict=True)
    candidate=Path(candidate).expanduser().resolve(strict=True)
    root=checkout/'kristals'
    parent=checkout.parent
    scratch=Path(tempfile.mkdtemp(prefix='.kristal-public-local-stage-',dir=parent))
    prepared=scratch/'prepared'
    prepared.mkdir()
    target=prepared/'kristals'
    backup=None
    if root.exists():
        backup_root=parent/'.kristal-manager-public-backups'
        backup_root.mkdir(exist_ok=True)
        backup=backup_root/('kristals-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
    try:
        if root.exists():
            shutil.copytree(root,target,symlinks=False)
        else:
            target.mkdir()
        if info['retire_legacy_zoology_stub']:
            shutil.rmtree(target/'zoology')
        if progress:
            progress({'phase':'stage_copy','completed':0,'total':len(info['slugs']),
                      'message':'Préparation des dossiers publics'})
        for position, slug in enumerate(info['slugs'],start=1):
            if progress:
                progress({'phase':'stage_copy','completed':position-1,'total':len(info['slugs']),
                          'slug':slug,'message':'Copie du Kristal '+slug})
            dest=target/slug
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(candidate/'kristals'/slug,dest,symlinks=False)
            if progress:
                progress({'phase':'stage_copy','completed':position,'total':len(info['slugs']),
                          'slug':slug,'message':'Copié : '+slug})
        (target/'index.json').unlink(missing_ok=True)
        if progress:
            progress({'phase':'verify','completed':0,'total':2,'message':'Construction de l’index C3'})
        new_index=_run_c3_index(checkout,prepared)
        # Check the full live selection again before touching the checkout.
        if plan_local_public(candidate=candidate,checkout=checkout,
                             retire_zoology_stub=retire_zoology_stub)['plan_token']!=expected_token:
            raise ManagerError('Les fichiers ont changé depuis l’aperçu : copie annulée')
        if backup is not None:
            root.rename(backup)
        try:
            target.rename(root)
            if progress:
                progress({'phase':'verify','completed':1,'total':2,'message':'Contrôle C3 après copie'})
            _validate_c3(checkout)
            if progress:
                progress({'phase':'verify','completed':2,'total':2,'message':'Contrôle C3 réussi'})
        except Exception:
            if root.exists():
                shutil.rmtree(root)
            if backup is not None and backup.exists():
                backup.rename(root)
            raise
        return {**info,'status':'LOCAL_PUBLIC_C3_VALID',
                'index_digest':new_index['index_digest'],
                'collection_count':new_index['count'],
                'backup_outside_checkout':str(backup) if backup else None,
                'next':'Relire le contenu et les autorisations indépendantes C1/C2 AVANT votre script GitHub. Aucune commande Git de modification exécutée par Manager.'}
    finally:
        # The old collection is either restored on failure or saved as a backup.
        shutil.rmtree(scratch,ignore_errors=True)


def prepare_and_copy_public_local(*, locals_root: Path, kit_script: Path, checkout: Path,
                                  slugs: list[str], retire_zoology_stub: bool=False, progress=None) -> dict:
    """Build, preflight and apply in one action using only a disposable candidate.

    The candidate is never a user-maintained directory. It is deleted on
    success AND on failures. apply_local_public preserves transactional
    validation and a separately designated rollback backup outside Git.
    This operation does not authorize or carry out any Git publishing.
    """
    # Existing C3 collections use the incremental engine: preserved Kristals are
    # never recopied, and already-built unchanged surfaces reuse their cache.
    # An initial empty/legacy checkout retains the original full-copy bootstrap.
    if (Path(checkout).expanduser() / 'kristals' / 'index.json').is_file():
        from .public_incremental import prepare_public_incremental
        return prepare_public_incremental(locals_root=locals_root,
            kit_script=kit_script, checkout=checkout, slugs=slugs, progress=progress)
    from .publication_stage import prepare_private_collection

    if not slugs or len(set(slugs)) != len(slugs):
        raise ManagerError('Sélectionner des Kristals distincts avant de préparer kristal-public')
    with tempfile.TemporaryDirectory(prefix='kristal-manager-public-c3-') as temporary:
        candidate=Path(temporary)/'candidate'
        prepared=prepare_private_collection(
            locals_root=locals_root,kit_script=kit_script,output=candidate,
            slugs=slugs,write_private=True,build_on_copy=True, progress=progress)
        plan=plan_local_public(candidate=candidate,checkout=checkout,
                               retire_zoology_stub=retire_zoology_stub)
        if sorted(plan['slugs']) != sorted(slugs):
            raise ManagerError('Le candidat ne correspond plus à la sélection')
        result=apply_local_public(candidate=candidate,checkout=checkout,
                                   expected_token=plan['plan_token'],
                                   retire_zoology_stub=retire_zoology_stub, progress=progress)
        # Do not leak a now-deleted private candidate path in the report.
        return {
            'status': 'LOCAL_PUBLIC_C3_VALID',
            'slugs':result['slugs'],
            'new_slugs':result['new_slugs'],
            'updated_slugs':result['updated_slugs'],
            'preserved_slugs':result['preserved_slugs'],
            'index_digest':result['index_digest'],
            'collection_count':result['collection_count'],
            'files_prepared':prepared['files_count'],
            'backup_outside_checkout':result['backup_outside_checkout'],
            'temporary_candidate_removed':True,
            'authorization':'C1_C2_NOT_VERIFIED',
            'git_add':False,'git_commit':False,'git_push':False,'upload':False,
            'next':'Le dossier local est préparé. Vérifier les autorisations C1/C2 et les droits avant votre script GitHub.',
        }
