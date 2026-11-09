"""One shared, non-certifying review queue for Manager and Analysis Center.

No maturity percentage, automatic approval, or Framework qualification is inferred.
Every action derives from current in-memory observations, with technical and
semantic uncertainties kept separate. This file never writes to Kristals.
"""
from __future__ import annotations

import csv
from pathlib import Path

REVIEW_FOCI = ('All Kristals', 'Authoring in progress', 'Source catalogue issues',
               'Workspace metadata updated', 'Structural attention', 'Source evidence changed',
               'AI draft outdated', 'UNESCO disagreement', 'PRF alternative',
               'Native contract', 'Other review',
               'Editorial: Ready', 'Editorial: Needs work',
               'Editorial: Building', 'Editorial: Not assessed')


def assess_review(row: dict) -> dict:
    from .editorial_state import assess_editorial_state
    editorial = assess_editorial_state(row)
    flags = []
    problems = row.get('problems') or []
    codes = {x.get('code') for x in problems if isinstance(x, dict)}
    status = str(row.get('readiness') or 'UNKNOWN')
    if (status not in ('READY',) or row.get('state_conflict') or row.get('identity_collision')
            or row.get('needs_migration') or row.get('priority') == 'blocker'):
        flags.append('structural')
    if 'LOCAL_DISCOVERY_STALE' in codes or 'LOCAL_DISCOVERY_INCOMPLETE' in codes:
        flags.append('discovery')
    authoring = row.get('authoring_observation') or {}
    if authoring.get('workspace_status') == 'building':
        flags.append('authoring_building')
    if authoring.get('source_catalog') in ('EMPTY', 'SCHEMA_ISSUE_OR_UNAVAILABLE'):
        flags.append('source_catalog_issue')
    native = (row.get('native_source_review') or {}).get('status')
    if native == 'SOURCES_CHANGED_REVIEW_AGAIN':
        flags.append('source_changed')
    elif native == 'WORKSPACE_METADATA_CHANGED':
        flags.append('workspace_metadata_changed')
    elif native != 'SOURCE_BYTES_MATCHED':
        flags.append('source_unverified')
    dossier = (row.get('semantic_enrichment') or {})
    if dossier.get('status') != 'MATCHED_CURRENT_DESCRIPTORS':
        flags.append('ai_outdated')
    if (row.get('editorial_unesco_review') or row.get('historical_unesco_attention')
            or dossier.get('unesco_proposal_disagrees_with_declared')):
        flags.append('unesco_disagreement')
    if dossier.get('prf_candidate'):
        flags.append('prf_alternative')
    if row.get('content_status') == 'native_observed':
        flags.append('native_contract')
    if row.get('priority') == 'warning' and not codes & {'LOCAL_DISCOVERY_STALE', 'LOCAL_DISCOVERY_INCOMPLETE'}:
        flags.append('technical_warning')
    if 'structural' in flags:
        stage, next_action = 'Structural attention', 'Resolve local state or identity issue; do not approve classification.'
    elif 'source_changed' in flags:
        stage, next_action = 'Source review outdated', 'Recheck changed source documents and renew the AI source review.'
    elif 'source_catalog_issue' in flags:
        stage, next_action = 'Source catalogue review', 'Repair source catalogue structure or document source gaps; do not invent evidence.'
    elif 'authoring_building' in flags:
        stage, next_action = 'Authoring in progress', 'Complete the workspace-specific release checklist; do not promote its local status automatically.'
    elif 'workspace_metadata_changed' in flags:
        stage, next_action = 'Metadata review outdated', 'Review updated workspace metadata; archived native document bytes still match.'
    elif 'source_unverified' in flags:
        stage, next_action = 'Source evidence pending', 'Inspect native documents and verify their identity and fingerprints.'
    elif 'ai_outdated' in flags:
        stage, next_action = 'AI draft outdated', 'Refresh semantic analysis against current workspace metadata.'
    elif 'unesco_disagreement' in flags:
        stage, next_action = 'UNESCO review', 'Compare proposed UNESCO term with declared subjects and native scope.'
    elif 'prf_alternative' in flags:
        stage, next_action = 'PRF review', 'Evaluate AI profile alternative using actual native semantics.'
    elif 'technical_warning' in flags:
        stage, next_action = 'Technical attention', 'Inspect observed technical issues separately from semantic classification.'
    elif 'native_contract' in flags:
        stage, next_action = 'Native semantics review', 'Inspect native contract semantics without assuming KQ/KP graphs.'
    elif 'discovery' in flags:
        stage, next_action = 'Discovery maintenance', 'Check registered-file integrity separately from semantic qualification.'
    else:
        stage, next_action = 'Decision pending', 'Conduct independent domain review; Framework C1/C2/C3 not established.'
    return {'stage': stage, 'next_action': next_action, 'flags': tuple(flags),
            'editorial_state': editorial['status'], 'editorial_reason': editorial['reason'],
            'source_review_status': native or 'NOT_CHECKED',
            'ai_draft_status': dossier.get('status') or 'NOT_REVIEWED',
            'qualification': 'NOT_ESTABLISHED', 'human_approved': False}


