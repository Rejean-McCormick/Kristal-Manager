"""Local workspace organization and portable backups.

No remote operations, no assumption of Framework package conformance. Mutations
are explicit, one workspace at a time, and never edit internal source files.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import re
import unicodedata
import zipfile

from .core import ManagerError, _read_json

HISTORIC_NAMES = {'original-snapshot-before-activation', 'original-snapshot', 'snapshots', 'historical-v9-materializations', '_historique_avant_kristalizer'}
HISTORIC_PARENT = {'archive', 'archives', 'backup', 'backups', 'history', 'historique', 'snapshots'}


def is_historical(row: dict) -> bool:
    """Context-sensitive, no deletion: classify nested/archive snapshots for the UI."""
    path = Path(row['path'])
    parts = [x.casefold() for x in path.parts]
    if row.get('nested_under') and (any(x in HISTORIC_PARENT for x in parts) or path.name.casefold() in HISTORIC_NAMES):
        return True
    if any(x in HISTORIC_NAMES for x in parts) and any(x in HISTORIC_PARENT for x in parts):
        return True
    return False


def classification_of(row: dict) -> dict:
    """Read *declared* Arketype classification; never infer ARK/PRF IDs.

    The workspace declaration is the primary design input. The discovery copy
    is derived metadata and is only used if no workspace classification exists.
    These are classification hints, not C1 verification or semantic authority.
    """
    discovery = (row.get('discovery') or {}).get('classification')
    path = row.get('path')
    data = _read_json(Path(path) / 'kristal.workspace.json') if path else {}
    declared = data.get('classification')
    if isinstance(declared, dict) and declared:
        return declared
    return discovery if isinstance(discovery, dict) else {}


def arketype_of(row: dict) -> str | None:
    value = classification_of(row).get('primary_archetype')
    return value if isinstance(value, str) and re.fullmatch(r'ARK-[0-9]{2,}', value) else None


def usage_profile_of(row: dict) -> str | None:
    value = classification_of(row).get('primary_usage')
    return value if isinstance(value, str) and re.fullmatch(r'PRF-[0-9]{2,}', value) else None


def category_of(row: dict) -> str:
    """Domain category only; ARK and PRF are independent classification axes."""
    if is_historical(row):
        return 'Archive historique'
    if row.get('nested_under'):
        return 'Kristal imbriqué'
    if row.get('hidden_auxiliary') or row.get('readiness') == 'AUXILIARY':
        return 'Auxiliaire'
    if row.get('kind') != 'local' or row.get('readiness') == 'STATE-ONLY':
        return 'État isolé'
    classified = classification_of(row)
    domain = classified.get('domain')
    if isinstance(domain, str) and domain.strip():
        return domain.strip()
    path = row.get('path')
    data = _read_json(Path(path) / 'kristal.workspace.json') if path else {}
    for obj, field in ((data.get('subject'), 'domain'), (data.get('state_scope'), 'domain')):
        if isinstance(obj, dict):
            value = obj.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return 'Non catégorisé'


def standard_folder_name(source: str | Path) -> str:
    """Read internal declared title (fallback slug). Never trust a path label."""
    root = Path(source)
    if root.is_symlink() or not (root / 'kristal.workspace.json').is_file():
        raise ManagerError('Seuls les Kristals avec métadonnées locales peuvent être renommés.')
    data = _read_json(root / 'kristal.workspace.json')
    title = data.get('title') or data.get('slug')
    if not isinstance(title, str) or not title.strip():
        raise ManagerError('Aucun nom déclaré dans kristal.workspace.json : renommage bloqué.')
    normalized = unicodedata.normalize('NFKD', title)
    normalized = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.replace('œ', 'oe').replace('Œ', 'Oe').replace('æ', 'ae').replace('Æ', 'Ae')
    words = re.findall(r'[A-Za-z0-9]+', normalized)
    if words and words[0].casefold() == 'kristal':
        words = words[1:]
    if not words:
        raise ManagerError('Nom interne vide après normalisation : renommage bloqué.')
    normalized_name = 'Kristal-' + '-'.join(words)
    if len(normalized_name) > 120:
        raise ManagerError('Nom interne trop long : intervention manuelle nécessaire.')
    return normalized_name


@dataclass(frozen=True)
class RenamePlan:
    source: Path
    destination: Path
    declared_title: str
    has_history: bool


def plan_rename(source: str | Path, scan_root: str | Path) -> RenamePlan:
    root = Path(scan_root).resolve(strict=True)
    source = Path(source)
    if source.is_symlink() or not source.is_dir():
        raise ManagerError('Dossier manquant ou lien symbolique : renommage interdit.')
    source = source.resolve(strict=True)
    if source.parent != root:
        raise ManagerError('Renommage limité aux Kristals directement sous le dossier inventorié.')
    dest = source.with_name(standard_folder_name(source))
    meta = _read_json(source / 'kristal.workspace.json')
    if dest.name.casefold() != source.name.casefold():
        if any(p.name.casefold() == dest.name.casefold() for p in root.iterdir()):
            raise ManagerError(f'Nom de destination déjà utilisé : {dest.name}')
    if dest.name == source.name:
        raise ManagerError('Le dossier utilise déjà son nom standard.')
    if dest.exists():
        raise ManagerError('Destination existante : renommage bloqué.')
    history = (source / 'archive').exists() or (source / 'archives').exists()
    return RenamePlan(source=source, destination=dest, declared_title=str(meta.get('title') or meta.get('slug')), has_history=history)


def apply_rename(plan: RenamePlan, *, scan_root: str | Path) -> Path:
    """Atomic sibling rename with revalidation at moment of operator approval."""
    fresh = plan_rename(plan.source, scan_root)
    if fresh != plan:
        raise ManagerError('Le dossier a changé depuis la prévisualisation. Recommencer.')
    fresh.source.rename(fresh.destination)
    return fresh.destination


def export_workspace(source: str | Path, destination: str | Path, *, format: str = 'zip',
                     max_file_bytes: int = 4 * 1024**3) -> dict:
    """ZIP preserving one top-level workspace folder; .kristal is *Manager-only*.

    Both are ZIP containers. The .kristal extension is explicitly experimental,
    not a claim of an official Framework exchange profile or restore compatibility.
    """
    if format not in ('zip', 'kristal'):
        raise ManagerError('Format inconnu, utiliser ZIP ou .kristal.')
    root = Path(source)
    if root.is_symlink() or not root.is_dir() or not (root / 'kristal.workspace.json').is_file():
        raise ManagerError('Sélectionner un vrai Kristal contenant kristal.workspace.json.')
    root = root.resolve(strict=True)
    dest = Path(destination).expanduser().absolute()
    if dest.suffix.lower() != '.' + format:
        raise ManagerError('Extension de fichier incorrecte.')
    if dest.is_relative_to(root):
        raise ManagerError('Impossible d’exporter à l’intérieur du Kristal source.')
    if dest.exists():
        raise ManagerError('Le fichier cible existe déjà : choisissez un autre nom.')
    if any(p.is_symlink() for p in root.parents):
        raise ManagerError('Dossier source sous un lien symbolique : export refusé.')
    if not dest.parent.is_dir() or dest.parent.is_symlink():
        raise ManagerError('Le dossier de sortie doit exister et ne pas être un lien.')
    import uuid
    temp = dest.with_name(f'.{dest.name}.{uuid.uuid4().hex}.tmp')
    entries = list(root.rglob('*'))
    for f in entries:
        if f.is_symlink() or not f.resolve().is_relative_to(root):
            raise ManagerError(f'Lien symbolique détecté, export refusé : {f}')
    files = sorted(p for p in entries if p.is_file())
    directories = sorted(p for p in entries if p.is_dir())
    for f in files:
        if f.stat().st_size > max_file_bytes:
            raise ManagerError(f'Fichier trop volumineux pour cette sauvegarde : {f}')
    if format == 'kristal' and (root / 'kristal-manager-export.json').exists():
        raise ManagerError('Manifeste de format expérimental déjà présent dans la source.')
    try:
        with zipfile.ZipFile(temp, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6,
                             allowZip64=True) as z:
            z.writestr(root.name + '/', b'')
            for directory in directories:
                z.writestr(f'{root.name}/{directory.relative_to(root).as_posix()}/', b'')
            if format == 'kristal':
                manifest = {
                    'format': 'kristal.manager-local-archive/0.1-experimental',
                    'warning': 'Not an official Kristal Framework exchange or conformance package.',
                    'source_name': root.name,
                    'title': _read_json(root / 'kristal.workspace.json').get('title'),
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'entries': len(files),
                }
                z.writestr(f'{root.name}/kristal-manager-export.json',
                           json.dumps(manifest, ensure_ascii=False, indent=2))
            for f in files:
                z.write(f, f'{root.name}/{f.relative_to(root).as_posix()}')
        # Check central directory, detect truncated zip before finalizing.
        with zipfile.ZipFile(temp) as z:
            if z.testzip() is not None:
                raise ManagerError('Une entrée de l’archive n’a pas passé la vérification CRC.')
        # Link only if absent: atomic publish without overwriting in another process.
        os.link(temp, dest)
    finally:
        temp.unlink(missing_ok=True)
    return {'path': str(dest), 'files': len(files), 'bytes': dest.stat().st_size,
            'format': format, 'official_framework_package': False}
