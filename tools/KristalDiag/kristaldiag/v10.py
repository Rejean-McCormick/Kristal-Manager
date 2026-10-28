from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from .jcs import canonicalize
from .v9 import verify_declared_state

PUBLICATION_BUNDLE_PROFILE = 'kristal.publication-bundle/1.0'
DIGEST_PREFIX = 'sha256:'


def sha256_bytes(data: bytes) -> str:
    return DIGEST_PREFIX + hashlib.sha256(data).hexdigest()


def publication_identity(*, node_id: str, binding_id: str, state: dict[str, Any], bundle_manifest_digest: str) -> str:
    projection = {
        'node_id': node_id,
        'binding_id': binding_id,
        'state': copy.deepcopy(state),
        'bundle_manifest_digest': bundle_manifest_digest,
    }
    hx = hashlib.sha256(canonicalize(projection).encode('utf-8')).hexdigest()
    return f'urn:kristal:publication:sha256:{hx}'


def _safe_relative(raw: Any) -> bool:
    if not isinstance(raw, str) or not raw:
        return False
    p = Path(raw)
    return not p.is_absolute() and '..' not in p.parts


def _issue(issues: list[dict[str, str]], path: str, code: str, message: str) -> None:
    issues.append({'path': path, 'code': code, 'message': message})


def find_publication_bundles(root: Path, *, max_depth: int = 6) -> list[Path]:
    root = root.resolve()
    if root.is_file():
        root = root.parent
    out: list[Path] = []
    seen: set[Path] = set()
    for pub in root.rglob('publication.json'):
        try:
            rel = pub.relative_to(root)
        except ValueError:
            continue
        if len(rel.parts) > max_depth + 1:
            continue
        bundle = pub.parent.resolve()
        if bundle in seen:
            continue
        if (bundle / 'bundle-manifest.json').is_file() and (bundle / 'state-snapshot.json').is_file():
            seen.add(bundle)
            out.append(bundle)
    return sorted(out, key=lambda p: p.as_posix())


