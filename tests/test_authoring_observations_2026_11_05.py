"""Regression tests: authoring status is never mistaken for C1/C2/C3."""
import csv
import json
from pathlib import Path

from kristal_manager.authoring_observations import (inspect_authoring, annotate_authoring,
    display_authoring_status, display_source_catalog)
from kristal_manager.review_progress import assess_review, matches_focus, export_review_queue
from kristal_manager.native_evidence import load_native_catalog, inspect_native_source


def workspace(tmp_path, *, state='urn:kristal:test:state', status='building', sources=None):
    root = tmp_path / 'Kristal-Test'
    root.mkdir()
    (root/'kristal.workspace.json').write_text(json.dumps({'state_ref': state, 'status': status}))
    (root/'sources').mkdir()
    (root/'sources/source-catalog.json').write_text(json.dumps({
        'format':'kristal.source-catalog/2.0.0', 'sources':sources if sources is not None else []}))
    (root/'validation').mkdir()
    (root/'validation/AI_RELEASE_GATE.md').write_text('Draft only, not an authorization.')
    (root/'derived/authoring-review').mkdir(parents=True)
    (root/'derived/authoring-review/AI_EDITORIAL_DOSSIER.json').write_text(json.dumps({
        'schema':'kristal.noncanonical-ai-authoring-review/1.0',
        'review_status':'AI_DRAFT_NOT_APPROVED', 'identity':{'state_ref':state}}))
    return {'state_ref':state,'readiness':'READY','path':str(root),
            'qualification_evidence':{'metadata_source':'LIVE_WORKSPACE'},
            'native_source_review':{'status':'SOURCE_BYTES_MATCHED'},
            'semantic_enrichment':{'status':'MATCHED_CURRENT_DESCRIPTORS'}}


def test_building_and_empty_catalog_are_never_qualified(tmp_path):
    row = workspace(tmp_path)
    totals=annotate_authoring([row])
    assert totals['building']==totals['source_catalog_empty']==1
    assert totals['release_gate_notes']==totals['editorial_drafts']==1
    assert row['authoring_observation']['human_approved'] is False
    assert 'not qualified' in display_authoring_status(row)
    assert '0 sources' in display_source_catalog(row)
    stage=assess_review(row)
    assert stage['stage']=='Source catalogue review'
    assert matches_focus(stage, 'Source catalogue issues')
    assert matches_focus(stage, 'Authoring in progress')
    assert stage['qualification']=='NOT_ESTABLISHED'


def test_source_shape_and_identity_are_checked(tmp_path):
    row=workspace(tmp_path, status='validated', sources=[{
        'id':'local:one','title':'An old local item','kind':'internal_document',
        'locator':{'type':'embedded_editorial_record','path':'sources/source-catalog.json'}}])
    x=inspect_authoring(row)
    assert x['source_catalog']=='SCHEMA_SHAPE_OK' and x['source_count']==1
    assert x['workspace_status']=='validated'
    assert x['framework_qualification']=='NOT_ESTABLISHED'
    p=Path(row['path'])/'sources/source-catalog.json'
    j=json.loads(p.read_text());del j['sources'][0]['locator'];p.write_text(json.dumps(j))
    assert inspect_authoring(row)['source_catalog']=='SCHEMA_ISSUE_OR_UNAVAILABLE'
    row['state_ref']='urn:kristal:other:state'
    assert inspect_authoring(row)['status']=='IDENTITY_MISMATCH'


def test_export_has_authoring_fields_and_does_not_approve(tmp_path):
    row=workspace(tmp_path)
    annotate_authoring([row])
    file=export_review_queue(tmp_path/'review.csv',[row],source_root=Path(row['path']))
    with file.open(encoding='utf-8-sig',newline='') as f:
        record=list(csv.DictReader(f))[0]
    assert record['authoring_status'].startswith('Building')
    assert record['source_count']=='0'
    assert record['qualification']=='NOT_ESTABLISHED'


def test_metadata_only_change_is_separate_from_native_documents(tmp_path):
    # The archived catalogue is read without granting any authority. A mismatch
    # in the current workspace metadata must not be labeled as a native change.
    catalog=load_native_catalog()
    ref='urn:kristal:state:k-monetary-system'
    row={'state_ref':ref, 'path':str(tmp_path),
         'qualification_evidence':{'metadata_source':'LIVE_WORKSPACE'}}
    info=inspect_native_source(row,catalog)
    assert info['status']=='SOURCES_UNAVAILABLE'
    stage=assess_review({'readiness':'READY',
        'native_source_review':{'status':'WORKSPACE_METADATA_CHANGED'},
        'semantic_enrichment':{'status':'MATCHED_CURRENT_DESCRIPTORS'}})
    assert stage['stage']=='Metadata review outdated'
    assert matches_focus(stage,'Workspace metadata updated')
    assert not matches_focus(stage,'Source evidence changed')


def test_view_profiles_expose_authoring_in_both_tables():
    from kristal_manager.column_views import PRESETS
    for surface in ('manager','analysis'):
        assert 'authoring_status' in PRESETS[surface]['Essential']
        assert 'source_catalog' in PRESETS[surface]['Review queue']
        assert 'source_catalog' in PRESETS[surface]['Diagnostics']


def test_source_catalog_fields_are_visible_in_both_windows():
    # Inspecting table design is a pure layout test; a GUI smoke test runs under
    # a virtual display in the local suite.
    from kristal_manager import gui, global_panel
    assert hasattr(gui, 'display_authoring_status')
    assert hasattr(global_panel, 'display_source_catalog')


def test_source_catalog_refuses_symlink(tmp_path):
    row=workspace(tmp_path)
    cat=Path(row['path'])/'sources/source-catalog.json'
    cat.unlink()
    target=tmp_path/'external-source-catalog.json'
    target.write_text(json.dumps({'format':'kristal.source-catalog/2.0.0','sources':[]}))
    cat.symlink_to(target)
    assert inspect_authoring(row)['source_catalog']=='SCHEMA_ISSUE_OR_UNAVAILABLE'
