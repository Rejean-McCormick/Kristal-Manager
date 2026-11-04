"""English display names for existing classification codes, without changing authority.

Sources: Manager-bundled Arketype definitions (19); Arketype usage profiles (21,
read-only copy of names); pinned Manager UNESCO reference (7 domains, 88 subjects).
Labels are presentation only and must never be interpreted as human approval.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent / 'reference'
_MAX_SIZE = 512 * 1024
_ARK = re.compile(r'^ARK-\d{2}$')
_PRF = re.compile(r'^PRF-\d{2}$')
_UNESCO = re.compile(r'^[1-7](?:\.\d{2})?$')


def _read_json(path: Path) -> dict:
    # Do not follow symlinks from an edited installation or untrusted overlay.
    if path.is_symlink() or not path.is_file() or path.stat().st_size > _MAX_SIZE:
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


@lru_cache(maxsize=1)
def _reference_names() -> dict[str, dict[str, str]]:
    output = {'ark':{}, 'prf':{}, 'unesco':{}, 'unesco_domain':{}}
    files = sorted((BASE / 'semantic' / 'arketype' / 'archetypes').glob('*.json'))
    for f in files[:50]:
        doc = _read_json(f)
        code, name = doc.get('id'), doc.get('name')
        if isinstance(code, str) and _ARK.fullmatch(code) and isinstance(name, str) and name.strip():
            output['ark'][code] = name.strip()
    profiles = _read_json(BASE / 'prf-use-profiles.en.json')
    if (profiles.get('format') == 'kristal.manager-prf-display-labels/1.0'
            and profiles.get('status') == 'descriptive_labels_only_not_approvals'):
        for row in profiles.get('profiles', []):
            if not isinstance(row, dict):
                continue
            code, name = row.get('id'), row.get('name')
            if isinstance(code, str) and _PRF.fullmatch(code) and isinstance(name, str) and name.strip():
                output['prf'][code] = name.strip()
    unesco = _read_json(BASE / 'unesco-thesaurus-profile.json')
    for domain in unesco.get('domains', []):
        if not isinstance(domain, dict):
            continue
        d_code, d_label = domain.get('notation'), domain.get('label_en')
        if isinstance(d_code, str) and _UNESCO.fullmatch(d_code) and isinstance(d_label, str) and d_label.strip():
            output['unesco_domain'][d_code] = d_label.strip()
        for mt in domain.get('microthesauri', []):
            if not isinstance(mt, dict):
                continue
            code, label = mt.get('notation'), mt.get('label_en')
            if isinstance(code, str) and _UNESCO.fullmatch(code) and isinstance(label, str) and label.strip():
                output['unesco'][code] = label.strip()
    return output


def display_category(code: object, kind: str) -> str:
    """Return descriptive name; do not quietly assign a meaning to unknown codes."""
    value = str(code or '').strip()
    if not value:
        return 'Not declared'
    labels = _reference_names().get(kind, {})
    if value in labels:
        return labels[value]
    return f'Unresolved category ({value})'


def category_name(code: object, kind: str) -> str:
    """For optional proposals, retain a clear absence vs unknown distinction."""
    value = str(code or '').strip()
    return display_category(value, kind) if value and value not in ('—','none') else 'None proposed'


def get_reference_counts() -> dict[str,int]:
    """Useful for tests and reporting source coverage, not classification confidence."""
    return {kind:len(values) for kind,values in _reference_names().items()}
