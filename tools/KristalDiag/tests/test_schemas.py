import json
from pathlib import Path
from kristaldiag.schemas import SchemaStore,ARTIFACT_SCHEMAS
ROOT=Path(__file__).resolve().parents[1]
PAIRS={
 'kristall-manifest.example.json':'kristall_manifest','entity-registry.example.json':'kristall_entity_registry','property-registry.example.json':'kristall_property_registry',
 'assertion-registry.example.json':'kristall_assertion_registry','source-registry.example.json':'kristall_source_registry','assertion-family-registry.example.json':'kristall_assertion_family_registry',
 'mesh.example.json':'kristall_mesh','axis-registry.example.json':'kristall_axis_registry','projection-recipe.example.json':'kristall_projection_recipe','crystallization-record.example.json':'kristall_crystallization_record','resonance.example.json':'semantic_resonance_set'}

def test_v7_positive_vectors_validate():
    store=SchemaStore(ROOT)
    for fn,typ in PAIRS.items():
        data=json.loads((ROOT/'tck/v7'/fn).read_text(encoding='utf-8'))
        assert data['artifact_type']==typ
        ok,errs=store.validate_v7(data)
        assert ok,(fn,errs)

def test_v6_projection_and_extension_validate():
    store=SchemaStore(ROOT);d=json.loads((ROOT/'tck/v7/v6-compatible-projection.example.json').read_text())
    ok,errs=store.validate_v6(d);assert ok,errs
    ok,errs=store.validate_extension(d['extensions']['kristal_v7']);assert ok,errs
