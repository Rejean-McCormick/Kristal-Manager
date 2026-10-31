"""Orchestrateur intégré de triage global, sans écriture dans les Kristals.

Sorties distinctes du dépôt de Kristals : catalogue/ et rapports/. L'outil ne
modifie ni identités, ni diK, ni déclarations UNESCO/Arketype, ni publication.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import csv
import json
import os
import secrets
import zipfile

from .content_catalog import build_catalog, write_overview
from .core import ManagerError, scan_roots
from .classification_bridge import build_audit
from .workspace_tools import is_historical
from .operational import assess_local
from . import semantic_triage

MANAGER_ROOT = Path(__file__).resolve().parent.parent
CATALOGUE_PATH = MANAGER_ROOT / 'catalogue' / 'kristal-contenu-global.sqlite3'
RAPPORTS_PATH = MANAGER_ROOT / 'rapports'
FORMAT = 'kristal.manager-global-triage/0.2-candidate'


def _ensure_outside_sources(source: Path, targets: list[Path]) -> None:
    root = source.resolve(strict=True)
    for target in targets:
        out = target.expanduser().resolve()
        if out == root or out.is_relative_to(root):
            raise ManagerError(f'Sortie dans le périmètre scanné interdite : {out}')
        if target.is_symlink():
            raise ManagerError(f'Sortie par lien symbolique interdite : {target}')


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _summary_row(report: dict, record: dict, audit: dict, assessment: dict | None) -> dict:
    ark = report['arketype_inference']; unesco = report['unesco_proposal']
    problems = []
    readiness = record.get('readiness') or 'UNKNOWN'
    state = record.get('state_ref')
    if readiness != 'READY':
        problems.append({'severity': 'warning', 'code': 'LOCAL_NOT_READY', 'detail': readiness})
    if record.get('state_conflict'):
        problems.append({'severity': 'blocker', 'code': 'STATE_CONFLICT', 'detail': 'État courant contradictoire'})
    if record.get('identity_collision'):
        problems.append({'severity': 'blocker', 'code': 'IDENTITY_COLLISION',
                         'detail': 'Identité partagée : examiner les archives/copies, ne rien supprimer automatiquement'})
    if report['status']['content_status'] != 'observed':
        problems.append({'severity': 'warning', 'code': 'CONTENT_NOT_OBSERVED',
                         'detail': report['status']['content_status'] or 'unknown'})
    for issue in report['issues_to_review']:
        problems.append({'severity': 'warning', 'code': 'CONTENT_OR_ALIGNMENT_REVIEW', 'detail': str(issue)})
    for issue in audit.get('issues', []):
        problems.append({'severity': 'warning', 'code': 'TAXONOMY_CONSISTENCY', 'detail': str(issue)})
    if assessment:
        for issue in assessment.get('issues', []):
            severity = issue.get('severity')
            if severity == 'blocker': sev = 'blocker'
            elif severity == 'warning': sev = 'warning'
            else: continue
            problems.append({'severity': sev, 'code': 'LOCAL_' + issue.get('code', 'ISSUE'),
                             'detail': issue.get('message', '')})
    # Unmapped taxonomy and an uncertain structural hypothesis are pending review,
    # not proof of technical non-conformity.
    reviews = []
    if audit.get('unesco', {}).get('status') == 'Not mapped':
        reviews.append('UNESCO non déclaré — examiner les propositions')
    if ark['status'] != 'candidate_to_review':
        reviews.append('Arketype sans indices structurels suffisants')
    else:
        reviews.append('Arketype proposé — validation humaine nécessaire')
    if audit.get('legacy_icon_migration_needed'):
        reviews.append('Icône/classification historique à migrer après validation')
    priority = 'blocker' if any(i['severity'] == 'blocker' for i in problems) else (
        'warning' if problems else 'review' if reviews else 'info')
    arktop = ark.get('primary_candidate')
    utop = (unesco.get('candidates') or [None])[0] if unesco.get('status') == 'candidates_to_review' else None
    dtop = (unesco.get('domain_candidates') or [None])[0]
    return {
        'title': report.get('title'), 'path': report.get('path'), 'state_ref': state,
        'readiness': readiness, 'content_status': report['status']['content_status'],
        'priority': priority, 'problems': problems, 'human_review': reviews,
        'proposed_arketype': arktop.get('arketype_id') if arktop else None,
        'arketype_status': ark['status'],
        'proposed_unesco': utop.get('microthesaurus_code') if utop else None,
        'proposed_unesco_domain': dtop.get('domain_code') if dtop else None,
        'unesco_status': unesco['status'],
        'keywords': [k['term'] for k in report['keyword_summary']['keywords'][:8]],
        'operational_result': assessment.get('operational_result') if assessment else 'NOT_EVALUATED',
        'diagnostic_source': 'Manager local structural assessment' if assessment else 'Inventory + content catalog',
    }


def _plans(entries: list[dict]) -> dict:
    plans = []
    for r in entries:
        suggestions = []
        codes = {issue['code'] for issue in r['problems']}
        if 'IDENTITY_COLLISION' in codes:
            suggestions.append({'action': 'REVIEW_IDENTITY', 'automatable': False,
                 'instruction': 'Distinguer la copie historique du Kristal actif; préserver les state_ref jusqu’à décision.'})
        if 'LOCAL_NOT_READY' in codes:
            suggestions.append({'action': 'REVIEW_STATE_MIGRATION', 'automatable': False,
                 'instruction': 'Inspecter les états existants avec le Framework/Kit avant toute migration.'})
        if 'CONTENT_NOT_OBSERVED' in codes:
            suggestions.append({'action': 'REVIEW_READER', 'automatable': False,
                 'instruction': 'Vérifier si le format est pris en charge par le catalogueur; ne pas inventer de contenu.'})
        if r['unesco_status'] == 'candidates_to_review':
            suggestions.append({'action': 'REVIEW_UNESCO_PROPOSAL', 'automatable': False,
                 'instruction': 'Examiner les preuves et valider explicitement le microthésaurus avant écriture via Kit.'})
        if r['arketype_status'] == 'candidate_to_review':
            suggestions.append({'action': 'REVIEW_ARKETYPE_PROPOSAL', 'automatable': False,
                 'instruction': 'Valider la structure indépendamment du domaine avant déclaration via Kit.'})
        if 'Icône/classification historique à migrer après validation' in r['human_review']:
            suggestions.append({'action': 'REVIEW_LEGACY_ICON', 'automatable': False,
                 'instruction': 'Ne pas mapper automatiquement ISCED à UNESCO; utiliser l’outil d’icônes après approbation.'})
        if suggestions:
            plans.append({'path': r['path'], 'state_ref': r['state_ref'], 'priority': r['priority'],
                          'proposals': suggestions})
    return {'format': 'kristal.manager-correction-plan/0.1-candidate',
            'write_authorized': False, 'auto_apply': False,
            'note': 'Aucune modification canonique automatisée. La normalisation des noms de dossiers reste offerte séparément avec sauvegardes et confirmation.',
            'plans': plans}


def export_problem_bundle(report_dir: str | Path) -> Path:
    """ZIP contenant seulement les résultats dérivés problématiques, jamais les sources."""
    folder = Path(report_dir).resolve(strict=True)
    if not (folder / 'rapport_global.json').is_file():
        raise ManagerError('Dossier de rapport global invalide')
    global_report = json.loads((folder / 'rapport_global.json').read_text('utf-8'))
    if global_report.get('format') != FORMAT:
        raise ManagerError('Format de rapport non reconnu')
    issue_paths = {r['path'] for r in global_report['entries'] if r['priority'] in ('warning', 'blocker')}
    index = {r['path']: r for r in json.loads((folder / 'correspondance_rapports.json').read_text('utf-8'))}
    selected = [folder / 'rapport_global.json', folder / 'plan_corrections.json',
                folder / 'unesco_audit.json', folder / 'semantique' / 'index.json', folder / 'semantique' / 'vue_globale.csv',
                folder / 'correspondance_rapports.json', folder / 'inventaire_observe.json']
    selected += [folder / index[p]['detail_file'] for p in sorted(issue_paths) if p in index]
    selected += [folder / 'verifications_locales.json'] if (folder / 'verifications_locales.json').exists() else []
    output = folder.parent / ('problemes-' + folder.name + '.zip')
    if output.exists():
        raise FileExistsError(f'Un export existe déjà : {output}')
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file in selected:
            path = file.resolve(strict=True)
            if not path.is_relative_to(folder):
                raise ManagerError('Fichier de rapport hors dossier')
            archive.write(path, arcname=path.relative_to(folder).as_posix())
        archive.writestr('LIRE_AVANT_PARTAGE.txt',
            'Rapports dérivés seulement; pas de Kristals sources. Les chemins locaux, sujets et mots-clés peuvent être sensibles. Vérifier avant tout partage.\n'
            'Un rapport de triage ne prouve pas une non-conformité Framework, diK ou UNESCO.\n')
    return output


def analyze_all(source: str | Path, *, update_catalogue: bool = True,
                verify_locally: bool = False, catalogue: str | Path | None = None,
                reports_base: str | Path | None = None) -> dict:
    """Pipeline unique, optimisé par le cache du catalogue pour les sources inchangées."""
    root = Path(source).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ManagerError('La source doit être un dossier Kristals existant')
    database = Path(catalogue or CATALOGUE_PATH).expanduser().absolute()
    reports_dir = Path(reports_base or RAPPORTS_PATH).expanduser().absolute()
    _ensure_outside_sources(root, [database, database.with_suffix('.html'), reports_dir])
    if database.is_symlink() or reports_dir.is_symlink():
        raise ManagerError('Lien symbolique de sortie interdit')
    if not update_catalogue and not database.is_file():
        raise ManagerError('Aucun catalogue existant : lancer une analyse avec actualisation du catalogue')
    reports_dir.mkdir(parents=True, exist_ok=True)
    # Unique name prevents collision and makes analyses comparable over time.
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    output = reports_dir / f'analyse-{stamp}-{secrets.token_hex(3)}'
    if update_catalogue:
        database.parent.mkdir(parents=True, exist_ok=True)
        catalog_stats = build_catalog([root], database)
        write_overview(database, database.with_suffix('.html'), overwrite=True)
    else:
        catalog_stats = {'database': str(database), 'workspaces': None, 'updated': 0,
                         'cached': None, 'reused_existing_catalog': True}
    # Read metadata once. Only current workspaces are eligible for taxonomy audits.
    all_rows = [r for r in scan_roots([root]) if not r.get('hidden_auxiliary')]
    rows = [r for r in all_rows if not is_historical(r)]
    audit = build_audit(rows)
    output.mkdir(parents=False, exist_ok=False)
    audit_path = output / 'unesco_audit.json'
    _write_json(audit_path, audit)
    # Triage is imported, not launched as a second program or shell subprocess.
    semantic_triage.main(['--catalogue', str(database), '--audit', str(audit_path), '--out', str(output / 'semantique')], quiet=True)
    semdir = output / 'semantique'
    details = []
    refs = {}
    for file in sorted((semdir / 'kristals').glob('*.json')):
        record = json.loads(file.read_text('utf-8'))
        details.append(record)
        refs[record['path'].casefold()] = {'detail_file': file.relative_to(output).as_posix()}
    by_path = {r['path'].casefold(): r for r in rows}
    audit_by_path = {r['path'].casefold(): r for r in audit['entries']}
    # Optional integrity verification (sha256 of registered source files) can be slow;
    # cap concurrency, never invoke any external executable or Kristal code.
    checks = {}
    if verify_locally:
        def verify(row):
            try:
                return row['path'], assess_local(row['path'])
            except (OSError, ValueError, ManagerError) as exc:
                return row['path'], {'operational_result': 'NOT_EVALUATED', 'issues': [
                    {'severity': 'warning', 'code': 'VERIFIER_ERROR', 'message': str(exc)[:350]}]}
        with ThreadPoolExecutor(max_workers=4) as pool:
            jobs = [pool.submit(verify, row) for row in rows]
            for completed in as_completed(jobs):
                key, assessment = completed.result()
                checks[key.casefold()] = assessment
        _write_json(output / 'verifications_locales.json', checks)
    items = []
    for rec in details:
        key = rec['path'].casefold()
        current = by_path.get(key)
        if current is None:
            # A reused catalog may have stale paths; don't pretend a source was observed.
            current = {'readiness': 'NOT_IN_CURRENT_INVENTORY', 'state_ref': rec.get('state_ref')}
        items.append(_summary_row(rec, current, audit_by_path.get(key, {}), checks.get(key)))
    priorities = Counter(item['priority'] for item in items)
    result = {'format': FORMAT, 'generated_at': datetime.now(timezone.utc).isoformat(),
              'source': str(root), 'catalogue': str(database), 'catalog_stats': catalog_stats,
              'semantic_reports': str(semdir), 'verification_mode': 'local_integrity' if verify_locally else 'inventory_only',
              'counts': {'kristals': len(items), **{k:priorities.get(k, 0) for k in ('blocker', 'warning', 'review', 'info')},
                         'arketype_candidates': sum(r['arketype_inference']['status']=='candidate_to_review' for r in details),
                         'unesco_micro_candidates': sum(r['unesco_proposal']['status']=='candidates_to_review' for r in details),
                         'unesco_domain_candidates': sum(bool(r['unesco_proposal']['domain_candidates']) for r in details)},
              'entries': items,
              'limits': ['Scores UNESCO et Arketype = propositions non canoniques.',
                         'diK = observations lexicales; aucun contrat de normalisation d’identités n’est exécuté.',
                         'Sans KristalDiag et Framework externe, aucune certification C1/C2/C3.',
                         'Les anomalies détectées ne prouvent pas à elles seules une non-conformité.']}
    _write_json(output / 'rapport_global.json', result)
    _write_json(output / 'inventaire_observe.json', [{'title': r.get('title'), 'path': r.get('path'), 'state_ref': r.get('state_ref'), 'readiness': r.get('readiness'), 'historical_archive': is_historical(r)} for r in all_rows])
    _write_json(output / 'plan_corrections.json', _plans(items))
    _write_json(output / 'correspondance_rapports.json', [dict(path=r['path'], **refs.get(r['path'].casefold(), {})) for r in items])
    # One convenient single-file CSV; preserve explicit tentative labels.
    with (output / 'tableau_global.csv').open('w', newline='', encoding='utf-8-sig') as out:
        fields = ('title', 'readiness', 'content_status', 'priority', 'proposed_arketype',
                  'proposed_unesco_domain', 'proposed_unesco', 'keywords', 'problem_count', 'path')
        writer = csv.DictWriter(out, fieldnames=fields); writer.writeheader()
        for r in items:
            writer.writerow({**{k:r.get(k) for k in fields}, 'keywords': '; '.join(r['keywords']),
                             'problem_count': len(r['problems'])})
    archive = export_problem_bundle(output)
    return {'report_directory': str(output), 'problem_archive': str(archive),
            'global_report': result, 'inventory': all_rows, 'catalog_stats': catalog_stats,
            'html_report': str(semdir / 'rapport.html'), 'index_path': str(output / 'rapport_global.json')}
