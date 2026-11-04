"""Read-only reconciliation of live Kristal descriptors and recovered review evidence.

A declared field, a recovered historical report and a human-approved decision are
three separate things.  This module never publishes, approves, or edits a Kristal.
"""
from __future__ import annotations

import json
from pathlib import Path
from .classification_labels import display_category

RECOVERY_PATH = Path(__file__).resolve().parent.parent / 'data' / 'recovered_qualification_evidence_2026-11-04.json'
MAX_METADATA_BYTES = 2 * 1024 * 1024
MAX_RECOVERY_BYTES = 4 * 1024 * 1024


def _load_recovered(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_RECOVERY_BYTES:
        raise ValueError('Recovery catalogue missing, symlinked or oversized')
    source = json.loads(path.read_text(encoding='utf-8'))
    if (not isinstance(source, dict)
            or source.get('format') != 'kristal.manager-recovered-qualification-evidence/1.0'
            or source.get('authority') != 'noncanonical_historical_evidence_only'
            or source.get('no_automatic_approval') is not True
            or not isinstance(source.get('entries'), list)):
        raise ValueError('Unsupported or untrusted qualification recovery catalogue')
    index = {}
    for row in source['entries']:
        if not isinstance(row, dict) or not isinstance(row.get('state_ref'), str):
            raise ValueError('Malformed recovered entry')
        key = row['state_ref']
        if key in index:
            raise ValueError('Duplicate state_ref in qualification recovery catalogue')
        index[key] = row
    return {'index': index, 'sources': source.get('sources') or {}, 'recovered_on': source.get('recovered_on')}


def _live_workspace(entry: dict, root: Path) -> tuple[dict | None, str]:
    """Only open a normal metadata file in a current direct child of the scan root."""
    try:
        ref = entry.get('state_ref')
        raw_path = entry.get('path')
        if not isinstance(ref, str) or not isinstance(raw_path, str):
            return None, 'MISSING_SCAN_IDENTITY'
        path = Path(raw_path)
        if path.is_symlink() or not path.is_dir():
            return None, 'WORKSPACE_UNAVAILABLE'
        resolved = path.resolve(strict=True)
        if resolved.parent != root:
            return None, 'OUTSIDE_CURRENT_SCAN_ROOT'
        file = resolved / 'kristal.workspace.json'
        if file.is_symlink() or not file.is_file() or file.stat().st_size > MAX_METADATA_BYTES:
            return None, 'WORKSPACE_METADATA_UNAVAILABLE'
        document = json.loads(file.read_text(encoding='utf-8-sig'))
        if not isinstance(document, dict) or document.get('state_ref') != ref:
            return None, 'WORKSPACE_IDENTITY_MISMATCH'
        return document, 'LIVE_WORKSPACE_MATCHED'
    except (OSError, ValueError, UnicodeError, TypeError, json.JSONDecodeError):
        return None, 'WORKSPACE_METADATA_UNREADABLE'


def _from_live(document: dict) -> dict:
    classification = document.get('classification')
    if not isinstance(classification, dict):
        classification = {}
    subject = document.get('subject')
    if not isinstance(subject, dict):
        subject = {}
    model = document.get('native_model')
    if not isinstance(model, dict):
        model = {}
    return {
        'title': document.get('title'),
        'profile': document.get('profile'),
        'status': document.get('status'),
        'primary_archetype': classification.get('primary_archetype'),
        'primary_usage': classification.get('primary_usage'),
        'verification_status': classification.get('verification_status'),
        'subject_id': subject.get('id'),
        'subject_label': subject.get('label'),
        'subject_domain': subject.get('domain'),
        'subject_orientation': subject.get('orientation'),
        'native_model_kind': model.get('kind'),
        'native_model_description': model.get('description'),
        'unesco': classification.get('unesco_thesaurus'),
        'semantic_mapping': document.get('semantic_mapping'),
    }


def annotate_qualifications(entries: list[dict], *, source: Path | str, recovery_path: Path | str | None = None) -> dict:
    """Enrich current scan rows in memory; never change priority or operational verdict.

    History is joined by state_ref, not folder spelling or arbitrary path. An
    archive never creates an approval: it is labeled separately from live data.
    """
    root = Path(source).expanduser().resolve()
    try:
        recovered = _load_recovered(Path(recovery_path or RECOVERY_PATH))
        index = recovered['index']
        status = 'AVAILABLE'
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        recovered = {'sources': {}, 'recovered_on': None}
        index = {}
        status = 'RECOVERY_CATALOGUE_UNAVAILABLE'
    totals = {'status': status, 'history_matched': 0, 'live_metadata_matched': 0,
              'snapshot_only': 0, 'identity_mismatches': 0, 'missing_history': 0}
    for entry in entries:
        ref = entry.get('state_ref')
        history = index.get(ref)
        live, live_status = _live_workspace(entry, root)
        if live_status == 'LIVE_WORKSPACE_MATCHED':
            totals['live_metadata_matched'] += 1
        elif live_status == 'WORKSPACE_IDENTITY_MISMATCH':
            totals['identity_mismatches'] += 1
        if history:
            totals['history_matched'] += 1
        else:
            totals['missing_history'] += 1
        # A current identity mismatch must not be hidden by a stale snapshot.
        if live_status == 'WORKSPACE_IDENTITY_MISMATCH':
            metadata = {}
            metadata_source = 'IDENTITY_MISMATCH_NO_FALLBACK'
        elif live:
            metadata = _from_live(live)
            metadata_source = 'LIVE_WORKSPACE'
        elif history:
            metadata = history.get('snapshot_metadata') or {}
            metadata_source = 'RECOVERED_SNAPSHOT_ONLY_NOT_CURRENTLY_VERIFIED'
            totals['snapshot_only'] += 1
        else:
            metadata = {}
            metadata_source = 'NOT_AVAILABLE'
        # Source JSON is a read-only, bounded summary of historical reports.
        # Never treat these scores or old PRF batches as current validation.
        entry['qualification_evidence'] = {
            'metadata': metadata,
            'metadata_source': metadata_source,
            'live_read_status': live_status,
            'recovered_on': recovered['recovered_on'] if history else None,
            'historical_arketype_structure': history.get('historical_structural_observation') if history else None,
            'historical_prf_batch': history.get('historical_prf_batch') if history else None,
            'historical_field_audit': history.get('historical_field_audit') if history else None,
            'sources': recovered['sources'] if history else {},
            'qualification_authority': 'NONE_FROM_RECOVERY',
            'human_approval_inferred': False,
            'limits': 'Declared metadata and prior AI/structural reports are not independently verified semantic or C1/C2/C3 qualifications.',
        }
    return totals


def display_declared(entry: dict, key: str) -> str:
    evidence = entry.get('qualification_evidence') or {}
    meta = evidence.get('metadata') or {}
    value = meta.get(key)
    if not value:
        return 'Not declared'
    # The underlying code is untouched. Only known classification fields get
    # descriptive, source-backed English labels in user-facing surfaces.
    kind = {'primary_archetype':'ark', 'primary_usage':'prf'}.get(key)
    label = display_category(value, kind) if kind else str(value)
    if evidence.get('metadata_source') == 'LIVE_WORKSPACE':
        return label
    return f'{label} (old snapshot)'


def display_ark_structure(entry: dict) -> str:
    evidence = entry.get('qualification_evidence') or {}
    row = evidence.get('historical_arketype_structure') or {}
    score = row.get('observed_facets_score')
    return str(score) + ' (historical)' if score else 'Not assessed'


def display_unesco_declaration(entry: dict) -> str:
    evidence = entry.get('qualification_evidence') or {}
    meta = evidence.get('metadata') or {}
    info = meta.get('unesco') or {}
    values = info.get('microthesauri') if isinstance(info, dict) else None
    if not isinstance(values, list) or not values:
        return 'Not declared'
    # The live UNESCO Thesaurus profile is the source of names; raw codes stay
    # in original metadata. Never reinterpret an unrecognized notation.
    names = [display_category(item.get('code'), 'unesco') for item in values
             if isinstance(item, dict) and item.get('code')]
    label = ', '.join(dict.fromkeys(names)) if names else 'Not declared'
    if evidence.get('metadata_source') != 'LIVE_WORKSPACE':
        label += ' (old snapshot)'
    return label
