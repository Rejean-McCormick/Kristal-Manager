"""Whole-project, read-only folder inventory for requesting complete Kristal ZIP bundles.

This counts *all* regular files (including hidden, .git, snapshots, tools, assets),
not merely selected canonical artifacts. No hashing, copying, conversion or writes.
Symbolic links / reparse points are never followed. Reports are observations, not
permission to remove or exclude any project file.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat

FORMAT = 'kristal.manager-bundle-inventory/1.0'
META_LIMIT = 2 * 1024 * 1024
MAX_REPORTED_ISSUES = 30
MAX_BIG_FILES = 5


def _is_link_or_reparse(path: Path) -> bool:
    """Include Windows junction/reparse points in exclusions without traversing."""
    attrs = path.lstat()
    return stat.S_ISLNK(attrs.st_mode) or bool(getattr(attrs, 'st_file_attributes', 0) & 0x400)


def _declared(root: Path) -> dict:
    """Return only *declared* workspace metadata; never derive Arketype tags."""
    result = {'state_ref': None, 'primary_archetype': None, 'structure_mode': None,
              'source': None, 'note': None}
    source = root / 'kristal.workspace.json'
    try:
        if _is_link_or_reparse(source):
            result['note'] = 'Workspace symlink/reparse: metadata not read'
            return result
        if source.stat().st_size > META_LIMIT:
            result['note'] = 'Workspace too large: metadata not read'
            return result
        workspace = json.loads(source.read_text(encoding='utf-8'))
        if not isinstance(workspace, dict):
            result['note'] = 'Workspace JSON root is not an object'
            return result
        result['state_ref'] = workspace.get('state_ref') if isinstance(workspace.get('state_ref'), str) else None
        cl = workspace.get('classification')
        if isinstance(cl, dict):
            result['primary_archetype'] = cl.get('primary_archetype') if isinstance(cl.get('primary_archetype'), str) else None
            result['structure_mode'] = cl.get('structure_mode') if isinstance(cl.get('structure_mode'), str) else None
        result['source'] = 'kristal.workspace.json'
    except (OSError, ValueError, UnicodeError, TypeError) as err:
        result['note'] = f'Workspace metadata unavailable: {type(err).__name__}'
    return result


def _project_candidates(source: Path) -> list[Path]:
    if (source / 'kristal.workspace.json').is_file():
        return [source]
    candidates = []
    for child in source.iterdir():
        if not child.is_dir() or _is_link_or_reparse(child):
            continue
        if (child / 'kristal.workspace.json').is_file() or child.name.casefold().startswith('kristal-'):
            candidates.append(child)
    return sorted(candidates, key=lambda p: (p.name.casefold(), p.name))


def scan_project(root: Path | str) -> dict:
    root = Path(root)
    result = {'project':root.name,'relative_dir':root.name,'path':str(root),
              'bytes_total':0,'bytes_canon':0,'bytes_noncanon':0,
              'file_count':0,'directory_count':0,'top_level_bytes':{},
              'largest_files':[], 'links_skipped':0,'files_failed':0,
              'issues':[],'measurement_complete':True,'declaration':_declared(root)}
    big = []

    def issue(kind: str, relative: str):
        if len(result['issues']) < MAX_REPORTED_ISSUES:
            result['issues'].append({'kind':kind,'path':relative})

    # scandir is shallow/metadata-only and avoids reading the possibly huge files.
    todo = [root]
    while todo:
        current = todo.pop()
        try:
            with os.scandir(current) as it:
                entries = list(it)
        except OSError as exc:
            result['files_failed'] += 1
            issue('directory_unreadable:'+type(exc).__name__, str(current.relative_to(root)).replace('\\','/'))
            result['measurement_complete'] = False
            continue
        for entry in entries:
            p = Path(entry.path)
            relative = p.relative_to(root)
            rel = relative.as_posix()
            try:
                st = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(st.st_mode) or getattr(st,'st_file_attributes',0) & 0x400:
                    result['links_skipped'] += 1
                    result['measurement_complete'] = False
                    issue('link_or_reparse_not_followed',rel)
                    continue
                if stat.S_ISDIR(st.st_mode):
                    result['directory_count'] += 1
                    todo.append(p)
                    continue
                if not stat.S_ISREG(st.st_mode):
                    result['files_failed'] += 1
                    result['measurement_complete'] = False
                    issue('non_regular_file',rel)
                    continue
                size = st.st_size
                result['file_count'] += 1
                result['bytes_total'] += size
                first = relative.parts[0].casefold() if len(relative.parts) > 1 else '(racine)'
                result['top_level_bytes'][first] = result['top_level_bytes'].get(first,0) + size
                if first == 'canon':
                    result['bytes_canon'] += size
                big.append((size,rel))
                # Maintain only the largest files (avoid holding every file path in RAM).
                if len(big) > MAX_BIG_FILES:
                    big.sort(reverse=True)
                    del big[MAX_BIG_FILES:]
            except OSError as exc:
                result['files_failed'] += 1
                result['measurement_complete'] = False
                issue('file_unreadable:'+type(exc).__name__,rel)
    result['bytes_noncanon'] = result['bytes_total'] - result['bytes_canon']
    result['top_level_bytes'] = dict(sorted(result['top_level_bytes'].items(), key=lambda kv:(-kv[1],kv[0])))
    result['largest_files'] = [{'path':rel,'size_bytes':size} for size,rel in sorted(big,reverse=True)]
    return result


def scan_inventory(source: Path | str) -> dict:
    source = Path(source).expanduser().resolve(strict=True)
    if not source.is_dir():
        raise ValueError('Le dossier source doit exister.')
    roots = _project_candidates(source)
    if not roots:
        raise ValueError('Aucun dossier Kristal reconnu dans la source.')
    projects = []
    for root in roots:
        try:
            projects.append(scan_project(root))
        except OSError as exc:
            projects.append({'project':root.name,'relative_dir':root.name, 'path':str(root),
                 'bytes_total':0,'bytes_canon':0,'bytes_noncanon':0,'file_count':0,
                 'directory_count':0,'top_level_bytes':{},'largest_files':[],
                 'links_skipped':0,'files_failed':1,
                 'issues':[{'kind':type(exc).__name__,'path':'(racine)'}],
                 'measurement_complete':False,'declaration':{}})
    return {'format':FORMAT,'generated_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
       'source':str(source),'counts':{'projects':len(projects),
       'total_bytes':sum(r['bytes_total'] for r in projects),
       'total_files':sum(r['file_count'] for r in projects),
       'total_canon_bytes':sum(r['bytes_canon'] for r in projects),
       'incomplete_projects':sum(not r['measurement_complete'] for r in projects)},
       'projects':projects,
       'limits':['Octets locaux bruts (non compressés); la taille ZIP réelle n’est pas connue.',
                 'Tous les fichiers réguliers sont comptés: historique, .git, dérivés, médias et outils inclus.',
                 'Les liens symboliques et jonctions ne sont jamais suivis et rendent la mesure incomplète.',
                 'Un fichier inaccessible rend le total un minimum, pas une taille définitive.',
                 'Les tags ARK proviennent du workspace, sans inférence ni validation.',
                 'Aucun fichier de Kristal n’est lu en contenu sauf le petit workspace JSON de métadonnées.',
                 'Ce rapport n’est ni une validation canonique, ni une certification Framework.']}


def format_brief(report: dict) -> str:
    counts = report['counts']
    lines = ['KRISTAL MANAGER — INVENTAIRE TAILLES & TAGS POUR BUNDLES COMPLETS',
       'Format : '+report['format'], 'Date UTC : '+report['generated_utc'],
       'Source : '+report['source'],
       f"Totaux : {counts['projects']} Kristals; {counts['total_files']} fichiers; "
       f"{counts['total_bytes']} octets; incomplets={counts['incomplete_projects']}.",
       'Chaque ligne : dossier | octets bruts | fichiers | octets canon | tag ARK déclaré | état scan',
       '']
    for r in report['projects']:
        cl = r.get('declaration') or {}
        lines.append(f"{r['relative_dir']} | {r['bytes_total']} | {r['file_count']} | {r['bytes_canon']} | "
           f"{cl.get('primary_archetype') or '—'} | {'COMPLET' if r['measurement_complete'] else 'INCOMPLET'}")
    lines += ['','LIMITES :', *(('- '+x) for x in report['limits']),
       'Demande : proposer des listes de packs de dossiers complets, en équilibrant taille et complexité.',
       'Ne pas écrire de tags, ne pas retirer de fichiers et ne pas créer de ZIP à partir de ce seul rapport.']
    return '\n'.join(lines)+'\n'