def verify_publication_bundle(bundle_dir: Path) -> dict[str, Any]:
    """Independent Python verification of the non-normative v10 bundle tool format.

    This intentionally does not execute the Kristal JavaScript reference implementation.
    JSON Schema validation of the Publication Record/State is performed by the v10 checks;
    this function verifies byte binding, publication identity, and v9 state commitment.
    """
    bundle = bundle_dir.resolve()
    issues: list[dict[str, str]] = []

    def read_json_file(name: str) -> dict[str, Any] | None:
        p = bundle / name
        try:
            value = json.loads(p.read_text(encoding='utf-8'))
        except Exception as exc:
            _issue(issues, name, 'MISSING_OR_INVALID_RESOURCE', str(exc))
            return None
        if not isinstance(value, dict):
            _issue(issues, name, 'INVALID_TYPE', 'document must be object')
            return None
        return value

    pub = read_json_file('publication.json')
    manifest = read_json_file('bundle-manifest.json')
    state = read_json_file('state-snapshot.json')
    if pub is None or manifest is None or state is None:
        return {'ok': False, 'issues': issues}

    if manifest.get('artifact_type') != 'kristal_publication_bundle_manifest' or manifest.get('profile') != PUBLICATION_BUNDLE_PROFILE:
        _issue(issues, 'bundle-manifest.json', 'UNSUPPORTED_PROFILE', f'expected {PUBLICATION_BUNDLE_PROFILE}')

    payloads = manifest.get('payloads')
    if not isinstance(payloads, list):
        _issue(issues, 'bundle-manifest.json.payloads', 'INVALID_TYPE', 'payloads must be array')
        payloads = []
    for i, resource in enumerate(payloads):
        path = f'bundle-manifest.json.payloads[{i}]'
        if not isinstance(resource, dict):
            _issue(issues, path, 'INVALID_TYPE', 'payload must be object')
            continue
        raw = resource.get('path')
        if not _safe_relative(raw):
            _issue(issues, path + '.path', 'INVALID_PATH', 'payload path must be relative and contained')
            continue
        file = (bundle / str(raw)).resolve()
        try:
            file.relative_to(bundle)
        except ValueError:
            _issue(issues, path + '.path', 'INVALID_PATH', 'payload escapes bundle')
            continue
        if not file.is_file():
            _issue(issues, str(raw), 'MISSING_RESOURCE', 'payload missing')
            continue
        data = file.read_bytes()
        if resource.get('size') != len(data):
            _issue(issues, str(raw), 'SIZE_MISMATCH', f"expected {resource.get('size')}, got {len(data)}")
        got = sha256_bytes(data)
        if resource.get('blob_digest') != got:
            _issue(issues, str(raw), 'DIGEST_MISMATCH', f"expected {resource.get('blob_digest')}, got {got}")

    manifest_bytes = (bundle / 'bundle-manifest.json').read_bytes()
    manifest_digest = sha256_bytes(manifest_bytes)
    extensions = pub.get('extensions') if isinstance(pub.get('extensions'), dict) else {}
    bundle_ext = extensions.get('bundle') if isinstance(extensions.get('bundle'), dict) else {}
    if bundle_ext.get('manifest_blob_digest') != manifest_digest:
        _issue(issues, 'publication.json.extensions.bundle.manifest_blob_digest', 'DIGEST_MISMATCH', 'publication does not bind exact bundle manifest bytes')

    try:
        expected_id = publication_identity(
            node_id=str(pub.get('node_id') or ''),
            binding_id=str(pub.get('binding_id') or ''),
            state=pub.get('state') if isinstance(pub.get('state'), dict) else {},
            bundle_manifest_digest=manifest_digest,
        )
        if pub.get('publication_id') != expected_id:
            _issue(issues, 'publication.json.publication_id', 'DIGEST_MISMATCH', 'publication_id does not match publication identity projection')
    except Exception as exc:
        _issue(issues, 'publication.json.publication_id', 'IDENTITY_ERROR', str(exc))
        expected_id = None

    resources = pub.get('resources')
    if isinstance(resources, list):
        for i, resource in enumerate(resources):
            if not isinstance(resource, dict):
                continue
            locator = resource.get('locator')
            if not isinstance(locator, str) or not locator.startswith('bundle://'):
                continue
            rel = locator[len('bundle://'):]
            if not _safe_relative(rel):
                _issue(issues, f'publication.json.resources[{i}].locator', 'INVALID_PATH', 'bundle locator invalid')
                continue
            file = (bundle / rel).resolve()
            try:
                file.relative_to(bundle)
            except ValueError:
                _issue(issues, f'publication.json.resources[{i}].locator', 'INVALID_PATH', 'bundle locator escapes bundle')
                continue
            if not file.is_file():
                _issue(issues, rel, 'MISSING_RESOURCE', 'publication resource missing')
                continue
            data = file.read_bytes()
            if resource.get('size') != len(data):
                _issue(issues, rel, 'SIZE_MISMATCH', f"expected {resource.get('size')}, got {len(data)}")
            got = sha256_bytes(data)
            if resource.get('blob_digest') != got:
                _issue(issues, rel, 'DIGEST_MISMATCH', f"expected {resource.get('blob_digest')}, got {got}")

    declared_state = pub.get('state') if isinstance(pub.get('state'), dict) else {}
    manifest_state = manifest.get('state') if isinstance(manifest.get('state'), dict) else {}
    snapshot_ref = {
        'state_ref': state.get('state_ref'),
        'logical_commitment': state.get('logical_commitment'),
    }
    if declared_state != manifest_state:
        _issue(issues, 'publication.json.state', 'STATE_BINDING_MISMATCH', 'publication state does not match bundle manifest state')
    if declared_state != snapshot_ref:
        _issue(issues, 'state-snapshot.json', 'STATE_BINDING_MISMATCH', 'publication state does not match bundled state snapshot')

    ok_state, actual_state, state_errors = verify_declared_state(state)
    if not ok_state:
        _issue(issues, 'state-snapshot.json.logical_commitment', 'STATE_COMMITMENT_MISMATCH', '; '.join(state_errors))
    elif declared_state.get('logical_commitment') != actual_state:
        _issue(issues, 'publication.json.state.logical_commitment', 'STATE_COMMITMENT_MISMATCH', 'publication does not bind independently recomputed v9 state commitment')

    return {
        'ok': not issues,
        'issues': issues,
        'publication_id': pub.get('publication_id'),
        'expected_publication_id': expected_id,
        'bundle_manifest_digest': manifest_digest,
        'state': declared_state,
    }

# ---------------------------------------------------------------------------
# Kristal v10 draft.3.1 GitHub AI/read-surface operational profile.
# These are independent Python checks; they do not call the Framework JS CLI.

GITHUB_READ_SURFACE_FORMAT = 'kristal.github-read-surface/1.0'
GITHUB_SYNC_MANIFEST_FORMAT = 'kristal.github-sync-manifest/1.0'
GITHUB_COLLECTION_INDEX_FORMAT = 'kristal.github-collection-index/1.0'
SYNC_MANIFEST_REL = '.kristal/sync-manifest.json'
COLLECTION_INDEX_REL = 'kristals/index.json'


def _utf8_sort_key(value: Any) -> bytes:
    return str(value).encode('utf-8')


