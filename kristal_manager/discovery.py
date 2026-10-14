"""Read-only inspection of Authoring Kit 3.3-derived Discovery manifests.

Never treats reader hints as executable code, a reader authorization, or proof of
publication. Presence and agreement of fingerprints is *not* a verification of
current source bytes; optional explicit integrity verification is provided.
"""
from __future__ import annotations

import hashlib
import json
import re
import math
from decimal import Decimal
from pathlib import Path

DISCOVERY_FORMAT = 'kristal.discovery/1.0'
INVENTORY_FORMAT = 'kristal.reader-inventory/1.0'
READER_FORMAT = 'kristal.reader-profile/1.0'
AUTHORITY = 'noncanonical_derived_metadata_not_access_or_publication_authority'
SHA = re.compile(r'^sha256:[0-9a-f]{64}$')
ARK = re.compile(r'^ARK-[0-9]{2,}$')
PRF = re.compile(r'^PRF-[0-9]{2,}$')
MAX_METADATA_BYTES = 8 * 1024 * 1024


def _object(file: Path) -> dict:
    if file.is_symlink() or not file.is_file() or file.stat().st_size > MAX_METADATA_BYTES:
        raise ValueError('metadata file unavailable, symlinked or too large')
    content = json.loads(file.read_text(encoding='utf-8'))
    if not isinstance(content, dict):
        raise ValueError('metadata root is not an object')
    return content


