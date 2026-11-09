"""Bounded, local read-only Authoring Kit observations for both Manager tables.

The workspace's own `validated` label is not a Framework approval. Source-catalog
schema shape and pointer existence are not checks of authority, URLs or truth.
AI release gates and authoring dossiers are noncanonical notes, not release grants.
"""
from __future__ import annotations

import json
from pathlib import Path

MAX_JSON_BYTES = 2 * 1024 * 1024
SOURCE_FORMAT = 'kristal.source-catalog/2.0.0'
DOSSIER_FORMAT = 'kristal.noncanonical-ai-authoring-review/1.0'


def _safe_source(root: Path, rel: str) -> Path:
    """Reject symlink traversal, absent paths and large local inputs."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Unsafe workspace root')
    parts = Path(rel).parts
    if not parts or any(x in ('', '.', '..') for x in parts) or Path(rel).is_absolute():
        raise ValueError('Unsafe relative path')
    p = root
    for item in parts:
        p = p / item
        if p.is_symlink():
            raise ValueError('Symlinked workspace source')
    return p


def _load_json(root: Path, rel: str) -> dict:
    p = _safe_source(root, rel)
    if not p.is_file() or p.stat().st_size > MAX_JSON_BYTES:
        raise ValueError('Missing or oversized JSON')
    data = json.loads(p.read_text('utf-8'))
    if not isinstance(data, dict):
        raise ValueError('Expected JSON object')
    return data


def inspect_authoring(row: dict) -> dict:
    """Observe local authoring material without changing any file or review status."""
    base = {'status': 'UNVERIFIED', 'workspace_status': 'UNKNOWN', 'source_catalog': 'NOT_CHECKED',
            'source_count': None, 'has_ai_release_gate': False, 'has_source_gap_note': False,
            'ai_dossier': 'NOT_CHECKED', 'human_approved': False,
            'framework_qualification': 'NOT_ESTABLISHED'}
    path = row.get('path')
    if (not isinstance(path, str) or not path or
            (row.get('qualification_evidence') or {}).get('metadata_source') != 'LIVE_WORKSPACE'):
        return base
    root = Path(path)
    try:
        ws = _load_json(root, 'kristal.workspace.json')
        if not isinstance(ws.get('state_ref'), str) or ws['state_ref'] != row.get('state_ref'):
            return {**base, 'status': 'IDENTITY_MISMATCH'}
        label = ws.get('status')
        status = label if label in ('validated', 'building') else 'UNKNOWN'
        result = {**base, 'status': 'OBSERVED', 'workspace_status': status}
        for flag, rel in [('has_ai_release_gate', 'validation/AI_RELEASE_GATE.md'),
                          ('has_source_gap_note', 'docs/09_SOURCE_EVIDENCE_GAPS.md')]:
            p = _safe_source(root, rel)
            result[flag] = p.is_file() and p.stat().st_size <= MAX_JSON_BYTES
        try:
            cat = _load_json(root, 'sources/source-catalog.json')
            sources = cat.get('sources')
            if cat.get('format') != SOURCE_FORMAT or not isinstance(sources, list):
                raise ValueError('Wrong source catalogue envelope')
            seen = set()
            for item in sources:
                if not isinstance(item, dict) or any(not isinstance(item.get(k), str) or not item[k].strip()
                        for k in ('id', 'title', 'kind')) or 'locator' not in item or item['locator'] is None:
                    raise ValueError('Missing required source fields')
                if not isinstance(item['locator'], (str, dict)) or not item['locator']:
                    raise ValueError('Invalid source locator')
                if item['id'] in seen:
                    raise ValueError('Duplicate source ID')
                seen.add(item['id'])
            result['source_count'] = len(sources)
            result['source_catalog'] = 'EMPTY' if not sources else 'SCHEMA_SHAPE_OK'
        except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
            result['source_catalog'] = 'SCHEMA_ISSUE_OR_UNAVAILABLE'
        try:
            editorial = _load_json(root, 'derived/authoring-review/AI_EDITORIAL_DOSSIER.json')
            identity = editorial.get('identity') or {}
            result['ai_dossier'] = ('AI_DRAFT_PRESENT' if editorial.get('schema') == DOSSIER_FORMAT
                                    and editorial.get('review_status') == 'AI_DRAFT_NOT_APPROVED'
                                    and isinstance(identity, dict)
                                    and identity.get('state_ref') == row.get('state_ref')
                                    else 'AI_DRAFT_UNVERIFIED')
        except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
            result['ai_dossier'] = 'NOT_AVAILABLE'
        return result
    except (OSError, ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        return base


def annotate_authoring(rows: list[dict]) -> dict:
    counts = {'observed': 0, 'building': 0, 'validated_label': 0, 'source_catalog_empty': 0,
              'source_catalog_issues': 0, 'source_entries': 0, 'editorial_drafts': 0,
              'release_gate_notes': 0, 'source_gap_notes': 0, 'not_verified': 0}
    for row in rows:
        data = inspect_authoring(row)
        row['authoring_observation'] = data
        if data['status'] != 'OBSERVED':
            counts['not_verified'] += 1
            continue
        counts['observed'] += 1
        counts['building'] += data['workspace_status'] == 'building'
        counts['validated_label'] += data['workspace_status'] == 'validated'
        counts['source_catalog_empty'] += data['source_catalog'] == 'EMPTY'
        counts['source_catalog_issues'] += data['source_catalog'] == 'SCHEMA_ISSUE_OR_UNAVAILABLE'
        counts['source_entries'] += data['source_count'] or 0
        counts['editorial_drafts'] += data['ai_dossier'] == 'AI_DRAFT_PRESENT'
        counts['release_gate_notes'] += data['has_ai_release_gate']
        counts['source_gap_notes'] += data['has_source_gap_note']
    return counts


def display_authoring_status(row: dict) -> str:
    x = row.get('authoring_observation') or {}
    if x.get('status') != 'OBSERVED':
        return 'Authoring not verified'
    if x.get('workspace_status') == 'building':
        return 'Building (local label; not qualified)'
    if x.get('workspace_status') == 'validated':
        return 'Validated label (not C1/C2/C3)'
    return 'Unknown workspace label'


def display_source_catalog(row: dict) -> str:
    x = row.get('authoring_observation') or {}
    code = x.get('source_catalog')
    if code == 'SCHEMA_SHAPE_OK':
        n = x['source_count']
        return f'{n} catalogued (links not verified)'
    if code == 'EMPTY':
        return '0 sources — provenance review'
    if code == 'SCHEMA_ISSUE_OR_UNAVAILABLE':
        return 'Catalog structure needs review'
    return 'Not verified'
