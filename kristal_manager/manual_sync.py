"""Selected, read-only Git inventory -> explicit local copies for MANUAL synchronization.

No Git add/commit/push/clone, remote network calls, deletion of destination files,
or copying of Git administrative directories. This is not a C1/C2 approval or
public-read-surface attestation. Never invoke from scans or diagnostics.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import uuid

from .core import ManagerError
from .publication_stage import SLUG

GITHUB = re.compile(r'^(?:https://(?:[^/@]+@)?github\.com/|git@github\.com:|ssh://git@github\.com/)([^\s]+?)(?:\.git)?$', re.I)
DENIED = {'.env', 'id_rsa', 'id_ed25519', 'credentials.json', 'secrets.json', '.npmrc', '.pypirc'}
DENIED_ENDINGS = ('.pem', '.p12', '.pfx', '.key')


def _git(root: Path, *args: str) -> str:
    try:
        r = subprocess.run(['git', '-C', str(root), *args], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=45, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ManagerError(f'Git local indisponible : {root}') from exc
    if r.returncode:
        raise ManagerError(f'Git local refuse {root.name}: {r.stderr.decode("utf-8", "replace")[-240:]}')
    return r.stdout.decode('utf-8', 'strict')


def _git_root(path: Path) -> None:
    if not path.is_dir() or path.is_symlink():
        raise ManagerError('Dépôt absent ou dossier symbolique : ' + str(path))
    root = Path(_git(path, 'rev-parse', '--show-toplevel').strip()).resolve()
    if root != path.resolve():
        raise ManagerError('Le dossier doit être la racine exacte du dépôt Git : ' + str(path))


def _safe_relative(path: str) -> Path:
    if not isinstance(path, str) or not path or '\\' in path or ':' in path or '\x00' in path:
        raise ManagerError('Chemin Git invalide')
    p = PurePosixPath(path)
    if p.is_absolute() or any(x in ('..', '.') for x in p.parts) or any(x.lower() == '.git' for x in p.parts):
        raise ManagerError('Chemin interdit : ' + path)
    if p.name.lower() in DENIED or p.name.lower().startswith('.env.') or p.name.lower().endswith(DENIED_ENDINGS):
        raise ManagerError('Fichier potentiellement secret dans les fichiers Git : ' + path)
    return Path(*p.parts)


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fd:
        for chunk in iter(lambda: fd.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _tracked(source: Path) -> list[tuple[str, Path, str, int]]:
    raw = _git(source, 'ls-files', '--cached', '-z').split('\x00')
    rows = []
    for rel in raw:
        if not rel:
            continue
        p = _safe_relative(rel)
        f = source / p
        if not f.is_file() or f.is_symlink() or not f.resolve().is_relative_to(source):
            raise ManagerError('Entrée Git absente, sous-module ou lien symbolique : ' + rel)
        # Reject symlinked parents, even if a platform resolves through them.
        if any((source / Path(*p.parts[:n])).is_symlink() for n in range(1, len(p.parts))):
            raise ManagerError('Lien symbolique parent : ' + rel)
        rows.append((rel, p, _sha(f), f.stat().st_size))
    if len({x[0].casefold() for x in rows}) != len(rows):
        raise ManagerError('Deux noms Git entrent en collision sur Windows : ' + source.name)
    if not rows:
        raise ManagerError('Aucun fichier Git suivi dans ' + source.name)
    return rows


def _selected_sources(locals_root: Path, slugs: list[str]) -> list[tuple[str, Path]]:
    if not locals_root.is_dir() or locals_root.is_symlink():
        raise ManagerError('Racine locals absente')
    if not slugs or len(slugs) != len(set(slugs)) or any(not isinstance(s, str) or not SLUG.fullmatch(s) for s in slugs):
        raise ManagerError('Sélection explicite de slugs uniques requise')
    matches = {}
    for d in locals_root.iterdir():
        if not d.is_dir() or d.is_symlink():
            continue
        f = d / 'kristal.workspace.json'
        if not f.is_file() or f.is_symlink():
            continue
        try:
            obj = json.loads(f.read_text(encoding='utf-8'))
            slug = obj.get('slug')
        except (ValueError, OSError, AttributeError):
            continue
        if slug in slugs:
            matches.setdefault(slug, []).append(d)
    if any(len(matches.get(slug, [])) != 1 for slug in slugs):
        raise ManagerError('Identité manquante ou dupliquée dans locals')
    return [(slug, matches[slug][0]) for slug in slugs]


def _github_dest(target: Path, source: Path, slug: str) -> None:
    _git_root(target)
    if _git(target, 'status', '--porcelain=v1', '--untracked-files=all').strip():
        raise ManagerError('Clone Git avec modifications locales : ' + target.name)
    remote = _git(target, 'remote', 'get-url', 'origin').strip()
    push_remote = _git(target, 'remote', 'get-url', '--push', 'origin').strip()
    if remote != push_remote:
        raise ManagerError('Destination GitHub push différente de origin : ' + target.name)
    m = GITHUB.fullmatch(remote)
    if not m:
        raise ManagerError('La destination n’a pas de remote origin GitHub : ' + target.name)
    name = m.group(1).split('/')[-1].removesuffix('.git')
    if name.casefold() not in (source.name.casefold(), slug.casefold()):
        raise ManagerError(f'Le remote GitHub {name} ne correspond pas à {source.name} / {slug}')
    workspace = target / 'kristal.workspace.json'
    if workspace.is_file():
        try: target_slug = json.loads(workspace.read_text(encoding='utf-8')).get('slug')
        except (ValueError, OSError, AttributeError) as exc:
            raise ManagerError('Métadonnées destination invalides : ' + target.name) from exc
        if target_slug != slug:
            raise ManagerError('Identité du clone GitHub différente du Kristal source : ' + target.name)


def plan_copies(*, locals_root: Path, destination_root: Path, slugs: list[str],
                mode: str = 'new') -> dict:
    """Inspect all selected tracked content. `new` creates private fresh folders;
    `clones` updates only clean, existing, matching GitHub clones.
    """
    if mode not in ('new', 'clones'):
        raise ManagerError('Mode de copie inconnu')
    locals_root = Path(locals_root).expanduser().resolve(strict=True)
    destination_root = Path(destination_root).expanduser().resolve(strict=True)
    if not destination_root.is_dir() or destination_root.is_symlink():
        raise ManagerError('Dossier de destination absent')
    if destination_root == locals_root or destination_root.is_relative_to(locals_root) or locals_root.is_relative_to(destination_root):
        raise ManagerError('La destination doit être séparée de locals')
    if any((p / '.git').exists() for p in (destination_root, *destination_root.parents)):
        raise ManagerError('La racine de destination ne peut pas être à l’intérieur d’un dépôt Git')
    selections = _selected_sources(locals_root, slugs)
    projects = []
    for slug, source in selections:
        _git_root(source)
        target = destination_root / source.name
        if target.is_symlink() or not target.resolve().is_relative_to(destination_root):
            raise ManagerError('Destination symbolique ou hors racine : ' + source.name)
        if mode == 'new':
            if target.exists():
                raise ManagerError('Copie déjà existante, aucun remplacement : ' + str(target))
        else:
            _github_dest(target, source, slug)
        entries = []
        for rel, p, digest, size in _tracked(source):
            dst = target / p
            if mode == 'clones':
                if dst.is_symlink() or any((target / Path(*p.parts[:n])).is_symlink() for n in range(1, len(p.parts))):
                    raise ManagerError('Lien symbolique dans la destination : ' + rel)
                if dst.exists() and not dst.is_file():
                    raise ManagerError('Conflit fichier / dossier : ' + rel)
                if not dst.exists():
                    ignored = subprocess.run(['git', '-C', str(target), 'check-ignore', '-q', '--', rel],
                                             capture_output=True, check=False, timeout=15)
                    if ignored.returncode == 0:
                        raise ManagerError('Fichier ignoré par le clone : ' + rel)
                    if ignored.returncode not in (0, 1):
                        raise ManagerError('Impossible de vérifier gitignore : ' + rel)
            old_sha = _sha(dst) if dst.is_file() else None
            entries.append({'path': rel, 'sha256': digest, 'size': size,
                            'destination_sha256': old_sha,
                            'action': 'UNCHANGED' if old_sha == digest else 'COPY'})
        projects.append({'slug': slug, 'source': str(source), 'target': str(target),
                         'files': len(entries), 'to_copy': sum(x['action'] == 'COPY' for x in entries),
                         'bytes': sum(x['size'] for x in entries if x['action'] == 'COPY'),
                         'entries': entries})
    # Fail closed for Windows case-insensitive target clashes.
    if len({p['target'].casefold() for p in projects}) != len(projects):
        raise ManagerError('Collision de noms de dossiers de destination')
    return {'status': 'DRY_RUN', 'mode': mode, 'source_root': str(locals_root),
            'destination_root': str(destination_root), 'slugs': list(slugs),
            'project_count': len(projects), 'copy_files': sum(p['to_copy'] for p in projects),
            'copy_bytes': sum(p['bytes'] for p in projects), 'projects': projects,
            'git_add': False, 'git_commit': False, 'git_push': False,
            'publication_authorized': False,
            'note': 'Vérifier les secrets, licences, données privées et autorisations avant toute synchronisation publique.'}


def apply_copies(*, locals_root: Path, destination_root: Path, slugs: list[str],
                 mode: str = 'new') -> dict:
    plan = plan_copies(locals_root=locals_root, destination_root=destination_root,
                       slugs=slugs, mode=mode)
    backup_root = Path(plan['destination_root']).parent / 'KristalManager-copy-backups'
    if any((p / '.git').exists() for p in (backup_root, *backup_root.parents)):
        raise ManagerError('Dossier de sauvegarde situé dans un dépôt Git')
    backup_root.mkdir(parents=True, exist_ok=True)
    run = backup_root / ('copy-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8])
    run.mkdir()
    made = []
    replaced = []
    created_dirs = []
    try:
        for proj in plan['projects']:
            source, target = Path(proj['source']), Path(proj['target'])
            if mode == 'new':
                target.mkdir()
                created_dirs.append(target)
            for entry in proj['entries']:
                if entry['action'] == 'UNCHANGED':
                    continue
                rel = _safe_relative(entry['path'])
                src, dst = source / rel, target / rel
                # Recheck after preview to catch changes before an individual write.
                if not src.is_file() or src.is_symlink() or _sha(src) != entry['sha256']:
                    raise ManagerError('Source modifiée pendant la copie : ' + str(src))
                if dst.is_symlink() or (dst.exists() and (not dst.is_file() or _sha(dst) != entry['destination_sha256'])) or \
                        (not dst.exists() and entry['destination_sha256'] is not None):
                    raise ManagerError('Destination modifiée pendant la copie : ' + str(dst))
                dst.parent.mkdir(parents=True, exist_ok=True)
                if dst.exists():
                    bak = run / 'previous' / source.name / rel
                    bak.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dst, bak)
                    replaced.append((dst, bak))
                else:
                    made.append(dst)
                tmp = dst.with_name(dst.name + '.kristal-copy-' + uuid.uuid4().hex[:8])
                try:
                    shutil.copyfile(src, tmp)
                    if _sha(tmp) != entry['sha256']:
                        raise ManagerError('Empreinte divergente : ' + str(dst))
                    os.replace(tmp, dst)
                finally:
                    tmp.unlink(missing_ok=True)
        record = {'status': 'COPIES_LOCALES_TERMINEES', 'mode': mode,
                  'copied_files': plan['copy_files'], 'projects': [{k: p[k] for k in ('slug', 'source', 'target', 'to_copy')} for p in plan['projects']],
                  'backup_folder': str(run), 'git_add': False, 'git_commit': False,
                  'git_push': False, 'publication_authorized': False}
        (run / 'BILAN-COPIES.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        return record
    except Exception:
        for dst in reversed(made):
            dst.unlink(missing_ok=True)
        for dst, bak in reversed(replaced):
            shutil.copy2(bak, dst)
        for folder in reversed(created_dirs):
            shutil.rmtree(folder, ignore_errors=True)
        raise
