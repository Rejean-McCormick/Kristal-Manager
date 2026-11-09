"""Current editorial decisions: product state, not historical approval."""
import json
from pathlib import Path

import pytest

from kristal_manager.editorial_state import assess_editorial_state
from kristal_manager.editorial_decisions import (
    set_decision, clear_decision, load_decisions, current_editorial_state,
    source_fingerprint,
)
from kristal_manager.review_progress import assess_review, matches_focus


def row(tmp_path):
    root = tmp_path / 'Kristal-Test'
    for rel in ('docs/00_INTENT_AND_SCOPE.md', 'docs/01_SEMANTIC_BOUNDARY.md',
                'docs/02_NATIVE_MODEL.md', 'canon/domain/record.json',
                'canon/state.index.json', 'sources/source-catalog.json'):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('model', encoding='utf-8')
    (root / 'kristal.workspace.json').write_text(json.dumps({'state_ref': 'urn:kristal:test:state'}), encoding='utf-8')
    (root / 'canon/state.index.json').write_text(json.dumps({
        'canonical_artifacts': [{'path': 'canon/domain/record.json'}]}), encoding='utf-8')
    return {'state_ref': 'urn:kristal:test:state', 'path': str(root), 'title': 'Test',
            'readiness': 'READY', 'priority': 'review', 'content_status': 'observed',
            'authoring_observation': {'status': 'OBSERVED', 'workspace_status': 'validated',
                                      'source_catalog': 'SCHEMA_SHAPE_OK'},
            'native_source_review': {'status': 'SOURCE_BYTES_MATCHED'},
            'semantic_enrichment': {'status': 'MATCHED_CURRENT_DESCRIPTORS'}}


def test_clean_editorial_state_is_not_framework_approval(tmp_path):
    sample = row(tmp_path)
    a = assess_editorial_state(sample)
    assert a['status'] == 'Ready'
    assert a['human_approved'] is False
    assert a['framework_qualification'] == 'NOT_ESTABLISHED'
    assert matches_focus(assess_review(sample), 'Editorial: Ready')


def test_four_states_do_not_confuse_suggestions_with_defects(tmp_path):
    sample = row(tmp_path)
    sample['semantic_enrichment']['prf_candidate'] = {'id': 'PRF-TEST'}
    assert assess_editorial_state(sample)['status'] == 'Not assessed'
    sample['authoring_observation']['source_catalog'] = 'EMPTY'
    assert assess_editorial_state(sample)['status'] == 'Needs work'
    sample['authoring_observation']['workspace_status'] = 'building'
    assert assess_editorial_state(sample)['status'] == 'Building'
    sample['readiness'] = 'BLOCKED'
    assert assess_editorial_state(sample)['status'] == 'Needs work'


def test_historical_suggestion_alone_is_not_current_defect(tmp_path):
    sample = row(tmp_path)
    sample['historical_unesco_attention'] = {'status': 'HISTORICAL'}
    assert assess_editorial_state(sample)['status'] == 'Ready'
    sample['editorial_unesco_review'] = {'status': 'AI_DRAFT_REVIEW_REQUIRED'}
    assert assess_editorial_state(sample)['status'] == 'Not assessed'


def test_one_current_note_is_replaced_and_fails_closed_on_source_change(tmp_path):
    sample = row(tmp_path)
    store = tmp_path / 'decisions.json'
    assert not store.exists()
    set_decision(sample, 'Needs work', 'Fix document scope', path=store)
    notes = load_decisions(store)
    assert len(notes) == 1
    assert current_editorial_state(sample, notes)['status'] == 'Needs work'
    set_decision(sample, 'Ready', path=store)
    notes = load_decisions(store)
    assert len(notes) == 1  # no accumulated historical ledger
    assert current_editorial_state(sample, notes)['status'] == 'Ready'
    (Path(sample['path']) / 'canon/domain/record.json').write_text('changed canon', encoding='utf-8')
    new = current_editorial_state(sample, notes)
    assert new['status'] == 'Not assessed' and new['outdated']
    clear_decision(sample, path=store)
    assert load_decisions(store) == {}


def test_never_mark_building_or_faulty_ready(tmp_path):
    sample = row(tmp_path)
    sample['authoring_observation']['workspace_status'] = 'building'
    with pytest.raises(ValueError): set_decision(sample, 'Ready', path=tmp_path/'d.json')
    sample['authoring_observation']['workspace_status'] = 'validated'
    sample['authoring_observation']['source_catalog'] = 'EMPTY'
    with pytest.raises(ValueError): set_decision(sample, 'Ready', path=tmp_path/'d.json')


def test_reject_symlinks_traversal_and_bad_existing_registry(tmp_path):
    sample = row(tmp_path)
    index = Path(sample['path']) / 'canon/state.index.json'
    index.write_text(json.dumps({'canonical_artifacts': [{'path': 'canon/../secret'}]}), encoding='utf-8')
    with pytest.raises(ValueError): source_fingerprint(sample)
    index.write_text(json.dumps({'canonical_artifacts': [{'path': 'canon/domain/record.json'}]}), encoding='utf-8')
    path = tmp_path / 'd.json'
    path.write_text('{"schema": "unknown", "decisions": {}}', encoding='utf-8')
    with pytest.raises(ValueError): set_decision(sample, 'Needs work', 'x', path=path)
    assert 'unknown' in path.read_text(encoding='utf-8')


def test_gui_column_profiles_show_new_state():
    from kristal_manager.column_views import PRESETS, PRESET_NAMES
    assert 'editorial_state' in PRESETS['manager']['Essential']
    assert 'editorial_state' in PRESETS['analysis']['Essential']
    assert 'editorial_state' in PRESETS['manager']['Review queue']
    assert 'editorial_state' in PRESETS['analysis']['Review queue']
    assert 'Review queue' in PRESET_NAMES
