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
            raise ManagerError(f'Output inside scanned source folder is forbidden: {out}')
        if target.is_symlink():
            raise ManagerError(f'Output through symlink forbidden: {target}')


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
        problems.append({'severity': 'blocker', 'code': 'STATE_CONFLICT', 'detail': 'Contradictory current state'})
    if record.get('identity_collision'):
        problems.append({'severity': 'blocker', 'code': 'IDENTITY_COLLISION',
                         'detail': 'Shared identity: review archives/copies; do not delete anything automatically'})
    # A native-observed contract can be valid without conforming to a KQ/KP graph.
    # It is a review item, not a reader failure or a Framework qualification.
    if report['status']['content_status'] not in ('observed', 'native_observed'):
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
    if report['status']['content_status'] == 'native_observed':
        reviews.append('Native contract recognized; KQ/KP semantics and Framework conformance not evaluated')
    unesco_observation_status = audit.get('unesco', {}).get('status')
    if unesco_observation_status == 'Not mapped':
        reviews.append('UNESCO not declared — review proposals')
    elif unesco_observation_status == 'Proposed':
        reviews.append('Local UNESCO proposal — recognized codes; semantic validation required')
    if ark['status'] != 'candidate_to_review':
        reviews.append('Insufficient structural evidence for Arketype')
    else:
        reviews.append('Proposed Arketype — human review required')
    if audit.get('legacy_icon_migration_needed'):
        reviews.append('Historical icon/classification needs migration after approval')
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
                 'instruction': 'Distinguish historical copy from active Kristal; preserve state_ref until a decision is made.'})
        if 'LOCAL_NOT_READY' in codes:
            suggestions.append({'action': 'REVIEW_STATE_MIGRATION', 'automatable': False,
                 'instruction': 'Inspect existing states with Framework/Kit before migration.'})
        if 'CONTENT_NOT_OBSERVED' in codes:
            suggestions.append({'action': 'REVIEW_READER', 'automatable': False,
                 'instruction': 'Check whether the catalog reader supports this format; do not invent content.'})
        if r['unesco_status'] == 'candidates_to_review':
            suggestions.append({'action': 'REVIEW_UNESCO_PROPOSAL', 'automatable': False,
                 'instruction': 'Review evidence and explicitly validate the microthesaurus before writing via Kit.'})
        if r['arketype_status'] == 'candidate_to_review':
            suggestions.append({'action': 'REVIEW_ARKETYPE_PROPOSAL', 'automatable': False,
                 'instruction': 'Validate structure independently of subject matter before declaration via Kit.'})
        if 'Historical icon/classification needs migration after approval' in r['human_review']:
            suggestions.append({'action': 'REVIEW_LEGACY_ICON', 'automatable': False,
                 'instruction': 'Do not map ISCED to UNESCO automatically; use the icon tool after approval.'})
        if suggestions:
            plans.append({'path': r['path'], 'state_ref': r['state_ref'], 'priority': r['priority'],
                          'proposals': suggestions})
    return {'format': 'kristal.manager-correction-plan/0.1-candidate',
            'write_authorized': False, 'auto_apply': False,
            'note': 'No automated canonical changes. Folder name normalization remains separate with backups and confirmation.',
            'plans': plans}


def export_problem_bundle(report_dir: str | Path) -> Path:
    """ZIP contenant seulement les résultats dérivés problématiques, jamais les sources."""
    folder = Path(report_dir).resolve(strict=True)
    if not (folder / 'rapport_global.json').is_file():
        raise ManagerError('Invalid global report folder')
    global_report = json.loads((folder / 'rapport_global.json').read_text('utf-8'))
    if global_report.get('format') != FORMAT:
        raise ManagerError('Unrecognized report format')
    issue_paths = {r['path'] for r in global_report['entries'] if r['priority'] in ('warning', 'blocker')}
    index = {r['path']: r for r in json.loads((folder / 'correspondance_rapports.json').read_text('utf-8'))}
    selected = [folder / 'rapport_global.json', folder / 'plan_corrections.json',
                folder / 'unesco_audit.json', folder / 'semantique' / 'index.json', folder / 'semantique' / 'vue_globale.csv',
                folder / 'correspondance_rapports.json', folder / 'inventaire_observe.json']
    selected += [folder / index[p]['detail_file'] for p in sorted(issue_paths) if p in index]
    selected += [folder / 'verifications_locales.json'] if (folder / 'verifications_locales.json').exists() else []
    output = folder.parent / ('problemes-' + folder.name + '.zip')
    if output.exists():
        raise FileExistsError(f'An export already exists: {output}')
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file in selected:
            path = file.resolve(strict=True)
            if not path.is_relative_to(folder):
                raise ManagerError('Report file outside the report folder')
            archive.write(path, arcname=path.relative_to(folder).as_posix())
        archive.writestr('LIRE_AVANT_PARTAGE.txt',
            'Derived reports only; no source Kristals. Local paths, subjects and keywords may be sensitive. Review before sharing.\n'
            'A triage report does not prove Framework, diK or UNESCO non-conformance.\n')
    return output


