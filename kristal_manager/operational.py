"""Non-authoritative v10 operational assessment of a LOCAL Kristal.

Manager does not issue a Framework conformance certificate, a C1 receipt, a
C2 grant, a C3 hosting attestation, or reader authorization. All operations
are read-only; independent Framework verification is optional and explicit.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from .core import ManagerError, detect_kristal
from .discovery import inspect_discovery, _path_under

REPORT_FORMAT = 'kristal.manager-operational-assessment/0.2-candidate'
FRAMEWORK_BASELINE = '10.0.0-draft.3.2'
# Pinned to the uploaded Framework snapshot used for this Manager integration.
FRAMEWORK_CONTRACT_SET_SHA256 = 'sha256:e4baf0b197162be963f29848623a1e4454911c3133e6993629ea994d12dd6942'


def _framework_verify(root: Path, framework_root: Path, state_source: str | None,
                      *, node_executable: str = 'node') -> dict:
    """Use the explicitly supplied, TRUSTED Framework reference (no shell).

    Only a pinned local checkout should be passed by the operator; Manager
    records the contract-set byte digest and does not install or fetch code.
    """
    import hashlib
    ref = framework_root.expanduser().resolve()
    contract = ref / 'contracts/contract-set.json'
    runner = ref / 'reference/js/bin/kristal-ref.mjs'
    if not contract.is_file() or not runner.is_file() or contract.is_symlink() or runner.is_symlink():
        return {'status':'NOT_EVALUATED','reason':'Framework reference or contract-set not found'}
    try:
        raw = contract.read_bytes()
        declared = json.loads(raw)
        version = declared.get('version')
        pin = 'sha256:' + hashlib.sha256(raw).hexdigest()
        if pin != FRAMEWORK_CONTRACT_SET_SHA256:
            return {'status':'NOT_EVALUATED','reason':'Framework contract-set SHA does not match the assessed snapshot pin',
                    'framework_version':version,'contract_set_sha256':pin}
        if version != FRAMEWORK_BASELINE:
            return {'status':'NOT_EVALUATED','reason':'Framework version differs from assessed baseline',
                    'framework_version':version,'contract_set_sha256':pin}
        source = {'state-export':'state/state-snapshot.json',
                  'build-v9':'build/v9/state-snapshot.json',
                  'node-v9':'.kristal/v9/state-snapshot.json'}.get(state_source)
        if not source:
            return {'status':'NOT_EVALUATED','reason':'No supported current v9 state surface',
                    'framework_version':version,'contract_set_sha256':pin}
        target = _path_under(root, source)
        if not target.is_file() or target.stat().st_size > 32*1024*1024:
            return {'status':'NOT_EVALUATED','reason':'State snapshot not present or over 32 MiB',
                    'framework_version':version,'contract_set_sha256':pin}
        completed = subprocess.run([node_executable,str(runner),'verify-state-v9',str(target)],
               capture_output=True,text=True,encoding='utf-8',errors='replace',
               timeout=30,check=False,cwd=ref)
        result = {'status':'VERIFIED' if completed.returncode == 0 else 'FAILED',
                  'framework_version':version,'contract_set_sha256':pin,
                  'validator':'Framework reference verify-state-v9',
                  'state_source':source}
        if completed.returncode:
            # Don't leak full untrusted stdout/stderr into reports; bounded diagnostic.
            result['reason'] = (completed.stderr or completed.stdout or 'Framework verifier rejected state').strip()[:320]
        return result
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired) as exc:
        return {'status':'NOT_EVALUATED', 'reason':f'Framework reference unavailable: {type(exc).__name__}'}


def assess_local(workspace: str | Path, *, framework_root: str | Path | None = None,
                 node_executable: str = 'node') -> dict:
    """Assess operational state, Discovery registered bytes and optional v9 commitment.

    No canonical writes, no publishing, no automatic regeneration, no
    authoritative knowledge qualification. A missing optional Discovery triple
    does not invalidate a legacy Kristal.
    """
    root = Path(workspace).expanduser().resolve()
    record = detect_kristal(root)
    if record is None:
        raise ManagerError('Not a recognized local Kristal workspace')
    issues = []
    structural = 'PRESENT' if record['readiness'] == 'READY' else 'NEEDS_ATTENTION'
    if record['readiness'] != 'READY':
        issues.append({'scope':'structure','severity':'blocker','code':'LOCAL_STATE_NOT_READY',
                       'message':record['readiness']})
    if record['state_conflict']:
        for msg in record['state_conflict_reasons']:
            issues.append({'scope':'structure','severity':'blocker','code':'STATE_CONFLICT','message':msg})
    discovery = inspect_discovery(root, verify_sources=True,
                  state_ref=record.get('declared_state_ref') or record.get('state_ref'))
    ds = discovery['status']
    if ds in ('stale','invalid','incomplete'):
        for msg in discovery['issues']:
            issues.append({'scope':'discovery','severity':'warning','code':'DISCOVERY_'+ds.upper(),
                           'message':msg})
    elif ds == 'absent':
        issues.append({'scope':'discovery','severity':'info','code':'DISCOVERY_OPTIONAL_ABSENT',
                       'message':'Optional Discovery triple absent; guarded generic reading only'})
    # Unlike the old 'VALID', assessment never certifies domain semantics.
    state_check = {'status':'NOT_EVALUATED','reason':'Framework reference not supplied; reported commitments are unverified'}
    if framework_root is not None:
        state_check = _framework_verify(root,Path(framework_root),record['state_source'],
                                        node_executable=node_executable)
        if state_check['status']=='FAILED':
            issues.append({'scope':'semantic_state','severity':'blocker','code':'FRAMEWORK_STATE_REJECTED',
                           'message':state_check.get('reason','State commitment rejected')})
        elif state_check['status']=='NOT_EVALUATED':
            issues.append({'scope':'semantic_state','severity':'warning','code':'FRAMEWORK_NOT_EVALUATED',
                           'message':state_check.get('reason','Framework not evaluated')})
    if any(item['severity']=='blocker' for item in issues):
        outcome = 'BLOCKED'
    elif any(item['severity']=='warning' for item in issues):
        outcome = 'ATTENTION_REQUIRED'
    else:
        outcome = 'LOCAL_CHECKS_PASSED' if ds == 'verified_registered_sources' else 'LOCAL_STRUCTURE_ONLY'
    return {'format':REPORT_FORMAT,
            'generated_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
            'workspace':str(root), 'title':record['title'],
            'state_ref':record['state_ref'],
            'framework_target':FRAMEWORK_BASELINE,
            'hosting_baseline':'kristal.hosting/10.0',
            'local_readiness':record['readiness'],
            'structural_status':structural,
            'discovery':discovery,
            'framework_state_verification':state_check,
            'operational_result':outcome,
            'qualification':'NOT_ESTABLISHED',
            'publication':'NOT_ESTABLISHED',
            'activation':'NOT_ESTABLISHED',
            'reader_authorization':'NOT_ESTABLISHED',
            'hosting_verification':'NOT_ESTABLISHED',
            'issues':issues,
            'limitations':[
                'Local operational assessment, not Framework release conformance or C1/C2/C3 evidence.',
                'Registered-source verification does not cover files absent from the Kit inventory.',
                'A verified v9 state commitment is distinct from v10 hosting/publication.',
                'Reader hints do not grant access or justify execution.'
            ]}
