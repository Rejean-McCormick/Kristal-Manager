"""Regressions: recover rather than infer classification; keep approval separate."""
from __future__ import annotations

import json
from pathlib import Path

from kristal_manager.qualification_history import (
    annotate_qualifications, display_ark_structure, display_declared,
    display_unesco_declaration, RECOVERY_PATH,
)
from kristal_manager.global_panel import format_chatgpt_summary


def _make_workspace(tmp_path, state='urn:kristal:accounting:state'):
    folder = tmp_path / 'Kristal-Accounting'
    folder.mkdir()
    (folder / 'kristal.workspace.json').write_text(json.dumps({
        'format': 'kristal.local-workspace/3.2.0',
        'state_ref': state,
        'status': 'building',
        'classification': {'primary_archetype': 'ARK-01', 'primary_usage': 'PRF-20',
                           'verification_status': 'AUTOMATED_CLASSIFICATION_REVIEW_REQUIRED',
                           'unesco_thesaurus': {'microthesauri': [{'code': '6.70'}]}},
        'subject': {'domain': 'accounting', 'orientation': 'economic event to ledger'},
        'native_model': {'kind': 'accounting_event_ledger_graph'},
    }), encoding='utf-8')
    return folder


def test_recovery_matches_127_unique_identity_records():
    obj = json.loads(RECOVERY_PATH.read_text(encoding='utf-8'))
    assert len(obj['entries']) == 127
    assert len({r['state_ref'] for r in obj['entries']}) == 127
    assert all(r.get('historical_structural_observation') for r in obj['entries'])
    assert all(r.get('historical_field_audit') for r in obj['entries'])
    assert all(r.get('historical_prf_batch') for r in obj['entries'])
    assert obj['no_automatic_approval'] is True


def test_live_metadata_overrides_historical_snapshot_without_claiming_approval(tmp_path):
    folder = _make_workspace(tmp_path)
    entry = {'path': str(folder), 'state_ref': 'urn:kristal:accounting:state',
             'title': 'Kristal-Accounting', 'priority': 'warning', 'operational_result': 'NOT_EVALUATED'}
    info = annotate_qualifications([entry], source=tmp_path)
    assert info['history_matched'] == 1
    assert info['live_metadata_matched'] == 1
    assert display_declared(entry, 'primary_archetype') == 'Semantic Reference'
    assert display_declared(entry, 'primary_usage') == 'Multi-Purpose Semantic Reference'
    assert display_unesco_declaration(entry) == 'Finance and trade'
    assert '(historical)' in display_ark_structure(entry)
    assert entry['qualification_evidence']['metadata']['status'] == 'building'
    assert entry['qualification_evidence']['human_approval_inferred'] is False
    assert entry['priority'] == 'warning'
    assert entry['operational_result'] == 'NOT_EVALUATED'


def test_identity_mismatch_is_not_silently_replaced_with_archive(tmp_path):
    folder = _make_workspace(tmp_path, state='urn:kristal:other:state')
    entry = {'path': str(folder), 'state_ref': 'urn:kristal:accounting:state'}
    totals = annotate_qualifications([entry], source=tmp_path)
    assert totals['identity_mismatches'] == 1
    assert display_declared(entry, 'primary_archetype') == 'Not declared'
    assert entry['qualification_evidence']['metadata_source'] == 'IDENTITY_MISMATCH_NO_FALLBACK'


def test_missing_live_workspace_keeps_archive_clearly_marked(tmp_path):
    entry = {'path': str(tmp_path / 'Kristal-Accounting'), 'state_ref': 'urn:kristal:accounting:state'}
    totals = annotate_qualifications([entry], source=tmp_path)
    assert totals['snapshot_only'] == 1
    assert display_declared(entry, 'primary_usage') == 'Multi-Purpose Semantic Reference (old snapshot)'
    assert 'old snapshot' in display_unesco_declaration(entry)


def test_no_history_does_not_infer_a_classification(tmp_path):
    folder = _make_workspace(tmp_path, state='urn:kristal:other:state')
    entry = {'path': str(folder), 'state_ref': 'urn:kristal:other:state'}
    totals = annotate_qualifications([entry], source=tmp_path)
    assert totals['missing_history'] == 1
    assert entry['qualification_evidence']['historical_arketype_structure'] is None
    assert display_declared(entry, 'primary_archetype') == 'Semantic Reference'
    assert display_ark_structure(entry) == 'Not assessed'


def test_chatgpt_export_separates_declared_and_automatically_proposed(tmp_path):
    folder = _make_workspace(tmp_path)
    entry = {'title': 'Kristal-Accounting', 'path': str(folder), 'state_ref': 'urn:kristal:accounting:state',
             'priority': 'review', 'readiness': 'READY', 'content_status': 'observed', 'operational_result': 'NOT_EVALUATED',
             'proposed_arketype': None, 'proposed_unesco': None, 'proposed_unesco_domain': None,
             'keywords': [], 'problems': [], 'human_review': []}
    totals = annotate_qualifications([entry], source=tmp_path)
    result = {'counts': {**totals, 'kristals':1}, 'entries':[entry]}
    text = format_chatgpt_summary(result)
    assert 'declared_ARK=Semantic Reference' in text
    assert 'declared_PRF=Multi-Purpose Semantic Reference' in text
    assert 'ARK_new_proposal=none' in text
    assert 'ARK_structural_observation=' in text
    assert 'human approvals' in text.lower() or 'not human approvals' in text.lower()


def test_global_analysis_table_shows_declared_columns(tmp_path):
    import os
    import pytest
    if os.name != 'nt' and not os.environ.get('DISPLAY'):
        pytest.skip('Tk requires a display')
    import tkinter as tk
    from kristal_manager.global_panel import GlobalAnalysisPanel
    folder = _make_workspace(tmp_path)
    entry = {'title':'Kristal-Accounting', 'path':str(folder), 'state_ref':'urn:kristal:accounting:state',
             'readiness':'READY','priority':'review','content_status':'observed','keywords':['accounting'],
             'proposed_arketype':None,'proposed_unesco':None,'proposed_unesco_domain':None,
             'operational_result':'NOT_EVALUATED','problems':[],'human_review':[]}
    annotate_qualifications([entry], source=tmp_path)
    root = tk.Tk()
    root.withdraw()
    root.path_var = tk.StringVar(value=str(tmp_path))
    root._asset_path = lambda name: tmp_path / name
    root.open_batch_rename = lambda: None
    try:
        panel = GlobalAnalysisPanel(root)
        try:
            report = {'entries':[entry], 'counts':{'kristals':1,'blocker':0,'warning':0,'review':1,
                   'native_contract_observed':0,'registered_review_matched':0,
                   'arketype_candidates':0,'unesco_micro_candidates':0,'historical_qualifications_matched':1}}
            panel.render_result({'global_report':report,'report_directory':str(tmp_path)},restored=False)
            col = tuple(panel.table['columns'])
            assert 'declared_ark' in col and 'declared_prf' in col
            values = tuple(panel.table.item(panel.table.get_children()[0], 'values'))
            assert values[col.index('declared_ark')] == 'Semantic Reference'
            assert values[col.index('declared_prf')] == 'Multi-Purpose Semantic Reference'
            assert values[col.index('declared_unesco')] == 'Finance and trade'
            assert values[col.index('new_suggestions')] == 'No new proposals'
        finally:
            panel.destroy()
    finally:
        root.destroy()
