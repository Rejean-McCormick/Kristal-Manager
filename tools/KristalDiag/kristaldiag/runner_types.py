from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .config import Config
from .schemas import SchemaStore

@dataclass
class Context:
    repo_root:Path
    target:Path
    scan_root:Path
    inv:object
    schemas:SchemaStore
    config:Config
    claimed_profile:str|None
    allow_exec:bool
    driver:dict|None
    target_kind:str
    resource_root:Path
    interop_evidence:Path|None

def target_kind(inv):
    has_v10=any(inv.get(t) for t in ('kristal_node_manifest','kristal_host_binding','kristal_publication','kristal_directory','kristal_v10_capabilities'))
    has_v9=any(inv.get(t) for t in ('kristal_logical_artifact','kristal_state_snapshot','kristal_derivation','kristal_materialization_manifest','kristal_exchange','kristal_activation','kristal_v9_capabilities'))
    has_v8=any(inv.get(t) for t in ('kristall_query_request','kristall_query_result','kristall_lexicon','kristall_v8_capabilities'))
    has_v7=any(inv.get(t) for t in ('kristall_manifest','kristall_mesh','kristall_entity_registry','kristall_projection_recipe'))
    has_v6=bool(inv.get('kristal_state'))
    if inv.implementation_manifest:return 'implementation'
    if inv.is_standard_repo:return 'standard-repository'
    if has_v10:return 'kristal-v10'
    if has_v9:return 'kristal-v9'
    if has_v8:return 'kristall-v8'
    if has_v7 and has_v6:return 'mixed-v6-v7'
    if has_v7:return 'kristall-v7'
    if has_v6:return 'kristal-state-v6'
    return 'repository-or-artifact'
