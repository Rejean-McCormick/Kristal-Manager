"""Import deterministic, read-only observations from a Kristalizer 1.2.x scan ZIP.

Never interprets a Wikidata candidate as a confirmed identity. No file under
locals/ or canon/ is written; only reports under the Manager reports directory.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import io
import json
import os
import zipfile

FORMAT = 'kristal.manager-kristalizer-observation/1.0'
LATEST_NAME = 'dernier.json'
BUILD_LATEST_NAME = 'dernier-build.json'
BUILD_FORMAT = 'kristal.manager-kristalizer-build-observation/1.0'
MAX_ZIP_BYTES = 25 * 1024 * 1024
MAX_MEMBER_BYTES = 12 * 1024 * 1024
EXPECTED = {
    'ANALYSE/RAPPORT.json',
    'ANALYSE/CANDIDATS.csv',
    'ANALYSE/DECISIONS.csv',
    'ANALYSE/LIAISONS_NOTIONS_ASSERTIONS.csv',
    'ANALYSE/NOTIONS_DOMAINE.csv',
    'ANALYSE/SUGGESTIONS_NOTIONS_WIKIDATA.csv',
}


def _read_checked(archive: zipfile.ZipFile, name: str) -> bytes:
    try:
        item = archive.getinfo(name)
    except KeyError as exc:
        raise ValueError(f'Rapport Kristalizer incomplet : {name}') from exc
    if item.is_dir() or item.file_size > MAX_MEMBER_BYTES:
        raise ValueError('Fichier de rapport invalide ou trop volumineux : ' + name)
    value = archive.read(item)
    if len(value) != item.file_size:
        raise ValueError('Fichier de rapport incomplet : ' + name)
    return value


def _csv_rows(raw: bytes, name: str) -> list[dict]:
    try:
        contents = raw.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(contents))
        if not reader.fieldnames or any(not c for c in reader.fieldnames):
            raise ValueError('CSV sans en-têtes : ' + name)
        rows = list(reader)
        if any(None in row for row in rows):
            raise ValueError('CSV avec des colonnes inattendues : ' + name)
        return rows
    except UnicodeError as exc:
        raise ValueError('CSV illisible : ' + name) from exc


def summarize_zip(zip_path: str | Path) -> dict:
    """Validate report consistency and return a small, tentative index by project."""
    path = Path(zip_path).expanduser().resolve(strict=True)
    if not path.is_file() or path.stat().st_size > MAX_ZIP_BYTES:
        raise ValueError('ZIP Kristalizer absent ou trop volumineux')
    try:
        with zipfile.ZipFile(path) as arc:
            if len(arc.namelist()) != len(set(arc.namelist())):
                raise ValueError('ZIP Kristalizer ambigu : noms de fichiers dupliqués')
            files = {name: _read_checked(arc, name) for name in EXPECTED}
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise ValueError('ZIP Kristalizer illisible : ' + str(exc)) from exc

    try:
        raw_report = json.loads(files['ANALYSE/RAPPORT.json'].decode('utf-8-sig'))
    except (ValueError, UnicodeError) as exc:
        raise ValueError('RAPPORT.json incorrect') from exc
    if not isinstance(raw_report, dict) or raw_report.get('format') != 'kristal.kristalizer.scan/1.2.2':
        raise ValueError('Version du scan Kristalizer non prise en charge (1.2.2 attendu)')
    detail = raw_report.get('projects_detail')
    if not isinstance(detail, list) or not all(isinstance(row, dict) for row in detail):
        raise ValueError('Liste de projets Kristalizer invalide')
    names = [row.get('project') for row in detail]
    if any(not isinstance(name, str) or not name.strip() or '/' in name or '\\' in name for name in names):
        raise ValueError('Noms de projets invalides')
    if len(names) != len(set(n.casefold() for n in names)) or len(names) != raw_report.get('projects'):
        raise ValueError('Doublons ou comptes de projets incohérents')
    candidates = _csv_rows(files['ANALYSE/CANDIDATS.csv'], 'CANDIDATS.csv')
    decisions = _csv_rows(files['ANALYSE/DECISIONS.csv'], 'DECISIONS.csv')
    links = _csv_rows(files['ANALYSE/LIAISONS_NOTIONS_ASSERTIONS.csv'], 'LIAISONS_NOTIONS_ASSERTIONS.csv')
    topics = _csv_rows(files['ANALYSE/NOTIONS_DOMAINE.csv'], 'NOTIONS_DOMAINE.csv')
    suggestions = _csv_rows(files['ANALYSE/SUGGESTIONS_NOTIONS_WIKIDATA.csv'], 'SUGGESTIONS_NOTIONS_WIKIDATA.csv')
    lengths = {
        'candidates': len(candidates), 'native_claim_links': len(links),
        'domain_topics': len(topics), 'topic_wikidata_suggestions': len(suggestions),
    }
    for key, actual in lengths.items():
        if raw_report.get(key) != actual:
            raise ValueError(f'Comptage incohérent pour {key} : {actual} != {raw_report.get(key)}')
    if len(decisions) != len(candidates):
        raise ValueError('Décisions/candidats Wikidata non alignés')
    project_set = set(names)
    for group in (candidates, links, topics, suggestions, decisions):
        if any(row.get('project') not in project_set for row in group):
            raise ValueError('Un rapport contient un projet non déclaré')
    if sum(row.get('state') == 'MIGRATION_V11_REQUISE' for row in detail) != raw_report.get('migration_required'):
        raise ValueError('Nombre de migrations incohérent')

    p_candidates = Counter(row['project'] for row in candidates)
    p_unique = defaultdict(set)
    p_risks = defaultdict(Counter)
    for row in candidates:
        p_unique[row['project']].add((row.get('kind'), row.get('local_id')))
        p_risks[row['project']][row.get('risk') or 'INCONNU'] += 1
    p_topics = Counter(row['project'] for row in topics)
    p_links = Counter(row['project'] for row in links)
    pending = Counter(row.get('decision') or 'non renseignée' for row in decisions)
    per = {}
    for row in detail:
        name = row['project']
        state = row.get('state')
        if state not in ('V11_NON_ACTIVE', 'MIGRATION_V11_REQUISE'):
            raise ValueError('État v11 inattendu : ' + str(state))
        per[name] = {
            'v11': state, 'candidates': p_candidates[name],
            'local_identities_with_candidates': len(p_unique[name]),
            'candidate_risks': dict(sorted(p_risks[name].items())),
            'documentary_topics': p_topics[name], 'native_claim_links': p_links[name],
            'indexed_labels': row.get('indexed_labels'), 'roles': row.get('roles') or {},
            'read_only': True,
        }
    return {
        'format': FORMAT,
        'source_format': raw_report['format'],
        'source_generated_at': raw_report.get('generated_at'),
        'imported_at': datetime.now(timezone.utc).isoformat(),
        'source_zip_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'source_zip_name': path.name,
        'projects': per,
        'totals': {
            'projects': len(per), 'v11_non_active': sum(x['v11'] == 'V11_NON_ACTIVE' for x in per.values()),
            'migration_required': raw_report['migration_required'],
            'wikidata_candidates': len(candidates),
            'distinct_local_identifiers': len({(r['project'], r.get('kind'), r.get('local_id')) for r in candidates}),
            'documentary_topics': len(topics),
            'native_claim_links': len(links),
            'unresolved_claim_links': raw_report.get('unresolved_claim_links'),
            'indexed_connected': bool((raw_report.get('indexed') or {}).get('connected')),
            'wikidata_decision_counts': dict(sorted(pending.items())),
        },
        'qualification': 'NON_EVALUEE',
        'write_authorized': False, 'auto_publish': False,
        'notice': 'Résultats Kristalizer provisoires. Aucun exactMatch, KS, KA, KQ ou KP n’est validé par l’import. Les données canoniques ne sont pas modifiées.',
    }


def import_report(zip_path: str | Path, reports_root: str | Path) -> dict:
    report = summarize_zip(zip_path)
    root = Path(reports_root).expanduser().resolve()
    if root.is_symlink():
        raise ValueError('Dossier de rapports via lien symbolique interdit')
    folder = root / 'kristalizer-imports'
    folder.mkdir(parents=True, exist_ok=True)
    if folder.is_symlink():
        raise ValueError('Dossier d’import via lien symbolique interdit')
    target = folder / LATEST_NAME
    if target.is_symlink():
        raise ValueError('Rapport importé via lien symbolique interdit')
    temp = folder / ('.import-' + report['source_zip_sha256'][:16] + '.tmp')
    temp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, target)
    return report


def load_last_import(reports_root: str | Path) -> dict | None:
    target = Path(reports_root).expanduser().resolve() / 'kristalizer-imports' / LATEST_NAME
    if target.is_symlink() or not target.is_file():
        return None
    result = json.loads(target.read_text(encoding='utf-8'))
    if not isinstance(result, dict) or result.get('format') != FORMAT:
        return None
    return result


def lookup(report: dict | None, name_or_path: str | None) -> dict | None:
    if not report or not name_or_path:
        return None
    name = str(name_or_path).replace('\\', '/').rstrip('/').rsplit('/', 1)[-1].casefold()
    for project, value in report.get('projects', {}).items():
        if project.casefold() == name:
            return value
    return None


def summarize_build_zip(zip_path: str | Path) -> dict:
    """Read a Kristalizer 1.2.x STAGING/BUILD report, never activate anything.

    The report certifies only what happened to copies in staging. It cannot
    prove canonical correctness of original projects, or any Framework level.
    """
    path = Path(zip_path).expanduser().resolve(strict=True)
    if not path.is_file() or path.stat().st_size > MAX_ZIP_BYTES:
        raise ValueError('ZIP de build absent ou trop volumineux')
    expected = ('STAGING/KRISTALIZER_STAGE_REPORT.json',
                'STAGING/KRISTALIZER_BUILD_REPORT.json', 'ANALYSE/RAPPORT.json')
    try:
        with zipfile.ZipFile(path) as archive:
            if len(archive.namelist()) != len(set(archive.namelist())):
                raise ValueError('ZIP ambigu : noms de fichiers dupliqués')
            raw = {name: json.loads(_read_checked(archive, name).decode('utf-8-sig'))
                   for name in expected}
    except (zipfile.BadZipFile, RuntimeError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('ZIP de build Kristalizer illisible : '+str(exc)) from exc
    stage = raw[expected[0]]
    build = raw[expected[1]]
    scan = raw[expected[2]]
    if not all(isinstance(x, dict) for x in (stage, build, scan)):
        raise ValueError('Les rapports Kristalizer doivent être des objets JSON')
    if (stage.get('format') != 'kristal.kristalizer.stage/1.1' or
        build.get('format') != 'kristal.kristalizer.build/1.1' or
        scan.get('format') != 'kristal.kristalizer.scan/1.2.2'):
        raise ValueError('Formats Kristalizer inconnus : scan 1.2.2 / stage 1.1 / build 1.1 requis')
    if build.get('staging') != stage.get('staging'):
        raise ValueError('Dossiers STAGING incohérents entre les rapports')
    for x, label in ((stage,'stage'), (build,'build'), (scan,'scan')):
        if not isinstance(x.get('projects') if label!='scan' else x.get('projects_detail'), list):
            raise ValueError('Liste de projets absente du '+label)
    names = [x.get('project') for x in stage['projects']]
    scan_names = [x.get('project') for x in scan['projects_detail']]
    build_names = [x.get('project') for x in build['projects']]
    if (any(not isinstance(n, str) or not n.strip() or '/' in n or '\\' in n or n in ('.','..') for n in names)
        or len(names) != len(set(n.casefold() for n in names))
        or set(names) != set(scan_names) or set(names) != set(build_names)
        or len(names) != len(build_names) or len(names) != len(scan_names)
        or len(names) != scan.get('projects')):
        raise ValueError('Incohérence entre les projets scan, staging et build')
    if stage.get('source_modified') is not False:
        raise ValueError('Le rapport de staging ne confirme pas le respect des sources')
    allowed = {'BUILT', 'MIGRATION_MANUELLE_V11', 'FAILED', 'ACTIVE', 'PUBLIE'}
    stages = {x['project']:x for x in stage['projects']}
    per = {}
    for x in build['projects']:
        name = x['project']
        status = x.get('status')
        if status not in allowed:
            raise ValueError('État build inconnu pour '+name+': '+str(status))
        if stages[name].get('status') == 'MIGRATION_MANUELLE_V11' and status != 'MIGRATION_MANUELLE_V11':
            raise ValueError('Un projet sans v11 est décrit comme construit : '+name)
        if status in {'BUILT', 'PUBLIE', 'ACTIVE'} and x.get('checks') != 'passed':
            raise ValueError('Build sans vérifications réussies : '+name)
        if status == 'ACTIVE' and not build.get('activate'):
            raise ValueError('Activation de build incohérente : '+name)
        if status == 'PUBLIE' and not build.get('publish'):
            raise ValueError('Publication de build incohérente : '+name)
        per[name] = {
            'status': status,
            'status_staging': stages[name].get('status'),
            'checks': x.get('checks'),
            'failure_phase': x.get('phase') if status == 'FAILED' else None,
            'failure_detail': x.get('error') if status == 'FAILED' else None,
            'staged_copy_only': not bool(build.get('publish') or build.get('activate')),
        }
    counts = Counter(x['status'] for x in per.values())
    if build.get('failures') != counts['FAILED']:
        raise ValueError('Nombre d’échecs de build incohérent')
    kit = build.get('authoring_kit') or {}
    if not isinstance(kit, dict):
        raise ValueError('Métadonnées Authoring Kit invalides')
    return {
        'format': BUILD_FORMAT, 'source_format': build['format'],
        'scan_generated_at': scan.get('generated_at'),
        'imported_at': datetime.now(timezone.utc).isoformat(),
        'source_zip_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'source_zip_name': path.name,
        'staging': build['staging'],
        'projects': per,
        'totals': {'projects': len(per), 'built': counts['BUILT'],
                   'migration_required': counts['MIGRATION_MANUELLE_V11'],
                   'failed': counts['FAILED'], 'published': counts['PUBLIE'],
                   'activated': counts['ACTIVE'], 'source_modified': stage['source_modified'],
                   'domain_assertions_added_by_stage': stage.get('canon_domain_assertions_added'),
                   'kit_version': kit.get('version'), 'kit_framework_pin': kit.get('framework_pin')},
        'qualification': 'NON_EVALUEE', 'canonical_source_modified': False,
        'notice': 'Résultats du Kit sur COPIES seulement. BUILT ne signifie ni activation, ni certification Framework C1/C2/C3, ni correction sémantique.',
    }



def merge_build_observations(previous: dict | None, incoming: dict) -> dict:
    """Consolide les lots partiels SANS perdre les statuts des autres projets.

    Choisit pour chaque projet le rapport de scan le plus récent. Les preuves
    restent des observations de constructions sur COPIES, jamais des activations.
    """
    if not previous or previous.get('format') != BUILD_FORMAT:
        previous = None
    combined = {}
    sources = {}
    for report in (previous, incoming):
        if not report:
            continue
        date = report.get('scan_generated_at') or ''
        for project, entry in report.get('projects', {}).items():
            if not isinstance(project, str) or not isinstance(entry, dict):
                continue
            value = dict(entry)
            item_date = value.get('observation_scan_generated_at') or date
            old = combined.get(project)
            if old and (old.get('observation_scan_generated_at') or '') > item_date:
                continue  # Réimporter un ancien lot ne fait pas régresser un projet.
            value['observation_scan_generated_at'] = item_date
            value['observation_source_zip'] = (value.get('observation_source_zip')
                                                or report.get('source_zip_name'))
            value['observation_source_sha256'] = (value.get('observation_source_sha256')
                                                   or report.get('source_zip_sha256'))
            combined[project] = value
        for source_entry in report.get('source_reports') or []:
            if isinstance(source_entry, dict) and source_entry.get('sha256'):
                sources[source_entry['sha256']] = source_entry
        sha = report.get('source_zip_sha256')
        if sha:
            sources[sha] = {
                'sha256': sha, 'name': report.get('source_zip_name'),
                'scan_generated_at': date, 'staging': report.get('staging'),
            }
    counts = Counter(x.get('status') for x in combined.values())
    chosen = dict(incoming if not previous or (incoming.get('scan_generated_at') or '') >= (previous.get('scan_generated_at') or '') else previous)
    chosen['projects'] = dict(sorted(combined.items()))
    chosen['totals'] = dict(incoming['totals'])
    chosen['totals'].update({
        'projects': len(combined), 'built': counts['BUILT'],
        'migration_required': counts['MIGRATION_MANUELLE_V11'],
        'failed': counts['FAILED'], 'published': counts['PUBLIE'],
        'activated': counts['ACTIVE'], 'source_modified': False,
    })
    chosen['aggregated'] = True
    chosen['source_reports'] = sorted(sources.values(),
                                      key=lambda x: (x.get('scan_generated_at') or '', x.get('sha256')))
    chosen['totals']['source_batches'] = len(chosen['source_reports'])
    chosen['notice'] = ('Synthèse cumulative par projet : chaque ligne conserve la date et '
                        'la source du dernier BUILD sur COPIE. Aucune activation, '
                        'publication, ni qualification Framework C1/C2/C3.')
    return chosen


def import_build_report(zip_path: str | Path, reports_root: str | Path) -> dict:
    observation = summarize_build_zip(zip_path)
    # La fusion s'effectue depuis le dernier état validé, jamais depuis les sources.
    previous = load_last_build(reports_root)
    observation = merge_build_observations(previous, observation)
    root = Path(reports_root).expanduser().resolve()
    if root.is_symlink():
        raise ValueError('Dossier de rapports via lien symbolique interdit')
    folder = root / 'kristalizer-imports'
    folder.mkdir(parents=True, exist_ok=True)
    if folder.is_symlink():
        raise ValueError('Dossier d’import via lien symbolique interdit')
    target = folder / BUILD_LATEST_NAME
    if target.is_symlink():
        raise ValueError('Rapport build via lien symbolique interdit')
    temp = folder / ('.import-build-' + observation['source_zip_sha256'][:16] + '.tmp')
    temp.write_text(json.dumps(observation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, target)
    return observation


def load_last_build(reports_root: str | Path) -> dict | None:
    target = Path(reports_root).expanduser().resolve() / 'kristalizer-imports' / BUILD_LATEST_NAME
    if target.is_symlink() or not target.is_file():
        return None
    value = json.loads(target.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or value.get('format') != BUILD_FORMAT:
        return None
    return value


def lookup_build(report: dict | None, name_or_path: str | None) -> dict | None:
    return lookup(report, name_or_path)
