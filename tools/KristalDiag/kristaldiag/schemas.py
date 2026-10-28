from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import jsonschema

ARTIFACT_SCHEMAS={
 'kristall_manifest':'kristall-manifest.schema.json',
 'kristall_entity_registry':'kristall-entity-registry.schema.json',
 'kristall_property_registry':'kristall-property-registry.schema.json',
 'kristall_assertion_registry':'kristall-assertion-registry.schema.json',
 'kristall_source_registry':'kristall-source-registry.schema.json',
 'kristall_assertion_family_registry':'kristall-assertion-family-registry.schema.json',
 'kristall_mesh':'kristall-mesh.schema.json',
 'kristall_axis_registry':'kristall-axis-registry.schema.json',
 'kristall_axis_type_registry':'kristall-axis-type-registry.schema.json',
 'kristall_projection_recipe':'kristall-projection-recipe.schema.json',
 'kristall_crystallization_record':'kristall-crystallization-record.schema.json',
 'kristall_kos_registry':'kristall-kos-registry.schema.json',
 'kristall_toc_registry':'kristall-toc-registry.schema.json',
 'semantic_resonance_set':'semantic-resonance.schema.json',
}

V8_SCHEMAS={
 'kristall_ai_context_bundle':'kristall-ai-context-bundle.schema.json',
 'kristall_lexicon_stack':'kristall-lexicon-stack.schema.json',
 'kristall_lexicon':'kristall-lexicon.schema.json',
 'kristall_query_index':'kristall-query-index.schema.json',
 'kristall_query_request':'kristall-query-request.schema.json',
 'kristall_query_result':'kristall-query-result.schema.json',
 'kristall_v8_capabilities':'kristall-v8-capabilities.schema.json',
}

V9_SCHEMAS={
 'kristal_activation':'kristal-activation.schema.json',
 'kristal_derivation':'kristal-derivation.schema.json',
 'kristal_exchange':'kristal-exchange.schema.json',
 'kristal_logical_artifact':'kristal-logical-artifact.schema.json',
 'kristal_materialization_manifest':'kristal-materialization-manifest.schema.json',
 'kristal_state_snapshot':'kristal-state-snapshot.schema.json',
 'kristal_v9_capabilities':'kristal-v9-capabilities.schema.json',
}

V10_SCHEMAS={
 'kristal_node_manifest':'kristal-node-manifest.schema.json',
 'kristal_host_binding':'kristal-host-binding.schema.json',
 'kristal_publication':'kristal-publication.schema.json',
 'kristal_directory':'kristal-directory.schema.json',
 'kristal_v10_capabilities':'kristal-v10-capabilities.schema.json',
}

class SchemaStore:
    def __init__(self, repo_root:Path):
        self.root=repo_root
        packaged=Path(__file__).resolve().parent/'resources'/'contracts'
        # Examiner independence: never validate a target with schemas supplied by that same target.
        # Target contracts are inspected separately by release/compatibility levels.
        self.v6=packaged/'v6'; self.v7=packaged/'v7'; self.v8=packaged/'v8'; self.v9=packaged/'v9'; self.v10=packaged/'v10'
        self.github=packaged/'github'
        self.target_schema_root=repo_root/'schemas'
        self._cache={}
    def _load(self,p:Path):
        key=str(p)
        if key not in self._cache:self._cache[key]=json.loads(p.read_text(encoding='utf-8'))
        return self._cache[key]
    def validate_v7(self,artifact:dict[str,Any]):
        typ=artifact.get('artifact_type'); fn=ARTIFACT_SCHEMAS.get(typ)
        if not fn:return False,[f'no v7 schema mapping for artifact_type={typ!r}']
        return self._validate(self._load(self.v7/fn),artifact)
    def validate_v8(self,artifact:dict[str,Any]):
        typ=artifact.get('artifact_type'); fn=V8_SCHEMAS.get(typ)
        if not fn:return False,[f'no v8 schema mapping for artifact_type={typ!r}']
        return self._validate(self._load(self.v8/fn),artifact)
    def validate_v9(self,artifact:dict[str,Any]):
        typ=artifact.get('artifact_type'); fn=V9_SCHEMAS.get(typ)
        if not fn:return False,[f'no v9 schema mapping for artifact_type={typ!r}']
        return self._validate(self._load(self.v9/fn),artifact)
    def validate_v10(self,artifact:dict[str,Any]):
        typ=artifact.get('artifact_type'); fn=V10_SCHEMAS.get(typ)
        if not fn:return False,[f'no v10 schema mapping for artifact_type={typ!r}']
        return self._validate(self._load(self.v10/fn),artifact)
    def validate_github_binding(self,artifact:dict[str,Any]):
        return self._validate(self._load(self.github/'kristal-github-binding.schema.json'),artifact)
    def validate_github_read_surface(self,artifact:dict[str,Any]):
        return self._validate(self._load(self.github/'kristal-github-read-surface.schema.json'),artifact)
    def validate_github_sync_manifest(self,artifact:dict[str,Any]):
        return self._validate(self._load(self.github/'kristal-github-sync-manifest.schema.json'),artifact)
    def validate_github_collection_index(self,artifact:dict[str,Any]):
        return self._validate(self._load(self.github/'kristal-github-collection-index.schema.json'),artifact)
    def validate_v6(self,artifact:dict[str,Any]):
        return self._validate(self._load(self.v6/'kristal-state.schema.json'),artifact)
    def validate_extension(self,ext:dict[str,Any]):
        return self._validate(self._load(self.v7/'kristal-v7-extension.schema.json'),ext)
    @staticmethod
    def _validate(schema,data):
        validator=jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker())
        errors=sorted(validator.iter_errors(data),key=lambda e:list(e.absolute_path))
        out=[]
        for e in errors:
            path='/'+'/'.join(str(x) for x in e.absolute_path) if e.absolute_path else '/'
            out.append(f'{path}: {e.message}')
        return not out,out