def analyze_all(source: str | Path, *, update_catalogue: bool = True,
                verify_locally: bool = False, catalogue: str | Path | None = None,
                reports_base: str | Path | None = None) -> dict:
    """Pipeline unique, optimisé par le cache du catalogue pour les sources inchangées."""
    root = Path(source).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ManagerError('Source must be an existing Kristals folder')
    database = Path(catalogue or CATALOGUE_PATH).expanduser().absolute()
    reports_dir = Path(reports_base or RAPPORTS_PATH).expanduser().absolute()
    _ensure_outside_sources(root, [database, database.with_suffix('.html'), reports_dir])
    if database.is_symlink() or reports_dir.is_symlink():
        raise ManagerError('Output symlink forbidden')
    if not update_catalogue and not database.is_file():
        raise ManagerError('No existing catalog: run an analysis with catalog refresh')
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
    # Recover declared metadata and historic AI/structural evidence without
    # assigning approval or changing the operational triage.
    from .qualification_history import annotate_qualifications
    qualification_summary = annotate_qualifications(items, source=root)
    # Separate, source-matched AI editorial dossiers; no changes to canonical metadata.
    from .semantic_enrichment import annotate_ai_dossiers
    ai_review_summary = annotate_ai_dossiers(items)
    from .editorial_review import annotate_editorial_review
    editorial_review_count = annotate_editorial_review(items)
    from .editorial_review import annotate_historical_unesco_attention
    historic_disagreements = annotate_historical_unesco_attention(items)
    from .native_evidence import annotate_native_sources
    from .authoring_observations import annotate_authoring
    native_review_summary = annotate_native_sources(items)
    authoring_summary = annotate_authoring(items)
    # A Manager window can outlive an overlay installation and still hold an
    # earlier native_evidence module in sys.modules. Do not let a missing new
    # counter abort the analysis or silently imply that evidence was approved.
    native_counters_complete = all(
        name in native_review_summary
        for name in ('matched', 'changed', 'metadata_changed', 'not_verified')
    )
    authoring_counters_complete = all(
        name in authoring_summary
        for name in ('building', 'source_catalog_empty', 'source_catalog_issues', 'source_entries')
    )
    compatibility_notes = []
    if not native_counters_complete:
        compatibility_notes.append(
            'Native-source counter API is incomplete (possibly a mixed Manager version). '
            'Restart both Manager windows and rescan; missing counter values are not proof of zero problems.'
        )
    if not authoring_counters_complete:
        compatibility_notes.append(
            'Authoring counter API is incomplete. Restart Manager and rescan; '
            'missing counter values are not evidence of validated authoring.'
        )
    from .review_progress import assess_review
    for row in items:
        row['review_progress'] = assess_review(row)
    # Historic local human decisions remain an independent register.
    from .review_registry import annotate_entries
    review_summary = annotate_entries(items, source=root)
    priorities = Counter(item['priority'] for item in items)
    reading = Counter(item.get('content_status') for item in items)
    result = {'format': FORMAT, 'generated_at': datetime.now(timezone.utc).isoformat(),
              'source': str(root), 'catalogue': str(database), 'catalog_stats': catalog_stats,
              'semantic_reports': str(semdir), 'verification_mode': 'local_integrity' if verify_locally else 'inventory_only',
              'counts': {'kristals': len(items), **{k:priorities.get(k, 0) for k in ('blocker', 'warning', 'review', 'info')},
                         'graph_content_observed': reading.get('observed', 0),
                         'native_contract_observed': reading.get('native_observed', 0),
                         'content_partial': reading.get('partial', 0),
                         'content_unsupported': reading.get('unsupported', 0),
                         'content_error': reading.get('error', 0),
                         'registered_review_matched': review_summary.get('matched', 0),
                         'historical_qualifications_matched': qualification_summary.get('history_matched', 0),
                         'live_classifications_read': qualification_summary.get('live_metadata_matched', 0),
                         'ai_semantic_dossiers_matched': ai_review_summary['matched_live'],
                         'ai_prf_alternatives': ai_review_summary['prf_alternatives'],
                         'ai_editorial_unesco_matches': editorial_review_count,
                         'historical_unesco_disagreements': historic_disagreements,
                         'native_sources_matched': native_review_summary.get('matched', 0),
                         'native_sources_changed': native_review_summary.get('changed', 0),
                         'native_metadata_only_changed': native_review_summary.get('metadata_changed', 0),
                         'native_review_counters_complete': native_counters_complete,
                         'authoring_building': authoring_summary.get('building', 0),
                         'source_catalog_empty': authoring_summary.get('source_catalog_empty', 0),
                         'source_catalog_issues': authoring_summary.get('source_catalog_issues', 0),
                         'source_catalog_entries': authoring_summary.get('source_entries', 0),
                         'authoring_counters_complete': authoring_counters_complete,
                         'ai_unesco_disagreements': ai_review_summary['unesco_proposal_disagreements'],
                         'arketype_candidates': sum(r['arketype_inference']['status']=='candidate_to_review' for r in details),
                         'unesco_micro_candidates': sum(r['unesco_proposal']['status']=='candidates_to_review' for r in details),
                         'unesco_domain_candidates': sum(bool(r['unesco_proposal']['domain_candidates']) for r in details)},
              'review_registry': review_summary, 'qualification_recovery': qualification_summary,
              'ai_semantic_review': ai_review_summary,
              'native_source_review': native_review_summary,
              'authoring_observations': authoring_summary,
              'entries': items,
              'limits': ['Native contract recognized means its structure/contract was observed, not that its complete semantics were validated.',
                         'Technical health, canonical reading and human classification are three separate assessments.',
                         'UNESCO and Arketype scores are non-canonical proposals.',
                         'diK provides lexical observations; no identity normalization contract was executed.',
                         'No C1/C2/C3 certification without independent KristalDiag and Framework verification.',
                         'The AI semantic dossier is project-metadata-derived, not independent reading of all canonical contents.',
                         'A semantic role is a descriptive draft, not an approved PRF or permission to publish.',
                         'Native source fingerprints prove only that archived files match current bytes, not that statements are correct.',
                         'Review stage is a work queue label; it never grants C1/C2/C3 or a human approval.',
                         'Detected issues alone do not prove non-conformance.'] + compatibility_notes}
    _write_json(output / 'rapport_global.json', result)
    _write_json(output / 'ai_semantic_review_127.json', {
        'format': 'kristal.manager-current-ai-review-export/1.0',
        'authority': 'draft_only_no_canonical_changes',
        'source': str(root), 'generated_at': result['generated_at'],
        'totals': ai_review_summary,
        'entries': [{'state_ref': r['state_ref'], 'title': r['title'],
                     'declared_prf': (r.get('qualification_evidence') or {}).get('metadata', {}).get('primary_usage'),
                     'review': r['semantic_enrichment']} for r in items],
    })
    _write_json(output / 'inventaire_observe.json', [{'title': r.get('title'), 'path': r.get('path'), 'state_ref': r.get('state_ref'), 'readiness': r.get('readiness'), 'historical_archive': is_historical(r)} for r in all_rows])
    _write_json(output / 'plan_corrections.json', _plans(items))
    _write_json(output / 'correspondance_rapports.json', [dict(path=r['path'], **refs.get(r['path'].casefold(), {})) for r in items])
    # One convenient single-file CSV; preserve explicit tentative labels.
    with (output / 'tableau_global.csv').open('w', newline='', encoding='utf-8-sig') as out:
        fields = ('title', 'editorial_state', 'review_stage', 'next_action', 'authoring_status', 'source_catalog', 'source_count', 'native_source_review', 'readiness', 'content_status', 'priority', 'declared_ark', 'declared_prf',
                  'semantic_role_ai_draft', 'semantic_scope_ai_draft', 'critical_distinction_ai_draft',
                  'prf_refinement_ai_draft', 'ai_review_status', 'declared_unesco', 'unesco_ai_review_status', 'subject_domain', 'ark_structure_history', 'classification_review_status',
                  'proposed_arketype', 'proposed_unesco_domain', 'proposed_unesco',
                  'keywords', 'problem_count', 'path')
        from .qualification_history import display_declared, display_unesco_declaration, display_ark_structure
        from .classification_labels import display_category
        from .semantic_enrichment import display_semantic_role, display_prf_refinement
        from .editorial_review import display_unesco_review
        writer = csv.DictWriter(out, fieldnames=fields); writer.writeheader()
        for r in items:
            evidence = r.get('qualification_evidence') or {}
            metadata = evidence.get('metadata') or {}
            progress = assess_review(r)
            from .native_evidence import display_native_source_review
            from .authoring_observations import display_authoring_status, display_source_catalog
            writer.writerow({**{k:r.get(k) for k in fields},
                             'editorial_state': progress['editorial_state'],
                             'review_stage': progress['stage'],
                             'next_action': progress['next_action'],
                             'native_source_review': display_native_source_review(r),
                             'authoring_status': display_authoring_status(r),
                             'source_catalog': display_source_catalog(r),
                             'source_count': (r.get('authoring_observation') or {}).get('source_count'),
                             'declared_ark': display_declared(r, 'primary_archetype'),
                             'declared_prf': display_declared(r, 'primary_usage'),
                             'semantic_role_ai_draft': display_semantic_role(r),
                             'semantic_scope_ai_draft': (r.get('semantic_enrichment') or {}).get('semantic_scope_en') or '',
                             'critical_distinction_ai_draft': (r.get('semantic_enrichment') or {}).get('critical_distinction_en') or '',
                             'prf_refinement_ai_draft': display_prf_refinement(r),
                             'ai_review_status': (r.get('semantic_enrichment') or {}).get('status') or 'NOT_REVIEWED',
                             'declared_unesco': display_unesco_declaration(r),
                             'subject_domain': display_declared(r, 'subject_domain'),
                             'ark_structure_history': display_ark_structure(r),
                             'classification_review_status': metadata.get('verification_status') or 'NOT_EVALUATED',
                             'unesco_ai_review_status': display_unesco_review(r),
                             # Human-facing CSV uses English names. Raw JSON keeps exact codes.
                             'proposed_arketype': (display_category(r['proposed_arketype'], 'ark')
                                                   if r.get('proposed_arketype') else 'None proposed'),
                             'proposed_unesco_domain': (display_category(r['proposed_unesco_domain'], 'unesco_domain')
                                                        if r.get('proposed_unesco_domain') else 'None proposed'),
                             'proposed_unesco': (display_category(r['proposed_unesco'], 'unesco')
                                                 if r.get('proposed_unesco') else 'None proposed'),
                             'keywords': '; '.join(r['keywords']),
                             'problem_count': len(r['problems'])})
    # Dedicated AI review sheet: suitable for review, never an approval or write plan.
    from .semantic_enrichment import display_semantic_role, display_prf_refinement
    with (output / 'ai_semantic_review_127.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        headers = ('title', 'state_ref', 'ai_review_status', 'semantic_role_ai_draft',
                   'semantic_scope_ai_draft', 'critical_distinction_ai_draft',
                   'declared_prf', 'prf_alternative_ai_draft', 'evidence_excerpt',
                   'unesco_proposal_disagrees', 'unesco_ai_editorial_review',
                   'unesco_ai_review_reason', 'human_approved', 'canonical_changed')
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        for row in items:
            info = row.get('semantic_enrichment') or {}
            writer.writerow({
                'title':row.get('title'), 'state_ref':row.get('state_ref'),
                'ai_review_status':info.get('status'),
                'semantic_role_ai_draft':display_semantic_role(row),
                'semantic_scope_ai_draft':info.get('semantic_scope_en') or '',
                'critical_distinction_ai_draft':info.get('critical_distinction_en') or '',
                'declared_prf':(row.get('qualification_evidence') or {}).get('metadata', {}).get('primary_usage') or '',
                'prf_alternative_ai_draft':display_prf_refinement(row),
                'evidence_excerpt':info.get('evidence_excerpt') or '',
                'unesco_proposal_disagrees':str(info.get('unesco_proposal_disagrees_with_declared', False)),
                'unesco_ai_editorial_review':display_unesco_review(row),
                'unesco_ai_review_reason':(row.get('editorial_unesco_review') or {}).get('reason') or '',
                'human_approved':'NO', 'canonical_changed':'NO',
            })
    from .semantic_enrichment import render_review_html
    from .review_progress import export_review_queue
    export_review_queue(output / 'review_queue.csv', items, source_root=root)
    render_review_html(items, output / 'ai_semantic_review_127.html')
    archive = export_problem_bundle(output)
    return {'report_directory': str(output), 'problem_archive': str(archive),
            'global_report': result, 'inventory': all_rows, 'catalog_stats': catalog_stats,
            'html_report': str(semdir / 'rapport.html'), 'index_path': str(output / 'rapport_global.json')}