def _safe_posix_relative(value: Any) -> bool:
    if not isinstance(value, str) or not value or '\\' in value:
        return False
    if value.startswith('/'):
        return False
    parts = value.split('/')
    return all(part not in {'', '.', '..'} for part in parts)


def _commitment_ok(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    profile = value.get('profile')
    digest = value.get('digest')
    return isinstance(profile, str) and bool(profile) and isinstance(digest, str) and len(digest) == 71 and digest.startswith('sha256:') and all(c in '0123456789abcdef' for c in digest[7:])


def _sha256_file_prefixed(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return DIGEST_PREFIX + h.hexdigest()


def github_read_surface_projection(doc: dict[str, Any], materialization_objects: list[Any] | None = None) -> dict[str, Any]:
    rows = list(doc.get('files') or [])
    ordered = sorted(rows, key=lambda row: _utf8_sort_key(row.get('path', '') if isinstance(row, dict) else ''))
    mats = list(doc.get('materialization_objects') or []) if materialization_objects is None else list(materialization_objects)
    return {
        'format': GITHUB_READ_SURFACE_FORMAT,
        'slug': doc.get('slug'),
        'state_ref': doc.get('state_ref'),
        'state_logical_commitment': copy.deepcopy(doc.get('state_logical_commitment')),
        'entrypoint': doc.get('entrypoint'),
        'files': [
            {
                'path': row.get('path'),
                'role': row.get('role'),
                'size': row.get('size'),
                'sha256': row.get('sha256'),
            }
            for row in ordered if isinstance(row, dict)
        ],
        'materialization_objects': copy.deepcopy(mats),
    }


def github_read_surface_digest(doc: dict[str, Any], materialization_objects: list[Any] | None = None) -> str:
    projection = github_read_surface_projection(doc, materialization_objects)
    return sha256_bytes(canonicalize(projection).encode('utf-8'))


def _stable_json_codepoint(value: Any) -> str:
    # Framework draft.3.1 collection indexes use a compact JSON projection with
    # Unicode code-point key ordering rather than the JCS UTF-16 key ordering.
    if value is None:
        return 'null'
    if value is True:
        return 'true'
    if value is False:
        return 'false'
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        # Index rows currently contain only integers; keep deterministic JSON for
        # completeness and reject non-finite values via json.dumps.
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    if isinstance(value, list):
        return '[' + ','.join(_stable_json_codepoint(v) for v in value) + ']'
    if isinstance(value, dict):
        keys = sorted(value.keys())
        return '{' + ','.join(
            json.dumps(str(k), ensure_ascii=False) + ':' + _stable_json_codepoint(value[k]) for k in keys
        ) + '}'
    raise TypeError(f'unsupported JSON type: {type(value).__name__}')


def github_collection_index_digest(rows: list[Any]) -> str:
    projection = {'format': GITHUB_COLLECTION_INDEX_FORMAT, 'kristals': rows}
    return sha256_bytes(_stable_json_codepoint(projection).encode('utf-8'))


def _file_rows_map(rows: Any, issues: list[dict[str, str]], base: str = '$.files') -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        _issue(issues, base, 'INVALID_TYPE', 'files must be array')
        return out
    for i, row in enumerate(rows):
        p = f'{base}[{i}]'
        if not isinstance(row, dict):
            _issue(issues, p, 'INVALID_TYPE', 'file entry must be object')
            continue
        rel = row.get('path')
        if not _safe_posix_relative(rel):
            _issue(issues, p + '.path', 'INVALID_PATH', 'safe relative POSIX path required')
        elif rel in out:
            _issue(issues, p + '.path', 'DUPLICATE_VALUE', 'duplicate file path')
        else:
            out[rel] = row
        if not isinstance(row.get('role'), str) or not row.get('role'):
            _issue(issues, p + '.role', 'MISSING_FIELD', 'role required')
        if not isinstance(row.get('size'), int) or isinstance(row.get('size'), bool) or row.get('size') < 0:
            _issue(issues, p + '.size', 'INVALID_SIZE', 'non-negative integer size required')
        digest = row.get('sha256')
        if not isinstance(digest, str) or not _commitment_ok({'profile': 'x', 'digest': digest}):
            _issue(issues, p + '.sha256', 'INVALID_DIGEST', 'sha256 digest required')
    return out


def verify_github_read_surface(doc: Any) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    if not isinstance(doc, dict):
        return {'ok': False, 'issues': [{'path': '$', 'code': 'INVALID_TYPE', 'message': 'document must be object'}]}
    if doc.get('format') != GITHUB_READ_SURFACE_FORMAT:
        _issue(issues, '$.format', 'UNSUPPORTED_PROFILE', f'expected {GITHUB_READ_SURFACE_FORMAT}')
    slug = doc.get('slug')
    if not isinstance(doc.get('kit_version'), str) or not doc.get('kit_version'):
        _issue(issues, '$.kit_version', 'MISSING_FIELD', 'kit_version required')
    if not isinstance(slug, str) or not slug or '/' in slug or '\\' in slug:
        _issue(issues, '$.slug', 'INVALID_VALUE', 'single path-segment slug required')
    if isinstance(slug, str) and doc.get('target_root') != f'kristals/{slug}':
        _issue(issues, '$.target_root', 'RELATION_MISMATCH', 'target_root must equal kristals/<slug>')
    if doc.get('entrypoint') != 'AI_START_HERE.md':
        _issue(issues, '$.entrypoint', 'INVALID_VALUE', 'AI_START_HERE.md required')
    if doc.get('state_ref') is not None and (not isinstance(doc.get('state_ref'), str) or not doc.get('state_ref')):
        _issue(issues, '$.state_ref', 'INVALID_VALUE', 'state_ref must be non-empty or null')
    if doc.get('state_logical_commitment') is not None and not _commitment_ok(doc.get('state_logical_commitment')):
        _issue(issues, '$.state_logical_commitment', 'INVALID_COMMITMENT', 'valid commitment or null required')
    if not isinstance(doc.get('ready'), bool):
        _issue(issues, '$.ready', 'INVALID_TYPE', 'ready boolean required')
    errors = doc.get('errors')
    if not isinstance(errors, list) or any(not isinstance(x, str) for x in errors):
        _issue(issues, '$.errors', 'INVALID_TYPE', 'errors must be string array')
    elif doc.get('ready') is True and errors:
        _issue(issues, '$.errors', 'RELATION_MISMATCH', 'ready surface must have no errors')
    rows = doc.get('files')
    fmap = _file_rows_map(rows, issues)
    if isinstance(rows, list):
        observed = [x.get('path') if isinstance(x, dict) else None for x in rows]
        expected = [x.get('path') if isinstance(x, dict) else None for x in sorted(rows, key=lambda r: _utf8_sort_key(r.get('path', '') if isinstance(r, dict) else ''))]
        if observed != expected:
            _issue(issues, '$.files', 'NONDETERMINISTIC_ORDER', 'files must be in deterministic UTF-8 path order')
        total = sum(x.get('size', 0) for x in rows if isinstance(x, dict) and isinstance(x.get('size'), int) and not isinstance(x.get('size'), bool))
        if doc.get('file_count') != len(rows):
            _issue(issues, '$.file_count', 'COUNT_MISMATCH', 'file_count mismatch')
        if doc.get('total_bytes') != total:
            _issue(issues, '$.total_bytes', 'SIZE_MISMATCH', 'total_bytes mismatch')
    mats = doc.get('materialization_objects')
    if not isinstance(mats, list):
        _issue(issues, '$.materialization_objects', 'INVALID_TYPE', 'materialization_objects must be array')
        mats = []
    elif doc.get('materialization_object_count') != len(mats):
        _issue(issues, '$.materialization_object_count', 'COUNT_MISMATCH', 'materialization_object_count mismatch')
    if doc.get('ready') is True:
        for req in ('AI_START_HERE.md', 'AI_MANIFEST.json', 'ai/INDEX.json'):
            if req not in fmap:
                _issue(issues, '$.files', 'MISSING_RESOURCE', f'ready surface missing {req}')
    declared = doc.get('surface_digest')
    if isinstance(declared, str) and _commitment_ok({'profile': 'x', 'digest': declared}):
        got = github_read_surface_digest(doc, mats)
        if got != declared:
            _issue(issues, '$.surface_digest', 'DIGEST_MISMATCH', f'expected {declared}, got {got}')
    else:
        _issue(issues, '$.surface_digest', 'INVALID_DIGEST', 'sha256 surface_digest required')
    return {'ok': not issues, 'issues': issues, 'surface_digest': declared, 'state_ref': doc.get('state_ref')}


def verify_github_sync_manifest(doc: Any) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    if not isinstance(doc, dict):
        return {'ok': False, 'issues': [{'path': '$', 'code': 'INVALID_TYPE', 'message': 'document must be object'}]}
    if doc.get('format') != GITHUB_SYNC_MANIFEST_FORMAT:
        _issue(issues, '$.format', 'UNSUPPORTED_PROFILE', f'expected {GITHUB_SYNC_MANIFEST_FORMAT}')
    if doc.get('read_surface_format') != GITHUB_READ_SURFACE_FORMAT:
        _issue(issues, '$.read_surface_format', 'UNSUPPORTED_PROFILE', f'expected {GITHUB_READ_SURFACE_FORMAT}')
    for key in ('manager_version', 'slug', 'title', 'target_root', 'entrypoint', 'state_ref'):
        if not isinstance(doc.get(key), str) or not doc.get(key):
            _issue(issues, f'$.{key}', 'MISSING_FIELD', f'{key} required')
    slug = doc.get('slug')
    if isinstance(slug, str) and slug and doc.get('target_root') != f'kristals/{slug}':
        _issue(issues, '$.target_root', 'RELATION_MISMATCH', 'target_root must equal kristals/<slug>')
    if doc.get('entrypoint') != 'AI_START_HERE.md':
        _issue(issues, '$.entrypoint', 'INVALID_VALUE', 'AI_START_HERE.md required')
    if not _commitment_ok(doc.get('state_logical_commitment')):
        _issue(issues, '$.state_logical_commitment', 'INVALID_COMMITMENT', 'valid commitment required')
    declared = doc.get('surface_digest')
    if not isinstance(declared, str) or not _commitment_ok({'profile': 'x', 'digest': declared}):
        _issue(issues, '$.surface_digest', 'INVALID_DIGEST', 'sha256 surface_digest required')
    rows = doc.get('files')
    fmap = _file_rows_map(rows, issues)
    if isinstance(rows, list):
        observed = [x.get('path') if isinstance(x, dict) else None for x in rows]
        expected = [x.get('path') if isinstance(x, dict) else None for x in sorted(rows, key=lambda r: _utf8_sort_key(r.get('path', '') if isinstance(r, dict) else ''))]
        if observed != expected:
            _issue(issues, '$.files', 'NONDETERMINISTIC_ORDER', 'files must be in deterministic UTF-8 path order')
        total = sum(x.get('size', 0) for x in rows if isinstance(x, dict) and isinstance(x.get('size'), int) and not isinstance(x.get('size'), bool))
        if doc.get('file_count') != len(rows):
            _issue(issues, '$.file_count', 'COUNT_MISMATCH', 'file_count mismatch')
        if doc.get('total_bytes') != total:
            _issue(issues, '$.total_bytes', 'SIZE_MISMATCH', 'total_bytes mismatch')
    if not isinstance(doc.get('materialization_object_count'), int) or isinstance(doc.get('materialization_object_count'), bool) or doc.get('materialization_object_count') < 0:
        _issue(issues, '$.materialization_object_count', 'INVALID_VALUE', 'non-negative integer required')
    if doc.get('entrypoint') not in fmap:
        _issue(issues, '$.entrypoint', 'MISSING_RESOURCE', 'entrypoint must be hosted file')
    for req in ('AI_MANIFEST.json', 'ai/INDEX.json'):
        if req not in fmap:
            _issue(issues, '$.files', 'MISSING_RESOURCE', f'sync manifest missing {req}')
    policy = doc.get('policy')
    if not isinstance(policy, dict):
        _issue(issues, '$.policy', 'INVALID_TYPE', 'policy object required')
    else:
        for key in ('derived_read_surface', 'sync_is_not_publication', 'activation_is_separate', 'materialization_blobs_are_not_implicitly_copied'):
            if policy.get(key) is not True:
                _issue(issues, f'$.policy.{key}', 'INVALID_VALUE', 'must be true')
    return {'ok': not issues, 'issues': issues, 'surface_digest': declared, 'state_ref': doc.get('state_ref')}


def verify_github_collection_index(doc: Any) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    if not isinstance(doc, dict):
        return {'ok': False, 'issues': [{'path': '$', 'code': 'INVALID_TYPE', 'message': 'document must be object'}]}
    if doc.get('format') != GITHUB_COLLECTION_INDEX_FORMAT:
        _issue(issues, '$.format', 'UNSUPPORTED_PROFILE', f'expected {GITHUB_COLLECTION_INDEX_FORMAT}')
    rows = doc.get('kristals')
    if not isinstance(rows, list):
        _issue(issues, '$.kristals', 'INVALID_TYPE', 'kristals must be array')
        rows = []
    if doc.get('count') != len(rows):
        _issue(issues, '$.count', 'COUNT_MISMATCH', 'count mismatch')
    declared = doc.get('index_digest')
    if not isinstance(declared, str) or not _commitment_ok({'profile': 'x', 'digest': declared}):
        _issue(issues, '$.index_digest', 'INVALID_DIGEST', 'sha256 index_digest required')
    paths: set[str] = set(); refs: set[str] = set(); slugs: set[str] = set()
    for i, row in enumerate(rows):
        p = f'$.kristals[{i}]'
        if not isinstance(row, dict):
            _issue(issues, p, 'INVALID_TYPE', 'entry must be object')
            continue
        for key in ('slug', 'title', 'path', 'entrypoint', 'state_ref'):
            if not isinstance(row.get(key), str) or not row.get(key):
                _issue(issues, f'{p}.{key}', 'MISSING_FIELD', f'{key} required')
        slug = row.get('slug'); path = row.get('path')
        if isinstance(slug, str) and slug and path != f'kristals/{slug}':
            _issue(issues, p + '.path', 'RELATION_MISMATCH', 'path must equal kristals/<slug>')
        if isinstance(path, str) and path and row.get('entrypoint') != f'{path}/AI_START_HERE.md':
            _issue(issues, p + '.entrypoint', 'RELATION_MISMATCH', 'entrypoint must point to AI_START_HERE.md')
        if not _commitment_ok(row.get('state_logical_commitment')):
            _issue(issues, p + '.state_logical_commitment', 'INVALID_COMMITMENT', 'valid commitment required')
        sd = row.get('surface_digest')
        if not isinstance(sd, str) or not _commitment_ok({'profile': 'x', 'digest': sd}):
            _issue(issues, p + '.surface_digest', 'INVALID_DIGEST', 'sha256 surface_digest required')
        for key in ('file_count', 'total_bytes', 'materialization_object_count'):
            if not isinstance(row.get(key), int) or isinstance(row.get(key), bool) or row.get(key) < 0:
                _issue(issues, f'{p}.{key}', 'INVALID_VALUE', 'non-negative integer required')
        for value, seen, field in ((path, paths, 'path'), (row.get('state_ref'), refs, 'state_ref'), (slug, slugs, 'slug')):
            if isinstance(value, str):
                if value in seen:
                    _issue(issues, f'{p}.{field}', 'DUPLICATE_VALUE', f'duplicate {field}')
                else:
                    seen.add(value)
    expected = sorted(rows, key=lambda r: (_utf8_sort_key(r.get('slug', '') if isinstance(r, dict) else ''), _utf8_sort_key(r.get('path', '') if isinstance(r, dict) else '')))
    if rows != expected:
        _issue(issues, '$.kristals', 'NONDETERMINISTIC_ORDER', 'entries must be in deterministic slug/path order')
    if isinstance(declared, str) and _commitment_ok({'profile': 'x', 'digest': declared}):
        got = github_collection_index_digest(rows)
        if got != declared:
            _issue(issues, '$.index_digest', 'DIGEST_MISMATCH', f'expected {declared}, got {got}')
    return {'ok': not issues, 'issues': issues, 'count': len(rows), 'index_digest': declared}


def _resolve_contained(root: Path, rel: str) -> Path | None:
    if not _safe_posix_relative(rel):
        return None
    base = root.resolve()
    file = (base / Path(*rel.split('/'))).resolve()
    try:
        file.relative_to(base)
    except ValueError:
        return None
    return file


def _read_object(path: Path, issues: list[dict[str, str]], label: str) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            raise ValueError('expected object')
        return value
    except Exception as exc:
        _issue(issues, label, 'INVALID_JSON', str(exc))
        return None


def verify_hosted_github_read_surface(repo_root: Path, root_rel: str) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    repo_root = repo_root.resolve()
    if not _safe_posix_relative(root_rel):
        _issue(issues, '$root', 'INVALID_PATH', 'safe relative root required')
        return {'ok': False, 'issues': issues}
    parts = root_rel.split('/')
    if len(parts) != 2 or parts[0] != 'kristals' or parts[1] == 'index.json':
        _issue(issues, '$root', 'INVALID_PATH', 'root must be exactly kristals/<slug>')
        return {'ok': False, 'issues': issues}
    root = _resolve_contained(repo_root, root_rel)
    if root is None or not root.is_dir():
        _issue(issues, '$root', 'MISSING_RESOURCE', 'hosted root missing')
        return {'ok': False, 'issues': issues}
    manifest_path = root / Path(*SYNC_MANIFEST_REL.split('/'))
    manifest = _read_object(manifest_path, issues, SYNC_MANIFEST_REL)
    if manifest is None:
        return {'ok': False, 'issues': issues}
    mc = verify_github_sync_manifest(manifest)
    for item in mc.get('issues', []):
        suffix = '' if item.get('path') == '$' else str(item.get('path', ''))[1:]
        issues.append({**item, 'path': SYNC_MANIFEST_REL + suffix})
    if manifest.get('target_root') != root_rel:
        _issue(issues, SYNC_MANIFEST_REL + '.target_root', 'RELATION_MISMATCH', 'target_root mismatch')
    fmap = _file_rows_map(manifest.get('files'), issues, SYNC_MANIFEST_REL + '.files')
    total = 0
    for rel, item in fmap.items():
        file = _resolve_contained(root, rel)
        if file is None or not file.is_file():
            _issue(issues, rel, 'MISSING_RESOURCE', 'hosted file missing')
            continue
        if file.is_symlink():
            _issue(issues, rel, 'INVALID_RESOURCE', 'symlink not allowed')
            continue
        st = file.stat()
        if st.st_size != item.get('size'):
            _issue(issues, rel, 'SIZE_MISMATCH', f"expected {item.get('size')}, got {st.st_size}")
        digest = _sha256_file_prefixed(file)
        if digest != item.get('sha256'):
            _issue(issues, rel, 'DIGEST_MISMATCH', f"expected {item.get('sha256')}, got {digest}")
        total += st.st_size
    state_rel = None
    for rel, item in fmap.items():
        if item.get('role') == 'state_snapshot':
            state_rel = rel
            break
    if state_rel is None and 'state/state-snapshot.json' in fmap:
        state_rel = 'state/state-snapshot.json'
    if state_rel is None:
        _issue(issues, 'state', 'MISSING_RESOURCE', 'read surface has no state snapshot')
    else:
        state = _read_object(root / Path(*state_rel.split('/')), issues, state_rel)
        if state is not None:
            ok_state, actual_state, state_errors = verify_declared_state(state)
            if not ok_state:
                _issue(issues, state_rel + '.logical_commitment', 'STATE_COMMITMENT_MISMATCH', '; '.join(state_errors))
            if state.get('state_ref') != manifest.get('state_ref'):
                _issue(issues, state_rel + '.state_ref', 'RELATION_MISMATCH', 'state_ref mismatch')
            if state.get('logical_commitment') != manifest.get('state_logical_commitment'):
                _issue(issues, state_rel + '.logical_commitment', 'RELATION_MISMATCH', 'state logical commitment mismatch')
            if ok_state and isinstance(manifest.get('state_logical_commitment'), dict) and manifest.get('state_logical_commitment') != actual_state:
                _issue(issues, state_rel + '.logical_commitment', 'STATE_COMMITMENT_MISMATCH', 'manifest does not bind independently recomputed v9 state commitment')
    ai_manifest = _read_object(root / 'AI_MANIFEST.json', issues, 'AI_MANIFEST.json')
    if ai_manifest is not None:
        if ai_manifest.get('state_ref') != manifest.get('state_ref'):
            _issue(issues, 'AI_MANIFEST.json.state_ref', 'RELATION_MISMATCH', 'state_ref mismatch')
        if ai_manifest.get('state_logical_commitment') != manifest.get('state_logical_commitment'):
            _issue(issues, 'AI_MANIFEST.json.state_logical_commitment', 'RELATION_MISMATCH', 'commitment mismatch')
    ai_index = _read_object(root / 'ai' / 'INDEX.json', issues, 'ai/INDEX.json')
    materialization_objects: list[Any] = []
    if ai_index is not None:
        indexed = ai_index.get('files')
        if not isinstance(indexed, list):
            _issue(issues, 'ai/INDEX.json.files', 'INVALID_TYPE', 'files must be array')
        else:
            for i, row in enumerate(indexed):
                p = f'ai/INDEX.json.files[{i}]'
                if not isinstance(row, dict) or not _safe_posix_relative(row.get('path')):
                    _issue(issues, p, 'INVALID_PATH', 'invalid file entry')
                    continue
                hosted = fmap.get(row.get('path'))
                if hosted is None:
                    _issue(issues, p + '.path', 'MISSING_RESOURCE', 'indexed file is outside hosted read surface')
                else:
                    if row.get('size') is not None and row.get('size') != hosted.get('size'):
                        _issue(issues, p + '.size', 'SIZE_MISMATCH', 'size drift')
                    if row.get('sha256') and row.get('sha256') != hosted.get('sha256'):
                        _issue(issues, p + '.sha256', 'DIGEST_MISMATCH', 'digest drift')
        materialization_objects = ai_index.get('materialization_blobs') or []
        if not isinstance(materialization_objects, list):
            _issue(issues, 'ai/INDEX.json.materialization_blobs', 'INVALID_TYPE', 'must be array')
            materialization_objects = []
        if manifest.get('materialization_object_count') != len(materialization_objects):
            _issue(issues, SYNC_MANIFEST_REL + '.materialization_object_count', 'COUNT_MISMATCH', 'materialization count mismatch')
    declared_surface = manifest.get('surface_digest')
    if isinstance(declared_surface, str) and _commitment_ok({'profile': 'x', 'digest': declared_surface}):
        pseudo = dict(manifest)
        pseudo['format'] = GITHUB_READ_SURFACE_FORMAT
        pseudo['files'] = list(fmap.values())
        pseudo['materialization_objects'] = materialization_objects
        got = github_read_surface_digest(pseudo, materialization_objects)
        if got != declared_surface:
            _issue(issues, SYNC_MANIFEST_REL + '.surface_digest', 'DIGEST_MISMATCH', f'expected {declared_surface}, got {got}')
    allowed = set(fmap) | {SYNC_MANIFEST_REL}
    for path in root.rglob('*'):
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            continue
        if path.is_symlink():
            _issue(issues, rel, 'INVALID_RESOURCE', 'symlink not allowed')
        elif path.is_file() and rel not in allowed:
            _issue(issues, rel, 'UNMANAGED_RESOURCE', 'unmanaged file under exact read surface')
    if manifest.get('total_bytes') != total:
        _issue(issues, SYNC_MANIFEST_REL + '.total_bytes', 'SIZE_MISMATCH', f"expected {manifest.get('total_bytes')}, got {total}")
    return {
        'ok': not issues,
        'issues': issues,
        'root': root_rel,
        'state_ref': manifest.get('state_ref'),
        'surface_digest': manifest.get('surface_digest'),
        'file_count': len(fmap),
        'total_bytes': total,
    }


def verify_hosted_github_collection(repo_root: Path, *, jobs: int = 8) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    issues: list[dict[str, str]] = []
    index_file = repo_root / Path(*COLLECTION_INDEX_REL.split('/'))
    if not index_file.is_file():
        return {'ok': True, 'issues': [], 'count': 0, 'status': 'not-yet-created'}
    index = _read_object(index_file, issues, COLLECTION_INDEX_REL)
    if index is None:
        return {'ok': False, 'issues': issues}
    ic = verify_github_collection_index(index)
    for item in ic.get('issues', []):
        suffix = '' if item.get('path') == '$' else str(item.get('path', ''))[1:]
        issues.append({**item, 'path': COLLECTION_INDEX_REL + suffix})
    rows = index.get('kristals') if isinstance(index.get('kristals'), list) else []
    roots: list[tuple[int, dict[str, Any]]] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or not _safe_posix_relative(row.get('path')):
            continue
        manifest_file = repo_root / Path(*row['path'].split('/')) / Path(*SYNC_MANIFEST_REL.split('/'))
        m = _read_object(manifest_file, issues, f"{row['path']}/{SYNC_MANIFEST_REL}")
        if m is not None:
            if m.get('state_ref') != row.get('state_ref'):
                _issue(issues, f'{COLLECTION_INDEX_REL}.kristals[{i}].state_ref', 'RELATION_MISMATCH', 'index/manifest state_ref drift')
            if m.get('surface_digest') != row.get('surface_digest'):
                _issue(issues, f'{COLLECTION_INDEX_REL}.kristals[{i}].surface_digest', 'RELATION_MISMATCH', 'index/manifest surface digest drift')
            if m.get('state_logical_commitment') != row.get('state_logical_commitment'):
                _issue(issues, f'{COLLECTION_INDEX_REL}.kristals[{i}].state_logical_commitment', 'RELATION_MISMATCH', 'index/manifest commitment drift')
            if row.get('entrypoint') != f"{row['path']}/{m.get('entrypoint')}":
                _issue(issues, f'{COLLECTION_INDEX_REL}.kristals[{i}].entrypoint', 'RELATION_MISMATCH', 'index/manifest entrypoint drift')
            if any(row.get(k) != m.get(k) for k in ('file_count', 'total_bytes', 'materialization_object_count')):
                _issue(issues, f'{COLLECTION_INDEX_REL}.kristals[{i}]', 'RELATION_MISMATCH', 'index/manifest stats drift')
        roots.append((i, row))
    # Large collections are byte-verified in bounded parallel workers. Each subtree
    # is independent and no target mutation occurs.
    from concurrent.futures import ThreadPoolExecutor
    results: list[tuple[int, dict[str, Any]]] = []
    max_workers = max(1, min(int(jobs or 1), 16, len(roots) or 1))
    if roots:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [(i, row, pool.submit(verify_hosted_github_read_surface, repo_root, row['path'])) for i, row in roots]
            for i, row, future in futures:
                results.append((i, future.result()))
    for i, result in sorted(results, key=lambda x: x[0]):
        row = rows[i]
        for item in result.get('issues', []):
            issues.append({**item, 'path': f"{row['path']}/{item.get('path')}"})
    return {
        'ok': not issues,
        'issues': issues,
        'count': len(rows),
        'index_digest': index.get('index_digest'),
        'verified_surfaces': len(results),
        'parallel_workers': max_workers if roots else 0,
    }
