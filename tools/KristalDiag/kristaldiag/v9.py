from __future__ import annotations

import copy
import hashlib
from typing import Any

from .jcs import canonicalize

LOGICAL_PROFILE = 'kristal.logical/jcs-sha256-v1'
STATE_PROFILE = 'kristal.state-commitment/jcs-sha256-v1'


def _deep(v: Any) -> Any:
    return copy.deepcopy(v)


def _commit(domain: str, projection: Any) -> dict[str, str]:
    payload = domain.encode('utf-8') + canonicalize(projection).encode('utf-8')
    return {'digest': 'sha256:' + hashlib.sha256(payload).hexdigest()}


def normalize_artifact_ref(ref: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        'artifact_id': ref['artifact_id'],
        'logical_commitment': _deep(ref['logical_commitment']),
    }
    if 'logical_contract' in ref:
        out['logical_contract'] = _deep(ref['logical_contract'])
    return out


def sort_artifact_refs(refs: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out = [normalize_artifact_ref(r) for r in (refs or [])]
    out.sort(key=lambda r: (r.get('artifact_id', ''), (r.get('logical_commitment') or {}).get('digest', '')))
    return out


def normalize_state_ref(ref: dict[str, Any]) -> dict[str, Any]:
    return {
        'state_ref': ref['state_ref'],
        'logical_commitment': _deep(ref['logical_commitment']),
    }


def sort_state_refs(refs: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out = [normalize_state_ref(r) for r in (refs or [])]
    out.sort(key=lambda r: (r.get('state_ref', ''), (r.get('logical_commitment') or {}).get('digest', '')))
    return out


def artifact_logical_projection(artifact: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {'payload': _deep(artifact.get('payload'))}
    if 'scope' in artifact:
        out['scope'] = _deep(artifact['scope'])
    if 'extensions' in artifact:
        out['extensions'] = _deep(artifact['extensions'])
    deps = artifact.get('dependencies')
    if isinstance(deps, list) and deps:
        out['dependencies'] = sort_artifact_refs(deps)
    return out


def logical_artifact_commitment(artifact: dict[str, Any], profile: str = LOGICAL_PROFILE) -> dict[str, str]:
    if profile != LOGICAL_PROFILE:
        raise ValueError(f'unsupported logical commitment profile: {profile}')
    contract = artifact.get('logical_contract')
    if not isinstance(contract, dict) or not isinstance(contract.get('id'), str) or not isinstance(contract.get('version'), str):
        raise ValueError('logical_contract id/version required')
    domain = (
        'KRISTAL\x00LOGICAL-COMMITMENT\x00'
        + profile + '\x00'
        + contract['id'] + '\x00'
        + contract['version'] + '\x00'
    )
    result = _commit(domain, artifact_logical_projection(artifact))
    return {'profile': profile, 'digest': result['digest']}


def state_logical_projection(state: dict[str, Any]) -> dict[str, Any]:
    refs: list[dict[str, Any]] = []
    for ref in state.get('references') or []:
        if 'artifact_id' in ref:
            refs.append({'kind': 'artifact', 'value': normalize_artifact_ref(ref)})
        elif 'state_ref' in ref:
            refs.append({'kind': 'state', 'value': normalize_state_ref(ref)})
    refs.sort(key=canonicalize)
    out: dict[str, Any] = {
        'members': sort_artifact_refs(state.get('members') or []),
        'references': refs,
    }
    if 'scope' in state:
        out['scope'] = _deep(state['scope'])
    return out


def state_commitment(state: dict[str, Any], profile: str = STATE_PROFILE) -> dict[str, str]:
    if profile != STATE_PROFILE:
        raise ValueError(f'unsupported state commitment profile: {profile}')
    domain = 'KRISTAL\x00STATE-COMMITMENT\x00' + profile + '\x00'
    result = _commit(domain, state_logical_projection(state))
    return {'profile': profile, 'digest': result['digest']}


def verify_declared_logical_artifact(artifact: dict[str, Any]) -> tuple[bool, dict[str, str] | None, list[str]]:
    errors: list[str] = []
    try:
        actual = logical_artifact_commitment(artifact)
    except Exception as exc:
        return False, None, [str(exc)]
    declared = artifact.get('logical_commitment')
    if not isinstance(declared, dict):
        errors.append('logical_commitment missing')
    else:
        if declared.get('profile') != actual['profile']:
            errors.append(f"logical_commitment profile mismatch: {declared.get('profile')!r} != {actual['profile']!r}")
        if declared.get('digest') != actual['digest']:
            errors.append(f"logical_commitment digest mismatch: {declared.get('digest')!r} != {actual['digest']!r}")
    return not errors, actual, errors


def verify_declared_state(state: dict[str, Any]) -> tuple[bool, dict[str, str] | None, list[str]]:
    errors: list[str] = []
    try:
        actual = state_commitment(state)
    except Exception as exc:
        return False, None, [str(exc)]
    declared = state.get('logical_commitment')
    if not isinstance(declared, dict):
        errors.append('logical_commitment missing')
    else:
        if declared.get('profile') != actual['profile']:
            errors.append(f"logical_commitment profile mismatch: {declared.get('profile')!r} != {actual['profile']!r}")
        if declared.get('digest') != actual['digest']:
            errors.append(f"logical_commitment digest mismatch: {declared.get('digest')!r} != {actual['digest']!r}")
    return not errors, actual, errors


def is_mutable_selector(value: str) -> bool:
    token = value.strip().lower()
    return token in {'head', 'main', 'master', 'current', 'latest'} or token.endswith(':latest') or token.endswith('/latest')
