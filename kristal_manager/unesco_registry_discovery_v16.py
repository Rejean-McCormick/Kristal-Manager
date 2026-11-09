#!/usr/bin/env python3
"""Find *existing* explicit branch-bound Kit v11 registries; never create identities.

Search is deliberately bounded to a root + its first two directory levels.
Registry material is always checked by the installed Authoring Kit read-only gate.
No auto-approval and no manager publication/sync function is invoked.
"""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys

BRANCH='unesco-mt1-10'
class DiscoveryError(ValueError): pass

def _paths(root:Path, limit:int=300):
    root=Path(root)
    if root.is_symlink(): raise DiscoveryError('Racine de recherche symbolique interdite')
    if not root.exists():return []
    if not root.is_dir():raise DiscoveryError('Racine de recherche non repertorie')
    seen=[]
    for child in [root]:
        seen.append(child)
    # Never recurse arbitrarily into large D: or repo trees.
    for layer in range(2):
        extra=[]
        for parent in seen if layer==0 else last:
            if not parent.is_dir():continue
            for p in parent.iterdir():
                if p.is_symlink():continue
                if p.is_dir() and p.name not in ('.git','node_modules','venv','.venv','__pycache__'):
                    extra.append(p)
                    if len(extra)>limit or len(seen)+len(extra)>limit:
                        raise DiscoveryError('Recherche trop large; preciser --registry-root')
        if layer==0:last=extra
        seen.extend(extra)
    return seen

def _check_gate(workspace:Path,gate_script:Path):
    p=subprocess.run([sys.executable,str(gate_script),'--workspace',str(workspace)],
        capture_output=True,text=True,timeout=100)
    if p.returncode:
        return {'state':'KIT_REJECTED','error':(p.stderr or p.stdout)[-600:]}
    try:report=json.loads(p.stdout)
    except ValueError:return {'state':'KIT_INVALID_JSON'}
    if report.get('workspace_branch_binding')!='EXPLICIT_SLUG_MATCH':return {'state':'WRONG_BRANCH'}
    if (report.get('workspace_v11_status')!='EXISTING_WORKSPACE_KIT_CHECK_V11_PASSED' or
        report.get('canonical_writes')!=0 or report.get('publication_authorized') is not False):
        return {'state':'KIT_NOT_QUALIFIED', 'reason':report.get('workspace_v11_status')}
    return {'state':'KIT_V11_EXISTING_BRANCH_VERIFIED', 'report':report}

def discover(roots:list[Path],gate_script:Path,*, explicit_workspace:Path|None=None,limit:int=300):
    gate_script=Path(gate_script)
    if not gate_script.is_file() or gate_script.is_symlink():raise DiscoveryError('Gate Kit v11 absent')
    skipped_roots=[]
    if explicit_workspace is not None:
        candidates=[Path(explicit_workspace)]
        if not candidates[0].is_dir() or candidates[0].is_symlink():raise DiscoveryError('Workspace explicitement fourni absent')
    else:
        candidates=[]
        for root in roots:
            try: bounded=_paths(Path(root),limit)
            except DiscoveryError:
                skipped_roots.append({"root":str(root),"reason":"BOUNDED_DISCOVERY_LIMIT_REACHED_OR_INVALID_ROOT"})
                continue
            for p in bounded:
                if (p/'.kristal/v11/authoring.json').is_file() and (p/'kristal.workspace.json').is_file():
                    candidates.append(p)
    uniq={str(p.resolve()):p for p in candidates if not p.is_symlink()}
    if len(uniq)>40:raise DiscoveryError('Plus de 40 workspaces candidats : selection manuelle requise')
    checked=[];verified=[]
    for key,p in sorted(uniq.items()):
        # Never accept Kit demo workspaces as authority.
        if 'demo-semantic-v11' in p.parts or ('examples' in p.parts and 'demo' in p.name):
            checked.append({'workspace':key,'state':'DEMO_EXCLUDED'});continue
        res=_check_gate(p,gate_script)
        checked.append({'workspace':key,'state':res['state'],**({'error':res['error']} if 'error' in res else {})})
        if res['state']=='KIT_V11_EXISTING_BRANCH_VERIFIED':verified.append((key,res['report']))
    choice=verified[0] if len(verified)==1 else None
    return {'format':'kristal-manager.unesco-mt1-10-registry-discovery/1.0',
        'branch':BRANCH,'search_roots':[str(Path(r)) for r in roots],
        'explicit_workspace_supplied':explicit_workspace is not None,
        'candidate_workspace_count':len(uniq),'branch_verified_workspace_count':len(verified),
        'checked':checked,'search_roots_skipped':skipped_roots,'selection_status':('ONE_VERIFIED_EXISTING_WORKSPACE' if choice else
          'MULTIPLE_VERIFIED_MANUAL_SELECTION_REQUIRED' if verified else 'NO_EXISTING_VERIFIED_WORKSPACE'),
        'selected_readonly_workspace':choice[0] if choice else None,
        'selected_kit_report':choice[1] if choice else None,
        'canonical_writes':0,'publication_authorized':False}
