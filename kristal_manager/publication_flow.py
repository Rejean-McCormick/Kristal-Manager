"""Explicit local Git publication workflow, built on the existing Kit/Manager/C3 gates.

Two-phase design: (1) prepare a C3-valid *local commit* with exact selected
read-surfaces; (2) independently review and sign C1/C2 evidence bound to that
commit; (3) verify both independent receipt systems, then push that exact SHA.
No network write is possible from prepare_commit, plan, or when evidence is absent.
"""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlparse

from .core import ManagerError

PUBLIC_REPO='Rejean-McCormick/kristal-public'
GIT_SHA=re.compile(r'^[0-9a-f]{40}$')
SLUG=re.compile(r'^[a-z0-9][a-z0-9._-]*$')


def _git(root: Path, *args: str, timeout: int=40) -> str:
    try:
        done=subprocess.run(['git','-C',str(root),*args],text=True,
                            encoding='utf-8',errors='replace',capture_output=True,
                            timeout=timeout,check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ManagerError('Git indisponible ou expiré') from exc
    if done.returncode:
        raise ManagerError(f'git {args[0]} échoué : {(done.stderr or done.stdout)[-500:]}')
    return done.stdout.strip()


def _assert_checkout(root: Path, *, require_clean: bool) -> str:
    root=Path(root).expanduser().resolve(strict=True)
    if not (root/'.git').exists() or Path(_git(root,'rev-parse','--show-toplevel')).resolve()!=root:
        raise ManagerError('Un vrai checkout Git à sa racine est obligatoire')
    if _git(root,'branch','--show-current')!='main':
        raise ManagerError('La branche main doit être active (pas de HEAD détaché)')
    remote=_git(root,'remote','get-url','origin').strip()
    allowed={f'https://github.com/{PUBLIC_REPO}',f'https://github.com/{PUBLIC_REPO}.git',
             f'git@github.com:{PUBLIC_REPO}',f'git@github.com:{PUBLIC_REPO}.git',
             f'ssh://git@github.com/{PUBLIC_REPO}',f'ssh://git@github.com/{PUBLIC_REPO}.git'}
    if remote not in allowed:
        raise ManagerError('Remote origin inattendu. Requis : '+PUBLIC_REPO)
    if require_clean and _git(root,'status','--porcelain=v1','--untracked-files=all'):
        raise ManagerError('Le checkout contient des modifications ou fichiers non suivis; Git doit être propre')
    sha=_git(root,'rev-parse','HEAD')
    if not GIT_SHA.fullmatch(sha):raise ManagerError('SHA Git invalide')
    return sha


def _validate_c3(root: Path, *,tool_root: Path | None=None) -> dict:
    script=(tool_root or root)/'tools'/'c3_collection.py'
    if not script.is_file():raise ManagerError('Contrôleur C3 manquant dans kristal-public (appliquer overlay C3)')
    try:
        done=subprocess.run([sys.executable,str(script),'--repo',str(root),'validate-index'],
                            capture_output=True,text=True,encoding='utf-8',errors='replace',
                            check=False,timeout=120)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise ManagerError('Contrôle C3 impossible') from exc
    if done.returncode:
        raise ManagerError('C3 refuse la collection : '+(done.stderr or done.stdout)[-900:])
    try:return json.loads(done.stdout)
    except ValueError as exc:raise ManagerError('Résultat C3 non JSON') from exc


def _candidate(candidate: Path, *,tool_root: Path) -> tuple[list[str], list[str]]:
    candidate=Path(candidate).expanduser().resolve(strict=True)
    if not candidate.is_dir() or not (candidate/'STAGING_ONLY.txt').is_file():
        raise ManagerError('Préparer d’abord un candidat privé avec le Manager')
    index=_validate_c3(candidate,tool_root=tool_root)
    rows=index.get('kristals',[])
    if not rows or any(not SLUG.fullmatch(x.get('slug','')) for x in rows):
        raise ManagerError('Index C3 vide ou invalide')
    slugs=[x['slug'] for x in rows]
    if len(set(slugs))!=len(slugs):raise ManagerError('Slugs dupliqués')
    tracked=['kristals/index.json']
    for row in rows:
        slug=row['slug']
        manifest=candidate/'kristals'/slug/'.kristal'/'sync-manifest.json'
        meta=json.loads(manifest.read_text(encoding='utf-8'))
        for file in meta['files']:
            rel=file['path']
            if not isinstance(rel,str) or '\\' in rel or ':' in rel or \
               PurePosixPath(rel).is_absolute() or '..' in PurePosixPath(rel).parts:
                raise ManagerError('Chemin public interdit dans le manifeste')
            tracked.append('kristals/'+slug+'/'+rel)
        tracked.append('kristals/'+slug+'/.kristal/sync-manifest.json')
    if len(tracked)!=len(set(tracked)):
        raise ManagerError('Manifestes à fichiers dupliqués')
    for rel in tracked:
        f=candidate.joinpath(*PurePosixPath(rel).parts)
        if not f.is_file() or f.is_symlink() or not f.resolve().is_relative_to(candidate):
            raise ManagerError('Fichier candidat absent ou lien symbolique : '+rel)
    return slugs,sorted(tracked)


def _legacy_zoology_stub(root: Path) -> bool:
    dest=root/'kristals'/'zoology'
    if not dest.exists():return False
    if dest.is_symlink() or not dest.is_dir():raise ManagerError('zoology non canonique')
    actual={p.relative_to(dest).as_posix() for p in dest.rglob('*') if p.is_file()}
    if any(p.is_symlink() for p in dest.rglob('*')):
        raise ManagerError('Lien symbolique dans zoology')
    if actual!={'state/state-snapshot.json'}:
        raise ManagerError('Le dossier zoology contient autre chose que le stub attendu: retrait automatique refusé')
    return True


def plan_commit(*,candidate: Path,checkout: Path,retire_zoology_stub: bool=False) -> dict:
    candidate=Path(candidate).expanduser().resolve(strict=True)
    checkout=Path(checkout).expanduser().resolve(strict=True)
    _assert_checkout(checkout,require_clean=True)
    if candidate.is_relative_to(checkout) or checkout.is_relative_to(candidate):
        raise ManagerError('Candidat privé et dépôt public doivent être disjoints')
    slugs,tracked=_candidate(candidate,tool_root=checkout)
    existing={p.name for p in (checkout/'kristals').iterdir() if p.is_dir()} if (checkout/'kristals').exists() else set()
    other=existing-set(slugs)
    retirement=[]
    if other:
        if other=={'zoology'} and retire_zoology_stub and _legacy_zoology_stub(checkout):
            retirement=['kristals/zoology/state/state-snapshot.json']
        else:
            raise ManagerError('Collection existante hors sélection : '+', '.join(sorted(other))+
                               '. Aucune suppression implicite.')
    for slug in slugs:
        if (checkout/'kristals'/slug).exists():
            raise ManagerError('Kristal déjà hébergé : '+slug+'. Éviter écrasements silencieux.')
    if (checkout/'kristals/index.json').exists():
        raise ManagerError('Index public déjà existant : mise à jour incrémentale non prise en charge par ce parcours')
    return {'status':'READY_FOR_LOCAL_COMMIT','slugs':slugs,'candidate_files':len(tracked),
            'retire_paths':retirement,'checkout':str(checkout),'online':False,
            'authorization':'REQUIRED_BEFORE_PUSH'}


def prepare_local_commit(*,candidate: Path,checkout: Path,retire_zoology_stub: bool=False,
                         write: bool=False) -> dict:
    info=plan_commit(candidate=candidate,checkout=checkout,retire_zoology_stub=retire_zoology_stub)
    if not write:return dict(info,status='DRY_RUN')
    candidate=Path(candidate).resolve()
    checkout=Path(checkout).resolve()
    before=_git(checkout,'rev-parse','HEAD')
    newpaths=[*('kristals/'+s for s in info['slugs']),'kristals/index.json']
    # The old Zoology stub is a tracked Git file. Require explicit opt-in to retire it.
    try:
        for rel in info['retire_paths']:
            (checkout/rel).unlink()
        if info['retire_paths']:
            (checkout/'kristals/zoology/state').rmdir()
            (checkout/'kristals/zoology').rmdir()
        for slug in info['slugs']:
            shutil.copytree(candidate/'kristals'/slug,checkout/'kristals'/slug,symlinks=False)
        shutil.copy2(candidate/'kristals/index.json',checkout/'kristals/index.json')
        _validate_c3(checkout)
        changed=[*newpaths,*info['retire_paths']]
        _git(checkout,'add','-A','--',*changed)
        staged=_git(checkout,'diff','--cached','--name-only','--diff-filter=ACDMRT')
        files={s.strip() for s in staged.splitlines() if s.strip()}
        allowed={str(x) for x in _candidate(candidate,tool_root=checkout)[1]} | set(info['retire_paths'])
        if not files or not files<=allowed:
            raise ManagerError('Git stage contient des chemins non autorisés / aucun changement')
        with tempfile.TemporaryDirectory(prefix='kristal-empty-hooks-') as hooks:
            _git(checkout,'-c','core.hooksPath='+hooks,'commit','-m',
                 'Prepare reviewed Kristal public candidate: '+', '.join(info['slugs']),timeout=120)
        current=_git(checkout,'rev-parse','HEAD')
        if current==before or _git(checkout,'status','--porcelain=v1','--untracked-files=all'):
            raise ManagerError('Postcommit Git incohérent: inspecter manuellement')
        return {**info,'status':'LOCAL_COMMIT_PREPARED','commit':current,
                'next':'Obtenir les preuves C1/C2 indépendantes liées à ce commit, puis vérifier avant push'}
    except Exception:
        # Only rollback if a new commit was NOT made; never alter a recorded Git commit.
        if _git(checkout,'rev-parse','HEAD')==before:
            _git(checkout,'restore','--source=HEAD','--staged','--worktree','--','kristals')
            for slug in info['slugs']:
                shutil.rmtree(checkout/'kristals'/slug,ignore_errors=True)
            (checkout/'kristals/index.json').unlink(missing_ok=True)
            # Clean up only empty directories. Tracked Zoology is restored by Git.
        raise


def publish_approved_commit(*,checkout: Path,trust: Path,c1_dir: Path,c2_dir: Path,
                             policy_dir: Path,external_approval_confirmed: bool=False,
                             push: bool=False) -> dict:
    """Both existing signed systems must pass; an operator must confirm external review.

    C123 offline verifier explicitly does not grant publication; the separate
    C2 pre-public qualification and the external operator review are required.
    """
    checkout=Path(checkout).expanduser().resolve(strict=True)
    sha=_assert_checkout(checkout,require_clean=True)
    index=_validate_c3(checkout)
    rows=index['kristals']
    if not rows:raise ManagerError('Collection vide')
    gate=checkout/'tools/c123_offline.py'
    if not gate.is_file():raise ManagerError('Vérificateur C1/C2 du dépôt public absent')
    # Verify both independent evidence families, exact current Git SHA and bytes.
    from .publication_gate import verify_public_write, PublicGateError
    from .publication_gate import sha256, candidate_digest
    for row in rows:
        slug=row['slug']
        from .publication_gate import candidate_rows
        manifest=json.loads((checkout/'kristals'/slug/'.kristal/sync-manifest.json').read_text(encoding='utf8'))
        paths=['kristals/'+slug+'/'+x['path'] for x in manifest['files']]
        paths+=['kristals/'+slug+'/.kristal/sync-manifest.json','kristals/index.json']
        paths=sorted(paths)
        try:
            result=subprocess.run([sys.executable,str(gate),'--repo',str(checkout),
                    '--slug',slug,'--trust',str(trust),'--c1',str(Path(c1_dir)/(slug+'.json')),
                    '--c2',str(Path(c2_dir)/(slug+'.json'))],capture_output=True,text=True,
                    encoding='utf8',errors='replace',timeout=60)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise ManagerError('Vérification C123 non disponible') from exc
        if result.returncode:
            raise ManagerError('C123 bloqué pour '+slug+': '+(result.stderr or result.stdout)[-500:])
        evidence=json.loads(result.stdout)
        if evidence.get('status')!='SIGNED_EVIDENCE_MATCHES_LOCAL_POLICY' or evidence.get('subject',{}).get('source_commit')!=sha:
            raise ManagerError('C123 ne correspond pas à ce commit : '+slug)
        try:
            c2=verify_public_write(operation='sync',slug=slug,state_ref=row['state_ref'],
                    repository=PUBLIC_REPO,local_root=checkout,paths=paths,
                    state_commitment=row['state_logical_commitment']['digest'],policy_dir=Path(policy_dir))
        except (PublicGateError,KeyError,TypeError) as exc:
            raise ManagerError('C2 prépublication bloquée pour '+slug+': '+str(exc)) from exc
        if c2.get('result')!='AUTHORIZED_AND_QUALIFIED':
            raise ManagerError('C2 n’est pas une qualification valide')
    if not external_approval_confirmed:
        raise ManagerError('Validation indépendante des émetteurs / révocations non confirmée; push bloqué')
    if _git(checkout,'rev-parse','HEAD')!=sha:
        raise ManagerError('Commit changé pendant la qualification')
    status={'status':'PRE_PUBLICATION_GATES_PASS','revision':sha,'slugs':[x['slug'] for x in rows],
            'repository':PUBLIC_REPO,'url':'https://github.com/'+PUBLIC_REPO,
            'push_performed':False,'wiki_native_activated':False}
    if not push:return status
    # No remote mutation until all gates have returned PASS.
    remote=_git(checkout,'ls-remote','origin','refs/heads/main',timeout=40)
    remote_sha=remote.split()[0] if remote else ''
    parent=_git(checkout,'rev-parse','HEAD^')
    if remote_sha!=parent:
        raise ManagerError('Le serveur ne correspond pas au parent du commit préparé : fetch/revue obligatoires')
    _git(checkout,'push','origin','HEAD:refs/heads/main',timeout=120)
    published=_git(checkout,'ls-remote','origin','refs/heads/main',timeout=40).split()[0]
    if published!=sha:
        raise ManagerError('Push non confirmé par le SHA distant')
    return {**status,'status':'PUSH_CONFIRMED','push_performed':True,
            'catalog_url':'https://github.com/'+PUBLIC_REPO+'/tree/'+sha+'/kristals'}


def export_wiki_candidate(*,checkout: Path, output: Path, write: bool=False) -> dict:
    """After a confirmed push, render the existing C3 wiki exporter privately.

    Never changes the native GitHub Wiki repository; no hidden Git mutation.
    """
    checkout=Path(checkout).expanduser().resolve(strict=True)
    sha=_assert_checkout(checkout,require_clean=True)
    _validate_c3(checkout)
    output=Path(output).expanduser().resolve()
    if output.exists() or not output.parent.is_dir() or output.is_relative_to(checkout):
        raise ManagerError('Sortie Wiki : dossier neuf, hors du dépôt public')
    remote=_git(checkout,'ls-remote','origin','refs/heads/main',timeout=40)
    if not remote or remote.split()[0]!=sha:
        raise ManagerError('Ce commit n’est pas confirmé en ligne : brouillon Wiki bloqué')
    script=checkout/'tools/wiki_export.py'
    if not script.is_file():raise ManagerError('Générateur Wiki manquant dans le dépôt public')
    args=[sys.executable,str(script),'--collection',str(checkout),
          '--output',str(output),'--repository',PUBLIC_REPO,'--revision',sha]
    if write:args+=['--write']
    try:
        r=subprocess.run(args,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=120)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise ManagerError('Export Wiki impossible') from exc
    if r.returncode:raise ManagerError('Export Wiki bloqué : '+(r.stderr or r.stdout)[-500:])
    try:return json.loads(r.stdout)
    except ValueError as exc:raise ManagerError('Générateur Wiki : résultat invalide') from exc
