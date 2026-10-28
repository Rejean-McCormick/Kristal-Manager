from __future__ import annotations

import argparse
import configparser
import hashlib
import html
import io
import json
import re
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CATALOG_OUT = PACKAGE_ROOT / 'knowledge-base' / 'registry' / 'kristal-registry.catalog.json'
STATE_OUT = PACKAGE_ROOT / 'knowledge-base' / 'projections' / 'kristal' / 'kristal-registry.kristal-state.json'
VIEW_OUT = PACKAGE_ROOT / 'knowledge-base' / 'views' / 'registry.html'
OVERRIDES = PACKAGE_ROOT / 'config' / 'kristal-metadata-overrides.json'
PACKAGE_VERSION = '0.4.0'
CATALOG_PROFILE = 'kristal-registry.catalog/1.1'
REGISTRY_ID = 'urn:kristal:registry:main'

STATE_SUFFIXES = (
    '.kristal-state.json',
    '.structured-epistemic-state.json',
    'kristal_state.json',
    '.semantic.json',
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError(f'JSON object expected: {path}')
    return value


def safe_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def digest(value: Any) -> str:
    return hashlib.sha256(safe_json_bytes(value)).hexdigest()


def read_title_text(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('# '):
            return line[2:].strip()
    return fallback


def normalize_title(name: str) -> str:
    text = re.sub(r'^Kristal[-_ ]*', '', name, flags=re.I)
    return re.sub(r'[-_]+', ' ', text).strip() or name


def parse_desktop_ini_text(text: str) -> dict[str, Any]:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    try:
        parser.read_file(io.StringIO(text.lstrip('\ufeff')))
    except Exception:
        return {}
    if not parser.has_section('Kristal'):
        return {}
    sec = parser['Kristal']
    domains = [sec.get(f'Domain{i}', '').strip() for i in (1, 2, 3)]
    domains = [x for x in domains if x]
    out: dict[str, Any] = {
        'profile': sec.get('Profile') or None,
        'icon_profile': sec.get('IconProfile') or None,
        'icon_code': sec.get('IconCode') or None,
        'title': sec.get('Title') or None,
        'kristal_ref': sec.get('KristalRef') or None,
        'nature': sec.get('Nature') or None,
        'domains': domains,
    }
    try:
        out['maturity'] = int(sec.get('Maturity', ''))
    except Exception:
        pass
    for src, dst in [('Assertions', 'assertions'), ('Sources', 'sources')]:
        try:
            out[dst] = int(sec.get(src, ''))
        except Exception:
            pass
    return {k: v for k, v in out.items() if v not in (None, [], '')}


def read_desktop_ini(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return parse_desktop_ini_text(decode_text_bytes(path.read_bytes()))
    except Exception:
        return {}


def find_state_file(root: Path) -> Path | None:
    candidates: list[Path] = []
    for p in root.rglob('*.json'):
        low = p.name.lower()
        if any(low.endswith(sfx) for sfx in STATE_SUFFIXES):
            candidates.append(p)
    if not candidates:
        return None

    def rank(p: Path):
        low = p.name.lower()
        modern = low.endswith('.kristal-state.json') or low == 'kristal_state.json'
        corpus = 'corpus' in [x.lower() for x in p.parts]
        return (0 if modern else 1, 0 if corpus else 1, len(p.parts), p.as_posix().lower())

    return sorted(candidates, key=rank)[0]


def read_state_metadata(path: Path | None) -> tuple[dict[str, Any], dict[str, int]]:
    if not path:
        return {}, {}
    try:
        data = load_json(path)
    except Exception:
        return {'state_file': path.name, 'read_error': True}, {}
    state = {
        'state_file': path.name,
        'schema_version': data.get('schema_version'),
        'artifact_type': data.get('artifact_type'),
        'artifact_status': data.get('artifact_status') or data.get('status'),
        'state_id': data.get('state_id'),
        'created_at': data.get('created_at'),
    }
    metrics: dict[str, int] = {}
    for src, dst in [('assertions', 'assertions'), ('source_refs', 'sources')]:
        if isinstance(data.get(src), list):
            metrics[dst] = len(data[src])
    return {k: v for k, v in state.items() if v is not None}, metrics


def load_overrides() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    if not OVERRIDES.is_file():
        return {'nature': 'REF'}, {}
    value = load_json(OVERRIDES)
    return value.get('defaults') or {'nature': 'REF'}, value.get('entries') or {}


def enrich_presentation(
    entry: dict[str, Any],
    desktop_binding: dict[str, Any],
    overrides: dict[str, dict[str, Any]],
    defaults: dict[str, Any],
) -> None:
    entry.setdefault('presentation', {})
    entry.setdefault('bindings', {})
    if desktop_binding:
        entry['bindings']['desktop'] = desktop_binding

    override = overrides.get(entry.get('kristal_ref') or '') or overrides.get(entry['kristal_id']) or {}
    icon: dict[str, Any] = {}
    for key in ('icon_code', 'nature', 'domains', 'maturity'):
        if key in desktop_binding:
            icon[key] = desktop_binding[key]
    if icon:
        icon['classification_origin'] = 'desktop_binding'
    for k, v in override.items():
        if k not in icon:
            icon[k] = v
    if 'nature' not in icon:
        icon['nature'] = defaults.get('nature', 'REF')
        icon['classification_origin'] = 'default'
    elif icon.get('classification_origin') != 'desktop_binding':
        icon.setdefault('classification_origin', 'curated_override')
    entry['presentation']['icon'] = icon

    # desktop counts are a presentation cache only; readable state counts win.
    if not entry.get('metrics') and desktop_binding:
        for k in ('assertions', 'sources'):
            if k in desktop_binding:
                entry.setdefault('metrics', {})[k] = desktop_binding[k]
                entry['metrics']['origin'] = 'desktop_cache'


VALID_NATURES = {'REF', 'COL', 'MOD', 'PRT', 'TWN', 'INV', 'SRC'}


def sanitize_icon_profile(value: dict[str, Any]) -> dict[str, Any] | None:
    if value.get('profile') != 'kristal-icon/1.0':
        return None
    nature = str(value.get('nature') or '')
    maturity = value.get('maturity')
    raw_domains = value.get('domains')
    if nature not in VALID_NATURES or not isinstance(maturity, int) or not (0 <= maturity <= 5):
        return None
    if not isinstance(raw_domains, list) or not (1 <= len(raw_domains) <= 3):
        return None
    domains: list[dict[str, str]] = []
    for d in raw_domains:
        if not isinstance(d, dict):
            return None
        code = str(d.get('code') or '').strip().upper()
        color = str(d.get('color') or '').strip()
        name = str(d.get('name') or code).strip()
        if not re.fullmatch(r'[A-Z0-9]{2,8}', code) or not re.fullmatch(r'#[0-9A-Fa-f]{6}', color):
            return None
        domains.append({'code': code, 'name': name, 'color': color.upper()})
    rendering = value.get('rendering') if isinstance(value.get('rendering'), dict) else {}
    filename = rendering.get('filename')
    if not filename:
        filename = f"KR-{nature}-{'-'.join(d['code'] for d in domains)}-M{maturity}.ico"
    return {
        'profile': 'kristal-icon/1.0',
        'kristal_ref': value.get('kristal_ref'),
        'nature': nature,
        'maturity': maturity,
        'domains': domains,
        'rendering': {
            'nature_icon_color': rendering.get('nature_icon_color') or '#1e6864',
            'sizes': rendering.get('sizes') or [16,20,24,32,40,48,64,96,128,256],
            'filename': filename,
        },
        'icon_code': str(filename).removesuffix('.ico'),
        'classification_origin': 'meta_overlay.icon_profile',
    }


def entry_match_index(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for e in entries:
        keys = [e.get('kristal_id'), e.get('kristal_ref')]
        loc = str(e.get('locator') or '').rstrip('/').split('/')[-1]
        keys.append(loc)
        for key in keys:
            if key:
                out[str(key)] = e
    return out


def apply_meta_record(entry: dict[str, Any], record: dict[str, Any], source_label: str) -> None:
    icon = sanitize_icon_profile(record.get('icon_profile') or {})
    if icon:
        entry.setdefault('presentation', {})['icon'] = icon
    desktop = record.get('desktop') or {}
    if desktop:
        desktop = dict(desktop)
        desktop['binding_origin'] = source_label
        # desktop.ini is a cache; the normalized icon profile remains presentation authority.
        entry.setdefault('bindings', {})['desktop'] = desktop
    normalization = record.get('normalization') or {}
    normalized = record.get('normalized_catalog_entry') or {}
    if normalization or normalized:
        meta: dict[str, Any] = {
            'source': source_label,
            'authority': 'derived_rebuildable_meta; canonical Kristal artifact remains authoritative',
        }
        if normalization:
            for key in ('profile', 'generated_at', 'semantic_rewrite', 'canonical_artifact', 'presentation', 'maturity_basis', 'v8_normalization'):
                if key in normalization:
                    meta[key] = normalization[key]
        if normalized:
            meta['normalized_catalog_observation'] = {
                k: normalized[k] for k in (
                    'adapter_kind', 'normalization_changes', 'record_role_mappings',
                    'portable_assertions', 'portable_state_id', 'portable_byte_sha256',
                    'lexicon_fr', 'query_indexes'
                ) if k in normalized
            }
        entry['normalization'] = meta


def _overlay_records_from_zip(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    summary: dict[str, Any] = {'source': str(path), 'kind': 'zip'}
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        catalog_name = next((n for n in names if n.endswith('domains/_catalog/kristal-v8-normalized-catalog.json')), None)
        normalized_by_ref: dict[str, dict[str, Any]] = {}
        if catalog_name:
            cat = zip_read_json(z, catalog_name) or {}
            summary['profile'] = cat.get('profile')
            summary['framework'] = cat.get('framework')
            for row in cat.get('entries') or []:
                if isinstance(row, dict) and row.get('kristal_ref'):
                    normalized_by_ref[str(row['kristal_ref'])] = row
        profile_names = [n for n in names if re.match(r'(?:.*/)?domains/Kristal-[^/]+/\.kristal/icon-profile\.json$', n)]
        for n in profile_names:
            prefix = n[:-len('.kristal/icon-profile.json')]
            icon = zip_read_json(z, n) or {}
            ref = str(icon.get('kristal_ref') or prefix.rstrip('/').split('/')[-1])
            record = records.setdefault(ref, {})
            record['icon_profile'] = icon
            norm_name = prefix + '.kristal/normalization.json'
            if norm_name in names:
                record['normalization'] = zip_read_json(z, norm_name) or {}
            desktop_name = prefix + 'desktop.ini'
            if desktop_name in names:
                record['desktop'] = zip_read_desktop_ini(z, desktop_name)
            if ref in normalized_by_ref:
                record['normalized_catalog_entry'] = normalized_by_ref[ref]
        summary['records'] = len(records)
        summary['icon_profiles'] = sum(1 for r in records.values() if r.get('icon_profile'))
    return records, summary


def _overlay_records_from_directory(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    base = path
    domains = base / 'domains'
    if not domains.is_dir() and base.name == 'domains':
        domains = base
    records: dict[str, dict[str, Any]] = {}
    summary: dict[str, Any] = {'source': str(path), 'kind': 'directory'}
    normalized_by_ref: dict[str, dict[str, Any]] = {}
    cat_path = domains / '_catalog' / 'kristal-v8-normalized-catalog.json'
    if cat_path.is_file():
        cat = load_json(cat_path)
        summary['profile'] = cat.get('profile')
        summary['framework'] = cat.get('framework')
        for row in cat.get('entries') or []:
            if isinstance(row, dict) and row.get('kristal_ref'):
                normalized_by_ref[str(row['kristal_ref'])] = row
    if domains.is_dir():
        for d in domains.iterdir():
            if not d.is_dir() or not d.name.startswith('Kristal-'):
                continue
            ip = d / '.kristal' / 'icon-profile.json'
            if not ip.is_file():
                continue
            icon = load_json(ip)
            ref = str(icon.get('kristal_ref') or d.name)
            record = records.setdefault(ref, {})
            record['icon_profile'] = icon
            np = d / '.kristal' / 'normalization.json'
            if np.is_file(): record['normalization'] = load_json(np)
            desktop = read_desktop_ini(d / 'desktop.ini')
            if desktop: record['desktop'] = desktop
            if ref in normalized_by_ref: record['normalized_catalog_entry'] = normalized_by_ref[ref]
    summary['records'] = len(records)
    summary['icon_profiles'] = sum(1 for r in records.values() if r.get('icon_profile'))
    return records, summary


def apply_meta_overlay(entries: list[dict[str, Any]], overlay: Path, source_collection: dict[str, Any], *, role: str) -> int:
    overlay = overlay.expanduser().resolve()
    if overlay.is_file() and zipfile.is_zipfile(overlay):
        records, summary = _overlay_records_from_zip(overlay)
    elif overlay.is_dir():
        records, summary = _overlay_records_from_directory(overlay)
    else:
        raise FileNotFoundError(overlay)
    idx = entry_match_index(entries)
    applied = 0
    unmatched: list[str] = []
    for ref, record in records.items():
        entry = idx.get(ref)
        if not entry:
            unmatched.append(ref)
            continue
        apply_meta_record(entry, record, f'{role}:{overlay.name}')
        applied += 1
    summary['role'] = role
    summary['applied'] = applied
    summary['unmatched'] = unmatched
    if summary.get('records') or role != 'embedded':
        source_collection.setdefault('meta_overlays', []).append(summary)
    return applied


def icon_is_renderable(icon: dict[str, Any]) -> bool:
    if icon.get('nature') not in VALID_NATURES:
        return False
    if not isinstance(icon.get('maturity'), int) or not 0 <= icon['maturity'] <= 5:
        return False
    ds = icon.get('domains')
    return isinstance(ds, list) and 1 <= len(ds) <= 3 and all(
        isinstance(d, dict) and re.fullmatch(r'[A-Z0-9]{2,8}', str(d.get('code') or '')) and re.fullmatch(r'#[0-9A-Fa-f]{6}', str(d.get('color') or ''))
        for d in ds
    )


def apply_mediatheque_binding(entries: list[dict[str, Any]], db_path: Path | None) -> None:
    if not db_path:
        return
    if not db_path.is_file():
        raise FileNotFoundError(db_path)
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'kristal_artifacts' not in tables:
            return
        has_versions = 'kristal_versions' in tables
        if has_versions:
            rows = con.execute('''
                SELECT a.kristal_uuid,a.kristal_id,a.canonical_locator,a.lifecycle_status,
                       COUNT(v.kristal_version_uuid) AS version_count,
                       MAX(v.observed_at) AS last_observed_at
                FROM kristal_artifacts a
                LEFT JOIN kristal_versions v ON v.kristal_uuid=a.kristal_uuid
                GROUP BY a.kristal_uuid,a.kristal_id,a.canonical_locator,a.lifecycle_status
            ''').fetchall()
        else:
            rows = con.execute('''
                SELECT a.kristal_uuid,a.kristal_id,a.canonical_locator,a.lifecycle_status,
                       0 AS version_count,NULL AS last_observed_at
                FROM kristal_artifacts a
            ''').fetchall()
        by_id = {str(r['kristal_id']): dict(r) for r in rows}
        for e in entries:
            hit = by_id.get(e['kristal_id']) or (by_id.get(str(e['kristal_ref'])) if e.get('kristal_ref') else None)
            if hit:
                binding = {'binding_profile': 'kristal-registry.binding/mediatheque-sqlite-1.0'}
                binding.update({k: v for k, v in hit.items() if v is not None})
                e.setdefault('bindings', {})['mediatheque'] = binding
    finally:
        con.close()


def base_entry(
    *, kristal_id: str, kristal_ref: str | None, title: str, kind: str,
    locator: str, parent_kristal_ref: str | None, availability: str,
    state: dict[str, Any], metrics: dict[str, Any], relations: list[dict[str, Any]],
    observed: str,
) -> dict[str, Any]:
    return {
        'kristal_id': kristal_id,
        'kristal_ref': kristal_ref,
        'title': title,
        'kind': kind,
        'locator': locator,
        'parent_kristal_ref': parent_kristal_ref,
        'availability': availability,
        'state_observation': state,
        'metrics': metrics,
        'presentation': {},
        'bindings': {},
        'relations': relations,
        'observed_at': observed,
    }


def observe_v9_state_dir(path: Path) -> dict[str, Any] | None:
    p = path / '.kristal' / 'v9' / 'state-snapshot.json'
    if not p.is_file(): return None
    try: d=load_json(p)
    except Exception: return None
    if d.get('schema_version')!='9.0' or d.get('artifact_type')!='kristal_state_snapshot': return None
    c=d.get('logical_commitment') or {}
    return {'profile':'kristal-registry.observation/v9-state-1.0','state_ref':d.get('state_ref'),'logical_commitment':c,'members':len(d.get('members') or []),'references':len(d.get('references') or []),'authority':'observed_only; source Kristal remains authoritative'}

def observe_v9_state_zip(z: zipfile.ZipFile, prefix: str) -> dict[str, Any] | None:
    name=prefix+'.kristal/v9/state-snapshot.json'
    if name not in z.namelist(): return None
    d=zip_read_json(z,name) or {}
    if d.get('schema_version')!='9.0' or d.get('artifact_type')!='kristal_state_snapshot': return None
    return {'profile':'kristal-registry.observation/v9-state-1.0','state_ref':d.get('state_ref'),'logical_commitment':d.get('logical_commitment') or {},'members':len(d.get('members') or []),'references':len(d.get('references') or []),'authority':'observed_only; source Kristal remains authoritative'}

def domain_entry(path: Path, collection_root: Path, observed: str, defaults, overrides) -> dict[str, Any]:
    state_path = find_state_file(path)
    state, metrics = read_state_metadata(state_path)
    title = normalize_title(path.name)
    readme = path / 'README.md'
    if readme.is_file():
        try:
            title = read_title_text(readme.read_text(encoding='utf-8', errors='replace'), title)
        except OSError:
            pass
    entry = base_entry(
        kristal_id=path.name,
        kristal_ref=state.get('state_id'),
        title=title,
        kind='domain',
        locator=path.relative_to(collection_root).as_posix(),
        parent_kristal_ref=None,
        availability='present' if state_path else 'unreadable',
        state=state,
        metrics=metrics,
        relations=[{'predicate': 'member_of_collection', 'object': 'Kristal-Kollection'}],
        observed=observed,
    )
    enrich_presentation(entry, read_desktop_ini(path / 'desktop.ini'), overrides, defaults)
    v9=observe_v9_state_dir(path)
    if v9: entry.setdefault('normalization', {})['v9_state'] = v9
    return entry


def university_entries(root: Path, collection_root: Path, observed: str, defaults, overrides) -> list[dict[str, Any]]:
    manifest_path = root / 'manifest.json'
    if not manifest_path.is_file():
        return []
    try:
        manifest = load_json(manifest_path)
    except Exception:
        return []
    items = manifest.get('entries')
    if not isinstance(items, list):
        return []
    out: list[dict[str, Any]] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        kind = {'course': 'course', 'voie': 'voie', 'university': 'university'}.get(str(row.get('kind') or ''), 'other')
        rel = str(row.get('path') or '')
        target = collection_root / rel if rel else root
        ref = row.get('kristal_ref') or row.get('kristal_id')
        eid = str(ref or rel or row.get('title') or 'unknown')
        state: dict[str, Any] = {}
        metrics: dict[str, Any] = {}
        availability = 'stub'
        if target.is_file():
            try:
                data = load_json(target)
                state = {k: v for k, v in {
                    'format': data.get('format'), 'status': data.get('status'), 'artifact_type': data.get('artifact_type'),
                    'schema_version': data.get('schema_version'), 'state_id': data.get('state_id')
                }.items() if v is not None}
                availability = 'stub' if data.get('status') == 'stub' or 'stub' in str(data.get('format', '')) else 'present'
            except Exception:
                availability = 'unreadable'
        relations = [
            {'predicate': 'member_of_collection', 'object': 'Kristal-Kollection'},
            {'predicate': 'member_of_university', 'object': root.name},
        ]
        if row.get('parent_kristal_ref'):
            relations.append({'predicate': 'child_of', 'object': row['parent_kristal_ref']})
        entry = base_entry(
            kristal_id=eid, kristal_ref=ref, title=str(row.get('title') or eid), kind=kind,
            locator=rel or root.relative_to(collection_root).as_posix(), parent_kristal_ref=row.get('parent_kristal_ref'),
            availability=availability, state=state, metrics=metrics, relations=relations, observed=observed,
        )
        desktop_path = target.parent / 'desktop.ini' if target.is_file() else target / 'desktop.ini'
        enrich_presentation(entry, read_desktop_ini(desktop_path), overrides, defaults)
        out.append(entry)
    refs = {e.get('kristal_ref'): e for e in out if e.get('kristal_ref')}
    for e in out:
        parent = e.get('parent_kristal_ref')
        if parent and parent in refs:
            refs[parent]['relations'].append({'predicate': 'parent_of', 'object': e.get('kristal_ref') or e['kristal_id']})
    return out


def scan_directory(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(root)
    observed = utc_now()
    defaults, overrides = load_overrides()
    entries: list[dict[str, Any]] = []
    domains = root / 'domains'
    if domains.is_dir():
        for p in sorted(domains.iterdir(), key=lambda x: x.name.lower()):
            if p.is_dir() and p.name.startswith('Kristal-'):
                entries.append(domain_entry(p, root, observed, defaults, overrides))
    universities = root / 'universities'
    if universities.is_dir():
        for p in sorted(universities.iterdir(), key=lambda x: x.name.lower()):
            if p.is_dir():
                entries.extend(university_entries(p, root, observed, defaults, overrides))
    tailored = root / 'tailored'
    if tailored.is_dir():
        for p in sorted(tailored.iterdir(), key=lambda x: x.name.lower()):
            if p.is_dir() and p.name.startswith('Kristal-'):
                e = domain_entry(p, root, observed, defaults, overrides)
                e['kind'] = 'tailored'
                entries.append(e)
    source_collection = {
        'id': 'Kristal-Kollection', 'root': str(root), 'source': 'filesystem',
        'layout_index': str(root / 'COLLECTION_INDEX.json') if (root / 'COLLECTION_INDEX.json').is_file() else None,
        'protected_paths': ['MediKristal/'],
        'policy': 'MediKristal is not recursively scanned by this builder.',
    }
    return source_collection, entries


def decode_text_bytes(data: bytes) -> str:
    if data.startswith(b'\xff\xfe') or data.startswith(b'\xfe\xff'):
        return data.decode('utf-16')
    try:
        return data.decode('utf-8-sig')
    except UnicodeDecodeError:
        return data.decode('utf-8', 'replace')


def zip_read_json(z: zipfile.ZipFile, name: str) -> dict[str, Any] | None:
    try:
        value = json.loads(z.read(name))
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def zip_read_text(z: zipfile.ZipFile, name: str) -> str | None:
    try:
        return decode_text_bytes(z.read(name))
    except Exception:
        return None


def zip_read_desktop_ini(z: zipfile.ZipFile, name: str) -> dict[str, Any]:
    text = zip_read_text(z, name)
    return parse_desktop_ini_text(text) if text is not None else {}


def scan_zip(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    observed = utc_now()
    defaults, overrides = load_overrides()
    entries: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        name_set = set(names)
        domain_names = sorted({n.split('/')[1] for n in names if n.startswith('domains/Kristal-') and len(n.split('/')) > 2})
        for d in domain_names:
            prefix = f'domains/{d}/'
            files = [n for n in names if n.startswith(prefix) and not n.endswith('/')]
            state_names = [n for n in files if any(n.lower().endswith(sfx) for sfx in STATE_SUFFIXES)]
            state_names = sorted(state_names, key=lambda n: (
                0 if n.lower().endswith('.kristal-state.json') or n.lower().endswith('/kristal_state.json') else 1,
                0 if '/corpus/' in n else 1, len(n.split('/')), n.lower()
            ))
            state: dict[str, Any] = {}
            metrics: dict[str, Any] = {}
            if state_names:
                data = zip_read_json(z, state_names[0]) or {}
                state = {k: v for k, v in {
                    'state_file': state_names[0][len(prefix):], 'schema_version': data.get('schema_version'),
                    'artifact_type': data.get('artifact_type'), 'artifact_status': data.get('artifact_status') or data.get('status'),
                    'state_id': data.get('state_id'), 'created_at': data.get('created_at')
                }.items() if v is not None}
                if isinstance(data.get('assertions'), list):
                    metrics['assertions'] = len(data['assertions'])
                if isinstance(data.get('source_refs'), list):
                    metrics['sources'] = len(data['source_refs'])
            title = normalize_title(d)
            readme = zip_read_text(z, prefix + 'README.md')
            if readme:
                title = read_title_text(readme, title)
            e = base_entry(
                kristal_id=d, kristal_ref=state.get('state_id'), title=title, kind='domain',
                locator=prefix.rstrip('/'), parent_kristal_ref=None,
                availability='present' if state_names else 'unreadable', state=state, metrics=metrics,
                relations=[{'predicate': 'member_of_collection', 'object': 'Kristal-Kollection'}], observed=observed,
            )
            enrich_presentation(e, zip_read_desktop_ini(z, prefix + 'desktop.ini'), overrides, defaults)
            v9=observe_v9_state_zip(z,prefix)
            if v9: e.setdefault('normalization', {})['v9_state']=v9
            entries.append(e)

        manifests = [n for n in names if re.match(r'universities/[^/]+/manifest\.json$', n)]
        for mn in manifests:
            manifest = zip_read_json(z, mn) or {}
            rows = manifest.get('entries') or []
            uni = mn.split('/')[1]
            if not isinstance(rows, list):
                continue
            temp: list[dict[str, Any]] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                kind = {'course': 'course', 'voie': 'voie', 'university': 'university'}.get(str(row.get('kind')), 'other')
                ref = row.get('kristal_ref') or row.get('kristal_id')
                locator = str(row.get('path') or f'universities/{uni}')
                target = zip_read_json(z, locator) or {}
                avail = 'stub' if target.get('status') == 'stub' or 'stub' in str(target.get('format', '')) else ('present' if locator in name_set else 'missing')
                relations = [
                    {'predicate': 'member_of_collection', 'object': 'Kristal-Kollection'},
                    {'predicate': 'member_of_university', 'object': uni},
                ]
                if row.get('parent_kristal_ref'):
                    relations.append({'predicate': 'child_of', 'object': row['parent_kristal_ref']})
                e = base_entry(
                    kristal_id=str(ref or locator), kristal_ref=ref, title=str(row.get('title') or ref or locator), kind=kind,
                    locator=locator, parent_kristal_ref=row.get('parent_kristal_ref'), availability=avail,
                    state={k: v for k, v in {
                        'format': target.get('format'), 'status': target.get('status'), 'schema_version': target.get('schema_version'),
                        'artifact_type': target.get('artifact_type'), 'state_id': target.get('state_id')
                    }.items() if v is not None}, metrics={}, relations=relations, observed=observed,
                )
                desktop_name = locator.rsplit('/', 1)[0] + '/desktop.ini' if '/' in locator else 'desktop.ini'
                enrich_presentation(e, zip_read_desktop_ini(z, desktop_name), overrides, defaults)
                temp.append(e)
            refs = {e.get('kristal_ref'): e for e in temp if e.get('kristal_ref')}
            for e in temp:
                p = e.get('parent_kristal_ref')
                if p in refs:
                    refs[p]['relations'].append({'predicate': 'parent_of', 'object': e.get('kristal_ref') or e['kristal_id']})
            entries.extend(temp)
    return {
        'id': 'Kristal-Kollection', 'root': str(path), 'source': 'zip_snapshot',
        'protected_paths': ['MediKristal/'], 'policy': 'MediKristal was not recursively cataloged.',
    }, entries


def counts(entries: list[dict[str, Any]]) -> dict[str, Any]:
    by_kind: dict[str, int] = {}
    by_nature: dict[str, int] = {}
    by_avail: dict[str, int] = {}
    bindings = {'desktop': 0, 'mediatheque': 0}
    for e in entries:
        by_kind[e['kind']] = by_kind.get(e['kind'], 0) + 1
        n = (((e.get('presentation') or {}).get('icon') or {}).get('nature') or 'UNCLASSIFIED')
        by_nature[n] = by_nature.get(n, 0) + 1
        a = e['availability']
        by_avail[a] = by_avail.get(a, 0) + 1
        for b in bindings:
            if b in (e.get('bindings') or {}):
                bindings[b] += 1
    normalized = sum(1 for e in entries if e.get('normalization'))
    renderable = sum(1 for e in entries if icon_is_renderable(((e.get('presentation') or {}).get('icon') or {})))
    return {
        'total': len(entries), 'by_kind': dict(sorted(by_kind.items())),
        'by_nature': dict(sorted(by_nature.items())), 'by_availability': dict(sorted(by_avail.items())),
        'bindings': bindings,
        'meta': {'normalized': normalized, 'renderable_icons': renderable},
    }


def make_assertion(subject: str, predicate: str, obj: dict[str, Any], *, coordinates: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    core = {
        'statement': {'subject': {'kind': 'item', 'id': subject}, 'predicate': predicate, 'object': obj},
        'assertion_status': 'reviewed', 'record_role': 'structural_record', 'coordinates': coordinates or [],
        'applicability': {'domain': 'kristal-registry', 'language': 'fr'},
        'actionability': {'mode': 'not_applicable'}, 'evidence_refs': [],
        'provenance_refs': ['prov:kristal-registry:scan'],
    }
    core['assertion_id'] = 'sha256:' + digest(core)
    return core


def build_state(catalog: dict[str, Any]) -> dict[str, Any]:
    observed = catalog['generated_at']
    assertions: list[dict[str, Any]] = []
    for e in catalog['entries']:
        eid = 'registry:kristal:' + hashlib.sha256(e['kristal_id'].encode('utf-8')).hexdigest()[:24]
        coords = [{'axis': 'entry_kind', 'value': e['kind']}, {'axis': 'availability', 'value': e['availability']}]
        assertions.append(make_assertion(eid, 'registry.member_of', {'kind': 'item', 'id': REGISTRY_ID}, coordinates=coords))
        assertions.append(make_assertion(eid, 'registry.has_title', {'kind': 'string', 'value': e['title']}, coordinates=coords))
        assertions.append(make_assertion(eid, 'registry.has_locator', {'kind': 'string', 'value': e['locator']}, coordinates=coords))
        assertions.append(make_assertion(eid, 'registry.has_kind', {'kind': 'string', 'value': e['kind']}, coordinates=coords))
        icon = ((e.get('presentation') or {}).get('icon') or {})
        if icon.get('nature'):
            assertions.append(make_assertion(eid, 'registry.has_icon_nature', {'kind': 'string', 'value': icon['nature']}, coordinates=coords))
        if isinstance(icon.get('maturity'), int):
            assertions.append(make_assertion(eid, 'registry.has_icon_maturity', {'kind': 'string', 'value': str(icon['maturity'])}, coordinates=coords))
        for domain in icon.get('domains') or []:
            code = domain.get('code') if isinstance(domain, dict) else domain
            if code:
                assertions.append(make_assertion(eid, 'registry.has_icon_domain', {'kind': 'string', 'value': str(code)}, coordinates=coords))
        if icon.get('icon_code'):
            assertions.append(make_assertion(eid, 'registry.has_icon_code', {'kind': 'string', 'value': str(icon['icon_code'])}, coordinates=coords))
        normalization = e.get('normalization') or {}
        if normalization.get('profile'):
            assertions.append(make_assertion(eid, 'registry.has_normalization_profile', {'kind': 'string', 'value': str(normalization['profile'])}, coordinates=coords))
        normalized_obs = normalization.get('normalized_catalog_observation') or {}
        if normalized_obs.get('portable_state_id'):
            assertions.append(make_assertion(eid, 'registry.has_portable_state_id', {'kind': 'string', 'value': str(normalized_obs['portable_state_id'])}, coordinates=coords))
        state_obs = e.get('state_observation') or {}
        if state_obs.get('schema_version'):
            assertions.append(make_assertion(eid, 'registry.observed_schema_version', {'kind': 'string', 'value': str(state_obs['schema_version'])}, coordinates=coords))
        if e.get('parent_kristal_ref'):
            assertions.append(make_assertion(eid, 'registry.child_of_ref', {'kind': 'string', 'value': str(e['parent_kristal_ref'])}, coordinates=coords))
        media = (e.get('bindings') or {}).get('mediatheque') or {}
        if media.get('kristal_uuid'):
            assertions.append(make_assertion(eid, 'registry.has_mediatheque_binding', {'kind': 'string', 'value': str(media['kristal_uuid'])}, coordinates=coords))

    state = {
        'schema_version': '6.0', 'artifact_type': 'kristal_state', 'artifact_status': 'working', 'created_at': observed,
        'created_by': {'kind': 'software', 'label': 'Kristal Registry builder', 'human_authority_claimed': False},
        'canonicalization_profile': 'kristal.v6:jcs-rfc8785', 'canonicalization_version': '1',
        'applicability': {'domain': 'kristal-registry', 'subdomain': 'inventory-of-kristals', 'language': 'fr'},
        'source_refs': ['src:kristal-kollection:layout', 'src:kristal-registry:catalog'],
        'assertions': assertions,
        'provenance': [{
            'event': 'registry_scan', 'created_at': observed,
            'method': 'filesystem/zip metadata scan + optional v8 normalization meta overlay + optional desktop.ini + optional Mediatheque SQLite binding',
            'notes': 'This state is a projection of the Registry catalog. It is not the native Registry serialization and is not semantic authority for inventoried Kristal content.'
        }],
        'build': {'package_version': PACKAGE_VERSION, 'generator': 'Build-Kristal-Registry.py', 'entry_count': len(catalog['entries']), 'assertion_count': len(assertions)},
        'warnings': [
            'This kristal_state is a derived projection of kristal-registry.catalog/1.1.',
            'Local paths, counts and desktop metadata are observational and may become stale.',
            'Kristal Registry is not semantic authority for inventoried Kristal content.',
            'Mediatheque bindings do not redefine Kristal identity.'
        ],
        'extensions': {'registry_profile': CATALOG_PROFILE, 'representation_role': 'kristal_projection', 'icon_nature': 'COL'},
    }
    identity_target = dict(state)
    for key in ('state_id', 'content_hash', 'signatures'):
        identity_target.pop(key, None)
    h = digest(identity_target)
    state['state_id'] = 'sha256:' + h
    state['content_hash'] = {'alg': 'sha256', 'value': h}
    return state


def render_html(catalog: dict[str, Any]) -> str:
    data = json.dumps(catalog, ensure_ascii=False).replace('</', '<\\/')
    return f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kristal Registry</title><style>
:root{{--bg:#f4f7f6;--card:#fff;--ink:#16302f;--muted:#6d7d7c;--line:#d9e3e0;--accent:#1e6864}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);font:14px/1.45 system-ui,sans-serif;color:var(--ink)}}main{{max-width:1250px;margin:auto;padding:28px}}h1{{font-size:34px;margin:0 0 4px}}.sub{{color:var(--muted);margin-bottom:18px}}.tools{{display:grid;grid-template-columns:2fr repeat(4,1fr);gap:8px;margin-bottom:16px}}input,select{{padding:10px;border:1px solid var(--line);border-radius:9px;background:#fff}}.stats{{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}}.stat{{background:#e5efed;border-radius:999px;padding:6px 10px}}.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}}.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px}}.top{{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}}.nature{{background:var(--accent);color:#fff;border-radius:8px;padding:4px 7px;font-weight:700}}.kind{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}}h2{{font-size:16px;margin:5px 0 8px}}.meta{{font-size:12px;color:var(--muted)}}code{{font-size:11px;overflow-wrap:anywhere}}.chips{{display:flex;gap:5px;flex-wrap:wrap;margin-top:8px}}.chip{{font-size:11px;background:#f0f4f3;border-radius:999px;padding:3px 7px}}@media(max-width:900px){{.tools{{grid-template-columns:1fr 1fr}}}}
</style></head><body><main><h1>Kristal Registry</h1><div class="sub">Inventaire logique des Kristals · format {html.escape(catalog['format'])} · généré {html.escape(catalog['generated_at'])}</div><div class="tools"><input id="q" placeholder="Rechercher titre, id, chemin…"><select id="kind"><option value="">Tous les types</option></select><select id="nature"><option value="">Toutes les natures</option></select><select id="avail"><option value="">Tous les états</option></select><select id="binding"><option value="">Tous les bindings</option><option value="desktop">desktop</option><option value="mediatheque">Médiathèque</option></select></div><div class="stats" id="stats"></div><div class="grid" id="grid"></div></main><script>const catalog={data};const entries=catalog.entries;const q=document.querySelector('#q'),kind=document.querySelector('#kind'),nature=document.querySelector('#nature'),avail=document.querySelector('#avail'),binding=document.querySelector('#binding'),grid=document.querySelector('#grid'),stats=document.querySelector('#stats');function fill(sel,vals){{[...new Set(vals.filter(Boolean))].sort().forEach(v=>{{let o=document.createElement('option');o.value=v;o.textContent=v;sel.append(o)}})}}fill(kind,entries.map(e=>e.kind));fill(nature,entries.map(e=>e.presentation?.icon?.nature));fill(avail,entries.map(e=>e.availability));function esc(s){{return String(s??'').replace(/[&<>\"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}}[c]))}}function render(){{const t=q.value.toLowerCase();const rows=entries.filter(e=>(!t||JSON.stringify([e.title,e.kristal_id,e.kristal_ref,e.locator]).toLowerCase().includes(t))&&(!kind.value||e.kind===kind.value)&&(!nature.value||e.presentation?.icon?.nature===nature.value)&&(!avail.value||e.availability===avail.value)&&(!binding.value||e.bindings?.[binding.value]));stats.innerHTML=`<span class="stat">${{rows.length}} / ${{entries.length}} Kristals</span>`;grid.innerHTML=rows.map(e=>`<article class="card"><div class="top"><div><div class="kind">${{esc(e.kind)}} · ${{esc(e.availability)}}</div><h2>${{esc(e.title)}}</h2></div><span class="nature">${{esc(e.presentation?.icon?.nature||'?')}}</span></div><div class="meta"><code>${{esc(e.kristal_id)}}</code><br>${{esc(e.locator)}}</div><div class="chips">${{e.state_observation?.schema_version?`<span class="chip">schema ${{esc(e.state_observation.schema_version)}}</span>`:''}}${{Number.isInteger(e.metrics?.assertions)?`<span class="chip">${{e.metrics.assertions}} assertions</span>`:''}}${{Number.isInteger(e.metrics?.sources)?`<span class="chip">${{e.metrics.sources}} sources</span>`:''}}${{e.presentation?.icon?.domains?.length?`<span class="chip">${{e.presentation.icon.domains.map(d=>esc(typeof d==='string'?d:d.code)).join(' / ')}}</span>`:''}}${{e.presentation?.icon?.maturity!=null?`<span class="chip">M${{esc(e.presentation.icon.maturity)}}/5</span>`:''}}${{e.normalization?`<span class="chip">v8 meta</span>`:''}}${{e.bindings?.desktop?`<span class="chip">desktop</span>`:''}}${{e.bindings?.mediatheque?`<span class="chip">Médiathèque</span>`:''}}</div></article>`).join('')}}[q,kind,nature,avail,binding].forEach(x=>x.addEventListener('input',render));render();</script></body></html>'''


def validate_basic(catalog: dict[str, Any]) -> None:
    if catalog.get('format') != CATALOG_PROFILE:
        raise ValueError('wrong registry catalog profile')
    ids: list[tuple[str, str]] = []
    for e in catalog['entries']:
        for key in ('kristal_id', 'title', 'kind', 'locator', 'availability'):
            if not e.get(key):
                raise ValueError(f'missing {key}: {e}')
        if 'mediatheque' in e or 'icon' in e:
            raise ValueError('legacy mixed representation key found')
        ids.append((str(e.get('kristal_ref') or e['kristal_id']), e['locator']))
    if len(ids) != len(set(ids)):
        dup = [x for x in set(ids) if ids.count(x) > 1]
        raise ValueError(f'duplicate registry identities: {dup[:5]}')


def make_catalog(source_collection: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        'format': CATALOG_PROFILE,
        'registry': {
            'registry_id': REGISTRY_ID,
            'title': 'Kristal Registry',
            'nature': 'COL',
            'authority': 'inventory_and_registry_relations_only',
            'representations': {
                'native_catalog': 'knowledge-base/registry/kristal-registry.catalog.json',
                'kristal_projection': 'knowledge-base/projections/kristal/kristal-registry.kristal-state.json',
                'human_view': 'knowledge-base/views/registry.html',
            },
            'icon_generation': {
                'profile': 'kristal-icon/1.0',
                'entry_path': 'entries[].presentation.icon',
                'authority': 'presentation_only',
                'missing_profile_policy': 'do_not_invent',
            },
        },
        'generated_at': utc_now(),
        'source_collection': source_collection,
        'counts': counts(entries),
        'entries': entries,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description='Build Kristal Registry native catalog, Kristal projection and HTML view.')
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument('--root', type=Path, help='Kristal-Kollection root directory')
    source.add_argument('--zip', type=Path, help='Kristal-Kollection ZIP snapshot')
    ap.add_argument('--mediatheque-db', type=Path, help='Optional Médiathèque SQLite database; used only as an external binding')
    ap.add_argument('--meta-overlay', type=Path, action='append', default=[], help='Optional v8 normalization metadata overlay directory/ZIP. Repeatable.')
    ap.add_argument('--out', type=Path, default=PACKAGE_ROOT, help='Output package root (default: this package)')
    args = ap.parse_args()

    global CATALOG_OUT, STATE_OUT, VIEW_OUT
    out = args.out.resolve()
    CATALOG_OUT = out / 'knowledge-base/registry/kristal-registry.catalog.json'
    STATE_OUT = out / 'knowledge-base/projections/kristal/kristal-registry.kristal-state.json'
    VIEW_OUT = out / 'knowledge-base/views/registry.html'
    for p in (CATALOG_OUT, STATE_OUT, VIEW_OUT):
        p.parent.mkdir(parents=True, exist_ok=True)

    source_collection, entries = scan_directory(args.root) if args.root else scan_zip(args.zip)
    # Embedded .kristal metadata, when present, is consumed first.
    embedded = args.root if args.root else args.zip
    try:
        apply_meta_overlay(entries, embedded, source_collection, role='embedded')
    except Exception:
        pass
    # Explicit overlays have priority and are applied in command-line order.
    for overlay in args.meta_overlay:
        apply_meta_overlay(entries, overlay, source_collection, role='external')
    apply_mediatheque_binding(entries, args.mediatheque_db)
    entries.sort(key=lambda e: (e['kind'], e['title'].casefold(), e['kristal_id']))
    catalog = make_catalog(source_collection, entries)
    validate_basic(catalog)
    state = build_state(catalog)

    CATALOG_OUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    STATE_OUT.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    VIEW_OUT.write_text(render_html(catalog), encoding='utf-8')
    from kristal_v9_package import build as build_v9_package
    build_v9_package(out, catalog, state)

    print(f'Catalog: {CATALOG_OUT}')
    print(f'State:   {STATE_OUT}')
    print(f'View:    {VIEW_OUT}')
    print(json.dumps(catalog['counts'], ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