def _path_under(root: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel or '\\' in rel or ':' in rel or rel.startswith('/'):
        raise ValueError('invalid relative path')
    parts = rel.split('/')
    if any(item in ('', '.', '..') for item in parts):
        raise ValueError('relative path traversal')
    candidate = root.joinpath(*parts)
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError('path leaves workspace')
    if any(node.is_symlink() for node in [candidate, *candidate.parents] if node != root and node.is_relative_to(root)):
        raise ValueError('symlinked metadata source')
    return candidate


def _validate(doc: dict, inv: dict, reader: dict, state_ref: str | None) -> list[str]:
    issues = []
    if doc.get('format') != DISCOVERY_FORMAT: issues.append('unsupported discovery format')
    if inv.get('format') != INVENTORY_FORMAT: issues.append('unsupported reader-inventory format')
    if reader.get('format') != READER_FORMAT: issues.append('unsupported reader-profile format')
    identity = doc.get('state_ref')
    if not isinstance(identity, str) or not identity: issues.append('missing discovery state_ref')
    if any(item.get('state_ref') != identity for item in (inv, reader)):
        issues.append('derived state identities disagree')
    if state_ref and identity != state_ref: issues.append('discovery state_ref differs from workspace or current state')
    prints = [item.get('source_fingerprint') for item in (doc, inv, reader)]
    if not all(isinstance(value, str) and SHA.fullmatch(value) for value in prints):
        issues.append('source fingerprint malformed')
    elif len(set(prints)) != 1: issues.append('source fingerprints disagree')
    if doc.get('authority') != AUTHORITY: issues.append('discovery authority is not advisory-only')
    layout = doc.get('data_layout')
    hints = doc.get('reader')
    size = doc.get('size')
    if not isinstance(layout, dict) or layout.get('inventory_ref') != 'derived/reader-inventory.json':
        issues.append('unexpected inventory reference')
    if not isinstance(hints, dict) or hints.get('hints_ref') != 'derived/reader-profile.json':
        issues.append('unexpected reader-profile reference')
    if isinstance(hints, dict) and hints.get('profile') != reader.get('specialization'):
        issues.append('reader specialization mismatch')
    if reader.get('configuration_status') != 'advisory_only': issues.append('reader hints not advisory-only')
    if not isinstance(size, dict) or size.get('class') != inv.get('size_class'):
        issues.append('size classes disagree')
    if not isinstance(size, dict) or size.get('tracked_local_bytes') != (inv.get('storage') or {}).get('tracked_local_bytes'):
        issues.append('measured sizes disagree')
    if not isinstance(size, dict) or size.get('completeness') != (inv.get('measurement') or {}).get('status'):
        issues.append('measurement status disagrees')
    cl = doc.get('classification')
    if not isinstance(cl, dict): issues.append('classification is not an object')
    else:
        for key, pattern in (('primary_archetype', ARK), ('primary_usage', PRF)):
            if key in cl and (not isinstance(cl[key], str) or not pattern.fullmatch(cl[key])):
                issues.append(f'invalid {key}')
    if not isinstance(inv.get('files'), list) or not isinstance(inv.get('segments'), list):
        issues.append('reader inventory files/segments malformed')
    return issues


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _canonicalize(value):
    """Use Authoring Kit 3.3's JCS-like representation for source fingerprints."""
    if value is None:return 'null'
    if value is True:return 'true'
    if value is False:return 'false'
    if isinstance(value,int):return str(value)
    if isinstance(value,float):
        if not math.isfinite(value):raise ValueError('non-finite number')
        if value==0.0:return '0'
        rendered=repr(value).lower()
        if rendered.endswith('.0') and 'e' not in rendered:rendered=rendered[:-2]
        if 1e-6<=abs(value)<1e21:
            if 'e' in rendered:rendered=format(Decimal(rendered),'f').rstrip('0').rstrip('.')
            return rendered
        if 'e' not in rendered:rendered=format(Decimal(rendered).normalize(),'e')
        mantissa,exponent=rendered.split('e',1)
        if mantissa.endswith('.0'):mantissa=mantissa[:-2]
        exponent=int(exponent)
        return f'{mantissa}e{"+" if exponent>=0 else "-"}{abs(exponent)}'
    if isinstance(value,str):return json.dumps(value,ensure_ascii=False,separators=(',',':'))
    if isinstance(value,list):return '['+','.join(_canonicalize(item) for item in value)+']'
    if isinstance(value,dict):
        keys=sorted(value,key=lambda key:key.encode('utf-16-be'))
        return '{'+','.join(_canonicalize(key)+':'+_canonicalize(value[key]) for key in keys)+'}'
    raise ValueError('unsupported fingerprint value')


def verify_source_fingerprint(root: Path, inv: dict) -> tuple[bool, str]:
    """Reproduce Kit 3.3 source fingerprint with *stored* inventory file/segment list.

    This may read large local payloads; never touches remote paths, ignores new
    unregistered files, and does not make qualification/publication claims.
    """
    files = inv['files']
    if len(files) > 100000 or len(inv['segments']) > 100000:
        return False, 'inventory too large for on-demand verification'
    verified = []
    try:
        for item in files:
            if not isinstance(item, dict) or not isinstance(item.get('path'), str):
                raise ValueError('malformed physical file entry')
            file = _path_under(root, item['path'])
            if not file.is_file():raise ValueError('tracked file is missing')
            if file.stat().st_size != item.get('size_bytes'):
                raise ValueError('tracked file size changed')
            digest = 'sha256:' + _hash_file(file)
            if digest != item.get('sha256'):
                raise ValueError('tracked file digest changed')
            verified.append(item)
        verified.sort(key=lambda v: v['path'].encode('utf-8'))
        required = ['kristal.workspace.json', 'canon/state.index.json']
        if (root / 'arketype.instance.json').is_file(): required.append('arketype.instance.json')
        inputs = [[name, _hash_file(_path_under(root, name))] for name in required]
        fingerprint_payload = {'inputs': inputs, 'physical_files': verified, 'segments': inv['segments']}
        # Authoring Kit canonicalize() = JCS-like sorted compact JSON with ensure_ascii=False.
        encoded = _canonicalize(fingerprint_payload)
        got = 'sha256:' + hashlib.sha256(encoded.encode('utf-8')).hexdigest()
        if got != inv['source_fingerprint']:
            return False, 'source fingerprint differs from current registered sources'
        return True, 'registered source fingerprint reverified; unregistered changes are outside measurement scope'
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return False, str(exc)


def inspect_discovery(root: Path | str, *, verify_sources: bool = False,
                      state_ref: str | None = None) -> dict:
    """Returns bounded status & display metadata. Missing metadata is normal."""
    root = Path(root).expanduser().resolve()
    desc = root / 'kristal.discovery.json'
    inventory_path = root / 'derived/reader-inventory.json'
    reader_path = root / 'derived/reader-profile.json'
    output = {'status':'absent', 'integrity':'not_checked', 'format':None,
              'classification':{}, 'reader_profile':None, 'size_class':None,
              'tracked_local_bytes':None, 'measure_status':None, 'issues':[]}
    if not any(p.exists() or p.is_symlink() for p in (desc, inventory_path, reader_path)):
        return output
    if not all(p.exists() for p in (desc, inventory_path, reader_path)):
        return {**output,'status':'incomplete','issues':['one or more Discovery 3.3 files are missing']}
    try:
        doc = _object(_path_under(root,'kristal.discovery.json'))
        inv = _object(_path_under(root,'derived/reader-inventory.json'))
        reader = _object(_path_under(root,'derived/reader-profile.json'))
        issues = _validate(doc, inv, reader, state_ref)
        if issues: return {**output,'status':'invalid', 'issues':issues}
        classification=doc['classification']
        # Export only bounded, explicitly declared noncanonical descriptors.
        safe_cl = {}
        for key in ('arketype_version','primary_archetype','primary_usage','usage_slug','usage_family','domain','organization'):
            value=classification.get(key)
            if isinstance(value,str) and 0 < len(value) <= 120 and value.isprintable():safe_cl[key]=value
        specialization=reader.get('specialization')
        if not isinstance(specialization,str) or len(specialization)>120 or not specialization.isprintable():
            raise ValueError('invalid reader specialization')
        output.update(status='consistent_unverified',format=DISCOVERY_FORMAT,
                      classification=safe_cl,reader_profile=specialization,
                      size_class=inv.get('size_class'),
                      tracked_local_bytes=inv.get('storage',{}).get('tracked_local_bytes'),
                      measure_status=inv.get('measurement',{}).get('status'))
        if verify_sources:
            good,reason=verify_source_fingerprint(root,inv)
            output['status']='verified_registered_sources' if good else 'stale'
            output['integrity']='verified' if good else 'mismatch'
            output['issues'] = [] if good else [reason]
        return output
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
        return {**output,'status':'invalid','issues':[str(exc)]}
