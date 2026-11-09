"""Match the 2026-11-05 editorial source review to CURRENT local sources.

The archived human-readable conclusions have *no* canonical authority. A match
means only that the particular archived source files have matching bytes; it
is not proof that the domain assertions are accurate or C1/C2/C3 approved.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parent.parent / 'data' / 'ai_native_source_review_127_2026-11-05.json'
CATALOG_FORMAT = 'kristal.manager-native-source-review/1.0'
MAX_DOCUMENT = 2 * 1024 * 1024


def load_native_catalog(path: Path | str | None = None) -> dict:
    p = Path(path or CATALOG_PATH)
    if p.is_symlink() or not p.is_file() or p.stat().st_size > MAX_DOCUMENT:
        raise ValueError('Native source catalogue unavailable or unsafe')
    data = json.loads(p.read_text(encoding='utf-8'))
    if (not isinstance(data, dict) or data.get('format') != CATALOG_FORMAT
            or data.get('no_canonical_updates') is not True
            or data.get('no_publication') is not True
            or data.get('no_c1_c2_c3_qualification') is not True
            or not isinstance(data.get('entries'), list)):
        raise ValueError('Unsupported source-review catalog')
    index = {}
    for item in data['entries']:
        if (not isinstance(item, dict) or not isinstance(item.get('state_ref'), str)
                or not item.get('state_ref') or item['state_ref'] in index
                or item.get('human_approved') is not False
                or not isinstance(item.get('workspace_sha256'), str)
                or not isinstance(item.get('source_documents'), dict)):
            raise ValueError('Invalid source-review record')
        index[item['state_ref']] = item
    return index


def _safe_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or '\\' in relative or ':' in relative:
        raise ValueError('Unsafe source path')
    rel = Path(relative)
    if rel.is_absolute() or any(p in ('', '.', '..') for p in rel.parts):
        raise ValueError('Unsafe source path')
    target = root / rel
    if any(node.is_symlink() for node in (root, *[root.joinpath(*rel.parts[:i]) for i in range(1, len(rel.parts)+1)])):
        raise ValueError('Symlinked source')
    if not target.is_file() or target.stat().st_size > MAX_DOCUMENT:
        raise ValueError('Source unavailable')
    return target


def inspect_native_source(row: dict, index: dict) -> dict:
    """Fail closed on changed/missing evidence, without modifying any source."""
    record = index.get(row.get('state_ref'))
    common = {'human_approved': False, 'c1_c2_c3': 'NOT_ESTABLISHED'}
    if not record:
        return {**common, 'status': 'NO_SOURCE_REVIEW'}
    if (row.get('qualification_evidence') or {}).get('metadata_source') != 'LIVE_WORKSPACE':
        return {**common, 'status': 'CURRENT_IDENTITY_NOT_VERIFIED'}
    path = row.get('path')
    if not isinstance(path, str) or not path:
        return {**common, 'status': 'CURRENT_IDENTITY_NOT_VERIFIED'}
    root = Path(path)
    try:
        if root.is_symlink() or not root.is_dir():
            raise ValueError('Untrusted source folder')
        expected = {'kristal.workspace.json': record['workspace_sha256']}
        documents = record['source_documents']
        if len(documents) < 2 or len(documents) > 12:
            raise ValueError('Incomplete source documentation')
        for doc in documents.values():
            if not isinstance(doc, dict):
                raise ValueError('Malformed source document')
            rel = doc.get('path')
            if not isinstance(rel, str) or rel in expected:
                raise ValueError('Duplicate source')
            expected[rel] = doc.get('sha256')
        mismatches = []
        for rel, digest in expected.items():
            if (not isinstance(digest, str) or len(digest) != 64
                    or any(x not in '0123456789abcdef' for x in digest)):
                raise ValueError('Invalid source hash')
            if hashlib.sha256(_safe_file(root, rel).read_bytes()).hexdigest() != digest:
                mismatches.append(rel)
        # Distinguish a metadata-only revision from a changed native model.
        # Both require renewed editorial review, neither is an approval.
        if any(rel != 'kristal.workspace.json' for rel in mismatches):
            return {**common, 'status': 'SOURCES_CHANGED_REVIEW_AGAIN',
                    'changed_paths': tuple(mismatches)}
        if mismatches:
            return {**common, 'status': 'WORKSPACE_METADATA_CHANGED',
                    'native_documents_match': True,
                    'changed_paths': ('kristal.workspace.json',)}
    except (OSError, ValueError, TypeError):
        return {**common, 'status': 'SOURCES_UNAVAILABLE'}
    return {**common, 'status': 'SOURCE_BYTES_MATCHED',
            'native_documents_match': True,
            'source_document_paths': tuple(x.get('path') for x in documents.values()),
            'native_kind': record.get('native_kind'),
            'prf_decision': record.get('prf_decision'),
            'prf_reason_en': record.get('prf_reason_en'),
            'unesco_decision': record.get('unesco_decision'),
            'unesco_reason_en': record.get('unesco_reason_en')}


def annotate_native_sources(rows: list[dict], *, catalog_path: Path | str | None = None) -> dict:
    try:
        index = load_native_catalog(catalog_path)
        state = 'AVAILABLE'
    except (OSError, ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        index, state = {}, 'UNAVAILABLE'
    counts = {'catalogue': state, 'matched': 0, 'metadata_changed': 0, 'changed': 0, 'not_verified': 0}
    for row in rows:
        info = inspect_native_source(row, index)
        row['native_source_review'] = info
        if info['status'] == 'SOURCE_BYTES_MATCHED':
            counts['matched'] += 1
        elif info['status'] == 'WORKSPACE_METADATA_CHANGED':
            counts['metadata_changed'] += 1
        elif info['status'] == 'SOURCES_CHANGED_REVIEW_AGAIN':
            counts['changed'] += 1
        else:
            counts['not_verified'] += 1
    return counts


def display_native_source_review(row: dict) -> str:
    status = (row.get('native_source_review') or {}).get('status')
    return {
        'SOURCE_BYTES_MATCHED': 'Source bytes matched (AI review)',
        'SOURCES_CHANGED_REVIEW_AGAIN': 'Native sources changed — review again',
        'WORKSPACE_METADATA_CHANGED': 'Workspace metadata updated — renew AI review',
        'SOURCES_UNAVAILABLE': 'Source evidence unavailable',
        'CURRENT_IDENTITY_NOT_VERIFIED': 'Live identity not verified',
        'NO_SOURCE_REVIEW': 'Not reviewed against native sources',
    }.get(status, 'Not checked')