def matches_focus(review: dict, focus: str) -> bool:
    if focus == 'All Kristals':
        return True
    if focus.startswith('Editorial: '):
        status = focus.removeprefix('Editorial: ')
        if status in ('Ready', 'Needs work', 'Building', 'Not assessed'):
            return review.get('editorial_state') == status
    key = {
        'Authoring in progress': 'authoring_building',
        'Source catalogue issues': 'source_catalog_issue',
        'Workspace metadata updated': 'workspace_metadata_changed',
        'Structural attention': 'structural',
        'Source evidence changed': 'source_changed',
        'AI draft outdated': 'ai_outdated',
        'UNESCO disagreement': 'unesco_disagreement',
        'PRF alternative': 'prf_alternative',
        'Native contract': 'native_contract',
    }.get(focus)
    if key:
        return key in review.get('flags', ())
    if focus == 'Other review':
        return not any(x in review.get('flags', ()) for x in
                       ('structural', 'source_catalog_issue', 'authoring_building', 'workspace_metadata_changed',
                        'source_changed', 'ai_outdated', 'unesco_disagreement', 'prf_alternative'))
    raise ValueError('Unknown review focus')


def export_review_queue(path: Path | str, rows: list[dict], *, source_root: Path | str | None = None) -> Path:
    """Export an explicit *unapproved* review queue, never within source roots.

    Refuse symlink targets and overwrites; caller chooses a user-visible path.
    """
    dest = Path(path).expanduser().absolute()
    if dest.exists() or dest.is_symlink():
        raise FileExistsError('Review export exists: choose a new filename.')
    parent = dest.parent.resolve(strict=True)
    if source_root is not None:
        root = Path(source_root).expanduser().resolve(strict=True)
        if parent == root or parent.is_relative_to(root):
            raise ValueError('Review exports must be outside the Kristal source tree.')
    if dest.suffix.casefold() != '.csv':
        raise ValueError('Review export must end in .csv')
    # Prevent spreadsheet-formula execution when exporting untrusted titles/notes.
    def csv_literal(value):
        if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
            return "'" + value
        return value

    fields = ('title', 'state_ref', 'editorial_state', 'editorial_reason', 'review_stage', 'next_action', 'review_flags',
              'structure', 'authoring_status', 'source_catalog', 'source_count',
              'native_source_review', 'ai_draft_status',
              'declared_ark', 'declared_prf', 'declared_unesco',
              'semantic_role_ai_draft', 'qualification', 'path')
    from .qualification_history import display_declared, display_unesco_declaration
    from .semantic_enrichment import display_semantic_role
    from .native_evidence import display_native_source_review
    from .authoring_observations import display_authoring_status, display_source_catalog
    from .editorial_decisions import load_decisions, current_editorial_state
    try:
        decisions = load_decisions()
    except (OSError, ValueError, TypeError):
        decisions = {}
    opened = False
    try:
        with dest.open('x', newline='', encoding='utf-8-sig') as file:
            opened = True
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                review = assess_review(row)
                editorial = current_editorial_state(row, decisions)
                fields_row = {'title': row.get('title') or Path(str(row.get('path') or '')).name,
                                 'state_ref': row.get('state_ref'),
                                 'editorial_state': editorial['status'],
                                 'editorial_reason': editorial['reason'],
                                 'review_stage': review['stage'],
                                 'next_action': review['next_action'],
                                 'review_flags': '; '.join(review['flags']),
                                 'structure': row.get('readiness'),
                                 'authoring_status': display_authoring_status(row),
                                 'source_catalog': display_source_catalog(row),
                                 'source_count': (row.get('authoring_observation') or {}).get('source_count'),
                                 'native_source_review': display_native_source_review(row),
                                 'ai_draft_status': review['ai_draft_status'],
                                 'declared_ark': display_declared(row, 'primary_archetype'),
                                 'declared_prf': display_declared(row, 'primary_usage'),
                                 'declared_unesco': display_unesco_declaration(row),
                                 'semantic_role_ai_draft': display_semantic_role(row),
                                 'qualification': review['qualification'],
                                 'path': row.get('path')}
                writer.writerow({k: csv_literal(v) for k,v in fields_row.items()})
    except (OSError, ValueError, TypeError):
        # Only remove our own partially created export, never an existing file.
        if opened:
            try:
                dest.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    return dest
