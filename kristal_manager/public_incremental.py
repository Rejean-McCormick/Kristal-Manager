"""Incremental LOCAL staging of C3 Kristals; never performs Git write/network.

Fast path: reuse a previously C3-validated public surface only if its exact
local-source fingerprint and Kit fingerprint still match the recorded cache.
A changed/new surface is built in a private temporary directory. Commit swaps
ONLY affected Kristal folders and the collection index, with a change-scoped
rollback backup outside the Git checkout. Nonselected surfaces are not copied.

The cache is a performance hint, not qualification/authorization evidence.
The C3 validator is still run on the full local collection before and after
any update. No C1/C2 claims are made.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid

from .core import ManagerError
from .publication_flow import _assert_checkout, _candidate, _validate_c3
from .publication_stage import SLUG, _json, prepare_private_collection

CACHE_VERSION = 'kristal-manager-public-incremental/1.0'
INDEX_FORMAT = 'kristal.github-collection-index/1.0'
INDEX_NOTE = 'Derived navigation index for GitHub/AI discovery; not semantic authority.'


def _emit(progress, phase, completed, total, *, slug='', message=''):
    if progress is not None:
        progress({'phase':phase, 'completed':completed, 'total':total,
                  'slug':slug, 'message':message})


def _digest(value: object) -> str:
    return 'sha256:' + hashlib.sha256(json.dumps(value, sort_keys=True,
        ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf8')).hexdigest()


def _file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return 'sha256:' + h.hexdigest()


def _metadata(path: Path) -> dict:
    st = path.stat(follow_symlinks=False)
    return dict(size=st.st_size, mtime_ns=st.st_mtime_ns, ctime_ns=st.st_ctime_ns,
                ino=st.st_ino, dev=st.st_dev)


def _kit_digest(script: Path) -> str:
    if script.is_symlink() or not script.is_file():
        raise ManagerError('Authoring Kit absent ou symbolique')
    # The Kit's sibling Python modules are part of its interpretation policy.
    kit_root = script.parent.parent
    modules = set(script.parent.glob('*.py')) | {script}
    # AI read models use templates: a template edit must invalidate the cache.
    for directory in (kit_root / 'templates', script.parent / '_templates'):
        if directory.is_dir():
            modules.update(path for path in directory.rglob('*') if path.is_file() or path.is_symlink())
    rows = []
    for module in sorted(modules, key=lambda p: str(p.relative_to(kit_root))):
        if module.is_symlink() or not module.is_file():
            raise ManagerError('Fichier Authoring Kit symbolique/invalide: ' + module.name)
        rows.append([module.relative_to(kit_root).as_posix(), _file_sha(module)])
    return _digest(rows)


def _cache_dir(checkout: Path) -> Path:
    # One private cache namespace per checkout, never inside Git.
    identity = hashlib.sha256(str(checkout).casefold().encode('utf8')).hexdigest()[:16]
    return checkout.parent / '.kristal-manager-public-cache' / identity


def _load_cache(folder: Path, slug: str) -> dict | None:
    path = folder / (slug + '.json')
    if not path.is_file() or path.is_symlink():
        return None
    try:
        data = json.loads(path.read_text(encoding='utf8'))
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(data, dict) or data.get('format') != CACHE_VERSION or data.get('slug') != slug:
        return None
    if not isinstance(data.get('files'), list):
        return None
    return data


def _source_snapshot(root: Path, prior: dict | None) -> dict:
    """Content bound fingerprint; reuse recorded hashes when file metadata is identical.

    Every first/changed file is fully SHA-256 hashed. On subsequent checks the
    size, mtime, ctime and inode tuple is a fast-path hint for unchanged files.
    In addition, the public surface is independently rehashed by C3.
    """
    if not root.is_dir() or root.is_symlink():
        raise ManagerError('Dossier source invalide ou symbolique: ' + root.name)
    previous = {row['path']: row for row in (prior or {}).get('files', [])
                if isinstance(row, dict) and isinstance(row.get('path'), str)}
    files = []
    for parent, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            if (Path(parent) / name).is_symlink():
                raise ManagerError('Lien symbolique interdit dans le Kristal : ' + name)
        for name in names:
            path = Path(parent) / name
            if not path.is_file():
                raise ManagerError('Fichier non régulier dans le Kristal : ' + name)
            rel = path.relative_to(root).as_posix()
            attrs = _metadata(path)
            prior_row = previous.get(rel)
            if prior_row is not None and all(prior_row.get(k) == v for k, v in attrs.items()) \
                    and isinstance(prior_row.get('sha256'), str):
                sha = prior_row['sha256']
            else:
                sha = _file_sha(path)
                if attrs != _metadata(path):
                    raise ManagerError('Fichier modifié pendant la lecture : ' + rel)
            files.append({'path': rel, **attrs, 'sha256': sha})
    files.sort(key=lambda row: row['path'].encode('utf8'))
    return {'files': files, 'source_digest': _digest([[f['path'], f['sha256']] for f in files])}


def _sources(locals_root: Path, slugs: list[str]) -> dict[str, Path]:
    selected = set(slugs)
    by_slug = {slug: [] for slug in slugs}
    for folder in locals_root.iterdir():
        if folder.is_symlink() or not folder.is_dir():
            continue
        metadata = folder / 'kristal.workspace.json'
        if not metadata.is_file() or metadata.is_symlink():
            continue
        try:
            obj = _json(metadata)
        except ManagerError:
            continue
        slug = obj.get('slug')
        if slug in selected:
            by_slug[slug].append(folder)
    for slug in slugs:
        if len(by_slug[slug]) != 1:
            raise ManagerError('Un seul Kristal source requis pour : ' + slug)
    return {slug: by_slug[slug][0] for slug in slugs}


def _index_from_rows(rows: list[dict]) -> dict:
    rows = sorted(rows, key=lambda row: (row['slug'].encode('utf8'), row['path'].encode('utf8')))
    projection = {'format': INDEX_FORMAT, 'kristals': rows}
    return {**projection, 'count': len(rows), 'index_digest': _digest(projection), 'note': INDEX_NOTE}


def _write_json_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name('.' + path.name + '-' + uuid.uuid4().hex + '.tmp')
    try:
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _apply_selected(checkout: Path, candidate: Path, changed: list[str],
                    current_rows: list[dict], new_rows: list[dict], progress=None) -> tuple[dict, Path]:
    """Incremental, rollback-safe update. Preserved directories never move/copy."""
    from .public_local_sync import _reject_symlinks
    root = checkout / 'kristals'
    _reject_symlinks(root)
    rows = {row['slug']: row for row in current_rows}
    rows.update({row['slug']: row for row in new_rows if row['slug'] in changed})
    next_index = _index_from_rows(list(rows.values()))
    if len({x['state_ref'] for x in rows.values()}) != len(rows):
        raise ManagerError('state_ref dupliqué entre Kristals : copie refusée')
    # All new files arrive in a sibling staging tree on the same filesystem.
    scratch = Path(tempfile.mkdtemp(prefix='.kristal-public-incremental-', dir=checkout.parent))
    staged = scratch / 'staged'
    staged.mkdir()
    backups = checkout.parent / '.kristal-manager-public-backups'
    if backups.is_symlink() or (backups.exists() and not backups.is_dir()):
        shutil.rmtree(scratch, ignore_errors=True)
        raise ManagerError('Emplacement de sauvegarde non régulier')
    backup = backups / ('change-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
                        + '-' + uuid.uuid4().hex[:8])
    moved_old = []
    installed = []
    index_saved = False
    index_installed = False
    started = False
    try:
        _emit(progress, 'stage_copy', 0, len(changed), message='Préparation des dossiers modifiés')
        for position, slug in enumerate(changed, start=1):
            _emit(progress, 'stage_copy', position-1, len(changed), slug=slug,
                  message='Préparation : '+slug)
            source = candidate / 'kristals' / slug
            if not source.is_dir() or source.is_symlink():
                raise ManagerError('Candidat manquant ou invalide : ' + slug)
            shutil.copytree(source, staged / slug, symlinks=False)
            _emit(progress, 'stage_copy', position, len(changed), slug=slug, message='Préparé : '+slug)
        (staged / 'index.json').write_text(
            json.dumps(next_index, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        # Last pre-write validation of the current collection. No mutation yet.
        _emit(progress, 'verify', 0, 2, message='Contrôle C3 avant copie')
        live = _validate_c3(checkout)
        if live['index_digest'] != _index_from_rows(current_rows)['index_digest']:
            raise ManagerError('Collection modifiée pendant la préparation : opération annulée')
        backups.mkdir(exist_ok=True)
        backup.mkdir()
        (backup / 'old').mkdir()
        started = True
        for slug in changed:
            old = root / slug
            if old.exists():
                os.replace(old, backup / 'old' / slug)
                moved_old.append(slug)
            os.replace(staged / slug, old)
            installed.append(slug)
        os.replace(root / 'index.json', backup / 'index.json')
        index_saved = True
        os.replace(staged / 'index.json', root / 'index.json')
        index_installed = True
        _emit(progress, 'verify', 1, 2, message='Contrôle C3 après copie')
        checked = _validate_c3(checkout)
        if checked['index_digest'] != next_index['index_digest']:
            raise ManagerError('Empreinte C3 après copie différente de l’index prévu')
        _emit(progress, 'verify', 2, 2, message='Contrôle C3 réussi')
        (backup / 'RESTAURATION.json').write_text(json.dumps({
            'format': 'kristal-manager-incremental-backup/1.0',
            'changed_slugs': changed,
            'original_slugs': moved_old,
            'index_before': _index_from_rows(current_rows)['index_digest'],
            'index_after': checked['index_digest'],
            'note': 'Only changed folders and previous index were saved. Other folders were not modified.',
        }, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        return checked, backup
    except BaseException:
        if started:
            # Do not rely on a full-directory copy for rollback.
            try:
                if index_installed and (root / 'index.json').exists():
                    (root / 'index.json').unlink()
                if index_saved and (backup / 'index.json').exists():
                    os.replace(backup / 'index.json', root / 'index.json')
                for slug in reversed(installed):
                    if (root / slug).exists():
                        shutil.rmtree(root / slug)
                for slug in reversed(moved_old):
                    os.replace(backup / 'old' / slug, root / slug)
            except BaseException as restore_error:
                raise ManagerError('ÉCHEC DE RESTAURATION. Sauvegarde conservée dans ' + str(backup)
                                   + ' : ' + str(restore_error)) from restore_error
        if backup.exists():
            shutil.rmtree(backup)
        raise
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def prepare_public_incremental(*, locals_root: Path, kit_script: Path, checkout: Path,
                               slugs: list[str], progress=None) -> dict:
    """One-click incremental build/copy; preflight C3, replace only changed slugs."""
    if not slugs or len(set(slugs)) != len(slugs) or any(not SLUG.fullmatch(slug) for slug in slugs):
        raise ManagerError('Sélection de Kristals unique et valide requise')
    locals_root = Path(locals_root).expanduser().resolve(strict=True)
    kit_script = Path(kit_script).expanduser().resolve(strict=True)
    checkout = Path(checkout).expanduser().resolve(strict=True)
    if locals_root == checkout or locals_root.is_relative_to(checkout) or checkout.is_relative_to(locals_root):
        raise ManagerError('Dossiers sources et public doivent être séparés')
    if not locals_root.is_dir() or not kit_script.is_file():
        raise ManagerError('Locals/Kit invalides')
    # The local public checkout is always verified, including for all-cache-hit runs.
    _assert_checkout(checkout, require_clean=False)
    _emit(progress, 'preflight', 0, 1, message='Vérification de la collection locale')
    current = _validate_c3(checkout)
    _emit(progress, 'preflight', 1, 1, message='Collection locale vérifiée')
    current_rows = current['kristals']
    current_by_slug = {r['slug']: r for r in current_rows}
    sources = _sources(locals_root, slugs)
    _emit(progress, 'kit', 0, 1, message='Vérification du Kit')
    kit_digest = _kit_digest(kit_script)
    _emit(progress, 'kit', 1, 1, message='Kit vérifié')
    cache_dir = _cache_dir(checkout)
    snapshots = {}
    reusable = []
    to_build = []
    _emit(progress, 'scan', 0, len(slugs), message='Analyse des Kristals sélectionnés')
    for position, slug in enumerate(slugs, start=1):
        _emit(progress, 'scan', position-1, len(slugs), slug=slug,
              message='Vérification : '+slug)
        previous = _load_cache(cache_dir, slug)
        snap = _source_snapshot(sources[slug], previous)
        snapshots[slug] = snap
        if previous is not None and previous.get('kit_digest') == kit_digest \
                and previous.get('source_root') == str(sources[slug].resolve()) \
                and previous.get('source_digest') == snap['source_digest'] \
                and slug in current_by_slug \
                and previous.get('surface_digest') == current_by_slug[slug]['surface_digest']:
            reusable.append(slug)
        else:
            to_build.append(slug)
        _emit(progress, 'scan', position, len(slugs), slug=slug,
              message='Réutilisable : '+slug if slug in reusable else 'À reconstruire : '+slug)

    staged_rows = []
    new_by_slug = {}
    skipped = []
    built_success = []
    files_prepared = 0
    backup = None
    with tempfile.TemporaryDirectory(prefix='kristal-manager-public-c3-') as temporary:
        candidate = Path(temporary) / 'candidate'
        if to_build:
            prepared = prepare_private_collection(locals_root=locals_root, kit_script=kit_script,
                        output=candidate, slugs=to_build, write_private=True, build_on_copy=True,
                        progress=progress, allow_partial=True,
                        c3_script=checkout/'tools'/'c3_collection.py')
            files_prepared = prepared['files_count']
            skipped = prepared.get('rejected', [])
            built_success = prepared.get('successful_slugs', to_build)
            _emit(progress, 'candidate_verify', 0, 1, message='Validation du candidat C3')
            actual_slugs, _ = _candidate(candidate, tool_root=checkout)
            _emit(progress, 'candidate_verify', 1, 1, message='Candidat C3 valide')
            if sorted(actual_slugs) != sorted(built_success):
                raise ManagerError('Candidat C3 ne correspond pas à la sélection')
            staged_rows = json.loads((candidate/'kristals/index.json').read_text(encoding='utf8'))['kristals']
            new_by_slug = {row['slug']: row for row in staged_rows}
        # Equal output bytes can stay in place even when input metadata changed.
        unchanged_built = []
        changed = []
        for slug in built_success:
            row = new_by_slug[slug]
            existing = current_by_slug.get(slug)
            if existing == row and (candidate/'kristals'/slug/'.kristal/sync-manifest.json').read_bytes() \
                    == (checkout/'kristals'/slug/'.kristal/sync-manifest.json').read_bytes():
                unchanged_built.append(slug)
            else:
                changed.append(slug)
        if changed:
            # Changed only, no copy/move of the other hosted Kristals.
            final, backup = _apply_selected(checkout, candidate, changed, current_rows, staged_rows, progress=progress)
        else:
            final = current

    # Cache writes are advisory and performed only AFTER the public update has
    # passed C3. A failed cache write must never misreport a successful copy.
    cache_saved = True
    final_by_slug = {row['slug']: row for row in final['kristals']}
    successful = [slug for slug in slugs if slug in reusable or slug in built_success]
    _emit(progress, 'cache', 0, len(successful), message='Enregistrement du cache local')
    for position, slug in enumerate(successful, start=1):
        try:
            _write_json_atomic(cache_dir / (slug + '.json'), {
                'format': CACHE_VERSION, 'slug': slug,
                'kit_digest': kit_digest,
                'source_root': str(sources[slug].resolve()),
                'source_digest': snapshots[slug]['source_digest'],
                'surface_digest': final_by_slug[slug]['surface_digest'],
                'files': snapshots[slug]['files'],
            })
        except (OSError, ValueError):
            cache_saved = False
        _emit(progress, 'cache', position, len(successful), slug=slug, message='Cache : '+slug)
    _emit(progress, 'finished', 1, 1, message='Préparation locale terminée')
    old_slugs = {row['slug'] for row in current_rows}
    return {
        'status': 'LOCAL_PUBLIC_C3_PARTIAL' if skipped else 'LOCAL_PUBLIC_C3_VALID',
        'slugs': successful,
        'requested_slugs': slugs,
        'rejected': skipped,
        'rejected_count': len(skipped),
        'new_slugs': sorted(set(changed) - old_slugs),
        'updated_slugs': sorted(set(changed) & old_slugs),
        'reused_slugs': sorted(set(reusable) | set(unchanged_built)),
        'preserved_slugs': sorted(old_slugs - set(changed)),
        'rebuilt_slugs': sorted(to_build),
        'index_digest': final['index_digest'],
        'collection_count': final['count'],
        'files_prepared': files_prepared,
        'backup_outside_checkout': str(backup) if backup else None,
        'incremental': True,
        'cache_saved': cache_saved,
        'temporary_candidate_removed': True,
        'authorization': 'C1_C2_NOT_VERIFIED',
        'git_add': False, 'git_commit': False, 'git_push': False, 'upload': False,
        'next': 'Le dossier public local est à jour. Aucun Git. Vérifier les droits avant synchronisation.',
    }
